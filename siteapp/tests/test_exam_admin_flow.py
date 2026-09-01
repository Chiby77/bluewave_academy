import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from siteapp.models import (
    CustomUser,
    Exam,
    Question,
    ExamAttempt,
    Answer,
    ExamGrading,
    ExamHold,
)


class ExamAdminFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = CustomUser.objects.create_user(
            username="admin_user",
            email="admin@test.com",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="Super",
            is_staff=True,
            is_superuser=True,
        )
        self.student = CustomUser.objects.create_user(
            username="regular_student",
            email="student@test.com",
            password="Password123!",
            first_name="John",
            last_name="Doe",
        )

        now = timezone.now()
        self.exam = Exam.objects.create(
            title="Database Systems",
            description="SQL and normalization",
            duration_minutes=60,
            total_marks=50,
            passing_marks=25,
            category="database",
            level="intermediate",
            is_active=True,
            start_date=now - datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=5),
            created_by=self.admin_user,
        )

    def test_admin_dashboard_access_control(self):
        """Regular student cannot access admin dashboard; admin can."""
        # Unauthenticated
        res = self.client.get(reverse("siteapp:admin_dashboard"))
        self.assertEqual(res.status_code, 302)

        # Logged in as student
        self.client.login(username="regular_student", password="Password123!")
        res_student = self.client.get(reverse("siteapp:admin_dashboard"))
        self.assertEqual(res_student.status_code, 302)

        # Logged in as admin
        self.client.login(username="admin_user", password="AdminPassword123!")
        res_admin = self.client.get(reverse("siteapp:admin_dashboard"))
        self.assertEqual(res_admin.status_code, 200)

    def test_admin_create_exam(self):
        """Admin can create a new exam via POST."""
        self.client.login(username="admin_user", password="AdminPassword123!")
        now = timezone.now()
        data = {
            "title": "Computer Networks Final",
            "description": "OSI and TCP/IP models",
            "duration_minutes": 90,
            "total_marks": 100,
            "passing_marks": 50,
            "category": "Networks",
            "level": "advanced",
            "start_date": (now + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "end_date": (now + datetime.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
            "is_active": "on",
            "enable_instant_grading": "on",
            "show_answers_after_submit": "on",
        }
        res = self.client.post(reverse("siteapp:create_exam"), data=data)
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Exam.objects.filter(title="Computer Networks Final").exists())

    def test_admin_add_question_to_exam(self):
        """Admin can add MCQ and programming questions to an exam."""
        self.client.login(username="admin_user", password="AdminPassword123!")
        data = {
            "question_text": "Which SQL clause filters records after grouping?",
            "question_type": "mcq",
            "option_a": "WHERE",
            "option_b": "HAVING",
            "option_c": "ORDER BY",
            "option_d": "GROUP BY",
            "mcq_correct_answer": "B",
            "marks": 5,
        }
        res = self.client.post(
            reverse("siteapp:add_question", args=[self.exam.id]),
            data=data,
        )
        self.assertEqual(res.status_code, 302)
        self.assertTrue(
            Question.objects.filter(exam=self.exam, question_text__contains="SQL", option_b="HAVING").exists()
        )

    def test_admin_hold_and_resume_exam(self):
        """Admin can pause (hold) an exam and resume it."""
        self.client.login(username="admin_user", password="AdminPassword123!")
        
        # Hold exam
        res_hold = self.client.post(
            reverse("siteapp:hold_exam", args=[self.exam.id]),
            data={"reason": "Emergency syllabus audit"},
        )
        self.assertEqual(res_hold.status_code, 302)
        self.exam.refresh_from_db()
        self.assertTrue(self.exam.is_held)
        self.assertTrue(ExamHold.objects.filter(exam=self.exam, reason="Emergency syllabus audit").exists())

        # Resume exam
        res_resume = self.client.post(reverse("siteapp:resume_exam", args=[self.exam.id]))
        self.assertEqual(res_resume.status_code, 302)
        self.exam.refresh_from_db()
        self.assertFalse(self.exam.is_held)
        self.assertFalse(ExamHold.objects.filter(exam=self.exam).exists())

    def test_admin_grade_attempt_override(self):
        """Admin can review and manually override grading scores."""
        attempt = ExamAttempt.objects.create(
            student=self.student,
            exam=self.exam,
            attempt_number=1,
            status="submitted",
            score=Decimal("20.00"),
        )
        q = Question.objects.create(
            exam=self.exam,
            question_text="Describe 3NF.",
            question_type="essay",
            correct_answer="No transitive dependencies.",
            marks=20,
        )
        ans = Answer.objects.create(
            attempt=attempt,
            question=q,
            answer_text="Every non-prime attribute is non-transitively dependent on the primary key.",
            marks_obtained=Decimal("15.00"),
            ai_graded=True,
        )

        self.client.login(username="admin_user", password="AdminPassword123!")
        post_data = {
            f"score_{ans.id}": "19.00",
            f"feedback_{ans.id}": "Excellent definition and accurate explanation.",
        }
        res = self.client.post(
            reverse("siteapp:grade_attempt", args=[attempt.id]),
            data=post_data,
        )
        self.assertEqual(res.status_code, 302)

        ans.refresh_from_db()
        self.assertEqual(ans.marks_obtained, Decimal("19.00"))
        
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, "graded")
        self.assertEqual(attempt.score, Decimal("19.00"))
