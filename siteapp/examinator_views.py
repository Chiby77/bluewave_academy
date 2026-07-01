"""
The Examinator — Student-facing and Admin views for the digital assessment platform.
"""

import json
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from django.conf import settings
from django.core.mail import EmailMessage
from django.views.decorators.http import require_POST
from django.db import transaction

from .models import (
    Classroom, Enrollment, Assignment, Submission, SpecialPaper, CustomUser, Material
)
from .examinator_service import get_grading_service
from .pdf_generator import generate_student_report
from .classroom_access import classroom_access_required
from .notifications import send_notification_to_user


# ====================================================
# STUDENT-FACING VIEWS
# ====================================================

@login_required
def examinator_home(request):
    """Student's Examinator dashboard — shows enrolled classrooms."""
    enrollments = Enrollment.objects.filter(
        student=request.user, is_active=True
    ).select_related("classroom", "classroom__instructor")
    context = {"enrollments": enrollments}
    return render(request, "siteapp/examinator/home.html", context)


@login_required
@classroom_access_required
def classroom_detail(request, slug):
    """Classroom detail — assignments, materials, videos, pending tasks."""
    classroom = get_object_or_404(Classroom, slug=slug, is_active=True)

    # Enrollment check
    enrollment = Enrollment.objects.filter(
        student=request.user, classroom=classroom, is_active=True
    ).first()
    enrolled = enrollment is not None

    if not enrolled and not request.user.is_staff:
        messages.error(request, "You are not enrolled in this classroom.")
        return redirect("siteapp:examinator_home")

    now = timezone.now()
    assignments = classroom.assignments.filter(is_active=True).order_by("deadline")

    # Annotate each assignment with student's submission
    for assignment in assignments:
        try:
            assignment.my_submission = Submission.objects.get(
                student=request.user, assignment=assignment
            )
        except Submission.DoesNotExist:
            assignment.my_submission = None

    # Pending tasks = not yet submitted, deadline in future
    pending_assignments = [
        a for a in assignments
        if a.my_submission is None and not a.is_past_deadline()
    ]

    # Materials split by type
    materials_qs = classroom.materials.filter(is_active=True)
    notes   = materials_qs.filter(material_type="note")
    videos  = materials_qs.filter(material_type="video")
    links   = materials_qs.filter(material_type="link")

    context = {
        "classroom": classroom,
        "enrollment": enrollment,
        "assignments": assignments,
        "enrolled": enrolled,
        "pending_assignments": pending_assignments,
        "notes": notes,
        "videos": videos,
        "links": links,
        "now": now,
    }
    return render(request, "siteapp/examinator/classroom_detail.html", context)


@login_required
def enroll_classroom(request, slug):
    """Enroll the logged-in student into a classroom."""
    classroom = get_object_or_404(Classroom, slug=slug, is_active=True)
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user, classroom=classroom,
        defaults={"is_active": True}
    )
    if not created and not enrollment.is_active:
        enrollment.is_active = True
        enrollment.save()
        messages.success(request, f"Re-enrolled in {classroom.name}.")
    elif created:
        messages.success(request, f"Successfully enrolled in {classroom.name}.")
    else:
        messages.info(request, f"You are already enrolled in {classroom.name}.")
    return redirect("siteapp:classroom_detail", slug=slug)


@login_required
def payment_required(request, slug):
    """Shown when a student's payment is overdue for a classroom."""
    classroom = get_object_or_404(Classroom, slug=slug, is_active=True)
    enrollment = Enrollment.objects.filter(
        student=request.user, classroom=classroom, is_active=True
    ).first()
    return render(request, "siteapp/examinator/payment_required.html", {
        "classroom": classroom,
        "enrollment": enrollment,
    })


