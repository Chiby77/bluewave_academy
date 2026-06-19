"""
Admin views for exam management
Real-time dashboard, exam CRUD, grading, and PDF report generation
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.db import transaction
from decimal import Decimal
import json

import os
from django.utils.text import slugify
from .models import (
    Exam,
    Question,
    ExamAttempt,
    Answer,
    CustomUser,
    ExamGrading,
    ExamHold,
    Announcement,
    BlogPost,
    Tutorial,
    VideoProgress,
)
from .forms import ExamAnswerForm, StudentLoginForm
from .examinator_service import get_grading_service
from .pdf_generator import generate_student_report


def is_admin(user):
    """Check if user is admin"""
    return user.is_staff or user.is_superuser


def admin_required(view_func):
    """Decorator to require admin access"""

    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not is_admin(request.user):
            messages.error(request, "You do not have permission to access this page.")
            return redirect("siteapp:admin_login")
        return view_func(request, *args, **kwargs)

    return wrapper


# ============= ADMIN LOGIN (HIDDEN) =============


def admin_login(request):
    """Hidden admin login page at /administration/login"""

    # If already logged in as admin, redirect to dashboard
    if request.user.is_authenticated and is_admin(request.user):
        return redirect("siteapp:admin_dashboard")

    if request.method == "POST":
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Check if user is admin
                if user.is_staff or user.is_superuser:
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.get_full_name()}!")
                    return redirect("siteapp:admin_dashboard")
                else:
                    messages.error(
                        request,
                        "Admin access required. Your account is not authorized.",
                    )
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = StudentLoginForm()

    context = {"form": form, "is_admin_login": True}
    return render(request, "siteapp/admin/login.html", context)


# ============= ADMIN DASHBOARD =============


@admin_required
def admin_dashboard(request):
    """Admin dashboard with real-time statistics"""

    # Statistics
    total_exams = Exam.objects.count()
    total_students = CustomUser.objects.filter(is_active_student=True).count()
    total_attempts = ExamAttempt.objects.count()
    total_graded = ExamAttempt.objects.filter(status="graded").count()

    # Grading statistics
    if total_graded > 0:
        pass_rate = (
            ExamAttempt.objects.filter(
                status="graded", score__gte=F("exam__passing_marks")
            ).count()
            / total_graded
        ) * 100
    else:
        pass_rate = 0

    # Recent attempts
    recent_attempts = ExamAttempt.objects.select_related("student", "exam").order_by(
        "-created_at"
    )[:10]

    # Category statistics
    category_stats = (
        Exam.objects.values("category")
        .annotate(count=Count("id"), avg_score=Avg("attempts__score"))
        .order_by("category")
    )

    # Held exams
    held_exams = Exam.objects.filter(is_held=True).count()

    context = {
        "total_exams": total_exams,
        "total_students": total_students,
        "total_attempts": total_attempts,
        "total_graded": total_graded,
        "pass_rate": round(pass_rate, 2),
        "recent_attempts": recent_attempts,
        "category_stats": category_stats,
        "held_exams": held_exams,
    }

    return render(request, "siteapp/admin/dashboard.html", context)


# ============= EXAM MANAGEMENT =============


@admin_required
def exam_list_admin(request):
    """List all exams with admin options"""

    exams = (
        Exam.objects.select_related("created_by")
        .annotate(question_count=Count("questions"), attempt_count=Count("attempts"))
        .order_by("-created_at")
    )

    # Filtering
    category = request.GET.get("category")
    level = request.GET.get("level")
    status = request.GET.get("status")

    if category:
        exams = exams.filter(category=category)
    if level:
        exams = exams.filter(level=level)
    if status == "active":
        exams = exams.filter(is_active=True, is_held=False)
    elif status == "held":
        exams = exams.filter(is_held=True)
    elif status == "inactive":
        exams = exams.filter(is_active=False)

    context = {
        "exams": exams,
        "categories": Exam.CATEGORY_CHOICES,
        "levels": Exam.LEVEL_CHOICES,
    }

    return render(request, "siteapp/admin/exam_list.html", context)


@admin_required
def create_exam(request):
    """Create new exam"""

    if request.method == "POST":
        try:
            with transaction.atomic():
                exam = Exam.objects.create(
                    title=request.POST.get("title"),
                    description=request.POST.get("description"),
                    category=request.POST.get("category"),
                    level=request.POST.get("level"),
                    duration_minutes=int(request.POST.get("duration_minutes", 60)),
                    total_marks=int(request.POST.get("total_marks", 100)),
                    passing_marks=int(request.POST.get("passing_marks", 50)),
                    start_date=request.POST.get("start_date"),
                    end_date=request.POST.get("end_date"),
                    is_active=request.POST.get("is_active") == "on",
                    enable_instant_grading=request.POST.get("enable_instant_grading")
                    == "on",
                    show_answers_after_submit=request.POST.get(
                        "show_answers_after_submit"
                    )
                    == "on",
                    shuffle_questions=request.POST.get("shuffle_questions") == "on",
                    shuffle_options=request.POST.get("shuffle_options") == "on",
                    created_by=request.user,
                )

                messages.success(request, f'Exam "{exam.title}" created successfully!')
                return redirect("siteapp:edit_exam", exam_id=exam.id)

        except Exception as e:
            messages.error(request, f"Error creating exam: {str(e)}")

    context = {
        "categories": Exam.CATEGORY_CHOICES,
        "levels": Exam.LEVEL_CHOICES,
    }

    return render(request, "siteapp/admin/create_exam.html", context)


@admin_required
def edit_exam(request, exam_id):
    """Edit exam details"""

    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == "POST":
        try:
            exam.title = request.POST.get("title", exam.title)
            exam.description = request.POST.get("description", exam.description)
            exam.category = request.POST.get("category", exam.category)
            exam.level = request.POST.get("level", exam.level)
            exam.duration_minutes = int(
                request.POST.get("duration_minutes", exam.duration_minutes)
            )
            exam.total_marks = int(request.POST.get("total_marks", exam.total_marks))
            exam.passing_marks = int(
                request.POST.get("passing_marks", exam.passing_marks)
            )
            exam.start_date = request.POST.get("start_date", exam.start_date)
            exam.end_date = request.POST.get("end_date", exam.end_date)
            exam.is_active = request.POST.get("is_active") == "on"
            exam.enable_instant_grading = (
                request.POST.get("enable_instant_grading") == "on"
            )
            exam.show_answers_after_submit = (
                request.POST.get("show_answers_after_submit") == "on"
            )
            exam.shuffle_questions = request.POST.get("shuffle_questions") == "on"
            exam.shuffle_options = request.POST.get("shuffle_options") == "on"

            exam.save()
            messages.success(request, "Exam updated successfully!")
            return redirect("siteapp:edit_exam", exam_id=exam.id)

        except Exception as e:
            messages.error(request, f"Error updating exam: {str(e)}")

    questions = exam.questions.all().order_by("order")

    context = {
        "exam": exam,
        "categories": Exam.CATEGORY_CHOICES,
        "levels": Exam.LEVEL_CHOICES,
        "questions": questions,
        "question_types": Question.QUESTION_TYPE_CHOICES,
    }

    return render(request, "siteapp/admin/edit_exam.html", context)


@admin_required
@require_http_methods(["POST"])
def delete_exam(request, exam_id):
    """Delete exam"""

    exam = get_object_or_404(Exam, id=exam_id)
    exam_title = exam.title

    # Check if exam has attempts
    attempt_count = exam.attempts.count()
    if attempt_count > 0:
        messages.warning(
            request,
            f'Cannot delete exam "{exam_title}" - {attempt_count} student(s) have already attempted it.',
        )
        return redirect("siteapp:exam_list_admin")

    exam.delete()
    messages.success(request, f'Exam "{exam_title}" deleted successfully!')
    return redirect("siteapp:exam_list_admin")


@admin_required
def preview_exam(request, exam_id):
    """Preview entire exam as admin"""

    exam = get_object_or_404(Exam, id=exam_id)
    questions = exam.questions.all().order_by("order")

    context = {
        "exam": exam,
        "questions": questions,
        "is_preview": True,
    }

    return render(request, "siteapp/admin/preview_exam.html", context)


# ============= EXAM HOLD/RESUME =============


@admin_required
def hold_exam(request, exam_id):
    """Hold/pause an exam"""

    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == "POST":
        try:
            reason = request.POST.get("reason", "Exam held by administrator")
            resume_at = request.POST.get("resume_at")

            hold = ExamHold.objects.update_or_create(
                exam=exam,
                defaults={
                    "held_by": request.user,
                    "reason": reason,
                    "resume_at": resume_at if resume_at else None,
                    "is_active": True,
                },
            )

            exam.is_held = True
            exam.save()

            messages.success(
                request,
                f'Exam "{exam.title}" has been held. Students cannot take this exam until resumed.',
            )
            return redirect("siteapp:exam_list_admin")

        except Exception as e:
            messages.error(request, f"Error holding exam: {str(e)}")

    context = {
        "exam": exam,
        "action": "Hold",
    }

    return render(request, "siteapp/admin/hold_exam.html", context)


@admin_required
def resume_exam(request, exam_id):
    """Resume a held exam"""

    exam = get_object_or_404(Exam, id=exam_id)

    try:
        ExamHold.objects.filter(exam=exam).delete()
        exam.is_held = False
        exam.save()

        messages.success(request, f'Exam "{exam.title}" has been resumed.')
    except Exception as e:
        messages.error(request, f"Error resuming exam: {str(e)}")

    return redirect("siteapp:exam_list_admin")


# ============= ATTEMPT MANAGEMENT =============


@admin_required
def view_attempts(request, exam_id=None):
    """View all exam attempts with filtering"""

    attempts = ExamAttempt.objects.select_related("student", "exam").order_by(
        "-created_at"
    )

    if exam_id:
        exam = get_object_or_404(Exam, id=exam_id)
        attempts = attempts.filter(exam=exam)

    # Filtering
    status = request.GET.get("status")
    exam_filter = request.GET.get("exam")

    if status:
        attempts = attempts.filter(status=status)
    if exam_filter:
        attempts = attempts.filter(exam__id=exam_filter)

    all_attempts_qs = ExamAttempt.objects.all()
    pending_count = all_attempts_qs.filter(status="submitted").count()
    graded_count  = all_attempts_qs.filter(status="graded").count()
    from django.db.models import Avg as _Avg
    avg_score = all_attempts_qs.filter(status="graded").aggregate(a=_Avg("percentage"))["a"]

    context = {
        "attempts": attempts[:200],
        "exam_id": exam_id,
        "exams": Exam.objects.all(),
        "pending_count": pending_count,
        "graded_count": graded_count,
        "avg_score": avg_score,
    }

    return render(request, "siteapp/admin/view_attempts.html", context)


@admin_required
def grade_attempt(request, attempt_id):
    """Grade non-MCQ answers in an attempt"""

    attempt = get_object_or_404(ExamAttempt, id=attempt_id)

    # Get non-MCQ answers that need grading
    answers_to_grade = attempt.answers.filter(
        question__question_type__in=["essay", "short_answer", "code"]
    ).select_related("question")

    if request.method == "POST":
        try:
            with transaction.atomic():
                # Update scores and feedback
                for answer in answers_to_grade:
                    score = Decimal(request.POST.get(f"score_{answer.id}", 0))
                    feedback = request.POST.get(f"feedback_{answer.id}", "")

                    # Create or update grading record
                    grading, created = ExamGrading.objects.update_or_create(
                        attempt=attempt,
                        question=answer.question,
                        defaults={
                            "student_answer": answer.answer_text,
                            "admin_score": score,
                            "admin_feedback": feedback,
                            "admin_overridden": True,
                            "overridden_by": request.user,
                        },
                    )

                    # Update answer with final score
                    answer.marks_obtained = score
                    answer.is_correct = score >= (answer.question.marks * 0.8)
                    answer.save()

                # Recalculate total score
                attempt.calculate_score()

                # Update status if all answers graded
                attempt.status = "graded"
                attempt.ai_graded = True
                attempt.save()

                messages.success(request, "Answers graded successfully!")
                return redirect("siteapp:view_attempts")

        except Exception as e:
            messages.error(request, f"Error grading attempt: {str(e)}")

    context = {
        "attempt": attempt,
        "answers_to_grade": answers_to_grade,
    }

    return render(request, "siteapp/admin/grade_attempt.html", context)


@admin_required
def auto_grade_attempt(request, attempt_id):
    """Auto-grade attempt using Gemini AI"""

    attempt = get_object_or_404(ExamAttempt, id=attempt_id)
    gemini_service = get_grading_service()

    if not gemini_service.is_enabled():
        messages.error(request, "Gemini AI service is not configured. Please set the GEMINI_API_KEY environment variable.")
        return redirect("siteapp:grade_attempt", attempt_id=attempt.id)

    try:
        # Get non-MCQ answers
        answers_to_grade = attempt.answers.filter(
            question__question_type__in=["essay", "short_answer", "code"]
        ).select_related("question")

        with transaction.atomic():
            for answer in answers_to_grade:
                question = answer.question

                # Grade using Gemini
                if question.question_type == "code":
                    grade_result = gemini_service.grade_code_submission(
                        question=question.question_text,
                        rubric=getattr(question, "rubric", "") or "",
                        expected_output=question.correct_answer or "",
                        student_code=answer.answer_text or "",
                        language=getattr(question, "code_language", "python") or "python",
                        total_marks=int(question.marks),
                    )
                else:
                    grade_result = gemini_service.grade_text_submission(
                        question=question.question_text,
                        rubric=getattr(question, "rubric", "") or "",
                        answer_key=question.correct_answer or "",
                        student_answer=answer.answer_text or "",
                        total_marks=int(question.marks),
                    )

                # Store results in existing grading record (reuse groq_ fields for AI results)
                ExamGrading.objects.update_or_create(
                    attempt=attempt,
                    question=question,
                    defaults={
                        "student_answer": answer.answer_text,
                        "groq_score": grade_result["score"],
                        "groq_feedback": grade_result["feedback"],
                        "groq_reasoning": grade_result["reasoning"],
                    },
                )

                # Update answer
                answer.marks_obtained = grade_result["score"]
                answer.is_correct = grade_result["is_correct"]
                answer.ai_graded = True
                answer.ai_feedback = grade_result["feedback"]
                answer.save()

            # Recalculate total
            attempt.calculate_score()
            attempt.status = "graded"
            attempt.ai_graded = True
            attempt.save()

            messages.success(request, "Attempt auto-graded using Gemini AI.")
            return redirect("siteapp:view_attempts")

    except Exception as e:
        messages.error(request, f"Error auto-grading: {str(e)}")
        return redirect("siteapp:grade_attempt", attempt_id=attempt.id)


# ============= PDF REPORT GENERATION =============


@admin_required
def download_report(request, attempt_id):
    """Download student exam report as PDF"""

    attempt = get_object_or_404(ExamAttempt, id=attempt_id)

    try:
        pdf_buffer = generate_student_report(attempt)

        filename = (
            f"{attempt.student.student_id}_{attempt.exam.id}_{attempt.id}_report.pdf"
        )

        response = FileResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect("siteapp:view_attempts")


# ============= REAL-TIME AJAX ENDPOINTS =============


@admin_required
@require_http_methods(["GET"])
def get_dashboard_stats(request):
    """Get real-time dashboard statistics (AJAX)"""

    total_exams = Exam.objects.count()
    total_students = CustomUser.objects.filter(is_active_student=True).count()
    total_attempts = ExamAttempt.objects.count()
    graded_attempts = ExamAttempt.objects.filter(status="graded").count()

    # Pass rate
    if graded_attempts > 0:
        passed = ExamAttempt.objects.filter(
            status="graded", score__gte=F("exam__passing_marks")
        ).count()
        pass_rate = (passed / graded_attempts) * 100
    else:
        pass_rate = 0

    return JsonResponse(
        {
            "total_exams": total_exams,
            "total_students": total_students,
            "total_attempts": total_attempts,
            "graded_attempts": graded_attempts,
            "pass_rate": round(pass_rate, 2),
        }
    )


@admin_required
@require_http_methods(["GET"])
def get_recent_attempts(request):
    """Get recent exam attempts (AJAX)"""

    recent = ExamAttempt.objects.select_related("student", "exam").order_by(
        "-created_at"
    )[:10]

    data = []
    for attempt in recent:
        data.append(
            {
                "id": attempt.id,
                "student": attempt.student.get_full_name(),
                "exam": attempt.exam.title,
                "status": attempt.status,
                "score": float(attempt.score or 0),
                "percentage": float(attempt.percentage or 0),
                "date": attempt.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        )

    return JsonResponse({"attempts": data})


@admin_required
@require_http_methods(["GET"])
def get_exam_statistics(request, exam_id):
    """Get statistics for a specific exam (AJAX)"""

    exam = get_object_or_404(Exam, id=exam_id)
    attempts = exam.attempts.all()

    total = attempts.count()
    graded = attempts.filter(status="graded").count()
    passed = attempts.filter(score__gte=exam.passing_marks).count()

    if graded > 0:
        avg_score = (
            attempts.filter(status="graded").aggregate(Avg("percentage"))[
                "percentage__avg"
            ]
            or 0
        )
    else:
        avg_score = 0

    return JsonResponse(
        {
            "total_attempts": total,
            "graded_attempts": graded,
            "passed": passed,
            "average_score": round(avg_score, 2),
            "pass_rate": round((passed / total * 100) if total > 0 else 0, 2),
        }
    )


@admin_required
@require_http_methods(["POST"])
def quick_hold_exam(request, exam_id):
    """Quick hold exam via AJAX"""

    exam = get_object_or_404(Exam, id=exam_id)

    try:
        ExamHold.objects.update_or_create(
            exam=exam,
            defaults={
                "held_by": request.user,
                "reason": "Held by admin",
                "is_active": True,
            },
        )

        exam.is_held = True
        exam.save()

        return JsonResponse({"success": True, "message": "Exam held successfully"})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@admin_required
@require_http_methods(["POST"])
def quick_resume_exam(request, exam_id):
    """Quick resume exam via AJAX"""

    exam = get_object_or_404(Exam, id=exam_id)

    try:
        ExamHold.objects.filter(exam=exam).delete()
        exam.is_held = False
        exam.save()

        return JsonResponse({"success": True, "message": "Exam resumed successfully"})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# ============= ANNOUNCEMENTS MANAGEMENT =============


@admin_required
def announcements_management(request):
    """Real-time announcements management interface"""

    announcements = Announcement.objects.all().order_by("-priority", "-created_at")

    context = {
        "announcements": announcements,
        "target_choices": Announcement._meta.get_field("target_audience").choices,
        "priority_choices": [(0, "Normal"), (1, "Important"), (2, "Urgent")],
    }

    return render(request, "siteapp/admin/announcements.html", context)


@admin_required
@require_http_methods(["POST"])
@transaction.atomic()
def create_announcement(request):
    """Create new announcement"""

    try:
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        target_audience = request.POST.get("target_audience", "all")
        priority = int(request.POST.get("priority", 0))
        is_active = request.POST.get("is_active", "on") == "on"

        # Validate
        if not title or not content:
            return JsonResponse(
                {"success": False, "error": "Title and content are required"}
            )

        # Create announcement
        announcement = Announcement.objects.create(
            title=title,
            content=content,
            target_audience=target_audience,
            priority=priority,
            is_active=is_active,
            created_by=request.user,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Announcement created successfully",
                "announcement": {
                    "id": announcement.id,
                    "title": announcement.title,
                    "content": announcement.content,
                    "target_audience": announcement.get_target_audience_display(),
                    "priority": announcement.get_priority_display(),
                    "is_active": announcement.is_active,
                    "created_at": announcement.created_at.strftime("%Y-%m-%d %H:%M"),
                    "created_by": announcement.created_by.get_full_name(),
                },
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@admin_required
@require_http_methods(["POST"])
@transaction.atomic()
def delete_announcement(request, announcement_id):
    """Delete announcement"""

    try:
        announcement = get_object_or_404(Announcement, id=announcement_id)
        title = announcement.title
        announcement.delete()

        return JsonResponse(
            {"success": True, "message": f'Announcement "{title}" deleted successfully'}
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@admin_required
@require_http_methods(["POST"])
@transaction.atomic()
def update_announcement(request, announcement_id):
    """Update announcement"""

    try:
        announcement = get_object_or_404(Announcement, id=announcement_id)

        announcement.title = request.POST.get("title", announcement.title).strip()
        announcement.content = request.POST.get("content", announcement.content).strip()
        announcement.target_audience = request.POST.get(
            "target_audience", announcement.target_audience
        )
        announcement.priority = int(request.POST.get("priority", announcement.priority))
        announcement.is_active = request.POST.get("is_active", "on") == "on"

        announcement.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Announcement updated successfully",
                "announcement": {
                    "id": announcement.id,
                    "title": announcement.title,
                    "content": announcement.content,
                    "target_audience": announcement.get_target_audience_display(),
                    "priority": announcement.get_priority_display(),
                    "is_active": announcement.is_active,
                    "created_at": announcement.created_at.strftime("%Y-%m-%d %H:%M"),
                    "created_by": announcement.created_by.get_full_name(),
                },
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@admin_required
@require_http_methods(["GET"])
def get_announcements(request):
    """Get all announcements as JSON (AJAX endpoint)"""

    try:
        announcements = Announcement.objects.all().order_by("-priority", "-created_at")

        data = [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "target_audience": a.get_target_audience_display(),
                "priority": a.get_priority_display(),
                "priority_level": a.priority,
                "is_active": a.is_active,
                "created_at": a.created_at.strftime("%Y-%m-%d %H:%M"),
                "updated_at": a.updated_at.strftime("%Y-%m-%d %H:%M"),
                "created_by": a.created_by.get_full_name(),
            }
            for a in announcements
        ]

        return JsonResponse(
            {"success": True, "count": len(data), "announcements": data}
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# ============= SUBMISSIONS & ANALYTICS =============


@admin_required
@admin_required
def student_submissions(request):
    """View all student exam submissions"""
    attempts = ExamAttempt.objects.select_related("student", "exam").order_by(
        "-created_at"
    )

    # Filter by status
    status_filter = request.GET.get("status", "all")
    if status_filter != "all":
        attempts = attempts.filter(status=status_filter)

    # Filter by exam
    exam_filter = request.GET.get("exam")
    if exam_filter:
        attempts = attempts.filter(exam_id=exam_filter)

    # Get stats
    total_submissions = attempts.count()
    submitted_count = attempts.filter(status__in=["submitted", "graded"]).count()
    pending_count = attempts.filter(
        status__in=["in_progress", "pending_review"]
    ).count()

    context = {
        "attempts": attempts[:100],  # Paginate to 100
        "total_submissions": total_submissions,
        "submitted_count": submitted_count,
        "pending_count": pending_count,
        "status_filter": status_filter,
        "exam_filter": exam_filter,
        "exams": Exam.objects.filter(is_active=True),
    }

    return render(request, "siteapp/admin/submissions.html", context)


@admin_required
def exam_analytics(request):
    """View pass rates and performance analytics by exam"""
    exams = Exam.objects.annotate(
        total_attempts=Count("attempts", distinct=True),
        avg_score=Avg("attempts__percentage"),
        passed_count=Count(
            "attempts", filter=Q(attempts__score__gte=F("passing_marks")), distinct=True
        ),
    ).order_by("-total_attempts")

    # Calculate pass rates
    for exam in exams:
        if exam.total_attempts > 0:
            exam.pass_rate = round((exam.passed_count / exam.total_attempts) * 100, 2)
            exam.avg_score = round(exam.avg_score or 0, 2)
        else:
            exam.pass_rate = 0
            exam.avg_score = 0

    context = {
        "exams": exams,
        "total_exams": exams.count(),
    }

    return render(request, "siteapp/admin/exam_analytics.html", context)


@admin_required
def student_performance(request):
    """View individual student performance"""
    students = (
        CustomUser.objects.filter(is_staff=False, is_superuser=False)
        .annotate(
            total_attempts=Count("exam_attempts", distinct=True),
            avg_score=Avg("exam_attempts__percentage"),
            passed_count=Count(
                "exam_attempts",
                filter=Q(
                    exam_attempts__score__gte=F("exam_attempts__exam__passing_marks")
                ),
                distinct=True,
            ),
        )
        .order_by("-total_attempts")
    )

    # Calculate pass rates and statistics for each student
    total_attempts = 0
    sum_pass_rates = 0
    for student in students:
        if student.total_attempts > 0:
            student.pass_rate = round(
                (student.passed_count / student.total_attempts) * 100, 2
            )
            student.avg_score = round(student.avg_score or 0, 2)
            total_attempts += student.total_attempts
            sum_pass_rates += student.pass_rate
        else:
            student.pass_rate = 0
            student.avg_score = 0

    # Calculate average pass rate
    avg_pass_rate = (
        round(sum_pass_rates / students.count(), 2) if students.count() > 0 else 0
    )

    context = {
        "students": students,
        "total_students": students.count(),
        "total_attempts": total_attempts,
        "avg_pass_rate": avg_pass_rate,
    }

    return render(request, "siteapp/admin/student_performance.html", context)


@admin_required
def submission_detail(request, attempt_id):
    """View detailed submission info"""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id)
    answers = Answer.objects.filter(attempt=attempt).select_related("question")
    total_questions = attempt.exam.questions.count()
    correct_count = answers.filter(is_correct=True).count()

    # Calculate time spent if available
    time_spent = None
    if attempt.start_time and attempt.end_time:
        time_spent = (attempt.end_time - attempt.start_time).total_seconds() / 60

    context = {
        "attempt": attempt,
        "answers": answers,
        "exam": attempt.exam,
        "student": attempt.student,
        "total_questions": total_questions,
        "correct_count": correct_count,
    }

    return render(request, "siteapp/admin/submission_detail.html", context)


@admin_required
def export_analytics(request):
    """Export analytics as JSON"""
    from django.http import JsonResponse

    # Exam analytics
    exams = Exam.objects.annotate(
        total_attempts=Count("attempts", distinct=True),
        avg_score=Avg("attempts__percentage"),
        passed_count=Count(
            "attempts", filter=Q(attempts__score__gte=F("passing_marks")), distinct=True
        ),
    ).order_by("-total_attempts")

    exam_data = []
    for exam in exams:
        pass_rate = 0
        if exam.total_attempts > 0:
            pass_rate = round((exam.passed_count / exam.total_attempts) * 100, 2)

        exam_data.append(
            {
                "id": exam.id,
                "title": exam.title,
                "total_attempts": exam.total_attempts,
                "avg_score": round(exam.avg_score or 0, 2),
                "passed": exam.passed_count,
                "pass_rate": pass_rate,
            }
        )

    # Student analytics
    students = (
        CustomUser.objects.filter(is_staff=False, is_superuser=False)
        .annotate(
            total_attempts=Count("exam_attempts", distinct=True),
            avg_score=Avg("exam_attempts__percentage"),
            passed_count=Count(
                "exam_attempts",
                filter=Q(
                    exam_attempts__score__gte=F("exam_attempts__exam__passing_marks")
                ),
                distinct=True,
            ),
        )
        .order_by("-total_attempts")
    )

    student_data = []
    for student in students:
        pass_rate = 0
        if student.total_attempts > 0:
            pass_rate = round((student.passed_count / student.total_attempts) * 100, 2)

        student_data.append(
            {
                "id": student.id,
                "name": student.get_full_name(),
                "email": student.email,
                "school": student.school,
                "total_attempts": student.total_attempts,
                "avg_score": round(student.avg_score or 0, 2),
                "passed": student.passed_count,
                "pass_rate": pass_rate,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "exams": exam_data,
            "students": student_data,
        }
    )


# ============= QUESTION MANAGEMENT =============


@admin_required
def add_question(request, exam_id):
    """Add a new question to an exam"""
    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == "POST":
        try:
            question_type = request.POST.get("question_type", "mcq")

            question = Question.objects.create(
                exam=exam,
                question_text=request.POST.get("question_text"),
                question_type=question_type,
                marks=int(request.POST.get("marks", 1)),
                order=exam.questions.count() + 1,
                explanation=request.POST.get("explanation", ""),
            )

            # Handle MCQ options
            if question_type == "mcq":
                question.option_a = request.POST.get("option_a", "")
                question.option_b = request.POST.get("option_b", "")
                question.option_c = request.POST.get("option_c", "")
                question.option_d = request.POST.get("option_d", "")
                question.correct_answer = request.POST.get("correct_answer", "")
                question.save()
            elif question_type == "true_false":
                question.correct_answer = request.POST.get("correct_answer", "true")
                question.save()
            else:
                question.correct_answer = request.POST.get("correct_answer", "")
                question.save()

            messages.success(request, "Question added successfully!")
            return redirect("siteapp:edit_exam", exam_id=exam.id)

        except Exception as e:
            messages.error(request, f"Error adding question: {str(e)}")

    context = {
        "exam": exam,
        "question_types": Question.QUESTION_TYPE_CHOICES,
    }

    return render(request, "siteapp/admin/add_question.html", context)


@admin_required
def edit_question(request, exam_id, question_id):
    """Edit an existing question"""
    exam = get_object_or_404(Exam, id=exam_id)
    question = get_object_or_404(Question, id=question_id, exam=exam)

    if request.method == "POST":
        try:
            question.question_text = request.POST.get(
                "question_text", question.question_text
            )
            question.question_type = request.POST.get(
                "question_type", question.question_type
            )
            question.marks = int(request.POST.get("marks", question.marks))
            question.explanation = request.POST.get("explanation", "")

            # Handle MCQ options
            if question.question_type == "mcq":
                question.option_a = request.POST.get("option_a", "")
                question.option_b = request.POST.get("option_b", "")
                question.option_c = request.POST.get("option_c", "")
                question.option_d = request.POST.get("option_d", "")
                question.correct_answer = request.POST.get("correct_answer", "")
            elif question.question_type == "true_false":
                question.correct_answer = request.POST.get("correct_answer", "true")
            else:
                question.correct_answer = request.POST.get("correct_answer", "")

            question.save()
            messages.success(request, "Question updated successfully!")
            return redirect("siteapp:edit_exam", exam_id=exam.id)

        except Exception as e:
            messages.error(request, f"Error updating question: {str(e)}")

    context = {
        "exam": exam,
        "question": question,
        "question_types": Question.QUESTION_TYPE_CHOICES,
    }

    return render(request, "siteapp/admin/edit_question.html", context)


@admin_required
@require_http_methods(["POST"])
def delete_question(request, exam_id, question_id):
    """Delete a question from an exam"""
    exam = get_object_or_404(Exam, id=exam_id)
    question = get_object_or_404(Question, id=question_id, exam=exam)

    try:
        question_text = question.question_text[:50]
        question.delete()

        # Reorder remaining questions
        for idx, q in enumerate(exam.questions.all().order_by("order"), 1):
            q.order = idx
            q.save()

        messages.success(request, f"Question deleted successfully!")
    except Exception as e:
        messages.error(request, f"Error deleting question: {str(e)}")

    return redirect("siteapp:edit_exam", exam_id=exam.id)


# ============= BLOG MANAGEMENT =============

@admin_required
def admin_blog_list(request):
    """List all blog posts for admin"""
    posts = BlogPost.objects.all().order_by("-created_at")
    return render(request, "siteapp/admin/blog_list.html", {"posts": posts})


@admin_required
def admin_blog_create(request):
    """Create a new blog post"""
    if request.method == "POST":
        title    = request.POST.get("title", "").strip()
        slug     = request.POST.get("slug", "").strip()
        content  = request.POST.get("content", "").strip()
        category = request.POST.get("category", "Other")
        image    = request.FILES.get("image")

        if not title or not content:
            messages.error(request, "Title and content are required.")
            return render(request, "siteapp/admin/blog_form.html", {"post": None})

        if not slug:
            slug = slugify(title)

        base_slug = slug
        counter = 1
        while BlogPost.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        post = BlogPost(
            title=title,
            slug=slug,
            content=content,
            category=category,
            author=request.user,
        )
        if image:
            post.image = image
        post.save()

        messages.success(request, f'Blog post "{title}" published successfully.')
        return redirect("siteapp:admin_blog_list")

    return render(request, "siteapp/admin/blog_form.html", {"post": None})


@admin_required
def admin_blog_edit(request, post_id):
    """Edit an existing blog post"""
    post = get_object_or_404(BlogPost, id=post_id)

    if request.method == "POST":
        post.title    = request.POST.get("title", post.title).strip()
        post.slug     = request.POST.get("slug", post.slug).strip()
        post.content  = request.POST.get("content", post.content).strip()
        post.category = request.POST.get("category", post.category)
        if request.FILES.get("image"):
            post.image = request.FILES["image"]
        post.save()
        messages.success(request, "Blog post updated successfully.")
        return redirect("siteapp:admin_blog_list")

    return render(request, "siteapp/admin/blog_form.html", {"post": post})


@admin_required
def admin_blog_delete(request, post_id):
    """Delete a blog post"""
    post = get_object_or_404(BlogPost, id=post_id)
    if request.method == "POST":
        title = post.title
        post.delete()
        messages.success(request, f'Blog post "{title}" deleted.')
    return redirect("siteapp:admin_blog_list")


# ============= TUTORIAL MANAGEMENT =============

@admin_required
def admin_tutorial_list(request):
    tutorials = Tutorial.objects.all().order_by("-created_at")
    stats = {
        "total": tutorials.count(),
        "published": tutorials.filter(status="published").count(),
        "drafts": tutorials.filter(status="draft").count(),
    }
    return render(request, "siteapp/admin/tutorial_list.html", {"tutorials": tutorials, "stats": stats})


@admin_required
def admin_tutorial_create(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        category = request.POST.get("category", "Other")
        status = request.POST.get("status", "draft")
        video_type = request.POST.get("video_type", "url")
        video_url = request.POST.get("video_url", "").strip()
        video_file = request.FILES.get("video_file")
        thumbnail = request.FILES.get("thumbnail")

        if not title:
            messages.error(request, "Title is required.")
            return render(request, "siteapp/admin/tutorial_form.html", {
                "tutorial": None,
                "categories": Tutorial.CATEGORY_CHOICES,
            })

        slug = slugify(title)
        base = slug
        n = 1
        while Tutorial.objects.filter(slug=slug).exists():
            slug = f"{base}-{n}"
            n += 1

        t = Tutorial(
            title=title,
            slug=slug,
            description=description,
            category=category,
            status=status,
            video_type=video_type,
            video_url=video_url if video_type == "url" else "",
            created_by=request.user,
        )
        if video_file and video_type == "file":
            t.video_file = video_file
        if thumbnail:
            t.thumbnail = thumbnail
        t.save()

        messages.success(request, f'Tutorial "{title}" saved as {status}.')
        return redirect("siteapp:admin_tutorial_list")

    return render(request, "siteapp/admin/tutorial_form.html", {
        "tutorial": None,
        "categories": Tutorial.CATEGORY_CHOICES,
    })


@admin_required
def admin_tutorial_edit(request, tutorial_id):
    t = get_object_or_404(Tutorial, id=tutorial_id)

    if request.method == "POST":
        t.title = request.POST.get("title", t.title).strip()
        t.description = request.POST.get("description", t.description).strip()
        t.category = request.POST.get("category", t.category)
        t.status = request.POST.get("status", t.status)
        t.video_type = request.POST.get("video_type", t.video_type)
        if t.video_type == "url":
            t.video_url = request.POST.get("video_url", t.video_url).strip()
            t.video_file = None
        if request.FILES.get("video_file") and t.video_type == "file":
            t.video_file = request.FILES["video_file"]
        if request.FILES.get("thumbnail"):
            t.thumbnail = request.FILES["thumbnail"]
        t.save()
        messages.success(request, "Tutorial updated.")
        return redirect("siteapp:admin_tutorial_list")

    return render(request, "siteapp/admin/tutorial_form.html", {
        "tutorial": t,
        "categories": Tutorial.CATEGORY_CHOICES,
    })


@admin_required
def admin_tutorial_delete(request, tutorial_id):
    t = get_object_or_404(Tutorial, id=tutorial_id)
    if request.method == "POST":
        title = t.title
        t.delete()
        messages.success(request, f'Tutorial "{title}" deleted.')
    return redirect("siteapp:admin_tutorial_list")


@admin_required
def admin_tutorial_toggle_status(request, tutorial_id):
    t = get_object_or_404(Tutorial, id=tutorial_id)
    if request.method == "POST":
        t.status = "published" if t.status == "draft" else "draft"
        t.save()
        messages.success(request, f'"{t.title}" is now {t.status}.')
    return redirect("siteapp:admin_tutorial_list")


# ============= STUDENT MANAGEMENT =============

@admin_required
def admin_students(request):
    """View and search all students"""
    students = CustomUser.objects.filter(is_staff=False).annotate(
        attempt_count=Count("exam_attempts"),
        avg_score=Avg("exam_attempts__percentage"),
    ).order_by("-date_joined")

    q_search = request.GET.get("q", "").strip()
    if q_search:
        from django.db.models import Q as Qfilter
        students = students.filter(
            Qfilter(first_name__icontains=q_search) |
            Qfilter(last_name__icontains=q_search) |
            Qfilter(email__icontains=q_search) |
            Qfilter(student_id__icontains=q_search)
        )

    level = request.GET.get("level", "")
    if level:
        students = students.filter(current_level=level)

    return render(request, "siteapp/admin/students.html", {"students": students})

    return redirect("siteapp:edit_exam", exam_id=exam.id)
