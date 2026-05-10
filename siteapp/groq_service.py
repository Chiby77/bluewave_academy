"""
Groq AI Grading Service for non-MCQ exam questions
Provides intelligent grading and feedback using Groq API
"""

import os
import json
from typing import Dict, Tuple
from decimal import Decimal

try:
    from groq import Groq
except ImportError:
    print("Warning: Groq package not installed. Install with: pip install groq")
    Groq = None


class GroqGradingService:
    """Service for grading non-MCQ answers using Groq AI"""

    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.enabled = self.api_key is not None and Groq is not None

        if self.enabled:
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None

    def is_enabled(self) -> bool:
        """Check if Groq service is enabled"""
        return self.enabled

    def grade_answer(
        self,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        total_marks: int,
        question_type: str,
    ) -> Dict:
        """
        Grade a student's answer using Groq AI

        Args:
            question_text: The exam question
            correct_answer: The expected/model answer
            student_answer: Student's submitted answer
            total_marks: Total marks for this question
            question_type: Type of question (essay, short_answer, code)

        Returns:
            {
                'score': Decimal score (0-total_marks),
                'feedback': str feedback message,
                'reasoning': str detailed reasoning,
                'is_correct': bool whether substantially correct,
                'strengths': list of correct points,
                'improvements': list of areas to improve
            }
        """

        if not self.enabled:
            return self._get_offline_response(
                question_text, correct_answer, student_answer, total_marks
            )

        try:
            prompt = self._build_grading_prompt(
                question_text,
                correct_answer,
                student_answer,
                total_marks,
                question_type,
            )

            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",  # Use appropriate model
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educator grading student exam answers. Provide fair, constructive feedback.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=1000,
            )

            result = response.choices[0].message.content
            parsed_result = self._parse_groq_response(result, total_marks)

            return parsed_result

        except Exception as e:
            print(f"Error calling Groq API: {str(e)}")
            return self._get_offline_response(
                question_text, correct_answer, student_answer, total_marks
            )

    def _build_grading_prompt(
        self,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        total_marks: int,
        question_type: str,
    ) -> str:
        """Build the grading prompt for Groq"""

        type_description = {
            "short_answer": "short answer (1-5 sentences)",
            "essay": "essay (multiple paragraphs)",
            "code": "programming code",
        }.get(question_type, "answer")

        prompt = f"""
You are grading a student's {type_description} on an exam.

QUESTION:
{question_text}

EXPECTED/MODEL ANSWER:
{correct_answer}

STUDENT'S ANSWER:
{student_answer}

TOTAL MARKS AVAILABLE: {total_marks}

Please grade this answer and provide your response in the following JSON format:
{{
    "score": (integer from 0 to {total_marks}, based on correctness and completeness),
    "is_correct": (boolean - is the answer substantially correct?),
    "feedback": (brief feedback, 1-2 sentences),
    "reasoning": (detailed explanation of the grade),
    "strengths": (list of 1-3 correct/good points in the answer),
    "improvements": (list of 1-3 areas that could be improved)
}}

Be fair but rigorous. 
- Full marks for completely correct answers
- Partial marks for partially correct answers
- Zero marks for completely wrong or blank answers

Provide ONLY the JSON response, no additional text.
"""
        return prompt

    def _parse_groq_response(self, response: str, total_marks: int) -> Dict:
        """Parse Groq's JSON response"""

        try:
            # Try to extract JSON from response
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]

            data = json.loads(response_clean)

            # Ensure score is within bounds
            score = min(int(data.get("score", 0)), total_marks)
            score = max(score, 0)

            return {
                "score": Decimal(str(score)),
                "feedback": data.get("feedback", "Graded by AI"),
                "reasoning": data.get("reasoning", ""),
                "is_correct": data.get("is_correct", score >= (total_marks * 0.8)),
                "strengths": data.get("strengths", []),
                "improvements": data.get("improvements", []),
            }

        except json.JSONDecodeError:
            print(f"Failed to parse Groq response: {response}")
            return self._get_default_response(total_marks)

    def _get_offline_response(
        self,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        total_marks: int,
    ) -> Dict:
        """
        Provide a basic grading when Groq is not available
        Uses keyword matching and length comparison
        """

        student_text_lower = student_answer.lower()
        correct_text_lower = correct_answer.lower()

        # Extract keywords from correct answer
        keywords = set(correct_text_lower.split())
        keywords = {w for w in keywords if len(w) > 3}  # Only meaningful words

        # Check matching keywords
        matches = sum(1 for w in keywords if w in student_text_lower)
        match_ratio = matches / len(keywords) if keywords else 0

        # Check length (rough estimate)
        correct_length = len(correct_text_lower)
        student_length = len(student_text_lower)
        length_ratio = student_length / correct_length if correct_length > 0 else 0
        length_ratio = min(length_ratio, 1.0)

        # Calculate score
        score = (match_ratio * 0.6 + length_ratio * 0.4) * total_marks
        score = Decimal(str(round(score)))

        return {
            "score": score,
            "feedback": f"Answer processed offline. {score} of {total_marks} marks awarded.",
            "reasoning": "Graded based on keyword matching and answer completeness.",
            "is_correct": score >= (total_marks * 0.8),
            "strengths": [],
            "improvements": [],
        }

    def _get_default_response(self, total_marks: int) -> Dict:
        """Get default response on error"""
        return {
            "score": Decimal("0"),
            "feedback": "Grading error. Please contact administrator.",
            "reasoning": "Could not process answer grading.",
            "is_correct": False,
            "strengths": [],
            "improvements": [],
        }

    def grade_code_answer(
        self,
        question_text: str,
        expected_behavior: str,
        student_code: str,
        total_marks: int,
    ) -> Dict:
        """
        Grade programming code
        Checks for syntax, logic, and output
        """

        prompt = f"""
You are grading student programming code.

QUESTION:
{question_text}

EXPECTED BEHAVIOR/SOLUTION:
{expected_behavior}

STUDENT'S CODE:
```
{student_code}
```

TOTAL MARKS: {total_marks}

Evaluate the code on:
1. Syntax correctness (does it have valid syntax?)
2. Logic correctness (does it implement the right algorithm?)
3. Efficiency (is it reasonably efficient?)
4. Edge cases (does it handle edge cases?)

Provide response as JSON:
{{
    "score": (integer from 0 to {total_marks}),
    "has_syntax_errors": boolean,
    "logic_correct": boolean,
    "feedback": (brief feedback),
    "reasoning": (detailed explanation),
    "strengths": ["point1", "point2"],
    "improvements": ["area1", "area2"]
}}

Provide ONLY the JSON response.
"""

        if not self.enabled:
            # Offline code analysis
            return self._analyze_code_offline(student_code, total_marks)

        try:
            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert programmer grading student code.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1000,
            )

            result = response.choices[0].message.content
            return self._parse_groq_response(result, total_marks)

        except Exception as e:
            print(f"Error grading code: {str(e)}")
            return self._analyze_code_offline(student_code, total_marks)

    def _analyze_code_offline(self, code: str, total_marks: int) -> Dict:
        """Basic offline code analysis"""

        # Check for basic syntax issues
        has_errors = False
        error_indicators = ["SyntaxError", "IndentationError", "NameError"]

        for indicator in error_indicators:
            if indicator.lower() in code.lower():
                has_errors = True
                break

        # Check for common patterns
        score = total_marks // 2  # Base score

        if not has_errors:
            score += total_marks // 4

        if any(keyword in code for keyword in ["if", "for", "while", "def"]):
            score += total_marks // 8

        score = min(score, total_marks)

        return {
            "score": Decimal(str(score)),
            "feedback": "Code analyzed offline. Manual review recommended.",
            "reasoning": "Offline analysis based on syntax patterns.",
            "is_correct": not has_errors,
            "strengths": [],
            "improvements": ["Manual review recommended"],
        }


# Singleton instance
_groq_service = None


def get_groq_service() -> GroqGradingService:
    """Get or create Groq grading service instance"""
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqGradingService()
    return _groq_service
