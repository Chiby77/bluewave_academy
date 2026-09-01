import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from siteapp.models import (
    CustomUser,
    Exam,
    Question,
    ExamAttempt,
    Answer,
    ExamGrading,
    ExamHold,
    Classroom,
    Enrollment,
    Assignment,
    Submission,
    SpecialPaper,
    Material,
    Notification,
    Tutorial,
    VideoProgress,
    Course,
    CourseLesson,
    CourseEnrollment,
)


class ModelTests(TestCase):
    def setUp(self):
        self.student = CustomUser.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="Password123!",
            first_name="Alice",
            last_name="Smith",
            school="Harare High",
            current_level="intermediate",
        )
        self.instructor = CustomUser.objects.create_user(
            username="teacher1",
            email="teacher1@test.com",
            password="Password123!",
            first_name="Bob",
            last_name="Jones",
            is_staff=True,
        )

    def test_custom_user_student_id_generation(self):
        """Verify student_id auto-generation format BW{year}001."""
        self.assertTrue(self.student.student_id.startswith(f"BW{timezone.now().year}"))
        self.assertEqual(len(self.student.student_id), 9)

        # Third user gets incremental ID because instructor also got an ID
        student2 = CustomUser.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="Password123!",
            school="Bulawayo Academy",
        )
        self.assertEqual(int(student2.student_id[-3:]), int(self.instructor.student_id[-3:]) + 1)

    def test_exam_availability(self):
        """Test is_available() logic based on time window and active flag."""
        now = timezone.now()
        active_exam = Exam.objects.create(
            title="Python Fundamentals",
            description="Basics of Python",
            duration_minutes=60,
            total_marks=100,
            passing_marks=50,
            is_active=True,
            start_date=now - datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=1),
            created_by=self.instructor,
        )
        self.assertTrue(active_exam.is_available())

        # Expired exam
        expired_exam = Exam.objects.create(
            title="Expired Exam",
            description="Past exam",
            duration_minutes=30,
            is_active=True,
            start_date=now - datetime.timedelta(days=10),
            end_date=now - datetime.timedelta(days=5),
            created_by=self.instructor,
        )
        self.assertFalse(expired_exam.is_available())

        # Inactive exam
        inactive_exam = Exam.objects.create(
            title="Inactive Exam",
            description="Draft",
            duration_minutes=30,
            is_active=False,
            start_date=now - datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=1),
            created_by=self.instructor,
        )
        self.assertFalse(inactive_exam.is_available())

    def test_question_choices(self):
        """Test get_choices property for MCQ questions."""
        now = timezone.now()
        exam = Exam.objects.create(
            title="CS101",
            description="Intro",
            duration_minutes=45,
            start_date=now - datetime.timedelta(hours=1),
            end_date=now + datetime.timedelta(hours=1),
            created_by=self.instructor,
        )
        q = Question.objects.create(
            exam=exam,
            question_text="What is 2 + 2?",
            question_type="mcq",
            option_a="3",
            option_b="4",
            option_c="5",
            option_d="",
            correct_answer="B",
            marks=5,
        )
        choices = q.get_choices
        self.assertEqual(choices, [("A", "3"), ("B", "4"), ("C", "5")])

    def test_exam_attempt_and_answer_scoring(self):
        """Test scoring calculations, MCQ checks, and passing status."""
        now = timezone.now()
        exam = Exam.objects.create(
            title="Math Exam",
            description="Maths",
            duration_minutes=30,
            total_marks=20,
            passing_marks=10,
            start_date=now - datetime.timedelta(hours=1),
            end_date=now + datetime.timedelta(hours=1),
            created_by=self.instructor,
        )
        q1 = Question.objects.create(
            exam=exam,
            question_text="Is Python interpreted?",
            question_type="true_false",
            correct_answer="True",
            marks=10,
            order=1,
        )
        q2 = Question.objects.create(
            exam=exam,
            question_text="Which keyword defines a function in Python?",
            question_type="mcq",
            option_a="func",
            option_b="def",
            option_c="function",
            option_d="define",
            correct_answer="B",
            marks=10,
            order=2,
        )

        attempt = ExamAttempt.objects.create(
            student=self.student,
            exam=exam,
            attempt_number=1,
            status="in_progress",
        )

        ans1 = Answer.objects.create(attempt=attempt, question=q1, answer_text="True")
        ans2 = Answer.objects.create(attempt=attempt, question=q2, answer_text="B")

        self.assertTrue(ans1.check_answer())
        self.assertEqual(ans1.marks_obtained, 10)

        self.assertTrue(ans2.check_answer())
        self.assertEqual(ans2.marks_obtained, 10)

        attempt.calculate_score()
        self.assertEqual(attempt.score, 20)
        self.assertEqual(attempt.percentage, Decimal("100.00"))
        self.assertTrue(attempt.is_passed())

    def test_exam_hold_auto_resume(self):
        """Test ExamHold auto-resume logic."""
        now = timezone.now()
        exam = Exam.objects.create(
            title="Held Exam",
            description="Hold test",
            duration_minutes=30,
            is_held=True,
            start_date=now - datetime.timedelta(hours=1),
            end_date=now + datetime.timedelta(hours=1),
            created_by=self.instructor,
        )
        past_time = now - datetime.timedelta(minutes=10)
        future_time = now + datetime.timedelta(minutes=30)

        hold_expired = ExamHold.objects.create(
            exam=exam,
            held_by=self.instructor,
            reason="Maintenance",
            resume_at=past_time,
        )
        self.assertTrue(hold_expired.should_auto_resume())

        hold_expired.resume_at = future_time
        hold_expired.save()
        self.assertFalse(hold_expired.should_auto_resume())

    def test_classroom_and_submission(self):
        """Test Classroom, Assignment, and Submission lifecycle."""
        classroom = Classroom.objects.create(
            name="Web Dev 101",
            slug="web-dev-101",
            instructor=self.instructor,
        )
        enrollment = Enrollment.objects.create(
            student=self.student,
            classroom=classroom,
            is_active=True,
        )
        self.assertTrue(enrollment.is_active)

        assignment = Assignment.objects.create(
            classroom=classroom,
            title="HTML Form Assignment",
            assignment_type="text",
            created_by=self.instructor,
            deadline=timezone.now() + datetime.timedelta(days=7),
            total_marks=50,
            passing_marks=25,
        )

        submission = Submission.objects.create(
            student=self.student,
            assignment=assignment,
            text_answer="<form action='/submit'></form>",
            ai_score=Decimal("40.00"),
            status="graded",
        )
        self.assertEqual(submission.get_score(), Decimal("40.00"))
        self.assertEqual(submission.get_percentage(), 80.0)
        self.assertTrue(submission.is_passed())
