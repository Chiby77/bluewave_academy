"""
pdf_generator.py — Bluewave Academy
=====================================
Professional, production-grade PDF exam report generator.
Uses the low-level ReportLab canvas API for absolute pixel control.

Exports
-------
    generate_exam_report(student, exam, submission, parsed_results)
        Primary function for Examinator (classroom assignment) reports.

    generate_student_report(exam_attempt)
        Legacy wrapper kept for compatibility with admin_views.py.

Author  : Tinodaishe Chibi — Chief Examiner & Director, Bluewave Academy
Palette : Corporate Blue  #0B3D91  |  Accent Cyan  #00AEEF
          Success Green   #27AE60  |  Amber        #F39C12
          Danger Red      #E74C3C  |  Light BG     #F0F6FF
"""

from io import BytesIO
from datetime import datetime
import math
import os

# ---------------------------------------------------------------------------
# ReportLab imports — guarded so Django can still import the module even
# when ReportLab is not yet installed (migrations, collectstatic, etc.).
# ---------------------------------------------------------------------------
try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# ---------------------------------------------------------------------------
# Brand constants
# ---------------------------------------------------------------------------
BW_BLUE       = colors.HexColor("#0B3D91")   # Primary corporate blue
BW_CYAN       = colors.HexColor("#00AEEF")   # Accent cyan
BW_DARK       = colors.HexColor("#0A1F44")   # Near-black navy for text
BW_LIGHT_BG   = colors.HexColor("#EEF4FF")   # Section background tint
BW_CARD_BG    = colors.HexColor("#F7FAFF")   # Card / row alternating fill
BW_RULE       = colors.HexColor("#D0DDEF")   # Divider lines
BW_WHITE      = colors.white
COLOR_PASS    = colors.HexColor("#27AE60")   # Green — pass
COLOR_AMBER   = colors.HexColor("#F39C12")   # Amber — borderline
COLOR_FAIL    = colors.HexColor("#E74C3C")   # Red — fail
COLOR_FDBK_BG = colors.HexColor("#F0F9FF")   # Feedback block tint
COLOR_FDBK_BD = colors.HexColor("#00AEEF")   # Feedback left-border

# Code / answer panel styling — answers are predominantly source code, so
# they are rendered in a monospace "code block" rather than reflowed prose.
CODE_FONT      = "Courier"
CODE_FONT_SIZE = 7.5
CODE_LINE_H    = 10
CODE_MAX_CHARS = 42                          # safe width at CODE_FONT_SIZE
CODE_BOX_BG    = colors.HexColor("#FFFFFF")  # code panel background

# ---------------------------------------------------------------------------
# Page geometry (A4)
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = A4          # 595.28 x 841.89 pts
MARGIN_L  = 40               # Left margin  (pts)
MARGIN_R  = 40               # Right margin (pts)
MARGIN_T  = 50               # Top margin for body content
MARGIN_B  = 50               # Bottom margin before footer area
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R   # 515.28 pts usable width

HEADER_H   = 90              # Header strip height
FOOTER_H   = 28              # Footer strip height
BODY_TOP   = PAGE_H - HEADER_H - 10   # Y where body content starts
BODY_BTM   = FOOTER_H + 10            # Y where body content ends


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _score_color(percentage: float):
    """Return the brand color matching a score threshold."""
    if percentage >= 70:
        return COLOR_PASS
    elif percentage >= 50:
        return COLOR_AMBER
    return COLOR_FAIL


def _set_font(c, name="Helvetica", size=10):
    c.setFont(name, size)


def _wrap_text(text: str, max_chars: int = 90) -> list:
    """
    Naive word-wrap: split text into lines no longer than max_chars.
    Returns a list of strings.
    """
    words = str(text).split()
    lines, current = [], ""
    for word in words:
        probe = (current + " " + word).strip()
        if len(probe) <= max_chars:
            current = probe
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _wrap_code_lines(text: str, max_chars: int = CODE_MAX_CHARS) -> list:
    """
    Word-wrap text for code/answer display while PRESERVING the source's
    original line breaks.

    THE BUG THIS FIXES: _wrap_text() (above) calls str.split() with no
    argument, which treats '\\n' as just more whitespace and collapses it.
    That's fine for prose, but student/correct *code* answers are
    multi-line — collapsing newlines jams several statements onto one
    line (e.g. "...Python.\") print(f\"Hello...") before the line is
    re-wrapped at a fixed width, which is what made the answer columns in
    the generated report look garbled/misaligned.

    This variant treats every '\\n' in the source as a hard line break and
    only soft-wraps an individual line if it's wider than the column,
    hard-breaking any single overlong token (e.g. a long string literal)
    so it never overflows the panel.
    """
    raw_lines = str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = []
    for raw in raw_lines:
        if raw.strip() == "":
            out.append("")
            continue
        words = raw.split(" ")
        current = ""
        for word in words:
            probe = f"{current} {word}".strip() if current else word
            if len(probe) <= max_chars:
                current = probe
                continue
            if current:
                out.append(current)
                current = ""
            while len(word) > max_chars:      # hard-wrap an overlong token
                out.append(word[:max_chars])
                word = word[max_chars:]
            current = word
        if current:
            out.append(current)
    return out or [""]


def _draw_multiline(c, text: str, x: float, y: float,
                    font="Helvetica", size=9, line_height=13,
                    max_chars=88, color=None) -> float:
    """
    Draw wrapped text starting at (x, y), moving downward.
    Returns the new Y position after the last line.
    """
    if color:
        c.setFillColor(color)
    _set_font(c, font, size)
    for line in _wrap_text(text, max_chars):
        c.drawString(x, y, line)
        y -= line_height
    return y


