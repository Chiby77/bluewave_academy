import json
import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from siteapp.models import (
    CustomUser,
    Exam,
    ExamAttempt,
    Notification,
    Tutorial,
    VideoProgress,
    TutorConversation,
    TutorMessage,
    SpecialPaper,
)


class APIEndpointsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = CustomUser.objects.create_user(
            username="api_student",
            email="apistudent@test.com",
            password="Password123!",
            first_name="API",
            last_name="Tester",
        )
        self.instructor = CustomUser.objects.create_user(
            username="api_instructor",
            email="apiinstructor@test.com",
            password="Password123!",
            is_staff=True,
        )

        now = timezone.now()
        self.exam = Exam.objects.create(
            title="Mobile Dev with Flutter",
            description="Dart, Widgets, State",
            duration_minutes=45,
            total_marks=50,
            passing_marks=25,
            category="web",
            level="beginner",
            is_active=True,
            start_date=now - datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=5),
            created_by=self.instructor,
        )

        self.tutorial = Tutorial.objects.create(
            title="Introduction to Flutter Widgets",
            slug="intro-flutter-widgets",
            description="Stateless and Stateful widgets",
            video_type="url",
            video_url="https://www.youtube.com/watch?v=12345678901",
            category="Programming",
            status="published",
            created_by=self.instructor,
        )

        self.notification = Notification.objects.create(
            user=self.student,
            title="Welcome to Bluewave",
            message="Your account is active.",
            notification_type="system",
            is_read=False,
        )

    def test_api_exams_list(self):
        """Test api_exams_list returns valid JSON with exams and categories."""
        self.client.login(username="api_student", password="Password123!")
        res = self.client.get(reverse("siteapp:api_exams_list"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("exams", data)
        self.assertIn("categories", data)
        self.assertEqual(len(data["exams"]), 1)
        self.assertEqual(data["exams"][0]["title"], "Mobile Dev with Flutter")
        self.assertTrue(data["exams"][0]["can_retake"])

    def test_api_notifications(self):
        """Test fetching notifications, marking single read, and marking all read."""
        self.client.login(username="api_student", password="Password123!")

        # List notifications
        res = self.client.get(reverse("siteapp:api_notifications"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 1)
        self.assertFalse(data["notifications"][0]["is_read"])

        # Mark single read
        res_read = self.client.post(
            reverse("siteapp:api_notification_read", args=[self.notification.id])
        )
        self.assertEqual(res_read.status_code, 200)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

        # Create another unread notification and mark all read
        Notification.objects.create(
            user=self.student,
            title="Exam Reminder",
            message="Exam tomorrow",
            is_read=False,
        )
        res_all = self.client.post(reverse("siteapp:api_notifications_mark_all_read"))
        self.assertEqual(res_all.status_code, 200)
        self.assertEqual(Notification.objects.filter(user=self.student, is_read=False).count(), 0)

    def test_api_tutorials_and_progress(self):
        """Test listing tutorials, viewing detail, and updating watch progress."""
        self.client.login(username="api_student", password="Password123!")

        # List tutorials
        res_list = self.client.get(reverse("siteapp:api_tutorials_list"))
        self.assertEqual(res_list.status_code, 200)
        data_list = res_list.json()
        self.assertEqual(data_list["total"], 1)

        # Tutorial detail
        res_detail = self.client.get(
            reverse("siteapp:api_tutorial_detail", args=[self.tutorial.slug])
        )
        self.assertEqual(res_detail.status_code, 200)
        data_detail = res_detail.json()
        self.assertEqual(data_detail["title"], "Introduction to Flutter Widgets")

        # Update progress to 95% (marks completed)
        payload = json.dumps({"tutorial_id": self.tutorial.id, "progress": 95})
        res_prog = self.client.post(
            reverse("siteapp:api_tutorial_update_progress"),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(res_prog.status_code, 200)
        prog = VideoProgress.objects.get(student=self.student, tutorial=self.tutorial)
        self.assertEqual(prog.progress_pct, 95.0)
        self.assertTrue(prog.completed)

    def test_api_ai_tutor_conversation_and_message(self):
        """Test AI Tutor API conversation retrieval and sending messages."""
        self.client.login(username="api_student", password="Password123!")

        # Get conversation
        res_conv = self.client.get(reverse("siteapp:api_tutor_conversation"))
        self.assertEqual(res_conv.status_code, 200)
        data_conv = res_conv.json()
        self.assertIn("conversation_id", data_conv)

        # Send message to AI tutor with mocked response
        mock_tutor_reply = {
            "response": "In Flutter, a StatefulWidget maintains state that might change during the widget lifecycle.",
            "suggestions": ["Tell me about setState", "What is an InheritedWidget?"],
        }

        with patch("siteapp.ai_tutor.AITutorService.chat_with_tutor", return_value=mock_tutor_reply):
            payload = json.dumps({"message": "What is a StatefulWidget?"})
            res_msg = self.client.post(
                reverse("siteapp:api_tutor_send_message"),
                data=payload,
                content_type="application/json",
            )
            self.assertEqual(res_msg.status_code, 200)
            data_msg = res_msg.json()
            self.assertTrue(data_msg.get("ok"))
            self.assertIn("StatefulWidget", data_msg["ai_message"]["content"])
            self.assertEqual(len(data_msg["suggestions"]), 2)