@login_required
@classroom_access_required
def take_assignment(request, assignment_id):
    """Page where student takes / submits an assignment."""
    assignment = get_object_or_404(Assignment, id=assignment_id, is_active=True)

    # Check enrollment
    enrolled = Enrollment.objects.filter(
        student=request.user, classroom=assignment.classroom, is_active=True
    ).exists()
    if not enrolled and not request.user.is_staff:
        messages.error(request, "Enroll in the classroom first.")
        return redirect("siteapp:examinator_home")

    # Check deadline
    if assignment.is_past_deadline():
        messages.warning(request, "The deadline for this assignment has passed.")
        return redirect("siteapp:classroom_detail", slug=assignment.classroom.slug)

    # Check existing submission
    try:
        existing = Submission.objects.get(student=request.user, assignment=assignment)
        if not assignment.allow_resubmit:
            return redirect("siteapp:submission_result", submission_id=existing.id)
    except Submission.DoesNotExist:
        existing = None

    if request.method == "POST":
        return _handle_submission(request, assignment)

    context = {
        "assignment": assignment,
        "existing": existing,
        "start_time": timezone.now().isoformat(),
    }
    return render(request, "siteapp/examinator/take_assignment.html", context)


def _handle_submission(request, assignment):
    """Process a submitted assignment and trigger async AI grading."""
    student = request.user
    text_answer = request.POST.get("text_answer", "").strip()
    code_text = request.POST.get("code_text", "").strip()
    pdf_file = request.FILES.get("pdf_file")
    time_taken = request.POST.get("time_taken_seconds")

    if not text_answer and not code_text and not pdf_file:
        messages.error(request, "Please provide your answer before submitting.")
        return redirect("siteapp:take_assignment", assignment_id=assignment.id)

    try:
        with transaction.atomic():
            submission, _ = Submission.objects.update_or_create(
                student=student,
                assignment=assignment,
                defaults={
                    "text_answer": text_answer,
                    "code_text": code_text,
                    "pdf_file": pdf_file,
                    "status": "grading",
                    "time_taken_seconds": int(time_taken) if time_taken else None,
                }
            )
    except Exception:
        messages.error(request, "Submission failed. Please try again.")
        return redirect("siteapp:take_assignment", assignment_id=assignment.id)

    # Run AI grading in background thread — main request returns immediately
    t = threading.Thread(target=_run_ai_grading, args=(submission.id,), daemon=True)
    t.start()

    # Send notification
    try:
        send_notification_to_user(
            user=student,
            title="Assignment Submitted!",
            message=f"Your submission for '{assignment.title}' has been received and is being graded.",
            notification_type="assignment",
            url=f"/examinator/submission/{submission.id}/result/",
        )
    except Exception as e:
        print(f"[Notification] Error sending submission notice: {e}")

    messages.success(request, "Assignment submitted! Grading is in progress.")
    return redirect("siteapp:submission_result", submission_id=submission.id)