def _check_page_break(c, y: float, needed: float,
                      draw_header_fn, draw_footer_fn,
                      page_state: dict) -> float:
    """
    If there is not enough vertical space remaining, finalize the current
    page and start a new one.  Returns the updated Y position.
    """
    if y - needed < BODY_BTM:
        draw_footer_fn(c, page_state)
        c.showPage()
        page_state["page_num"] += 1
        draw_header_fn(c, page_state)
        y = BODY_TOP - 10
    return y


# ---------------------------------------------------------------------------
# Geometric icon primitives  (NO emojis — pure canvas paths)
# ---------------------------------------------------------------------------

def _draw_checkmark(c, cx: float, cy: float, size: float = 7,
                    color=COLOR_PASS):
    """Draw a clean geometric checkmark tick inside a filled circle."""
    c.setFillColor(color)
    c.circle(cx, cy, size, fill=1, stroke=0)
    # White tick drawn with lines
    c.setStrokeColor(BW_WHITE)
    c.setLineWidth(1.5)
    p = c.beginPath()
    p.moveTo(cx - size * 0.45, cy)
    p.lineTo(cx - size * 0.1,  cy - size * 0.35)
    p.lineTo(cx + size * 0.5,  cy + size * 0.4)
    c.drawPath(p, stroke=1, fill=0)


def _draw_xmark(c, cx: float, cy: float, size: float = 7,
                color=COLOR_FAIL):
    """Draw a clean X mark inside a filled circle."""
    c.setFillColor(color)
    c.circle(cx, cy, size, fill=1, stroke=0)
    c.setStrokeColor(BW_WHITE)
    c.setLineWidth(1.5)
    off = size * 0.4
    p = c.beginPath()
    p.moveTo(cx - off, cy - off)
    p.lineTo(cx + off, cy + off)
    c.drawPath(p, stroke=1, fill=0)
    p2 = c.beginPath()
    p2.moveTo(cx + off, cy - off)
    p2.lineTo(cx - off, cy + off)
    c.drawPath(p2, stroke=1, fill=0)


def _draw_partial_mark(c, cx: float, cy: float, size: float = 7):
    """Draw an amber dash-circle for partial credit."""
    c.setFillColor(COLOR_AMBER)
    c.circle(cx, cy, size, fill=1, stroke=0)
    c.setStrokeColor(BW_WHITE)
    c.setLineWidth(2)
    p = c.beginPath()
    p.moveTo(cx - size * 0.45, cy)
    p.lineTo(cx + size * 0.45, cy)
    c.drawPath(p, stroke=1, fill=0)


def _draw_info_icon(c, cx: float, cy: float, size: float = 7):
    """Draw a blue information 'i' circle for AI feedback label."""
    c.setFillColor(BW_CYAN)
    c.circle(cx, cy, size, fill=1, stroke=0)
    _set_font(c, "Helvetica-Bold", size * 1.4)
    c.setFillColor(BW_WHITE)
    c.drawCentredString(cx, cy - size * 0.45, "i")


# ---------------------------------------------------------------------------
# Watermark
# ---------------------------------------------------------------------------

def _draw_watermark(c, text: str = "BLUEWAVE ACADEMY"):
    """
    Render a large, diagonal, semi-transparent watermark across the page.
    Called once per page before any other content.
    """
    c.saveState()
    c.setFillColor(colors.Color(0.8, 0.88, 0.96, alpha=0.18))
    _set_font(c, "Helvetica-Bold", 52)
    c.translate(PAGE_W / 2, PAGE_H / 2)
    c.rotate(42)
    c.drawCentredString(0, 0, text)
    c.restoreState()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def _draw_header(c, page_state: dict):
    """
    Full-width corporate header strip.

    Layout
    ------
    [ Blue bar | BLUEWAVE ACADEMY + tagline ] [ student / exam meta ]
    """
    # ------ Solid blue header background ------
    c.setFillColor(BW_BLUE)
    c.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)

    # Cyan accent stripe at the very top
    c.setFillColor(BW_CYAN)
    c.rect(0, PAGE_H - 4, PAGE_W, 4, fill=1, stroke=0)

    # ------ Logo placeholder (left) ------
    logo_x, logo_y = MARGIN_L, PAGE_H - HEADER_H + 14
    logo_path = page_state.get("logo_path")
    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, logo_x, logo_y, width=54, height=54,
                        mask="auto", preserveAspectRatio=True)
        except Exception:
            _draw_logo_placeholder(c, logo_x, logo_y)
    else:
        _draw_logo_placeholder(c, logo_x, logo_y)

    # ------ Academy name & tagline ------
    text_x = MARGIN_L + 64
    c.setFillColor(BW_WHITE)
    _set_font(c, "Helvetica-Bold", 17)
    c.drawString(text_x, PAGE_H - 30, "BLUEWAVE ACADEMY")

    c.setFillColor(BW_CYAN)
    _set_font(c, "Helvetica-Oblique", 8)
    c.drawString(text_x, PAGE_H - 42, "Excellence in Digital Education  |  bluewaveacademy.co.zw")

    # Thin horizontal rule under tagline
    c.setStrokeColor(BW_CYAN)
    c.setLineWidth(0.5)
    c.line(text_x, PAGE_H - 47, text_x + 200, PAGE_H - 47)

    # Report type label
    c.setFillColor(BW_WHITE)
    _set_font(c, "Helvetica-Bold", 10)
    report_title = page_state.get("report_title", "EXAM PERFORMANCE REPORT")
    c.drawString(text_x, PAGE_H - 60, report_title)

    # ------ Right-hand meta block ------
    rx = PAGE_W - MARGIN_R
    c.setFillColor(BW_WHITE)

    _set_font(c, "Helvetica-Bold", 8)
    c.drawRightString(rx, PAGE_H - 26, page_state.get("student_name", ""))

    c.setFillColor(BW_CYAN)
    _set_font(c, "Helvetica", 7.5)
    c.drawRightString(rx, PAGE_H - 38, page_state.get("student_id", ""))

    c.setFillColor(BW_WHITE)
    _set_font(c, "Helvetica", 7.5)
    c.drawRightString(rx, PAGE_H - 50, page_state.get("exam_title", ""))
    c.drawRightString(rx, PAGE_H - 62, page_state.get("exam_date", ""))

    # Page number badge
    c.setFillColor(BW_CYAN)
    badge_x = PAGE_W - MARGIN_R - 40
    c.roundRect(badge_x, PAGE_H - HEADER_H + 8, 50, 18, 4, fill=1, stroke=0)
    c.setFillColor(BW_WHITE)
    _set_font(c, "Helvetica-Bold", 7.5)
    c.drawCentredString(badge_x + 25, PAGE_H - HEADER_H + 14,
                        f"Page {page_state['page_num']}")


