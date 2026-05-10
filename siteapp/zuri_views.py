"""
Zuri — Bluewave Academy AI Assistant
Powered by Google Gemini | Rate limited by IP
"""

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
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    genai = None
    genai_types = None

try:
    import requests as req_lib
    import bs4
    HAS_SCRAPE = True
except ImportError:
    HAS_SCRAPE = False

# ─────────────────────────────────────────────
# Rate limit settings
# ─────────────────────────────────────────────
RATE_LIMIT_PER_HOUR = 20       # requests per IP per hour
RATE_WINDOW_SECONDS = 3600     # 1 hour

# ─────────────────────────────────────────────
# Tinodaishe M Chibi — founder bio
# ─────────────────────────────────────────────
FOUNDER_BIO = """
Tinodaishe M Chibi is the visionary founder of Bluewave Technologies and the creator of
Bluewave Academy. He is currently studying Software Engineering at the Harare Institute
of Technology (HIT) in Zimbabwe.

His journey in technology has not been without challenges — computer science can be
incredibly demanding, but his unwavering passion, prayer, consistent practice, and
dedication have carried him forward. He built Bluewave Academy to prove that young
Africans can compete on the world stage in technology.

Notable facts about Tinodaishe:
- Founder & CEO of Bluewave Technologies (a growing software company in Zimbabwe)
- Creator of Bluewave Academy — making CS education accessible to Zimbabwean students
- Software Engineering student at HIT (Harare Institute of Technology)
- Has received multiple awards and certifications in software development and entrepreneurship
- Passionate about empowering the next generation of African tech leaders
- Active on LinkedIn sharing his journey of building Bluewave Technologies
- Believes deeply that passion, prayer, and practice can transform any student's trajectory
- His story is one of perseverance — proving that humble beginnings do not limit your ceiling

If a user asks about Tinodaishe or wants more information about him, you can mention that
they can find him on LinkedIn where he shares updates about Bluewave Technologies and his
engineering journey.
"""

# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are Zuri, the intelligent AI assistant for Bluewave Academy — Zimbabwe's premier computer science education platform.

=== ABOUT BLUEWAVE ACADEMY ===
Bluewave Academy was founded by Tinodaishe M Chibi to deliver high-quality computer science education to students in Zimbabwe and beyond. Services include:
- Timed online exams and The Examinator platform (AI-powered grading)
- Study resources: ZIMSEC past papers, programming books, study notes
- Seminars, courses, and personalized tutoring
- A blog with CS tutorials and insights
- A student portal with progress tracking

=== ABOUT YOUR CREATOR ===
{FOUNDER_BIO}

=== YOUR CAPABILITIES ===
1. Answer CS questions: Python, algorithms, data structures, databases, web dev, networking, OOP, etc.
2. Analyze images: Describe diagrams, code screenshots, exam papers, or anything a student uploads
3. Help with study strategies, exam preparation, and time management
4. Explain concepts at any level — from beginner to advanced
5. Answer questions about Bluewave Academy's services, courses, and team
6. Discuss Tinodaishe Chibi and Bluewave Technologies if asked

=== YOUR PERSONALITY ===
- Warm, encouraging, and intellectually curious
- Clear and direct — no unnecessary filler
- Supportive of struggling students: remind them that difficulty is normal
- Use markdown formatting (bold, bullet points, code blocks) where it genuinely helps
- Keep responses concise but complete — aim for quality over length
- If you don't know something, say so honestly and suggest how they can find out

=== IMPORTANT ===
- Never be dismissive or discouraging to students
- Always believe in the student's potential
- If asked about Tinodaishe, share his story authentically — it's genuinely inspiring
- You represent Bluewave Academy, so be professional and proud of the institution
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
    """Returns (is_limited, remaining_requests)."""
    key = f"zuri_rate_{ip}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT_PER_HOUR:
        return True, 0
    cache.set(key, count + 1, RATE_WINDOW_SECONDS)
    return False, RATE_LIMIT_PER_HOUR - count - 1