def _run_ai_grading(submission_id: int):
    """Trigger Groq AI grading in a background thread with full fallback."""
    import django
    try:
        submission = Submission.objects.select_related("assignment").get(id=submission_id)
    except Submission.DoesNotExist:
        return

    assignment = submission.assignment
    service = get_grading_service()

    try:
        if assignment.is_pdf_upload() and submission.pdf_file:
            try:
                pdf_bytes = submission.pdf_file.read()
            except Exception:
                pdf_bytes = None
            if pdf_bytes:
                result = service.grade_pdf_submission(
                    question=assignment.description,
                    rubric=assignment.rubric,
                    answer_key=assignment.answer_key,
                    pdf_bytes=pdf_bytes,
                    total_marks=assignment.total_marks,
                )
            else:
                result = service._get_pending_response(assignment.total_marks)
        elif assignment.is_coding() and submission.code_text:
            result = service.grade_code_submission(
                question=assignment.description,
                rubric=assignment.rubric,
                expected_output=assignment.answer_key,
                student_code=submission.code_text,
                language=assignment.programming_language or "python",
                total_marks=assignment.total_marks,
            )
        else:
            result = service.grade_text_submission(
                question=assignment.description,
                rubric=assignment.rubric,
                answer_key=assignment.answer_key,
                student_answer=submission.text_answer or submission.code_text,
                total_marks=assignment.total_marks,
            )

        submission.ai_score = result["score"]
        submission.ai_percentage = result.get("percentage", 0)
        submission.ai_feedback = result.get("feedback", "")
        submission.ai_strengths = result.get("strengths", [])
        submission.ai_improvements = result.get("improvements", [])
        submission.ai_improvement_tips = result.get("improvement_tips", [])
        submission.ai_reasoning = result.get("reasoning", "")
        submission.status = "graded"
        submission.save()

        if assignment.show_results_immediately:
            _send_result_email(submission)

        # Send notification
        try:
            student = submission.student
            send_notification_to_user(
                user=student,
                title="Assignment Graded!",
                message=f"Your submission for '{assignment.title}' has been graded! Score: {submission.ai_score or 0}/{assignment.total_marks}",
                notification_type="result",
                url=f"/examinator/submission/{submission.id}/result/",
            )
        except Exception as e:
            print(f"[Notification] Error sending grading notice: {e}")

    except Exception as e:
        print(f"[Examinator] Grading error for submission {submission_id}: {e}")
        # Fallback: mark for manual review, never leave in 'grading' limbo
        try:
            Submission.objects.filter(id=submission_id).update(
                status="manual_review",
                ai_feedback="Automatic grading could not be completed. Your instructor will review shortly."
            )
        except Exception:
            pass


def _send_result_email(submission: Submission):
    """Email the student their result."""
    try:
        student = submission.student
        assignment = submission.assignment
        score = submission.get_score()
        percentage = submission.get_percentage()
        passed = submission.is_passed()

        subject = f"Your result: {assignment.title} — Bluewave Academy"
        body = f"""
Dear {student.get_full_name()},

Your assignment has been graded.

Assignment: {assignment.title}
Classroom: {assignment.classroom.name}
Score: {score}/{assignment.total_marks} ({percentage}%)
Result: {"PASSED" if passed else "NOT PASSED"}

Feedback:
{submission.ai_feedback}

{"Strengths: " + ", ".join(submission.ai_strengths) if submission.ai_strengths else ""}
{"Areas to improve: " + ", ".join(submission.ai_improvements) if submission.ai_improvements else ""}

Log in to your student portal for detailed feedback and improvement tips.
{settings.DEFAULT_FROM_EMAIL}

Bluewave Academy
"""
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email],
        )
        email.send(fail_silently=True)
        submission.report_sent = True
        submission.save(update_fields=["report_sent"])
    except Exception as e:
        print(f"[Examinator] Email error: {e}")


@login_required
def submission_result(request, submission_id):
    """Show the student their grading result. Supports AJAX status polling."""
    submission = get_object_or_404(
        Submission, id=submission_id, student=request.user
    )
    # AJAX polling — return only the status
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("status_check"):
        return JsonResponse({"status": submission.status})

    context = {"submission": submission, "assignment": submission.assignment}
    return render(request, "siteapp/examinator/submission_result.html", context)


@login_required
def browse_classrooms(request):
    """Browse all active classrooms students can enroll in."""
    classrooms = Classroom.objects.filter(is_active=True).select_related("instructor")
    enrolled_ids = Enrollment.objects.filter(
        student=request.user, is_active=True
    ).values_list("classroom_id", flat=True)
    for classroom in classrooms:
        classroom.is_enrolled = classroom.id in enrolled_ids
    context = {"classrooms": classrooms}
    return render(request, "siteapp/examinator/browse_classrooms.html", context)


# ====================================================
# ADMIN VIEWS — Classroom & Assignment Management
# ====================================================