def _draw_logo_placeholder(c, x: float, y: float):
    """Draw a geometric BW shield logo when no image is available."""
    c.setFillColor(BW_CYAN)
    c.roundRect(x, y, 50, 50, 6, fill=1, stroke=0)
    c.setFillColor(BW_WHITE)
    _set_font(c, "Helvetica-Bold", 16)
    c.drawCentredString(x + 25, y + 18, "BW")
    _set_font(c, "Helvetica", 7)
    c.drawCentredString(x + 25, y + 8, "ACADEMY")


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

def _draw_footer(c, page_state: dict):
    """
    Full-width footer: generation timestamp | page | confidentiality notice.
    """
    # Background strip
    c.setFillColor(BW_BLUE)
    c.rect(0, 0, PAGE_W, FOOTER_H, fill=1, stroke=0)

    # Cyan rule on top of footer
    c.setFillColor(BW_CYAN)
    c.rect(0, FOOTER_H, PAGE_W, 2, fill=1, stroke=0)

    ts = page_state.get("generated_at",
                        datetime.now().strftime("%d %b %Y  %H:%M:%S"))
    c.setFillColor(BW_WHITE)
    _set_font(c, "Helvetica", 6.5)
    c.drawString(MARGIN_L, 10,
                 f"Generated: {ts}   |   Chief Examiner: Tinodaishe Chibi   |   "
                 f"Director, Bluewave Academy")
    c.drawRightString(PAGE_W - MARGIN_R, 10,
                      f"CONFIDENTIAL  |  Page {page_state['page_num']}")


# ---------------------------------------------------------------------------
# Score donut ring  (Page 1 — hero visual)
# ---------------------------------------------------------------------------

def _draw_donut_ring(c, cx: float, cy: float, percentage: float,
                     outer_r: float = 52, inner_r: float = 35):
    """
    Draw a color-coded donut ring representing the score percentage.

    The filled arc spans from 90 degrees (12 o'clock) clockwise by the
    proportion corresponding to the score.  The center shows the pct text.

    Parameters
    ----------
    cx, cy      : Centre coordinates
    percentage  : 0-100 float
    outer_r     : Outer radius of the ring
    inner_r     : Inner (hole) radius — creates the donut effect
    """
    score_color = _score_color(percentage)

    # ------ Track (grey background arc — full 360) ------
    c.setFillColor(colors.HexColor("#DDE6F0"))
    # Draw full disc then cut inner circle to fake a ring track
    c.circle(cx, cy, outer_r, fill=1, stroke=0)
    c.setFillColor(BW_WHITE)
    c.circle(cx, cy, inner_r, fill=1, stroke=0)

    # ------ Score arc ------
    if percentage > 0:
        # ReportLab arc: start/end in degrees, measured CCW from East (0=3 o'clock)
        # We want to start at North (90) and sweep clockwise.
        # Clockwise in ReportLab means decreasing degrees.
        sweep = (percentage / 100) * 360
        start_angle = 90
        end_angle   = 90 - sweep   # clockwise

        # Draw as a pie wedge then cut the center
        c.setFillColor(score_color)
        c.wedge(cx - outer_r, cy - outer_r,
                cx + outer_r, cy + outer_r,
                end_angle, sweep,
                fill=1, stroke=0)

        # White inner disc to create donut hole
        c.setFillColor(BW_WHITE)
        c.circle(cx, cy, inner_r, fill=1, stroke=0)

    # ------ Thin border ring ------
    c.setStrokeColor(score_color)
    c.setLineWidth(1.8)
    c.circle(cx, cy, outer_r, fill=0, stroke=1)

    # ------ Centre percentage text ------
    c.setFillColor(score_color)
    _set_font(c, "Helvetica-Bold", 18)
    c.drawCentredString(cx, cy + 5, f"{percentage:.1f}%")

    _set_font(c, "Helvetica", 7)
    c.setFillColor(BW_DARK)
    c.drawCentredString(cx, cy - 8, "SCORE")

    # ------ Label below ring ------
    label = "PASS" if percentage >= 50 else "FAIL"
    c.setFillColor(score_color)
    c.roundRect(cx - 22, cy - outer_r - 18, 44, 14, 4, fill=1, stroke=0)
    c.setFillColor(BW_WHITE)
    _set_font(c, "Helvetica-Bold", 7.5)
    c.drawCentredString(cx, cy - outer_r - 8, label)


# ---------------------------------------------------------------------------
# First-page summary block (student/exam metadata + donut)
# ---------------------------------------------------------------------------

