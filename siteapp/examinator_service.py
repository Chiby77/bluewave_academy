"""
The Examinator — AI Grading Service
Powered by Google Gemini for intelligent, multimodal exam grading.
"""

import os
import json
import base64
from decimal import Decimal
from typing import Dict, Optional

try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GEMINI = True
except ImportError:
    try:
        import google.generativeai as genai
        genai_types = None
        HAS_GEMINI = True
    except ImportError:
        HAS_GEMINI = False
        genai = None
        genai_types = None


class GeminiGradingService:
    """
    AI grading engine using Google Gemini 1.5 Pro.
    Grades text, code, and PDF submissions against instructor rubrics.
    """

    MODEL_NAME = "gemini-2.0-flash"

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_AI_API_KEY")
        self.enabled = bool(self.api_key and HAS_GEMINI)
        if self.enabled:
            # New google.genai SDK
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def is_enabled(self) -> bool:
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
        if not self.enabled:
            return self._offline_grade(student_answer, answer_key, total_marks)

        prompt = self._build_text_prompt(question, rubric, answer_key, student_answer, total_marks)
        return self._call_gemini(prompt, total_marks)

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
        if not self.enabled:
            return self._offline_grade(student_code, expected_output, total_marks)

        prompt = self._build_code_prompt(
            question, rubric, expected_output, student_code, language, total_marks
        )
        return self._call_gemini(prompt, total_marks)

    def grade_pdf_submission(
        self,
        question: str,
        rubric: str,
        answer_key: str,
        pdf_bytes: bytes,
        total_marks: int,
    ) -> Dict:
        """Grade a PDF submission using Gemini's multimodal capability."""
        if not self.enabled:
            return self._get_pending_response(total_marks)

        try:
            encoded = base64.b64encode(pdf_bytes).decode("utf-8")
            user_prompt = self._build_pdf_prompt(question, rubric, answer_key, total_marks)

            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=[
                    genai_types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    user_prompt,
                ],
            )
            return self._parse_response(response.text, total_marks)
        except Exception as e:
            print(f"[Gemini PDF] Error: {e}")
            return self._get_pending_response(total_marks)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_text_prompt(self, question, rubric, answer_key, student_answer, total_marks) -> str:
        return f"""You are a fair and rigorous academic grader evaluating a student's exam answer.

QUESTION:
{question}

MARKING RUBRIC:
{rubric or "Award marks based on accuracy, completeness, and clarity."}

MODEL ANSWER / ANSWER KEY:
{answer_key}

STUDENT'S ANSWER:
{student_answer}

TOTAL MARKS: {total_marks}

Grade this answer strictly and fairly. Return ONLY valid JSON in this exact format:
{{
  "score": <integer 0–{total_marks}>,
  "percentage": <float>,
  "is_correct": <boolean>,
  "feedback": "<2–3 sentence summary of the grade>",
  "strengths": ["<point 1>", "<point 2>"],
  "improvements": ["<area 1>", "<area 2>"],
  "improvement_tips": ["<specific tip 1>", "<specific tip 2>"],
  "reasoning": "<detailed grading explanation>"
}}"""

    def _build_code_prompt(self, question, rubric, expected_output, student_code, language, total_marks) -> str:
        return f"""You are an expert software engineer and educator grading a student's programming exam.

QUESTION:
{question}

LANGUAGE: {language}

RUBRIC:
{rubric or "Award marks for correct logic, syntax, efficiency, and handling of edge cases."}

EXPECTED OUTPUT / SOLUTION:
{expected_output}

STUDENT'S CODE:
```{language}
{student_code}
```

TOTAL MARKS: {total_marks}

Evaluate: correctness, syntax, logic, efficiency, edge cases. Return ONLY valid JSON:
{{
  "score": <integer 0–{total_marks}>,
  "percentage": <float>,
  "is_correct": <boolean>,
  "has_syntax_errors": <boolean>,
  "feedback": "<concise summary>",
  "strengths": ["<point 1>", "<point 2>"],
  "improvements": ["<area 1>", "<area 2>"],
  "improvement_tips": ["<tip 1>", "<tip 2>"],
  "reasoning": "<detailed explanation>"
}}"""

    def _build_pdf_prompt(self, question, rubric, answer_key, total_marks) -> str:
        return f"""Grade the student's handwritten or typed exam answer in the attached PDF.

QUESTION:
{question}

RUBRIC:
{rubric or "Award marks based on accuracy, completeness, and clarity."}

MODEL ANSWER:
{answer_key}

TOTAL MARKS: {total_marks}

Return ONLY valid JSON:
{{
  "score": <integer 0–{total_marks}>,
  "percentage": <float>,
  "is_correct": <boolean>,
  "feedback": "<2–3 sentences>",
  "strengths": ["<point>"],
  "improvements": ["<area>"],
  "improvement_tips": ["<tip>"],
  "reasoning": "<explanation>"
}}"""

    def _call_gemini(self, prompt: str, total_marks: int) -> Dict:
        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
            )
            return self._parse_response(response.text, total_marks)
        except Exception as e:
            print(f"[Gemini] API error: {e}")
            return self._get_error_response(total_marks)

    def _parse_response(self, text: str, total_marks: int) -> Dict:
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
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"[Gemini] Parse error: {e}\nRaw: {text[:500]}")
            return self._get_error_response(total_marks)

    # ------------------------------------------------------------------
    # Offline / error responses
    # ------------------------------------------------------------------

    def _offline_grade(self, student_answer: str, reference: str, total_marks: int) -> Dict:
        """Basic keyword-matching fallback when Gemini is unavailable."""
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
            "feedback": f"Answer analysed offline. {score}/{total_marks} marks awarded. Manual review recommended.",
            "strengths": [],
            "improvements": ["Manual review by instructor recommended for accurate grading."],
            "improvement_tips": [],
            "reasoning": "Graded offline via keyword matching — AI service not available.",
            "has_syntax_errors": False,
        }

    def _get_pending_response(self, total_marks: int) -> Dict:
        return {
            "score": Decimal("0"),
            "percentage": 0.0,
            "is_correct": False,
            "feedback": "PDF submission received. Awaiting manual grading.",
            "strengths": [],
            "improvements": [],
            "improvement_tips": [],
            "reasoning": "Gemini AI not configured. Please grade manually.",
            "has_syntax_errors": False,
        }

    def _get_error_response(self, total_marks: int) -> Dict:
        return {
            "score": Decimal("0"),
            "percentage": 0.0,
            "is_correct": False,
            "feedback": "Grading error. Please contact your instructor.",
            "strengths": [],
            "improvements": [],
            "improvement_tips": [],
            "reasoning": "An error occurred during AI grading.",
            "has_syntax_errors": False,
        }


# Singleton
_service: Optional[GeminiGradingService] = None


def get_grading_service() -> GeminiGradingService:
    global _service
    if _service is None:
        _service = GeminiGradingService()
    return _service
