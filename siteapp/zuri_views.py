"""
Zuri — Bluewave Academy AI Assistant
Powered by Groq (llama-3.3-70b-versatile) | Rate limited by IP
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
    from groq import Groq as GroqClient
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    GroqClient = None

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
# Rate limit settings
# ─────────────────────────────────────────────
RATE_LIMIT_PER_HOUR = 20
RATE_WINDOW_SECONDS = 3600

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


def _build_messages(history: list, message: str, image_b64: str | None, mime: str, extra_context: str) -> list:
    """Build the Groq messages array from conversation history + current turn."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Prior conversation turns (last 16 messages = 8 pairs)
    for turn in history[-16:]:
        role = turn.get("role", "user")
        # Normalise Gemini "model" role to Groq "assistant"
        if role == "model":
            role = "assistant"
        messages.append({"role": role, "content": turn.get("content", "")})

    # Build current user turn
    user_text = message
    if extra_context:
        user_text = f"{message}\n\n[Additional context]\n{extra_context}"

    if image_b64:
        # Vision message — multimodal content
        content = []
        if user_text:
            content.append({"type": "text", "text": user_text})
        content.append({
            "type": "image_url",
            "image_url": {"url": image_b64},
        })
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_text or "(image attached)"})

    return messages


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
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not HAS_GROQ or not api_key:
        return JsonResponse(
            {
                "error": "unavailable",
                "message": (
                    "Zuri's AI engine isn't configured yet. "
                    "Please add your GROQ_API_KEY to get started!"
                ),
            },
            status=503,
        )

    # Parse request body
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({"error": "invalid_json"}, status=400)

    message   = data.get("message", "").strip()
    image_b64 = data.get("image", "")    # optional base64 data-URL
    history   = data.get("history", [])  # [{role, content}, ...]

    if not message and not image_b64:
        return JsonResponse({"error": "empty"}, status=400)

    if len(message) > 3000:
        return JsonResponse({"error": "too_long", "message": "Message too long (max 3000 chars)."}, status=400)

    # Determine MIME for image
    mime = "image/jpeg"
    if image_b64:
        if image_b64.startswith("data:image/png"):
            mime = "image/png"
        elif image_b64.startswith("data:image/webp"):
            mime = "image/webp"
        elif image_b64.startswith("data:image/gif"):
            mime = "image/gif"

    # Optional web scrape for founder context
    extra_context = ""
    tinodaishe_keywords = ["tinodaishe", "chibi", "founder", "bluewave tech", "linkedin", "award", "certif"]
    if message and any(kw in message.lower() for kw in tinodaishe_keywords):
        result_container = []
        def _scrape():
            result_container.append(_scrape_tinodaishe())
        t = threading.Thread(target=_scrape, daemon=True)
        t.start()
        t.join(timeout=5)
        if result_container:
            extra_context = result_container[0]

    # Pick model — use vision model when image is attached
    model = GROQ_VISION_MODEL if image_b64 else GROQ_TEXT_MODEL

    # Build and send request
    try:
        client = GroqClient(api_key=api_key)
        messages = _build_messages(history, message, image_b64 if image_b64 else None, mime, extra_context)

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1200,
            temperature=0.72,
        )

        reply = completion.choices[0].message.content or "I couldn't generate a response. Please try again."
        return JsonResponse({"reply": reply, "remaining": remaining, "status": "ok"})

    except Exception as e:
        print(f"[Zuri] Groq API error: {e}")
        return JsonResponse(
            {
                "error": "ai_error",
                "message": "Zuri ran into a hiccup. Please try again in a moment.",
            },
            status=500,
        )