def _draw_summary_block(c, y: float, student, exam_obj,
                        submission, percentage: float) -> float:
    """
    Draw the top-of-first-page summary card.

    Returns the Y position after the block.
    """
    # Section heading bar
    y = _draw_section_heading(c, y, "CANDIDATE & ASSESSMENT SUMMARY")

    card_top = y
    card_h   = 130

    # Card background
    c.setFillColor(BW_LIGHT_BG)
    c.roundRect(MARGIN_L, card_top - card_h, CONTENT_W, card_h, 6,
                fill=1, stroke=0)

    # Subtle card border
    c.setStrokeColor(BW_RULE)
    c.setLineWidth(0.8)
    c.roundRect(MARGIN_L, card_top - card_h, CONTENT_W, card_h, 6,
                fill=0, stroke=1)

    # ------ Donut ring (right side) ------
    donut_cx = PAGE_W - MARGIN_R - 72
    donut_cy = card_top - card_h / 2 + 6
    _draw_donut_ring(c, donut_cx, donut_cy, percentage)

    # ------ Left meta columns ------
    col1_x = MARGIN_L + 16
    col2_x = MARGIN_L + CONTENT_W * 0.42

    # Helper: draw a labeled field
    def meta_field(label, value, x, fy):
        c.setFillColor(BW_CYAN)
        _set_font(c, "Helvetica-Bold", 7)
        c.drawString(x, fy, label.upper())
        c.setFillColor(BW_DARK)
        _set_font(c, "Helvetica", 9.5)
        c.drawString(x, fy - 12, str(value)[:55])
        return fy - 26

    ly = card_top - 18
    ly = meta_field("Candidate Name",
                    getattr(student, "get_full_name", lambda: str(student))(),
                    col1_x, ly)
    ly = meta_field("Student ID",
                    getattr(student, "student_id", "—") or "—",
                    col1_x, ly)
    meta_field("School / Institution",
               getattr(student, "school", "—") or "—",
               col1_x, ly)

    ry = card_top - 18
    # exam_obj can be Exam or Assignment — use title attr
    ry = meta_field("Assessment Title",
                    getattr(exam_obj, "title", str(exam_obj))[:55],
                    col2_x, ry)
    # Score
    score_val = getattr(submission, "get_score", lambda: None)() or 0
    total     = getattr(exam_obj, "total_marks", 100) or 100
    ry = meta_field("Score Achieved",
                    f"{score_val} / {total}",
                    col2_x, ry)
    sub_date  = getattr(submission, "submitted_at",
                        getattr(submission, "created_at", None))
    meta_field("Submission Date",
               sub_date.strftime("%d %B %Y  %H:%M") if sub_date else "—",
               col2_x, ry)

    return card_top - card_h - 18


# ---------------------------------------------------------------------------
# Section heading helper
# ---------------------------------------------------------------------------

def _draw_section_heading(c, y: float, title: str,
                          icon_draw_fn=None) -> float:
    """
    Draw a solid blue heading bar.  Returns new Y (below the bar).
    """
    bar_h = 20
    c.setFillColor(BW_BLUE)
    c.roundRect(MARGIN_L, y - bar_h, CONTENT_W, bar_h, 4, fill=1, stroke=0)

    # Cyan left accent
    c.setFillColor(BW_CYAN)
    c.rect(MARGIN_L, y - bar_h, 5, bar_h, fill=1, stroke=0)

    c.setFillColor(BW_WHITE)
    _set_font(c, "Helvetica-Bold", 9)
    c.drawString(MARGIN_L + 12, y - bar_h + 6, title)

    return y - bar_h - 8


# ---------------------------------------------------------------------------
# Performance stats strip
# ---------------------------------------------------------------------------

def _draw_stats_strip(c, y: float, submission, exam_obj,
                      percentage: float) -> float:
    """
    Draw a row of three stat boxes: Marks | Time | Status.
    Returns updated Y.
    """
    y = _draw_section_heading(c, y, "PERFORMANCE METRICS")

    box_w = (CONTENT_W - 20) / 3
    box_h = 52
    gap   = 10
    bx    = MARGIN_L

    score_val = getattr(submission, "get_score", lambda: None)() or 0
    total     = getattr(exam_obj, "total_marks", 100) or 100
    passing   = getattr(exam_obj, "passing_marks", 50) or 50

    # Time taken
    time_secs = getattr(submission, "time_taken_seconds", None)
    if time_secs:
        mins = int(time_secs) // 60
        secs = int(time_secs) % 60
        time_str = f"{mins}m {secs:02d}s"
    else:
        dur = getattr(exam_obj, "duration_minutes",
                      getattr(exam_obj, "duration", None))
        time_str = f"{dur} min limit" if dur else "—"

    status_text  = "PASS" if percentage >= (passing / total * 100) else "FAIL"
    status_color = COLOR_PASS if status_text == "PASS" else COLOR_FAIL

    metrics = [
        ("Marks Achieved",  f"{score_val} / {total}", BW_BLUE),
        ("Time Taken",      time_str,                  BW_CYAN),
        ("Final Result",    status_text,               status_color),
    ]

    for label, value, accent in metrics:
        # Box background
        c.setFillColor(BW_CARD_BG)
        c.roundRect(bx, y - box_h, box_w, box_h, 5, fill=1, stroke=0)

        # Left accent strip
        c.setFillColor(accent)
        c.rect(bx, y - box_h, 4, box_h, fill=1, stroke=0)

        # Label
        c.setFillColor(colors.HexColor("#7A8FAF"))
        _set_font(c, "Helvetica", 7)
        c.drawString(bx + 10, y - 16, label.upper())

        # Value
        c.setFillColor(accent)
        _set_font(c, "Helvetica-Bold", 16)
        c.drawString(bx + 10, y - 38, str(value))

        bx += box_w + gap

    return y - box_h - 14


# ---------------------------------------------------------------------------
# AI feedback block
# ---------------------------------------------------------------------------

