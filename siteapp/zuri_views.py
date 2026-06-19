"""
Zuri — Bluewave Academy AI Assistant
Powered by Groq (llama-3.3-70b-versatile / llama-3.2-11b-vision-preview)
Supports: text, images (JPEG/PNG/WebP/GIF), PDF documents
"""

import io
import json
import base64
import os
import re
import threading

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

try:
    from groq import Groq as GroqClient
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    GroqClient = None

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    import requests as req_lib
    import bs4
    HAS_SCRAPE = True
except ImportError:
    HAS_SCRAPE = False

# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
GROQ_TEXT_MODEL   = "llama-3.3-70b-versatile"
GROQ_VISION_MODEL = "llama-3.2-11b-vision-preview"

# ─────────────────────────────────────────────
# Rate limit
# ─────────────────────────────────────────────
RATE_LIMIT_PER_HOUR = 20
RATE_WINDOW_SECONDS = 3600

# ─────────────────────────────────────────────
# Founder / director bio
# ─────────────────────────────────────────────
FOUNDER_BIO = """
Tinodaishe M Chibi is the founder and director of Bluewave Technologies and the creator of
Bluewave Academy. He is currently studying Software Engineering at the Harare Institute
of Technology (HIT) in Zimbabwe.

His journey in technology has not been without challenges — computer science is demanding,
but his unwavering passion, prayer, consistent practice, and dedication have carried him
forward. He built Bluewave Academy to prove that young Africans can compete on the world
stage in technology.

Key facts:
- Founder & Director of Bluewave Technologies (software company, Zimbabwe)
- Creator of Bluewave Academy — making CS education accessible across Zimbabwe and Africa
- Software Engineering student at HIT (Harare Institute of Technology), Harare, Zimbabwe
- Multiple awards and certifications in software development and entrepreneurship
- Passionate about empowering the next generation of African tech leaders
- Shares his journey on LinkedIn: building Bluewave Technologies from the ground up
- Believes that passion, prayer, and consistent practice can transform any student's life
- His story is one of perseverance — proving humble beginnings do not limit your ceiling
- Advocates for African students to pursue global tech careers without leaving their values behind

If asked about Tinodaishe, share his story authentically and encourage students the way
he would — with warmth, ambition, and zero condescension.
"""

# ─────────────────────────────────────────────
# System prompt — comprehensive
# ─────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are Zuri, the intelligent AI assistant for Bluewave Academy — Zimbabwe's premier computer science education and technology platform.

=== ABOUT BLUEWAVE ACADEMY ===
Bluewave Academy was founded by Tinodaishe M Chibi to deliver world-class computer science education to students in Zimbabwe and across Africa. Core services:
- The Examinator: AI-powered timed online exam platform with instant grading and detailed feedback
- Study Resources: ZIMSEC past papers, programming textbooks, study notes, and reference materials
- Seminars & Courses: live and recorded sessions covering Python, web development, databases, networking, algorithms, and more
- Personalized Tutoring: 1-on-1 sessions with experienced tutors
- Student Portal: progress tracking, exam history, analytics, and performance insights
- Blog: CS tutorials, industry insights, and tech news written for African students
- Career Guidance: advice for students pursuing careers in software engineering, data science, cybersecurity, cloud computing, and more

=== FOUNDER & DIRECTOR ===
{FOUNDER_BIO}

=== YOUR CAPABILITIES ===
1. **Computer Science Education** — Python, Java, C++, algorithms, data structures, OOP, databases (SQL/NoSQL), web development (HTML, CSS, JS, Django, React), networking, OS concepts, cybersecurity basics, cloud computing, AI/ML fundamentals
2. **Image Analysis** — describe diagrams, flowcharts, ERDs, UML, code screenshots, exam papers, circuit diagrams, or any image a student shares
3. **Document Analysis** — when a PDF is uploaded, read its contents and answer questions about it accurately; can summarise documents, extract key points, explain concepts from textbooks or past papers
4. **Career Guidance** — advise on CS career paths (software engineering, data science, cybersecurity, DevOps, cloud, mobile dev, AI/ML); job markets in Zimbabwe, Africa, and globally; how to build a portfolio; FAANG/big tech preparation; internship hunting; freelancing; open-source contributions; LinkedIn and CV tips
5. **Study Strategies** — exam preparation, time management, how to approach ZIMSEC CS exams, how to study algorithms and data structures effectively
6. **Bluewave Academy Info** — courses, how to register, pricing, events, team, founder story, how The Examinator works
7. **Motivational Support** — encourage students who are struggling; remind them difficulty is part of growth

=== YOUR PERSONALITY ===
- Warm, direct, and intellectually curious — you genuinely care about every student
- Never condescending; always assume the student is capable
- Use markdown where it helps: **bold**, bullet lists, numbered steps, `inline code`, code blocks
- Keep answers focused and useful — quality over word count
- When answering career questions, give concrete, actionable advice, not vague platitudes
- When analysing a document or image, be thorough and cite specific details from it
- If you don't know something, say so honestly and suggest where the student can find out
- Represent Bluewave Academy with pride — this platform is building Africa's next generation of engineers

=== IMPORTANT RULES ===
- Never be dismissive or discouraging
- Always believe in the student's potential
- For PDF/document questions, reference the actual content of the document in your answer
- For career questions, tailor advice to the African tech context where relevant, but always include global perspective
- If asked about Tinodaishe Chibi, share his story with genuine admiration — it IS inspiring
"""


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _is_rate_limited(ip: str) -> tuple[bool, int]:
    key = f"zuri_rate_{ip}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT_PER_HOUR:
        return True, 0
    cache.set(key, count + 1, RATE_WINDOW_SECONDS)
    return False, RATE_LIMIT_PER_HOUR - count - 1


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF using pypdf."""
    if not HAS_PYPDF:
        return "[PDF processing unavailable — pypdf not installed]"
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for i, page in enumerate(reader.pages[:40]):  # cap at 40 pages
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(f"--- Page {i + 1} ---\n{text.strip()}")
        if not pages_text:
            return "[This PDF does not contain extractable text — it may be a scanned image.]"
        return "\n\n".join(pages_text)
    except Exception as e:
        return f"[Could not read PDF: {e}]"


