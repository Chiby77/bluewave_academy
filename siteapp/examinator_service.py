"""
The Examinator — AI Grading Service
Powered by Groq (llama-3.3-70b-versatile / moonshotai/kimi-k2-instruct)
Grades text, code, essay and PDF submissions with fallback keyword scoring.
"""

import os
import json
import threading
from decimal import Decimal
from typing import Dict, Optional

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    Groq = None

try:
    import pypdf
    import io
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


# Valid Groq model IDs (verified against https://console.groq.com/docs/models)
GROQ_PRIMARY_MODEL   = "llama-3.3-70b-versatile"   # Best quality, fast
GROQ_SECONDARY_MODEL = "llama3-70b-8192"            # Reliable fallback
GROQ_FALLBACK_MODEL  = "llama3-8b-8192"             # Fastest, always available


class GroqGradingService:
    """
    Unified AI grading engine using Groq.
    Grades text, code, and PDF submissions against instructor rubrics.
    Falls back to keyword matching if Groq is unavailable.
    """

    def __init__(self):
        # Re-read env var every time so the singleton picks up the key
        self.api_key = os.environ.get("GROQ_API_KEY", "").strip().strip('"\'')
        self.enabled = bool(self.api_key and HAS_GROQ)
        self.client = Groq(api_key=self.api_key) if self.enabled else None

    def is_enabled(self) -> bool:
        # Always re-check so a stale singleton is never stuck as disabled
        api_key = os.environ.get("GROQ_API_KEY", "").strip().strip('"\'')
        if api_key and HAS_GROQ and not self.enabled:
            self.api_key = api_key
            self.enabled = True
            self.client = Groq(api_key=self.api_key)
        return self.enabled

    # ------------------------------------------------------------------
    # Public grading methods
    # ------------------------------------------------------------------

    def grade_text_submission(
        self,
        question: str,
        rubric: str,
        answer_key: str,
        student_answer: str,
        total_marks: int,
    ) -> Dict:
        """Grade a text / short-answer / essay submission."""
        self.is_enabled()  # re-check in case singleton was stale
        if not self.enabled or not student_answer.strip():
            return self._offline_grade(student_answer, answer_key, total_marks)

        prompt = f"""You are a fair and rigorous academic grader.

QUESTION:
{question}

MARKING RUBRIC:
{rubric or "Award marks based on accuracy, completeness, and clarity."}

MODEL ANSWER:
{answer_key}

STUDENT'S ANSWER:
{student_answer}

TOTAL MARKS: {total_marks}

Return ONLY valid JSON:
{{
  "score": <integer 0-{total_marks}>,
  "percentage": <float>,
  "is_correct": <boolean>,
  "feedback": "<2-3 sentence summary>",
  "strengths": ["<point 1>", "<point 2>"],
  "improvements": ["<area 1>", "<area 2>"],
  "improvement_tips": ["<tip 1>", "<tip 2>"],
  "reasoning": "<detailed grading explanation>"
}}"""
        return self._call_groq(prompt, total_marks,
                               student_answer=student_answer, reference=answer_key)

    def grade_code_submission(
        self,
        question: str,
        rubric: str,
        expected_output: str,
        student_code: str,
        language: str,
        total_marks: int,
    ) -> Dict:
        """Grade a programming / code submission."""
        self.is_enabled()  # re-check in case singleton was stale
        if not self.enabled or not student_code.strip():
            return self._offline_grade(student_code, expected_output, total_marks)

        prompt = f"""You are an expert software engineer grading a student's programming exam.

QUESTION:
{question}

LANGUAGE: {language}

RUBRIC:
{rubric or "Award marks for correct logic, syntax, efficiency, and edge case handling."}

EXPECTED OUTPUT / SOLUTION:
{expected_output}

STUDENT'S CODE:
```{language}
{student_code}
```

TOTAL MARKS: {total_marks}

Return ONLY valid JSON:
{{
  "score": <integer 0-{total_marks}>,
  "percentage": <float>,
  "is_correct": <boolean>,
  "has_syntax_errors": <boolean>,
  "feedback": "<concise summary>",
  "strengths": ["<point 1>", "<point 2>"],
  "improvements": ["<area 1>", "<area 2>"],
  "improvement_tips": ["<tip 1>", "<tip 2>"],
  "reasoning": "<detailed explanation>"
}}"""
        return self._call_groq(prompt, total_marks,
                               student_answer=student_code, reference=expected_output)

    def grade_pdf_submission(
        self,
        question: str,
        rubric: str,
        answer_key: str,
        pdf_bytes: bytes,
        total_marks: int,
    ) -> Dict:
        """Grade a PDF submission by extracting text then grading via Groq."""
        pdf_text = self._extract_pdf_text(pdf_bytes)

        if not pdf_text or pdf_text.startswith("["):
            # Could not extract text — queue for manual review
            return self._get_pending_response(total_marks)

        return self.grade_text_submission(
            question=question,
            rubric=rubric,
            answer_key=answer_key,
            student_answer=pdf_text,
            total_marks=total_marks,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_groq(self, prompt: str, total_marks: int,
                   student_answer: str = "", reference: str = "") -> Dict:
        """Call Groq API with automatic model fallback.
        Always produces a usable score — falls back to keyword matching on
        total API failure rather than returning zeros.
        """
        models_to_try = [GROQ_PRIMARY_MODEL, GROQ_SECONDARY_MODEL, GROQ_FALLBACK_MODEL]

        last_error = None
        for model in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert academic grader. Return only valid JSON as instructed.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=1200,
                )
                return self._parse_response(
                    response.choices[0].message.content, total_marks,
                    student_answer=student_answer, reference=reference,
                )
            except Exception as e:
                last_error = e
                print(f"[Groq Grading] Model {model} failed: {e}")
                continue

        # All models failed — keyword fallback, never zeros
        print(f"[Groq Grading] All models failed. Using offline fallback. Last error: {last_error}")
        return self._offline_grade(student_answer or "", reference or "", total_marks)

    def _parse_response(self, text: str, total_marks: int,
                        student_answer: str = "", reference: str = "") -> Dict:
        try:
            clean = text.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()

            data = json.loads(clean)
            score = max(0, min(int(data.get("score", 0)), total_marks))
            percentage = round((score / total_marks) * 100, 2) if total_marks > 0 else 0.0

            return {
                "score": Decimal(str(score)),
                "percentage": percentage,
                "is_correct": data.get("is_correct", score >= total_marks * 0.8),
                "feedback": data.get("feedback", "Graded by AI."),
                "strengths": data.get("strengths", []),
                "improvements": data.get("improvements", []),
                "improvement_tips": data.get("improvement_tips", []),
                "reasoning": data.get("reasoning", ""),
                "has_syntax_errors": data.get("has_syntax_errors", False),
            }
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[Groq Grading] Parse error: {e} | Raw: {text[:300]}")
            # Fall back to keyword matching — never return zeros
            return self._offline_grade(student_answer, reference, total_marks)

    def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        if not HAS_PYPDF:
            return "[PDF processing unavailable — install pypdf]"
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            pages = []
            for i, page in enumerate(reader.pages[:40]):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"--- Page {i + 1} ---\n{text.strip()}")
            return "\n\n".join(pages) if pages else "[No extractable text in PDF — may be scanned image]"
        except Exception as e:
            return f"[Could not read PDF: {e}]"

    # ------------------------------------------------------------------
    # Fallback responses
    # ------------------------------------------------------------------

    def _offline_grade(self, student_answer: str, reference: str, total_marks: int) -> Dict:
        """Keyword-matching fallback when Groq is unavailable."""
        student_lower = student_answer.lower()
        ref_lower = reference.lower()
        keywords = {w for w in ref_lower.split() if len(w) > 3}
        if keywords:
            matched = sum(1 for w in keywords if w in student_lower)
            ratio = matched / len(keywords)
        else:
            ratio = 0.5
        score = max(0, min(round(ratio * total_marks), total_marks))
        return {
            "score": Decimal(str(score)),
            "percentage": round((score / total_marks) * 100, 2) if total_marks else 0,
            "is_correct": score >= total_marks * 0.6,
            "feedback": f"Graded offline (AI unavailable). {score}/{total_marks} marks awarded. Manual review recommended.",
            "strengths": [],
            "improvements": ["Manual review by instructor recommended for accurate grading."],
            "improvement_tips": [],
            "reasoning": "Offline keyword-matching — Groq AI not available.",
            "has_syntax_errors": False,
        }

    def _get_pending_response(self, total_marks: int) -> Dict:
        return {
            "score": Decimal("0"),
            "percentage": 0.0,
            "is_correct": False,
            "feedback": "PDF submission received. Awaiting manual grading by your instructor.",
            "strengths": [],
            "improvements": [],
            "improvement_tips": [],
            "reasoning": "Could not extract text from PDF. Manual grading required.",
            "has_syntax_errors": False,
        }

    def _get_error_response(self, total_marks: int, student_answer: str = "", reference: str = "") -> Dict:
        """On API error, fall back to keyword matching rather than returning zeros."""
        if student_answer and reference:
            return self._offline_grade(student_answer, reference, total_marks)
        return {
            "score": Decimal("0"),
            "percentage": 0.0,
            "is_correct": False,
            "feedback": "Grading encountered an error. Keyword fallback was used.",
            "strengths": [],
            "improvements": [],
            "improvement_tips": [],
            "reasoning": "AI grading error — fallback to keyword scoring.",
            "has_syntax_errors": False,
        }


# Thread-safe singleton
_service_lock = threading.Lock()
_service: Optional[GroqGradingService] = None


def get_grading_service() -> GroqGradingService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = GroqGradingService()
    return _service