def _draw_feedback_block(c, y: float, label: str,
                         text: str, page_state: dict,
                         draw_header_fn, draw_footer_fn) -> float:
    """
    Draw a tinted block with a cyan left-border containing AI feedback text.
    Handles multi-line wrapping and page breaks automatically.
    Returns updated Y.
    """
    if not text or not text.strip():
        return y

    lines      = _wrap_text(text, max_chars=86)
    line_h     = 12
    pad_top    = 14
    pad_btm    = 10
    block_h    = pad_top + len(lines) * line_h + pad_btm

    # Page-break check
    y = _check_page_break(c, y, block_h + 10,
                          draw_header_fn, draw_footer_fn, page_state)

    # Background rect
    c.setFillColor(COLOR_FDBK_BG)
    c.roundRect(MARGIN_L, y - block_h, CONTENT_W, block_h, 4, fill=1, stroke=0)

    # Left accent border
    c.setFillColor(COLOR_FDBK_BD)
    c.rect(MARGIN_L, y - block_h, 4, block_h, fill=1, stroke=0)

    # Info icon + label
    _draw_info_icon(c, MARGIN_L + 16, y - 9, size=6)
    c.setFillColor(BW_CYAN)
    _set_font(c, "Helvetica-Bold", 7.5)
    c.drawString(MARGIN_L + 26, y - 12, label.upper())

    # Feedback text lines
    ty = y - pad_top - 4
    c.setFillColor(BW_DARK)
    _set_font(c, "Helvetica-Oblique", 8)
    for line in lines:
        c.drawString(MARGIN_L + 12, ty, line)
        ty -= line_h

    return y - block_h - 8


# ---------------------------------------------------------------------------
# Question-by-question breakdown
# ---------------------------------------------------------------------------

def _draw_question_breakdown(c, y: float, parsed_results: list,
                              page_state: dict,
                              draw_header_fn, draw_footer_fn) -> float:
    """
    Render each question item with:
      - Question number badge + question text
      - Student answer  vs  Correct answer (side by side)
      - Correct / Incorrect / Partial icon
      - AI feedback block (tinted, left-bordered)

    Parameters
    ----------
    parsed_results : list of dicts, each with keys:
        question_text   str   — the question
        student_answer  str   — what the student wrote
        correct_answer  str   — the expected answer
        is_correct      bool  — grading result (None = partial)
        marks_obtained  float — marks for this item
        total_marks     float — max marks for this item
        ai_feedback     str   — Groq-generated feedback (may be empty)
        question_type   str   — 'mcq'|'essay'|'code'|...
        question_num    int   — display number
    """
    y = _draw_section_heading(c, y, "DETAILED ANSWER BREAKDOWN")

    for idx, item in enumerate(parsed_results):
        q_num    = item.get("question_num", idx + 1)
        q_text   = str(item.get("question_text", ""))
        s_ans    = str(item.get("student_answer", "—"))
        c_ans    = str(item.get("correct_answer", "—"))
        is_corr  = item.get("is_correct")        # True / False / None
        marks_got= float(item.get("marks_obtained", 0))
        marks_tot= float(item.get("total_marks", 1))
        feedback = str(item.get("ai_feedback", ""))
        q_type   = str(item.get("question_type", "")).upper()

        result_color = (COLOR_PASS if is_corr is True else
                        (COLOR_FAIL if is_corr is False else COLOR_AMBER))

        # ---- Estimate height needed for this card ----
        # NOTE: these constants mirror the exact drawing geometry below
        # (header bar + code panel + paddings) so the card background is
        # always tall enough for what actually gets drawn inside it —
        # previously the answer text could run past the card/header
        # boundary because the two weren't kept in sync.
        q_lines  = _wrap_text(q_text,   max_chars=82)
        sa_lines = _wrap_code_lines(s_ans)
        ca_lines = _wrap_code_lines(c_ans)
        fb_lines = _wrap_text(feedback, max_chars=86) if feedback.strip() else []

        ans_rows   = max(len(sa_lines), len(ca_lines))
        code_box_h = ans_rows * CODE_LINE_H + 16     # 8pt top/bottom padding

        card_h = 66 + len(q_lines) * 12 + code_box_h + 6
        if fb_lines:
            card_h += 28 + len(fb_lines) * 12

        # Page break if needed
        y = _check_page_break(c, y, card_h + 10,
                              draw_header_fn, draw_footer_fn, page_state)

        # ---- Card background (alternating shade) ----
        bg = BW_LIGHT_BG if idx % 2 == 0 else BW_CARD_BG
        c.setFillColor(bg)
        c.roundRect(MARGIN_L, y - card_h, CONTENT_W, card_h, 5, fill=1, stroke=0)
        c.setStrokeColor(BW_RULE)
        c.setLineWidth(0.5)
        c.roundRect(MARGIN_L, y - card_h, CONTENT_W, card_h, 5, fill=0, stroke=1)

        # ---- Question number badge ----
        badge_x = MARGIN_L + 8
        badge_y = y - 15
        c.setFillColor(BW_BLUE)
        c.roundRect(badge_x, badge_y - 8, 26, 16, 3, fill=1, stroke=0)
        c.setFillColor(BW_WHITE)
        _set_font(c, "Helvetica-Bold", 8)
        c.drawCentredString(badge_x + 13, badge_y - 2, f"Q{q_num}")

        # Question type tag
        if q_type:
            tag_x = badge_x + 32
            tag_w = len(q_type) * 5 + 10
            c.setFillColor(BW_CYAN)
            c.roundRect(tag_x, badge_y - 8, tag_w, 14, 3, fill=1, stroke=0)
            c.setFillColor(BW_WHITE)
            _set_font(c, "Helvetica", 6.5)
            c.drawString(tag_x + 4, badge_y - 2, q_type)
            badge_right = tag_x + tag_w + 6
        else:
            badge_right = badge_x + 32

        # Marks badge (right side of card)
        marks_label = f"{marks_got:.0f} / {marks_tot:.0f} pts"
        c.setFillColor(BW_BLUE)
        c.roundRect(MARGIN_L + CONTENT_W - 74, badge_y - 8, 66, 16, 3,
                    fill=1, stroke=0)
        c.setFillColor(BW_WHITE)
        _set_font(c, "Helvetica-Bold", 7.5)
        c.drawCentredString(MARGIN_L + CONTENT_W - 41, badge_y - 2, marks_label)

        # ---- Correct / Incorrect icon ----
        icon_cx = MARGIN_L + CONTENT_W - 90
        if is_corr is True:
            _draw_checkmark(c, icon_cx, badge_y - 1, size=7)
        elif is_corr is False:
            _draw_xmark(c, icon_cx, badge_y - 1, size=7)
        else:
            _draw_partial_mark(c, icon_cx, badge_y - 1, size=7)

        # ---- Question text ----
        qy = y - 30
        c.setFillColor(BW_DARK)
        _set_font(c, "Helvetica-Bold", 8.5)
        for line in q_lines:
            c.drawString(MARGIN_L + 12, qy, line)
            qy -= 12

        qy -= 6  # gap before answers

        # ---- Answers header row (equal-width columns, evenly spaced) ----
        gap     = 8
        half_w  = (CONTENT_W - 24 - gap) / 2
        left_x  = MARGIN_L + 12
        right_x = left_x + half_w + gap

        c.setFillColor(BW_BLUE)
        c.roundRect(left_x,  qy - 14, half_w, 14, 3, fill=1, stroke=0)
        c.roundRect(right_x, qy - 14, half_w, 14, 3, fill=1, stroke=0)

        c.setFillColor(BW_WHITE)
        _set_font(c, "Helvetica-Bold", 7)
        c.drawCentredString(left_x  + half_w / 2, qy - 9.5, "STUDENT ANSWER")
        c.drawCentredString(right_x + half_w / 2, qy - 9.5, "CORRECT ANSWER")

        qy -= 14

        # ---- Code panels (monospace, preserves original line breaks) ----
        code_box_top = qy
        code_box_h   = ans_rows * CODE_LINE_H + 16

        for box_x in (left_x, right_x):
            c.setFillColor(CODE_BOX_BG)
            c.roundRect(box_x, code_box_top - code_box_h, half_w, code_box_h,
                        3, fill=1, stroke=0)
            c.setStrokeColor(BW_RULE)
            c.setLineWidth(0.5)
            c.roundRect(box_x, code_box_top - code_box_h, half_w, code_box_h,
                        3, fill=0, stroke=1)

        text_top = code_box_top - 11

        c.setFillColor(BW_DARK)
        _set_font(c, CODE_FONT, CODE_FONT_SIZE)
        sa_y = text_top
        for line in sa_lines:
            c.drawString(left_x + 6, sa_y, line)
            sa_y -= CODE_LINE_H

        c.setFillColor(result_color)
        _set_font(c, CODE_FONT, CODE_FONT_SIZE)
        ca_y = text_top
        for line in ca_lines:
            c.drawString(right_x + 6, ca_y, line)
            ca_y -= CODE_LINE_H

        qy = code_box_top - code_box_h - 6

        # ---- AI Feedback block (inside the card) ----
        if feedback.strip():
            # Draw directly — no outer page-break needed here since we
            # already estimated the card height includes feedback.
            fb_block_h = len(fb_lines) * 12 + 22

            c.setFillColor(COLOR_FDBK_BG)
            c.roundRect(left_x, qy - fb_block_h, CONTENT_W - 24,
                        fb_block_h, 3, fill=1, stroke=0)
            c.setFillColor(COLOR_FDBK_BD)
            c.rect(left_x, qy - fb_block_h, 3, fb_block_h, fill=1, stroke=0)

            _draw_info_icon(c, left_x + 14, qy - 10, size=5.5)
            c.setFillColor(BW_CYAN)
            _set_font(c, "Helvetica-Bold", 7)
            c.drawString(left_x + 23, qy - 13, "AI FEEDBACK")

            fby = qy - 22
            c.setFillColor(BW_DARK)
            _set_font(c, "Helvetica-Oblique", 7.5)
            for line in fb_lines:
                c.drawString(left_x + 8, fby, line)
                fby -= 12

            qy = qy - fb_block_h - 6

        y = qy - 10   # gap between cards

    return y