def _scrape_tinodaishe() -> str:
    if not HAS_SCRAPE:
        return ""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        query = "Tinodaishe Chibi Bluewave Technologies Zimbabwe HIT Software Engineering"
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num=5"
        resp = req_lib.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            soup = bs4.BeautifulSoup(resp.text, "html.parser")
            snippets = []
            for tag in soup.select("div.BNeawe, span.aCOpRe, div[data-sncf] span"):
                text = tag.get_text(" ", strip=True)
                if len(text) > 40 and any(
                    kw in text for kw in ["Tinodaishe", "Bluewave", "Chibi", "HIT", "Zimbabwe"]
                ):
                    snippets.append(text)
            if snippets:
                return "Recent web results about Tinodaishe Chibi:\n" + "\n".join(snippets[:6])
    except Exception:
        pass
    return ""


def _build_messages(
    history: list,
    message: str,
    image_b64: str | None,
    pdf_text: str | None,
    extra_context: str,
) -> list:
    """Build the Groq messages array."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Prior turns (last 16 = 8 pairs)
    for turn in history[-16:]:
        role = turn.get("role", "user")
        if role == "model":
            role = "assistant"
        messages.append({"role": role, "content": turn.get("content", "")})

    # Build user turn text
    parts = []
    if message:
        parts.append(message)
    if pdf_text:
        parts.append(
            f"\n\n=== UPLOADED PDF CONTENTS ===\n{pdf_text}\n=== END OF PDF ===\n"
            "\nPlease answer my question using the PDF content above."
        )
    if extra_context:
        parts.append(f"\n[Additional context]\n{extra_context}")

    user_text = "\n".join(parts).strip() or "(file attached — please describe it)"

    if image_b64:
        # Multimodal content for vision model
        content = []
        if user_text:
            content.append({"type": "text", "text": user_text})
        content.append({
            "type": "image_url",
            "image_url": {"url": image_b64},
        })
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_text})

    return messages


# ─────────────────────────────────────────────
# Main view
# ─────────────────────────────────────────────

@csrf_exempt
@require_POST
def zuri_chat(request):
    ip = _get_client_ip(request)

    limited, remaining = _is_rate_limited(ip)
    if limited:
        return JsonResponse(
            {
                "error": "rate_limited",
                "message": (
                    "You've reached the hourly limit of 20 messages. "
                    "Please try again in an hour!"
                ),
            },
            status=429,
        )

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not HAS_GROQ or not api_key:
        return JsonResponse(
            {
                "error": "unavailable",
                "message": "Zuri's AI engine isn't configured. Please add GROQ_API_KEY.",
            },
            status=503,
        )

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "invalid_json"}, status=400)

    message   = data.get("message", "").strip()
    image_b64 = data.get("image", "")       # base64 data-URL for images
    file_b64  = data.get("file", "")        # base64 data-URL for PDFs
    file_type = data.get("file_type", "")   # "pdf" | "image"
    history   = data.get("history", [])

    if not message and not image_b64 and not file_b64:
        return JsonResponse({"error": "empty"}, status=400)

    if len(message) > 4000:
        return JsonResponse({"error": "too_long", "message": "Message too long (max 4000 chars)."}, status=400)

    # ── Decode attachments ──────────────────────────────────
    pdf_text  = None
    use_image = None  # b64 data-URL to pass to vision model

    # PDF handling
    if file_b64 and file_type == "pdf":
        try:
            raw = file_b64
            if raw.startswith("data:"):
                _, raw = raw.split(",", 1)
            pdf_bytes = base64.b64decode(raw)
            pdf_text  = _extract_pdf_text(pdf_bytes)
        except Exception as e:
            pdf_text = f"[Could not decode PDF: {e}]"

    # Image handling
    if image_b64 or (file_b64 and file_type in ("image", "image/png", "image/jpeg", "image/webp", "image/gif")):
        use_image = image_b64 or file_b64

    # ── Optional founder web scrape ─────────────────────────
    extra_context = ""
    founder_kws = ["tinodaishe", "chibi", "founder", "director", "bluewave tech", "linkedin"]
    if message and any(kw in message.lower() for kw in founder_kws):
        result = []
        def _scrape():
            result.append(_scrape_tinodaishe())
        t = threading.Thread(target=_scrape, daemon=True)
        t.start()
        t.join(timeout=5)
        if result:
            extra_context = result[0]

    # ── Pick model ──────────────────────────────────────────
    model = GROQ_VISION_MODEL if use_image else GROQ_TEXT_MODEL

    # ── Call Groq ───────────────────────────────────────────
    try:
        client   = GroqClient(api_key=api_key)
        messages = _build_messages(history, message, use_image, pdf_text, extra_context)

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1500,
            temperature=0.70,
        )

        reply = (
            completion.choices[0].message.content
            or "I couldn't generate a response. Please try again."
        )
        return JsonResponse({"reply": reply, "remaining": remaining, "status": "ok"})

    except Exception as e:
        print(f"[Zuri] Groq error: {e}")
        return JsonResponse(
            {"error": "ai_error", "message": "Zuri ran into a hiccup. Please try again in a moment."},
            status=500,
        )
