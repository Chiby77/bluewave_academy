import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from siteapp.models import (
    CustomUser,
    Classroom,
    Enrollment,
    Assignment,
    Submission,
    Material,
    SpecialPaper,
)


class ExaminatorClassroomTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.instructor = CustomUser.objects.create_user(
            username="teacher_tino",
            email="tino@test.com",
            password="Password123!",
            is_staff=True,
        )
        self.student = CustomUser.objects.create_user(
            username="student_tariro",
            email="tariro@test.com",
            password="Password123!",
            school="Chitepo High",
        )

        self.classroom = Classroom.objects.create(
            name="Advanced Algorithms & Data Structures",
            slug="adv-algorithms",
            instructor=self.instructor,
            description="Graphs, Trees, and DP",
            is_active=True,
        )

        self.assignment = Assignment.objects.create(
            classroom=self.classroom,
            title="Dijkstra Shortest Path Implementation",
            description="Implement Dijkstra using a priority queue in Python",
            assignment_type="coding",
            programming_language="python",
            total_marks=50,
            passing_marks=25,
            deadline=timezone.now() + datetime.timedelta(days=7),
            created_by=self.instructor,
        )

    def test_student_browse_and_enroll_classroom(self):
        """Student can browse classrooms and enroll."""
        self.client.login(username="student_tariro", password="Password123!")
        
        # Browse classrooms
        res = self.client.get(reverse("siteapp:browse_classrooms"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Advanced Algorithms")

        # Enroll in free classroom
        res_enroll = self.client.post(
            reverse("siteapp:enroll_classroom", args=[self.classroom.slug])
        )
        self.assertEqual(res_enroll.status_code, 302)
        self.assertTrue(
            Enrollment.objects.filter(student=self.student, classroom=self.classroom, is_active=True).exists()
        )

    def test_student_submit_assignment_and_grading(self):
        """Student submits code assignment and receives AI grade."""
        Enrollment.objects.create(student=self.student, classroom=self.classroom, is_active=True)
        self.client.login(username="student_tariro", password="Password123!")

        mock_code_result = {
            "score": Decimal("45"),
            "percentage": 90.0,
            "is_correct": True,
            "has_syntax_errors": False,
            "feedback": "Optimal O((V+E) log V) implementation using heapq.",
            "strengths": ["Optimal time complexity", "Clean variable names"],
            "improvements": ["Add edge case docstrings"],
            "reasoning": "Excellent solution.",
        }

        with patch("siteapp.examinator_service.GroqGradingService.grade_code_submission", return_value=mock_code_result):
            post_data = {
                "submission_type": "code",
                "code_text": "import heapq\ndef dijkstra(graph, start): pass",
            }
            res = self.client.post(
                reverse("siteapp:take_assignment", args=[self.assignment.id]),
                data=post_data,
            )
            self.assertEqual(res.status_code, 302)

        sub = Submission.objects.get(student=self.student, assignment=self.assignment)
        self.assertEqual(sub.status, "graded")
        self.assertEqual(sub.ai_score, Decimal("45.00"))
        self.assertTrue(sub.is_passed())

    def test_admin_upload_and_delete_material(self):
        """Instructor can upload note material and delete it."""
        self.client.login(username="teacher_tino", password="Password123!")

        # Upload material
        data = {
            "title": "Dijkstra Algorithm Lecture Slides",
            "material_type": "link",
            "external_url": "https://docs.bluewaveacademy.com/dijkstra.pdf",
        }
        res = self.client.post(
            reverse("siteapp:admin_upload_material", args=[self.classroom.slug]),
            data=data,
        )
        self.assertEqual(res.status_code, 302)
        material = Material.objects.filter(classroom=self.classroom, title="Dijkstra Algorithm Lecture Slides").first()
        self.assertIsNotNone(material)

        # Delete material
        res_del = self.client.post(reverse("siteapp:admin_delete_material", args=[material.id]))
        self.assertEqual(res_del.status_code, 302)
        self.assertFalse(Material.objects.filter(id=material.id).exists())