# ---------------------------------------------------------------------------
# Strengths & Improvements strip
# ---------------------------------------------------------------------------

def _draw_bullet_list(c, y: float, items: list,
                      icon_draw_fn, label: str, color,
                      page_state: dict,
                      draw_header_fn, draw_footer_fn) -> float:
    """
    Generic bullet list renderer.  Returns updated Y.
    """
    if not items:
        return y

    y = _check_page_break(c, y, 30 + len(items) * 16,
                          draw_header_fn, draw_footer_fn, page_state)
    c.setFillColor(color)
    _set_font(c, "Helvetica-Bold", 8)
    c.drawString(MARGIN_L, y, label)
    y -= 12

    for text in items:
        y = _check_page_break(c, y, 16,
                              draw_header_fn, draw_footer_fn, page_state)
        icon_draw_fn(c, MARGIN_L + 8, y + 3, size=5)
        c.setFillColor(BW_DARK)
        _set_font(c, "Helvetica", 8.5)
        # Wrap long bullet text
        lines = _wrap_text(str(text), max_chars=84)
        for i, line in enumerate(lines):
            c.drawString(MARGIN_L + 20, y, line)
            y -= 12
        y -= 2

    return y - 4


# ---------------------------------------------------------------------------
# Official certification / signature block
# ---------------------------------------------------------------------------