def staff_required(view_func):
    """Decorator to require staff/superuser access."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "Access denied.")
            return redirect("siteapp:admin_login")
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_required
def admin_classrooms(request):
    """Admin: list all classrooms."""
    classrooms = Classroom.objects.all().select_related("instructor")
    context = {"classrooms": classrooms}
    return render(request, "siteapp/examinator/admin/classrooms.html", context)


@staff_required
def admin_create_classroom(request):
    """Admin: create a classroom."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        cover_color = request.POST.get("cover_color", "#2563eb")
        if name:
            classroom = Classroom.objects.create(
                name=name, description=description,
                cover_color=cover_color, instructor=request.user,
            )
            messages.success(request, f'Classroom "{classroom.name}" created.')
            return redirect("siteapp:admin_classroom_detail", slug=classroom.slug)
        messages.error(request, "Classroom name is required.")
    return render(request, "siteapp/examinator/admin/create_classroom.html")


@staff_required
def admin_classroom_detail(request, slug):
    """Admin: view/manage a classroom."""
    classroom = get_object_or_404(Classroom, slug=slug)
    assignments = classroom.assignments.all().order_by("-created_at")
    enrollments = classroom.enrollments.filter(is_active=True).select_related("student")
    context = {
        "classroom": classroom,
        "assignments": assignments,
        "enrollments": enrollments,
    }
    return render(request, "siteapp/examinator/admin/classroom_detail.html", context)


@staff_required
def admin_create_assignment(request, slug):
    """Admin: create an assignment for a classroom."""
    classroom = get_object_or_404(Classroom, slug=slug)
    if request.method == "POST":
        try:
            assignment = Assignment.objects.create(
                classroom=classroom,
                title=request.POST.get("title", ""),
                description=request.POST.get("description", ""),
                assignment_type=request.POST.get("assignment_type", "quiz"),
                rubric=request.POST.get("rubric", ""),
                answer_key=request.POST.get("answer_key", ""),
                total_marks=int(request.POST.get("total_marks", 100)),
                passing_marks=int(request.POST.get("passing_marks", 50)),
                deadline=request.POST.get("deadline"),
                duration_minutes=int(request.POST.get("duration_minutes", 60)),
                programming_language=request.POST.get("programming_language", ""),
                show_results_immediately=request.POST.get("show_results") == "on",
                allow_resubmit=request.POST.get("allow_resubmit") == "on",
                created_by=request.user,
            )
            messages.success(request, f'Assignment "{assignment.title}" created.')
            return redirect("siteapp:admin_classroom_detail", slug=slug)
        except Exception as e:
            messages.error(request, f"Error creating assignment: {e}")
    context = {"classroom": classroom}
    return render(request, "siteapp/examinator/admin/create_assignment.html", context)


@staff_required
def admin_submissions(request, assignment_id):
    """Admin: view all submissions for an assignment."""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    submissions = assignment.submissions.select_related("student").order_by("-submitted_at")
    context = {"assignment": assignment, "submissions": submissions}
    return render(request, "siteapp/examinator/admin/submissions.html", context)


@staff_required
def admin_grade_submission(request, submission_id):
    """Admin: manually grade or override AI grading."""
    submission = get_object_or_404(Submission, id=submission_id)
    if request.method == "POST":
        final_score = request.POST.get("final_score")
        instructor_feedback = request.POST.get("instructor_feedback", "")
        if final_score:
            submission.final_score = float(final_score)
            submission.instructor_feedback = instructor_feedback
            submission.status = "graded"
            submission.graded_by = request.user
            submission.graded_at = timezone.now()
            submission.save()

            # Send updated email and notification
            _send_result_email(submission)
            try:
                send_notification_to_user(
                    user=submission.student,
                    title="Assignment Graded!",
                    message=f"Your submission for '{submission.assignment.title}' has been graded! Score: {submission.final_score}/{submission.assignment.total_marks}",
                    notification_type="result",
                    url=f"/examinator/submission/{submission.id}/result/",
                )
            except Exception as e:
                print(f"[Notification] Error sending manual grading notice: {e}")

            messages.success(request, "Submission graded and student notified.")
            return redirect("siteapp:admin_submissions", assignment_id=submission.assignment.id)
    context = {"submission": submission}
    return render(request, "siteapp/examinator/admin/grade_submission.html", context)


