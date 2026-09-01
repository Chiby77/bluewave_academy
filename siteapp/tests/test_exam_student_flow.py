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
)


class ExamStudentFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = CustomUser.objects.create_user(
            username="student_alice",
            email="alice@test.com",
            password="Password123!",
            first_name="Alice",
            last_name="Moyo",
            school="St George College",
        )
        self.instructor = CustomUser.objects.create_user(
            username="instructor_bob",
            email="bob@test.com",
            password="Password123!",
            is_staff=True,
        )

        now = timezone.now()
        self.exam = Exam.objects.create(
            title="Introduction to Programming",
            description="Python syntax and basics",
            duration_minutes=30,
            total_marks=20,
            passing_marks=10,
            category="python",
            level="beginner",
            is_active=True,
            is_held=False,
            start_date=now - datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=2),
            created_by=self.instructor,
        )

        self.q_mcq = Question.objects.create(
            exam=self.exam,
            question_text="What is the output of print(2**3)?",
            question_type="mcq",
            option_a="6",
            option_b="8",
            option_c="9",
            option_d="5",
            correct_answer="B",
            marks=10,
            order=1,
        )

        self.q_essay = Question.objects.create(
            exam=self.exam,
            question_text="Explain Python list comprehension with an example.",
            question_type="essay",
            correct_answer="List comprehension provides a concise way to create lists like [x for x in range(5)].",
            marks=10,
            order=2,
        )

    def test_unauthenticated_user_redirected(self):
        """Unauthenticated student cannot view exams or take exams."""
        res = self.client.get(reverse("siteapp:exam_list"))
        self.assertEqual(res.status_code, 302)

        res_take = self.client.get(reverse("siteapp:take_exam", args=[self.exam.id]))
        self.assertEqual(res_take.status_code, 302)

    def test_student_exam_list_view(self):
        """Authenticated student can view available exams."""
        self.client.login(username="student_alice", password="Password123!")
        res = self.client.get(reverse("siteapp:exam_list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Introduction to Programming")

    def test_student_take_exam_creates_attempt(self):
        """Visiting take_exam initializes attempt #1 in progress."""
        self.client.login(username="student_alice", password="Password123!")
        res = self.client.get(reverse("siteapp:take_exam", args=[self.exam.id]))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, self.q_mcq.question_text)

        attempts = ExamAttempt.objects.filter(student=self.student, exam=self.exam)
        self.assertEqual(attempts.count(), 1)
        attempt = attempts.first()
        self.assertEqual(attempt.attempt_number, 1)
        self.assertEqual(attempt.status, "in_progress")

    def test_student_submit_exam_and_instant_grading(self):
        """Submitting exam via AJAX grades MCQ and subjective questions."""
        self.client.login(username="student_alice", password="Password123!")

        # Start attempt
        self.client.get(reverse("siteapp:take_exam", args=[self.exam.id]))

        # Mock the Groq AI grading service so test runs reliably without external network dependency
        mock_ai_result = {
            "score": Decimal("8"),
            "percentage": 80.0,
            "is_correct": True,
            "feedback": "Clear explanation with accurate syntax.",
            "strengths": ["Clear syntax"],
            "improvements": ["Could mention performance"],
            "reasoning": "Good answer.",
        }

        with patch("siteapp.examinator_service.GroqGradingService.grade_text_submission", return_value=mock_ai_result):
            post_data = {
                f"question_{self.q_mcq.id}": "B",
                f"question_{self.q_essay.id}": "List comprehension simplifies creating lists, e.g. [x**2 for x in range(10)].",
            }
            res = self.client.post(
                reverse("siteapp:submit_exam", args=[self.exam.id]),
                data=post_data,
            )

            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data.get("success"))

        # Verify attempt was updated to graded
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam, attempt_number=1)
        self.assertEqual(attempt.status, "graded")
        # MCQ (10) + Essay (8) = 18 marks out of 20 = 90%
        self.assertEqual(attempt.score, Decimal("18.00"))
        self.assertEqual(attempt.percentage, Decimal("90.00"))
        self.assertTrue(attempt.is_passed())

    def test_max_two_attempts_policy_enforcement(self):
        """Student cannot take an exam more than 2 times."""
        # Attempt 1
        ExamAttempt.objects.create(
            student=self.student,
            exam=self.exam,
            attempt_number=1,
            status="graded",
            score=Decimal("12.00"),
        )
        # Attempt 2
        attempt2 = ExamAttempt.objects.create(
            student=self.student,
            exam=self.exam,
            attempt_number=2,
            status="graded",
            score=Decimal("15.00"),
        )

        self.client.login(username="student_alice", password="Password123!")
        res = self.client.get(reverse("siteapp:take_exam", args=[self.exam.id]))

        # Must redirect to results page of the last attempt
        self.assertEqual(res.status_code, 302)
        self.assertIn(f"/student/exam/results/{attempt2.id}/", res.url)