def _draw_signature_block(c, y: float,
                           page_state: dict,
                           draw_header_fn, draw_footer_fn) -> float:
    """
    Draw the official sign-off with two signature lines:
    - Chief Examiner  (Tinodaishe Chibi)
    - Director, Bluewave Academy
    """
    cert_text = ("This report is an official record of academic performance issued by "
                 "Bluewave Academy. The results herein are final unless subject to "
                 "a formal review request submitted within 14 days of this report.")
    cert_lines = _wrap_text(cert_text, max_chars=88)

    # Block height derived from actual content (cert paragraph + signature
    # rows + verification line) rather than a fixed constant. The previous
    # fixed height of 100 was too short once the cert text wrapped to 3
    # lines, which pushed the "Director & Founder" role label past the
    # card's bottom edge, overlapping the verification-ID caption below it.
    top_pad      = 16
    cert_block_h = len(cert_lines) * 12
    gap_1        = 10
    sig_block_h  = 14 + 12 + 11 + 10   # underline -> name -> role -> org
    gap_2        = 14
    verif_h      = 10
    bottom_pad   = 14
    block_h = (top_pad + cert_block_h + gap_1 + sig_block_h
               + gap_2 + verif_h + bottom_pad)

    y = _check_page_break(c, y, block_h + 30,
                          draw_header_fn, draw_footer_fn, page_state)

    y = _draw_section_heading(c, y, "OFFICIAL CERTIFICATION")

    # Light background cert block
    c.setFillColor(BW_LIGHT_BG)
    c.roundRect(MARGIN_L, y - block_h, CONTENT_W, block_h, 6, fill=1, stroke=0)
    c.setStrokeColor(BW_RULE)
    c.setLineWidth(0.8)
    c.roundRect(MARGIN_L, y - block_h, CONTENT_W, block_h, 6, fill=0, stroke=1)

    # Certification statement
    c.setFillColor(BW_DARK)
    _set_font(c, "Helvetica-Oblique", 8.5)
    ty = y - top_pad
    for line in cert_lines:
        c.drawString(MARGIN_L + 14, ty, line)
        ty -= 12

    ty -= gap_1

    # Two signature columns
    sig_col_w = CONTENT_W / 2 - 20
    cols = [
        {
            "name": "Tinodaishe Chibi",
            "role": "Chief Examiner",
            "org":  "Bluewave Academy",
            "x":    MARGIN_L + 20,
        },
        {
            "name": "Tinodaishe Chibi",
            "role": "Director & Founder",
            "org":  "Bluewave Academy",
            "x":    MARGIN_L + CONTENT_W / 2 + 10,
        },
    ]

    sig_bottom = ty  # track lowest point drawn so far
    for col in cols:
        sx = col["x"]

        # Signature underline
        c.setStrokeColor(BW_BLUE)
        c.setLineWidth(1)
        c.line(sx, ty - 14, sx + sig_col_w - 10, ty - 14)

        # Name / role / org
        c.setFillColor(BW_BLUE)
        _set_font(c, "Helvetica-Bold", 8)
        c.drawString(sx, ty - 26, col["name"])

        c.setFillColor(colors.HexColor("#5A7099"))
        _set_font(c, "Helvetica", 7.5)
        c.drawString(sx, ty - 37, col["role"])
        c.drawString(sx, ty - 48, col["org"])
        sig_bottom = ty - 48

    # Verification ID — placed below the signature rows with its own
    # padding so it never collides with the "org" line above it.
    attempt_id = page_state.get("attempt_id", "")
    verif_y = sig_bottom - gap_2
    c.setFillColor(colors.HexColor("#A0AFBF"))
    _set_font(c, "Helvetica", 6.5)
    c.drawCentredString(PAGE_W / 2, verif_y,
                        f"Verification ID: BW-{attempt_id}  |  "
                        "This document was generated electronically and is valid without a wet signature.")

    return y - block_h - 12


# ---------------------------------------------------------------------------
# Main public function — Examinator (classroom assignment) reports
# ---------------------------------------------------------------------------

