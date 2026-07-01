"""
AI Tutor Service — Personalized learning paths, AI tutoring, and advanced analytics.
Powered by Groq for an interactive learning experience.
"""

import os
import json
import threading
from typing import Dict, List, Optional
from django.db.models import Avg, Count, Q
from .models import (
    CustomUser, ExamAttempt, Submission, Tutorial, VideoProgress, Classroom, Enrollment
)

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    Groq = None


class AITutorService:
    """
    Advanced AI tutoring and personalized learning service.
    """
    PRIMARY_MODEL = "openai/gpt-oss-120b"
    FALLBACK_MODEL = "qwen/qwen3.6-27b"

    def __init__(self):
        self.groq_key = os.environ.get("GROQ_API_KEY", "").strip().strip('"\'')
        self.enabled = bool(self.groq_key and HAS_GROQ)
        self.groq_client = Groq(api_key=self.groq_key) if self.enabled else None

    def is_enabled(self) -> bool:
        return self.enabled

    def _call_groq_with_fallback(self, messages, temperature, max_tokens):
        """Call Groq API with primary and fallback models"""
        models_to_try = [self.PRIMARY_MODEL, self.FALLBACK_MODEL]
        last_error = None
        
        for model in models_to_try:
            try:
                return self.groq_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            except Exception as e:
                print(f"[AI Tutor] Error with model {model}: {e}")
                last_error = e
        
        # If both models failed
        raise last_error or Exception("All models failed")

    # ------------------------------------------------------------------
    # AI Tutor Chat
    # ------------------------------------------------------------------

    def chat_with_tutor(
        self,
        user: CustomUser,
        message: str,
        context: Optional[str] = None
    ) -> Dict:
        """
        Have a conversation with the AI tutor about any topic.
        """
        if not self.is_enabled():
            return {
                "response": "I'm sorry, the AI tutor is currently unavailable. Please try again later.",
                "suggestions": []
            }

        # Build user profile context
        user_profile = self._build_user_profile(user)

        system_prompt = f"""You are Bluewave Academy's friendly and knowledgeable AI tutor.
Your goal is to help students learn effectively. Be encouraging, clear, and thorough.

STUDENT PROFILE:
{user_profile}

Respond in a conversational, helpful way. Keep answers concise but thorough.
If the student asks about a specific topic, provide explanations, examples, and practice suggestions.
Always encourage the student and offer additional help."""

        prompt = f"Student question: {message}\n\n"
        if context:
            prompt += f"Context from previous conversation: {context}\n\n"
        prompt += "Please help the student with their question."

        try:
            response = self._call_groq_with_fallback(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            content = response.choices[0].message.content

            return {
                "response": content,
                "suggestions": self._generate_suggestions(message)
            }
        except Exception as e:
            print(f"[AI Tutor] Error: {e}")
            return {
                "response": "I'm having trouble responding right now. Please try again in a moment.",
                "suggestions": []
            }

    # ------------------------------------------------------------------
    # Personalized Learning Paths
    # ------------------------------------------------------------------

    def generate_learning_path(self, user: CustomUser, topic: Optional[str] = None) -> Dict:
        """
        Generate a personalized learning path based on the student's performance.
        """
        profile = self._analyze_student_performance(user)

        if not self.is_enabled():
            return self._generate_fallback_path(profile, topic)

        prompt = f"""You are an expert learning path designer. Create a personalized learning path for this student.

STUDENT PROFILE & PERFORMANCE:
{json.dumps(profile, indent=2)}

TOPIC FOCUS: {topic or "All subjects"}

Create a 4-week learning path with:
1. Weekly goals
2. Specific resources (tutorials, practice problems)
3. Milestone checkpoints
4. Recommended study schedule

Return as JSON:
{{
  "title": "<path title>",
  "duration_weeks": 4,
  "weeks": [
    {{
      "week": 1,
      "focus": "<topic focus>",
      "goals": ["<goal 1>", "<goal 2>"],
      "resources": ["<resource 1>", "<resource 2>"],
      "milestone": "<what to achieve this week>"
    }}
  ],
  "recommendations": ["<tip 1>", "<tip 2>"],
  "weak_areas": ["<area to improve>"],
  "strong_areas": ["<strength area>"]
}}"""

        try:
            response = self._call_groq_with_fallback(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            return self._parse_json_response(response.choices[0].message.content)
        except Exception as e:
            print(f"[Learning Path] Error: {e}")
            return self._generate_fallback_path(profile, topic)

    # ------------------------------------------------------------------
    # Performance Analysis
    # ------------------------------------------------------------------

    def _analyze_student_performance(self, user: CustomUser) -> Dict:
        """
        Analyze the student's performance across all exams and assignments.
        """
        # Exam performance
        exam_attempts = ExamAttempt.objects.filter(student=user, status="graded")
        exam_avg = exam_attempts.aggregate(Avg("percentage"))["percentage__avg"] or 0

        # Assignment performance
        submissions = Submission.objects.filter(student=user, status="graded")
        submission_avg = submissions.aggregate(Avg("ai_percentage"))["ai_percentage__avg"] or 0

        # Progress on tutorials
        video_progress = VideoProgress.objects.filter(student=user)
        completed_tutorials = video_progress.filter(completed=True).count()
        total_tutorials = Tutorial.objects.filter(status="published").count()

        # Enrolled classrooms
        enrollments = Enrollment.objects.filter(student=user, is_active=True)

        # Category performance
        category_performance = {}
        for attempt in exam_attempts:
            cat = attempt.exam.category
            if cat not in category_performance:
                category_performance[cat] = []
            if attempt.percentage:
                category_performance[cat].append(float(attempt.percentage))

        avg_by_category = {}
        for cat, scores in category_performance.items():
            avg_by_category[cat] = sum(scores) / len(scores) if scores else 0

        return {
            "user_id": user.id,
            "username": user.username,
            "level": user.current_level,
            "exam_avg": round(exam_avg, 2),
            "assignment_avg": round(submission_avg, 2),
            "completed_tutorials": completed_tutorials,
            "total_tutorials": total_tutorials,
            "enrolled_classrooms": [e.classroom.name for e in enrollments],
            "category_performance": avg_by_category,
            "total_exams_taken": exam_attempts.count(),
            "total_assignments_submitted": submissions.count()
        }

    def get_student_insights(self, user: CustomUser) -> Dict:
        """
        Get detailed insights and recommendations for the student.
        """
        profile = self._analyze_student_performance(user)

        # Identify weak and strong areas
        weak_areas = []
        strong_areas = []

        for cat, avg in profile["category_performance"].items():
            if avg < 60:
                weak_areas.append(cat)
            elif avg > 80:
                strong_areas.append(cat)

        return {
            "profile": profile,
            "weak_areas": weak_areas,
            "strong_areas": strong_areas,
            "recommendations": self._generate_recommendations(profile, weak_areas, strong_areas)
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_user_profile(self, user: CustomUser) -> str:
        profile = f"""Name: {user.get_full_name() or user.username}
Level: {user.current_level}
School: {user.school or 'Not specified'}
Student ID: {user.student_id or 'N/A'}"""
        return profile

    def _generate_suggestions(self, message: str) -> List[str]:
        """Generate follow-up suggestions based on the conversation."""
        base_suggestions = [
            "Can you give me more examples?",
            "What should I practice next?",
            "Explain this in simpler terms",
            "Give me a practice problem"
        ]
        return base_suggestions[:3]

    def _generate_fallback_path(self, profile: Dict, topic: Optional[str]) -> Dict:
        """Fallback learning path if AI is unavailable."""
        return {
            "title": f"Personalized Learning Path{' for ' + topic if topic else ''}",
            "duration_weeks": 4,
            "weeks": [
                {
                    "week": 1,
                    "focus": "Foundational Concepts",
                    "goals": ["Review basics", "Complete introductory tutorials"],
                    "resources": ["Browse available tutorials", "Practice past exam questions"],
                    "milestone": "Complete 2 tutorials"
                },
                {
                    "week": 2,
                    "focus": "Practice & Application",
                    "goals": ["Solve practice problems", "Apply concepts"],
                    "resources": ["Try practice exams", "Work on assignments"],
                    "milestone": "Score 70% on a practice exam"
                },
                {
                    "week": 3,
                    "focus": "Advanced Topics",
                    "goals": ["Learn advanced concepts", "Build projects"],
                    "resources": ["Advanced tutorials", "Project-based learning"],
                    "milestone": "Complete a small project"
                },
                {
                    "week": 4,
                    "focus": "Review & Assessment",
                    "goals": ["Review everything", "Take assessment"],
                    "resources": ["Review notes", "Take final assessment"],
                    "milestone": "Complete comprehensive assessment"
                }
            ],
            "recommendations": ["Consistent daily practice", "Ask instructors for help when stuck"],
            "weak_areas": [],
            "strong_areas": []
        }

    def _generate_recommendations(self, profile: Dict, weak_areas: List, strong_areas: List) -> List[str]:
        recommendations = []

        if profile["exam_avg"] < 70:
            recommendations.append("Focus on understanding core concepts before taking more exams")
        if weak_areas:
            recommendations.append(f"Spend extra time on: {', '.join(weak_areas)}")
        if strong_areas:
            recommendations.append(f"You're doing great in {', '.join(strong_areas)} — consider tutoring others!")
        if profile["completed_tutorials"] < profile["total_tutorials"] * 0.5:
            recommendations.append("Try to complete more tutorials to build your knowledge")

        if not recommendations:
            recommendations = ["Keep up the good work!", "Consistency is key to success"]

        return recommendations

    def _parse_json_response(self, text: str) -> Dict:
        """Parse and clean JSON response from AI."""
        try:
            clean = text.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            return json.loads(clean.strip())
        except Exception:
            return {
                "title": "Personalized Learning Path",
                "duration_weeks": 4,
                "weeks": [],
                "recommendations": ["Focus on your studies and ask your instructor for guidance"],
                "weak_areas": [],
                "strong_areas": []
            }


# Singleton instance
_tutor_lock = threading.Lock()
_tutor_service: Optional[AITutorService] = None


def get_tutor_service() -> AITutorService:
    global _tutor_service
    if _tutor_service is None:
        with _tutor_lock:
            if _tutor_service is None:
                _tutor_service = AITutorService()
    return _tutor_service