@staff_required
def admin_regrade_submission(request, submission_id):
    """Admin: re-run AI grading on a submission."""
    submission = get_object_or_404(Submission, id=submission_id)
    submission.status = "grading"
    submission.save()
    _run_ai_grading(submission)
    messages.success(request, "Re-grading complete.")
    return redirect("siteapp:admin_submissions", assignment_id=submission.assignment.id)


# ====================================================
# SPECIAL PAPERS (Supabase)
# ====================================================

def special_paper_download(request, paper_id):
    """
    Serve a signed Supabase URL for a special paper.
    Public papers: anyone. Private papers: authenticated users only.
    """
    paper = get_object_or_404(SpecialPaper, id=paper_id, is_active=True)

    if not paper.is_public and not request.user.is_authenticated:
        messages.warning(request, "Please log in to download this paper.")
        return redirect(f"{request.build_absolute_uri('/login/')}?next={request.path}")

    # Generate a short-lived signed URL via the centralised storage helper.
    from siteproject.storage_backends import get_signed_url
    signed_url = get_signed_url(
        bucket_name=settings.SUPABASE_PAPERS_BUCKET,
        path=paper.supabase_path,
        expiry_seconds=300,
    )

    if signed_url:
        paper.download_count += 1
        paper.save(update_fields=["download_count"])
        return redirect(signed_url)
    else:
        messages.error(request, "Download unavailable. Please contact support.")
        return redirect("siteapp:downloads")


# ====================================================
# ADMIN — Material & Enrollment Fee Management
# ====================================================

@staff_required
def admin_upload_material(request, slug):
    """Admin: upload a note, video, or link to a classroom."""
    classroom = get_object_or_404(Classroom, slug=slug)
    if request.method == "POST":
        material_type = request.POST.get("material_type", "note")
        title = request.POST.get("title", "").strip()
        if not title:
            messages.error(request, "Title is required.")
            return redirect("siteapp:admin_classroom_detail", slug=slug)
        Material.objects.create(
            classroom=classroom,
            title=title,
            description=request.POST.get("description", ""),
            material_type=material_type,
            file=request.FILES.get("file") if material_type == "note" else None,
            video_url=request.POST.get("video_url", "") if material_type == "video" else "",
            external_url=request.POST.get("external_url", "") if material_type == "link" else "",
            order=int(request.POST.get("order", 0)),
            uploaded_by=request.user,
        )
        messages.success(request, f'Material "{title}" added.')
    return redirect("siteapp:admin_classroom_detail", slug=slug)


@staff_required
def admin_delete_material(request, material_id):
    """Admin: delete a classroom material."""
    material = get_object_or_404(Material, id=material_id)
    slug = material.classroom.slug
    material.delete()
    messages.success(request, "Material deleted.")
    return redirect("siteapp:admin_classroom_detail", slug=slug)


@staff_required
def admin_set_enrollment_fee(request, enrollment_id):
    """Admin: set or update the enrollment fee and due date for a student."""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    if request.method == "POST":
        fee = request.POST.get("enrollment_fee")
        due_date = request.POST.get("payment_due_date")
        status = request.POST.get("payment_status", enrollment.payment_status)

        enrollment.enrollment_fee = fee if fee else None
        enrollment.payment_due_date = due_date if due_date else None
        enrollment.payment_status = status

        # Reset notification flag if fee changes (so the email fires again)
        if fee and enrollment.enrollment_fee != fee:
            enrollment.fee_notification_sent = False

        enrollment.save()
        messages.success(
            request,
            f"Fee updated for {enrollment.student.get_full_name()}. "
            f"Notification email will be sent."
        )
    return redirect("siteapp:admin_classroom_detail", slug=enrollment.classroom.slug)