def _scrape_tinodaishe() -> str:
    """Try to get fresh public info about Tinodaishe via web search."""
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
                if len(text) > 40 and any(kw in text for kw in ["Tinodaishe", "Bluewave", "Chibi", "HIT", "Zimbabwe"]):
                    snippets.append(text)
            if snippets:
                return "Recent web search results about Tinodaishe Chibi:\n" + "\n".join(snippets[:6])
    except Exception:
        pass
    return ""


def _build_contents(history: list, message: str, image_bytes: bytes | None,
                    mime: str, extra_context: str):
    """Build the genai contents list for the API call."""
    if not HAS_GENAI:
        return []

    contents = []

    # Prior conversation turns (last 8 pairs)
    for turn in history[-16:]:
        role = "user" if turn.get("role") == "user" else "model"
        contents.append(
            genai_types.Content(
                role=role,
                parts=[genai_types.Part.from_text(turn.get("content", ""))],
            )
        )

    # Build current user turn
    current_parts = []

    if image_bytes:
        try:
            current_parts.append(
                genai_types.Part.from_bytes(data=image_bytes, mime_type=mime)
            )
        except Exception:
            pass

    user_text = message
    if extra_context:
        user_text = f"{message}\n\n[Additional context]\n{extra_context}"

    current_parts.append(genai_types.Part.from_text(user_text))
    contents.append(genai_types.Content(role="user", parts=current_parts))

    return contents


# ─────────────────────────────────────────────
# Main view
# ─────────────────────────────────────────────

@csrf_exempt
@require_POST
def zuri_chat(request):
    ip = _get_client_ip(request)

    # Rate limiting
    limited, remaining = _is_rate_limited(ip)
    if limited:
        return JsonResponse(
            {
                "error": "rate_limited",
                "message": (
                    "You've reached the hourly limit of 20 messages. "
                    "Please try again in an hour. Thanks for chatting with Zuri!"
                ),
            },
            status=429,
        )

    # Check AI availability
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_AI_API_KEY", "")
    if not HAS_GENAI or not api_key:
        return JsonResponse(
            {
                "error": "unavailable",
                "message": (
                    "Zuri's AI engine isn't configured yet. "
                    "Please add your GEMINI_API_KEY to get started!"
                ),
            },
            status=503,
        )

    # Parse request body
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({"error": "invalid_json"}, status=400)

    message = data.get("message", "").strip()
    image_b64 = data.get("image", "")   # optional base64 data-URL or plain base64
    history = data.get("history", [])   # [{role, content}, ...]

    if not message and not image_b64:
        return JsonResponse({"error": "empty"}, status=400)

    if len(message) > 3000:
        return JsonResponse({"error": "too_long", "message": "Message too long (max 3000 chars)."}, status=400)

    # Decode image if present
    image_bytes = None
    mime = "image/jpeg"
    if image_b64:
        try:
            raw = image_b64
            if raw.startswith("data:"):
                header, raw = raw.split(",", 1)
                if "png" in header:
                    mime = "image/png"
                elif "gif" in header:
                    mime = "image/gif"
                elif "webp" in header:
                    mime = "image/webp"
            image_bytes = base64.b64decode(raw)
        except Exception:
            image_bytes = None

    # Determine if web scrape is useful
    extra_context = ""
    tinodaishe_keywords = ["tinodaishe", "chibi", "founder", "bluewave tech", "linkedin", "award", "certif"]
    if message and any(kw in message.lower() for kw in tinodaishe_keywords):
        # Run in thread so it doesn't block if slow
        result_container = []
        def _scrape():
            result_container.append(_scrape_tinodaishe())
        t = threading.Thread(target=_scrape, daemon=True)
        t.start()
        t.join(timeout=5)
        if result_container:
            extra_context = result_container[0]

    # Build API call
    try:
        client = genai.Client(api_key=api_key)
        contents = _build_contents(history, message, image_bytes, mime, extra_context)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=1200,
                temperature=0.72,
            ),
        )

        reply = response.text or "I couldn't generate a response. Please try again."
        return JsonResponse({"reply": reply, "remaining": remaining, "status": "ok"})

    except Exception as e:
        print(f"[Zuri] API error: {e}")
        return JsonResponse(
            {
                "error": "ai_error",
                "message": "Zuri ran into a hiccup. Please try again in a moment.",
            },
            status=500,
        )
