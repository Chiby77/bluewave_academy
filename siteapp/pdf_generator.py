"""
Professional PDF Report Generation for Exam Results
Creates stunning, next-gen exam reports with signatures and examiner details
"""

from io import BytesIO
from datetime import datetime
from decimal import Decimal

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
        PageBreak,
        Image,
        Line,
        Preformatted,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def generate_student_report(exam_attempt, output_path=None):
    """
    Generate stunning next-gen PDF report for exam attempt

    Args:
        exam_attempt: ExamAttempt object
        output_path: Optional file path to save PDF

    Returns:
        BytesIO object containing PDF data
    """
    if not HAS_REPORTLAB:
        raise ImportError(
            "ReportLab is not installed. Install with: pip install reportlab"
        )

    # Create PDF buffer with custom canvas for backgrounds
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=50,
        title=f"Exam Report - {exam_attempt.student.get_full_name()}",
    )

    # Build story/elements
    elements = []

    # ============= COLOR SCHEME - Next Gen =============
    primary_color = colors.HexColor("#0066ff")  # Blue
    secondary_color = colors.HexColor("#00d4ff")  # Cyan
    success_color = colors.HexColor("#00cc66")  # Green
    error_color = colors.HexColor("#ff3333")  # Red
    dark_bg = colors.HexColor("#1a1a2e")  # Dark blue-black
    light_bg = colors.HexColor("#f0f4ff")  # Light blue
    white = colors.HexColor("#ffffff")
    text_dark = colors.HexColor("#2d3748")  # Dark gray

    # ============= STYLES =============
    styles = getSampleStyleSheet()

    # Header style
    header_style = ParagraphStyle(
        "HeaderStyle",
        parent=styles["Heading1"],
        fontSize=32,
        textColor=primary_color,
        alignment=TA_CENTER,
        spaceAfter=6,
        fontName="Helvetica-Bold",
        letterSpacing=1.5,
    )

    # SubHeader style
    subheader_style = ParagraphStyle(
        "SubHeaderStyle",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=secondary_color,
        alignment=TA_CENTER,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )

    # Section heading
    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=white,
        spaceAfter=8,
        spaceBefore=8,
        fontName="Helvetica-Bold",
        backColor=primary_color,
        leftIndent=8,
        rightIndent=8,
        leading=20,
    )

    # Label style
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#666666"),
        fontName="Helvetica",
    )

    # ============= HEADER SECTION =============
    # Institution Name
    institution = Paragraph("<b>🎓 BLUEWAVE ACADEMY</b>", header_style)
    elements.append(institution)

    # Tagline
    tagline = Paragraph(
        "<font size=10 color='#00d4ff'><i>Excellence in Education</i></font>",
        subheader_style,
    )
    elements.append(tagline)
    elements.append(Spacer(1, 0.2 * inch))

    # Title
    title = Paragraph(
        "<b>📋 EXAM RESULT CERTIFICATE</b>",
        ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=20,
            textColor=primary_color,
            alignment=TA_CENTER,
            spaceAfter=8,
            fontName="Helvetica-Bold",
        ),
    )
    elements.append(title)
    elements.append(Spacer(1, 0.15 * inch))

    # ============= STUDENT & EXAM INFO =============
    score = exam_attempt.score or 0
    percentage = exam_attempt.percentage or 0
    passing_marks = exam_attempt.exam.passing_marks
    total_marks = exam_attempt.exam.total_marks
    is_passed = percentage >= passing_marks

    # Student info section with blue background
    student_data = [
        [
            Paragraph(
                "<b>Student Name</b><br/><font size=11>"
                + str(exam_attempt.student.get_full_name())
                + "</font>",
                label_style,
            ),
            Paragraph(
                "<b>Student ID</b><br/><font size=11>"
                + (exam_attempt.student.student_id or "N/A")
                + "</font>",
                label_style,
            ),
        ],
        [
            Paragraph(
                "<b>Exam Title</b><br/><font size=11>"
                + exam_attempt.exam.title
                + "</font>",
                label_style,
            ),
            Paragraph(
                "<b>Category</b><br/><font size=11>"
                + exam_attempt.exam.category
                + "</font>",
                label_style,
            ),
        ],
        [
            Paragraph(
                "<b>Exam Date</b><br/><font size=11>"
                + (
                    exam_attempt.created_at.strftime("%d %B %Y")
                    if exam_attempt.created_at
                    else "N/A"
                )
                + "</font>",
                label_style,
            ),
            Paragraph(
                "<b>Duration</b><br/><font size=11>"
                + str(exam_attempt.exam.duration_minutes)
                + " minutes</font>",
                label_style,
            ),
        ],
    ]

    student_table = Table(student_data, colWidths=[3.25 * inch, 3.25 * inch])
    student_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), light_bg),
                ("TEXTCOLOR", (0, 0), (-1, -1), text_dark),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 1.5, secondary_color),
                ("ROUNDED", True),
            ]
        )
    )

    elements.append(student_table)
    elements.append(Spacer(1, 0.3 * inch))

    # ============= SCORE SECTION - PROMINENT =============
    # Score circles/badges
    score_status_color = success_color if is_passed else error_color

    score_data = [
        [
            Paragraph(
                f"<font size=18 color='{primary_color}'><b>{score}/{total_marks}</b></font><br/><font size=10 color='#666666'>Marks Obtained</font>",
                ParagraphStyle("Score", parent=styles["Normal"], alignment=TA_CENTER),
            ),
            Paragraph(
                f"<font size=18 color='{secondary_color}'><b>{percentage:.1f}%</b></font><br/><font size=10 color='#666666'>Percentage</font>",
                ParagraphStyle("Score", parent=styles["Normal"], alignment=TA_CENTER),
            ),
            Paragraph(
                f"<font size=18 color='{score_status_color}'><b>{'PASS ✓' if is_passed else 'FAIL ✗'}</b></font><br/><font size=10 color='#666666'>Status</font>",
                ParagraphStyle("Score", parent=styles["Normal"], alignment=TA_CENTER),
            ),
        ]
    ]

    score_table = Table(score_data, colWidths=[2.1 * inch, 2.1 * inch, 2.1 * inch])
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8faff")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 20),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
                ("GRID", (0, 0), (-1, -1), 2, secondary_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 15),
                ("RIGHTPADDING", (0, 0), (-1, -1), 15),
            ]
        )
    )

    elements.append(score_table)
    elements.append(Spacer(1, 0.3 * inch))

    # ============= DETAILED BREAKDOWN =============
    elements.append(Paragraph("Performance Breakdown", section_heading_style))
    elements.append(Spacer(1, 0.1 * inch))

    breakdown_data = [
        ["Metric", "Value"],
        ["Total Questions", str(exam_attempt.answers.count())],
        ["Correct Answers", str(exam_attempt.answers.filter(is_correct=True).count())],
        ["Passing Marks Required", str(passing_marks)],
        ["Time Taken", f"{exam_attempt.time_taken_minutes or 0} minutes"],
    ]

    breakdown_table = Table(breakdown_data, colWidths=[3 * inch, 3.5 * inch])
    breakdown_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), primary_color),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#e0e0e0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, light_bg]),
            ]
        )
    )

    elements.append(breakdown_table)
    elements.append(Spacer(1, 0.4 * inch))

    # ============= SIGNATURES AND APPROVALS =============
    elements.append(Paragraph("Official Certification", section_heading_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Signatures section
    sig_data = [
        [
            Paragraph(
                "<b>Examiner</b><br/><br/><br/>_________________<br/><b>Tinodaishe Chibi</b><br/><font size=8>Chief Examiner<br/>BlueWave Academy</font>",
                ParagraphStyle(
                    "Sig", parent=styles["Normal"], alignment=TA_CENTER, leading=14
                ),
            ),
            Paragraph(
                "<b>Founder</b><br/><br/><br/>_________________<br/><b>BlueWave Founder</b><br/><font size=8>Director<br/>BlueWave Academy</font>",
                ParagraphStyle(
                    "Sig", parent=styles["Normal"], alignment=TA_CENTER, leading=14
                ),
            ),
        ]
    ]

    sig_table = Table(sig_data, colWidths=[3.25 * inch, 3.25 * inch])
    sig_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 15),
                ("RIGHTPADDING", (0, 0), (-1, -1), 15),
                ("BORDER", (0, 0), (-1, -1), 1, colors.HexColor("#cccccc")),
            ]
        )
    )

    elements.append(sig_table)
    elements.append(Spacer(1, 0.3 * inch))

    # ============= FOOTER =============
    footer_text = f"Generated on {datetime.now().strftime('%d %b %Y at %H:%M:%S')} | Verification ID: EX{exam_attempt.id:06d}"
    footer = Paragraph(
        f"<font size=8 color='#888888'><i>{footer_text}</i><br/>"
        + f"This is an official document from BlueWave Academy. All rights reserved.</font>",
        ParagraphStyle("Footer", parent=styles["Normal"], alignment=TA_CENTER),
    )

    elements.append(footer)

    # Build PDF
    doc.build(elements)

    # Get PDF data
    buffer.seek(0)

    # Save to file if path provided
    if output_path:
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())

    return buffer


__all__ = ["generate_student_report", "HAS_REPORTLAB"]
