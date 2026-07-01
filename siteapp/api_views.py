
"""
API endpoints for Bluewave Academy mobile app and AJAX functionality.
Includes notifications, AI tutor, and tutorials APIs.
"""
import json
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Prefetch

from .models import (
    CustomUser,
    Notification,
    TutorConversation,
    TutorMessage,
    Tutorial,
    VideoProgress,
    Exam,
    ExamAttempt,
)
from .ai_tutor import get_tutor_service
from .notifications import send_notification_to_user


@login_required
@require_GET
def api_notifications_list(request):
    """Get list of notifications for authenticated user."""
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:50]
    data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.notification_type,
            "url": n.url,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]
    return JsonResponse({"notifications": data, "count": notifications.count()})


@login_required
@require_POST
def api_notification_mark_read(request, notification_id):
    """Mark a single notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def api_notifications_mark_all_read(request):
    """Mark all notifications as read for user."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True, "count": Notification.objects.filter(user=request.user, is_read=True).count()})


@login_required
@require_GET
def api_tutor_get_conversation(request):
    """Get or create a tutor conversation for the user."""
    conversation, created = TutorConversation.objects.get_or_create(user=request.user)
    messages = conversation.messages.all().order_by("timestamp")
    message_data = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in messages
    ]
    return JsonResponse({
        "conversation_id": conversation.id,
        "messages": message_data,
        "created_at": conversation.created_at.isoformat(),
    })


@login_required
@require_POST
def api_tutor_send_message(request):
    """Send a message to AI tutor and get a response."""
    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        if not user_message:
            return JsonResponse({"error": "Message is required"}, status=400)
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid request data"}, status=400)

    conversation, _ = TutorConversation.objects.get_or_create(user=request.user)

    # Save user message
    user_msg = TutorMessage.objects.create(
        conversation=conversation,
        role="user",
        content=user_message,
    )

    # Get AI response
    tutor_service = get_tutor_service()
    response = tutor_service.chat_with_tutor(
        user=request.user,
        message=user_message,
    )

    # Save AI message
    ai_msg = TutorMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content=response["response"],
    )

    return JsonResponse({
        "ok": True,
        "user_message": {
            "id": user_msg.id,
            "role": "user",
            "content": user_msg.content,
            "timestamp": user_msg.timestamp.isoformat(),
        },
        "ai_message": {
            "id": ai_msg.id,
            "role": "assistant",
            "content": ai_msg.content,
            "timestamp": ai_msg.timestamp.isoformat(),
        },
        "suggestions": response.get("suggestions", []),
    })


@login_required
@require_GET
def api_tutorials_list(request):
    """Get list of tutorials with user progress."""
    tutorials = Tutorial.objects.filter(status="published")

    category = request.GET.get("category", "").strip()
    if category:
        tutorials = tutorials.filter(category=category)

    q = request.GET.get("q", "").strip()
    if q:
        tutorials = tutorials.filter(title__icontains=q)

    progress_map = {}
    for p in VideoProgress.objects.filter(student=request.user, tutorial__in=tutorials):
        progress_map[p.tutorial_id] = p

    tutorial_data = []
    for t in tutorials:
        prog = progress_map.get(t.id)
        tutorial_data.append({
            "id": t.id,
            "title": t.title,
            "slug": t.slug,
            "description": t.description,
            "category": t.category,
            "video_type": t.video_type,
            "video_url": t.video_url,
            "thumbnail": t.thumbnail.url if t.thumbnail else None,
            "view_count": t.view_count,
            "progress": prog.progress_pct if prog else 0,
            "completed": prog.completed if prog else False,
            "created_at": t.created_at.isoformat(),
        })

    categories = [{"value": c[0], "label": c[1]} for c in Tutorial.CATEGORY_CHOICES]

    return JsonResponse({
        "tutorials": tutorial_data,
        "categories": categories,
        "total": tutorials.count(),
    })


@login_required
@require_GET
def api_tutorial_detail(request, slug):
    """Get tutorial details by slug."""
    tutorial = get_object_or_404(Tutorial, slug=slug, status="published")

    # Increment view count
    tutorial.view_count += 1
    tutorial.save(update_fields=["view_count"])

    progress_obj, _ = VideoProgress.objects.get_or_create(
        student=request.user,
        tutorial=tutorial,
        defaults={"progress_pct": 0, "completed": False},
    )

    related = Tutorial.objects.filter(
        status="published", category=tutorial.category
    ).exclude(pk=tutorial.pk)[:4]

    related_data = [
        {"id": r.id, "title": r.title, "slug": r.slug, "thumbnail": r.thumbnail.url if r.thumbnail else None}
        for r in related
    ]

    return JsonResponse({
        "id": tutorial.id,
        "title": tutorial.title,
        "slug": tutorial.slug,
        "description": tutorial.description,
        "category": tutorial.category,
        "video_type": tutorial.video_type,
        "video_url": tutorial.video_url,
        "embed_url": tutorial.get_embed_url() if tutorial.video_type == "url" else None,
        "thumbnail": tutorial.thumbnail.url if tutorial.thumbnail else None,
        "view_count": tutorial.view_count,
        "progress": progress_obj.progress_pct,
        "completed": progress_obj.completed,
        "related": related_data,
    })


@login_required
@require_POST
def api_tutorial_update_progress(request):
    """Update tutorial progress for user."""
    try:
        data = json.loads(request.body)
        tutorial_id = int(data.get("tutorial_id", 0))
        pct = float(data.get("progress", 0))
        pct = max(0, min(100, pct))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Invalid data"}, status=400)

    tutorial = get_object_or_404(Tutorial, pk=tutorial_id, status="published")
    prog, _ = VideoProgress.objects.get_or_create(
        student=request.user,
        tutorial=tutorial,
        defaults={"progress_pct": 0, "completed": False},
    )

    if pct > prog.progress_pct:
        prog.progress_pct = pct
    if pct >= 90:
        prog.completed = True
    prog.save()

    return JsonResponse({"ok": True, "progress": prog.progress_pct, "completed": prog.completed})


@login_required
@require_GET
def api_exams_list(request):
    """Get list of exams with user attempt info."""
    now = timezone.now()
    exams_qs = Exam.objects.filter(is_active=True, is_held=False, start_date__lte=now, end_date__gte=now)

    items = []
    for exam in exams_qs:
        finished = ExamAttempt.objects.filter(student=request.user, exam=exam, status__in=["submitted", "graded"])
        finished_count = finished.count()
        latest_attempt = finished.order_by("-attempt_number").first()
        in_progress = ExamAttempt.objects.filter(student=request.user, exam=exam, status="in_progress").first()
        can_retake = finished_count < 2

        items.append({
            "id": exam.id,
            "title": exam.title,
            "description": exam.description,
            "category": exam.category,
            "level": exam.level,
            "duration_minutes": exam.duration_minutes,
            "total_marks": exam.total_marks,
            "passing_marks": exam.passing_marks,
            "start_date": exam.start_date.isoformat(),
            "end_date": exam.end_date.isoformat(),
            "attempt_count": finished_count,
            "can_retake": can_retake,
            "latest_score": latest_attempt.percentage if latest_attempt else None,
            "in_progress": in_progress is not None,
        })

    categories = [{"value": c[0], "label": c[1]} for c in Exam.CATEGORY_CHOICES]
    return JsonResponse({"exams": items, "categories": categories})