def generate_exam_report(student, exam, submission, parsed_results: list,
                         logo_path: str = None) -> BytesIO:
    """
    Generate a full-page PDF exam report for a classroom assignment submission.

    Parameters
    ----------
    student         : CustomUser instance
    exam            : Assignment (or Exam) instance — must have .title,
                      .total_marks, .passing_marks
    submission      : Submission (or ExamAttempt) instance — must have
                      .get_score(), .submitted_at (or .created_at),
                      .ai_feedback, .ai_strengths, .ai_improvements,
                      .ai_improvement_tips, .time_taken_seconds
    parsed_results  : list of dicts.  Each dict represents one question
                      and should contain:
                        question_num    int
                        question_text   str
                        question_type   str  ('MCQ', 'Essay', 'Code', …)
                        student_answer  str
                        correct_answer  str
                        is_correct      bool | None  (None = partial)
                        marks_obtained  float
                        total_marks     float
                        ai_feedback     str
    logo_path       : optional absolute path to a PNG/JPG logo file

    Returns
    -------
    BytesIO  — ready to stream as an HTTP response or write to disk.

    Example (Django view)
    ---------------------
        buffer = generate_exam_report(
            student=submission.student,
            exam=submission.assignment,
            submission=submission,
            parsed_results=build_parsed_results(submission),
        )
        return FileResponse(buffer, content_type='application/pdf',
                            as_attachment=True,
                            filename='report.pdf')
    """
    if not HAS_REPORTLAB:
        raise ImportError(
            "ReportLab is required: pip install reportlab"
        )

    # ------------------------------------------------------------------ setup
    buffer = BytesIO()
    c = rl_canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"Bluewave Academy — Exam Report — "
               f"{getattr(student, 'get_full_name', lambda: '')()}")
    c.setAuthor("Tinodaishe Chibi — Bluewave Academy")
    c.setSubject("Student Exam Performance Report")

    # Score & percentage
    score_val  = float(getattr(submission, "get_score", lambda: 0)() or 0)
    total      = float(getattr(exam, "total_marks", 100) or 100)
    percentage = round((score_val / total) * 100, 2) if total > 0 else 0.0

    # Submission date
    sub_date = getattr(submission, "submitted_at",
                       getattr(submission, "created_at", None))
    exam_date = sub_date.strftime("%d %B %Y") if sub_date else datetime.now().strftime("%d %B %Y")

    # Shared state passed to header/footer on every page
    page_state = {
        "page_num":      1,
        "student_name":  getattr(student, "get_full_name", lambda: str(student))(),
        "student_id":    getattr(student, "student_id", "") or "",
        "exam_title":    getattr(exam, "title", str(exam))[:60],
        "exam_date":     exam_date,
        "report_title":  "EXAM PERFORMANCE REPORT",
        "generated_at":  datetime.now().strftime("%d %b %Y  %H:%M:%S"),
        "logo_path":     logo_path,
        "attempt_id":    getattr(submission, "id", ""),
    }

    # Closures that accept (canvas, page_state) — passed through as callables
    def hdr(cv, ps):  _draw_header(cv, ps)
    def ftr(cv, ps):  _draw_footer(cv, ps)

    # ---------------------------------------------------------------- page 1
    _draw_watermark(c)
    hdr(c, page_state)
    ftr(c, page_state)

    y = BODY_TOP

    # Summary card + donut
    y = _draw_summary_block(c, y, student, exam, submission, percentage)
    y -= 6

    # Metrics strip
    y = _draw_stats_strip(c, y, submission, exam, percentage)
    y -= 6

    # Overall AI feedback (top-level submission feedback)
    overall_feedback = getattr(submission, "ai_feedback", "") or ""
    if overall_feedback.strip():
        y = _draw_feedback_block(c, y, "Overall AI Feedback",
                                 overall_feedback, page_state, hdr, ftr)
        y -= 4

    # ---- Strengths ----
    strengths = getattr(submission, "ai_strengths", []) or []
    if strengths:
        y = _check_page_break(c, y, 40 + len(strengths) * 16,
                              hdr, ftr, page_state)
        y = _draw_bullet_list(c, y, strengths, _draw_checkmark,
                              "Strengths", COLOR_PASS,
                              page_state, hdr, ftr)
        y -= 4

    # ---- Areas for Improvement ----
    improvements = getattr(submission, "ai_improvements", []) or []
    if improvements:
        y = _check_page_break(c, y, 40 + len(improvements) * 16,
                              hdr, ftr, page_state)
        y = _draw_bullet_list(c, y, improvements, _draw_xmark,
                              "Areas for Improvement", COLOR_FAIL,
                              page_state, hdr, ftr)
        y -= 4

    # ---- Improvement Tips ----
    tips = getattr(submission, "ai_improvement_tips", []) or []
    if tips:
        y = _check_page_break(c, y, 40 + len(tips) * 16,
                              hdr, ftr, page_state)
        y = _draw_bullet_list(c, y, tips, _draw_partial_mark,
                              "Improvement Tips", COLOR_AMBER,
                              page_state, hdr, ftr)
        y -= 4

    # ---------------------------------------------------------------- Q breakdown
    if parsed_results:
        y = _check_page_break(c, y, 60, hdr, ftr, page_state)
        y = _draw_question_breakdown(c, y, parsed_results,
                                     page_state, hdr, ftr)

    # ---------------------------------------------------------------- Signature
    y = _check_page_break(c, y, 120, hdr, ftr, page_state)
    _draw_signature_block(c, y, page_state, hdr, ftr)

    # ---------------------------------------------------------------- Finalize
    c.save()
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Legacy wrapper — keeps admin_views.py download_report() working unchanged
# ---------------------------------------------------------------------------

def generate_student_report(exam_attempt, output_path: str = None) -> BytesIO:
    """
    Legacy compatibility wrapper used by admin_views.download_report().

    Translates a legacy ExamAttempt into the new generate_exam_report()
    signature by building a parsed_results list from the attempt's answers.

    Parameters
    ----------
    exam_attempt  : ExamAttempt model instance
    output_path   : optional file path — if given, the PDF is also saved
                    to disk in addition to being returned as BytesIO

    Returns
    -------
    BytesIO
    """
    if not HAS_REPORTLAB:
        raise ImportError("ReportLab is required: pip install reportlab")

    # Build parsed_results from attempt.answers queryset
    parsed_results = []
    try:
        answers = exam_attempt.answers.select_related("question").order_by(
            "question__order"
        )
        for idx, answer in enumerate(answers, start=1):
            q = answer.question

            # Prefer admin-overridden feedback from ExamGrading if available
            ai_feedback = answer.ai_feedback or ""
            try:
                grading = exam_attempt.groq_gradings.get(question=q)
                ai_feedback = grading.get_final_feedback() or ai_feedback
            except Exception:
                pass

            parsed_results.append({
                "question_num":   idx,
                "question_text":  q.question_text,
                "question_type":  q.get_question_type_display(),
                "student_answer": answer.answer_text or "—",
                "correct_answer": q.correct_answer or "—",
                "is_correct":     answer.is_correct,
                "marks_obtained": float(answer.marks_obtained or 0),
                "total_marks":    float(q.marks or 1),
                "ai_feedback":    ai_feedback,
            })
    except Exception as e:
        # If DB access fails mid-build, still generate with what we have
        print(f"[pdf_generator] Warning building parsed_results: {e}")

    # Build a thin adapter so the attempt exposes the Submission interface
    class _AttemptAdapter:
        """Shims ExamAttempt to look like a Submission for generate_exam_report."""
        def __init__(self, attempt):
            self._a = attempt

        def get_score(self):
            return self._a.score

        @property
        def submitted_at(self):
            return getattr(self._a, "end_time", None) or self._a.created_at

        @property
        def ai_feedback(self):
            return self._a.ai_feedback or ""

        @property
        def ai_strengths(self):
            return []

        @property
        def ai_improvements(self):
            return []

        @property
        def ai_improvement_tips(self):
            return []

        @property
        def time_taken_seconds(self):
            mins = getattr(self._a, "time_taken_minutes", None)
            return int(mins) * 60 if mins else None

        @property
        def id(self):
            return self._a.id

    buffer = generate_exam_report(
        student=exam_attempt.student,
        exam=exam_attempt.exam,
        submission=_AttemptAdapter(exam_attempt),
        parsed_results=parsed_results,
    )

    if output_path:
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
        buffer.seek(0)

    return buffer


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------
__all__ = [
    "generate_exam_report",
    "generate_student_report",
    "HAS_REPORTLAB",
]