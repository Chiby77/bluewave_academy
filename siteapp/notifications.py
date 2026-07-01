from django.conf import settings
from .models import Notification, CustomUser

try:
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    HAS_CHANNELS = True
except ImportError:
    HAS_CHANNELS = False


def send_notification_to_user(user, title, message, notification_type="system", url=None):
    """
    Send a real-time notification to a user via WebSocket and save it to the database.
    """
    # Save to database
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        url=url
    )

    # Send via WebSocket only if channels are available
    if HAS_CHANNELS:
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}",
                {
                    "type": "send_notification",
                    "title": title,
                    "message": message,
                    "url": url
                }
            )
        except Exception:
            pass  # Fail silently if WebSocket isn't available

    return notification


def send_notification_to_classroom(classroom, title, message, notification_type="system", url=None, exclude_users=None):
    """
    Send a notification to all enrolled students in a classroom.
    """
    exclude_users = exclude_users or []
    users = CustomUser.objects.filter(
        enrollments__classroom=classroom,
        enrollments__is_active=True
    ).exclude(id__in=[u.id for u in exclude_users])

    for user in users:
        send_notification_to_user(user, title, message, notification_type, url)


def notify_exam_available(exam):
    """Notify students when a new exam is available."""
    for user in CustomUser.objects.filter(is_active_student=True, is_active=True):
        send_notification_to_user(
            user,
            "New Exam Available!",
            f"Exam '{exam.title}' is now available. Take it before {exam.end_date}.",
            "exam",
            f"/exams/{exam.id}/"
        )


def notify_grading_complete(attempt):
    """Notify a student when their exam has been graded."""
    send_notification_to_user(
        attempt.student,
        "Exam Graded!",
        f"Your attempt for '{attempt.exam.title}' has been graded. You scored {attempt.score}%.",
        "grading",
        f"/exams/results/{attempt.id}/"
    )


def notify_assignment_submission(submission):
    """Notify instructor when an assignment is submitted."""
    if submission.assignment.classroom.instructor:
        send_notification_to_user(
            submission.assignment.classroom.instructor,
            "New Assignment Submission",
            f"{submission.student.get_full_name()} submitted '{submission.assignment.title}'.",
            "assignment",
            f"/examinator/assignments/{submission.assignment.id}/submissions/"
        )