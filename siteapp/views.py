from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, FileResponse, JsonResponse
from django.db.models import Avg, Count, Q, Sum, F, IntegerField
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse_lazy
from django.views.decorators.cache import cache_control
from datetime import timedelta

from .models import (
    CustomUser,
    Exam,
    Question,
    ExamAttempt,
    Answer,
    Announcement,
    DownloadResource,
    BlogPost,
    Comment,
)
from .forms import (
    StudentRegistrationForm,
    StudentLoginForm,
    ProfileUpdateForm,
    ExamAnswerForm,
    ContactForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
)
from .pdf_generator import generate_student_report

# ============= PUBLIC VIEWS =============


def home(request):
    """Homepage view"""
    announcements = Announcement.objects.filter(is_active=True)[:3]
    latest_blogs = BlogPost.objects.all().order_by("-created_at")[:3]
    context = {
        "announcements": announcements,
        "latest_blogs": latest_blogs,
    }
    return render(request, "siteapp/home.html", context)


def about(request):
    """About page view"""
    return render(request, "siteapp/about.html")


def terms_of_service(request):
    """Terms of Service page view"""
    return render(request, "siteapp/terms_of_service.html")


def privacy_policy(request):
    """Privacy Policy page view"""
    return render(request, "siteapp/privacy_policy.html")


def downloads(request):
    """Downloads page view"""
    programming_notes = DownloadResource.objects.filter(
        category="programming_notes", is_active=True
    )
    paper_1 = DownloadResource.objects.filter(category="paper_1", is_active=True)
    paper_2 = DownloadResource.objects.filter(category="paper_2", is_active=True)
    cs_books = DownloadResource.objects.filter(category="cs_books", is_active=True)
    qa_resources = DownloadResource.objects.filter(category="qa", is_active=True)

    context = {
        "programming_notes": programming_notes,
        "paper_1": paper_1,
        "paper_2": paper_2,
        "cs_books": cs_books,
        "qa_resources": qa_resources,
    }
    return render(request, "siteapp/downloads.html", context)


def blog(request):
    """Blog page view with search and carousel support"""
    query = request.GET.get("q")
    posts = BlogPost.objects.all().order_by("-created_at")

    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(content__icontains=query))

    carousel_posts = BlogPost.objects.all().order_by("-created_at")[:4]

    context = {
        "posts": posts,
        "carousel_posts": carousel_posts,
    }
    return render(request, "siteapp/blog.html", context)


def contact(request):
    """Contact page view"""
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            subject = f"Contact Form: {form.cleaned_data['subject']}"
            message = f"""
            Name: {form.cleaned_data['name']}
            Email: {form.cleaned_data['email']}
            Phone: {form.cleaned_data['phone']}
           
            Message:
            {form.cleaned_data['message']}
            """

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    ["academybluewave@gmail.com"],
                    fail_silently=False,
                )
                messages.success(request, "Your message has been sent successfully!")
            except:
                messages.error(request, "Failed to send message. Please try WhatsApp.")

            return redirect("siteapp:contact")
    else:
        form = ContactForm()

    return render(request, "siteapp/contact.html", {"form": form})


# ============= AUTHENTICATION VIEWS =============


def register(request):
    """Student registration view"""
    if request.user.is_authenticated:
        return redirect("siteapp:dashboard")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request, f"Welcome to Bluewave Academy, {user.first_name}!"
            )
            return redirect("siteapp:dashboard")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = StudentRegistrationForm()

    return render(request, "siteapp/student/register.html", {"form": form})


def student_login(request):
    """Student login view"""
    if request.user.is_authenticated:
        return redirect("siteapp:dashboard")

    if request.method == "POST":
        form = StudentLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            remember_me = form.cleaned_data.get("remember_me")

            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)

                if not remember_me:
                    request.session.set_expiry(0)

                messages.success(request, f"Welcome back, {user.first_name}!")

                next_page = request.GET.get("next")
                if next_page:
                    return redirect(next_page)
                return redirect("siteapp:dashboard")
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Invalid email or password.")
    else:
        form = StudentLoginForm()

    return render(request, "siteapp/student/login.html", {"form": form})


def student_logout(request):
    """Student logout view"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("siteapp:home")


def logout_page(request):
    """Logout confirmation page"""
    return render(request, "siteapp/student/logout.html")


# ============= STUDENT DASHBOARD =============


def is_ajax(request):
    """Check if request is AJAX"""
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


@login_required(login_url="siteapp:login")
def student_dashboard(request):
    """Student portal with tabbed interface"""
    student = request.user
    from django.utils import timezone

    context = {
        "student": student,
        "current_date": timezone.now(),
    }

    return render(request, "siteapp/student/dashboard.html", context)


@login_required(login_url="siteapp:login")
def profile(request):
    """View student profile - returns partial HTML"""
    if is_ajax(request):
        return render(
            request, "siteapp/student/partials/profile.html", {"user": request.user}
        )
    return render(request, "siteapp/student/dashboard.html", {"user": request.user})


@login_required(login_url="siteapp:login")
def edit_profile(request):
    """Edit student profile"""
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("siteapp:profile")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "siteapp/student/edit_profile.html", {"form": form})


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url="siteapp:login")
def analytics(request):
    """Student analytics - returns partial HTML"""
    student = request.user

    attempts = (
        ExamAttempt.objects.filter(student=student, status="graded")
        .select_related("exam")
        .order_by("-created_at")
    )

    context = {
        "attempts": attempts,
    }

    # Return partial template for AJAX requests
    if is_ajax(request):
        return render(request, "siteapp/student/partials/analytics.html", context)

    return render(request, "siteapp/student/dashboard.html", context)


# ============= EXAM VIEWS =============


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url="siteapp:login")
def exam_list(request):
    """List all exams - returns partial HTML for AJAX"""
    student = request.user

    exams = Exam.objects.filter(
        is_active=True, start_date__lte=timezone.now(), end_date__gte=timezone.now()
    )

    context = {
        "exams": exams,
    }

    # Return partial template for AJAX requests
    if is_ajax(request):
        return render(request, "siteapp/student/partials/exam_list.html", context)

    return render(request, "siteapp/student/dashboard.html", context)


@login_required(login_url="siteapp:login")
def exam_detail(request, exam_id):
    """View exam details"""
    exam = get_object_or_404(Exam, id=exam_id)

    attempt = ExamAttempt.objects.filter(student=request.user, exam=exam).first()

    context = {
        "exam": exam,
        "attempt": attempt,
        "question_count": exam.questions.count(),
    }

    return render(request, "siteapp/exams/exam_detail.html", context)


@login_required(login_url="siteapp:login")
def take_exam(request, exam_id):
    """Take an exam"""
    exam = get_object_or_404(Exam, id=exam_id)
    student = request.user

    if not exam.is_available():
        messages.error(request, "This exam is not currently available.")
        return redirect("siteapp:exam_list")

    # Only redirect to results if exam was already submitted/graded
    existing_attempt = ExamAttempt.objects.filter(
        student=student, exam=exam, status__in=["submitted", "graded"]
    ).first()

    if existing_attempt:
        messages.warning(request, "You have already attempted this exam.")
        return redirect("siteapp:exam_results", attempt_id=existing_attempt.id)

    # Check if there's an in-progress attempt and use it, otherwise create new
    in_progress_attempt = ExamAttempt.objects.filter(
        student=student, exam=exam, status="in_progress"
    ).first()

    if in_progress_attempt:
        attempt = in_progress_attempt
    else:
        attempt = ExamAttempt.objects.create(
            student=student, exam=exam, status="in_progress"
        )

    questions = exam.questions.all()

    # Only submit exam when user confirms (submit=true)
    if request.method == "POST" and request.POST.get("submit") == "true":
        # Delete existing answers to avoid duplicates
        attempt.answers.all().delete()

        # Process answers
        for question in questions:
            answer_text = request.POST.get(f"question_{question.id}")
            if answer_text:
                answer = Answer.objects.create(
                    attempt=attempt, question=question, answer_text=answer_text
                )
                answer.check_answer()

        attempt.end_time = timezone.now()
        time_diff = attempt.end_time - attempt.start_time
        attempt.time_taken_minutes = int(time_diff.total_seconds() / 60)
        attempt.status = "submitted"
        attempt.save()

        attempt.calculate_score()

        messages.success(request, "Exam submitted successfully!")
        return redirect("siteapp:exam_results", attempt_id=attempt.id)

    context = {
        "exam": exam,
        "attempt": attempt,
        "questions": questions,
    }

    return render(request, "siteapp/exams/take_exam.html", context)


@login_required(login_url="siteapp:login")
def submit_exam(request, exam_id):
    """Submit exam (AJAX)"""
    if request.method == "POST":
        exam = get_object_or_404(Exam, id=exam_id)
        student = request.user

        attempt = ExamAttempt.objects.filter(
            student=student, exam=exam, status="in_progress"
        ).first()

        if not attempt:
            return JsonResponse({"error": "No active attempt found"}, status=400)

        attempt.end_time = timezone.now()
        time_diff = attempt.end_time - attempt.start_time
        attempt.time_taken_minutes = int(time_diff.total_seconds() / 60)
        attempt.status = "submitted"
        attempt.save()

        attempt.calculate_score()

        return JsonResponse(
            {
                "success": True,
                "attempt_id": attempt.id,
                "redirect_url": f"/student/exam/results/{attempt.id}/",
            }
        )

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required(login_url="siteapp:login")
def exam_results(request, attempt_id):
    """View exam results"""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)

    answers = attempt.answers.select_related("question").all()
    total_questions = answers.count()
    correct_answers = answers.filter(is_correct=True).count()
    incorrect_answers = total_questions - correct_answers

    # Calculate marks needed to pass (if failed)
    marks_needed = max(0, attempt.exam.passing_marks - (attempt.score or 0))

    context = {
        "attempt": attempt,
        "answers": answers,
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "incorrect_answers": incorrect_answers,
        "passed": attempt.is_passed(),
        "marks_needed": marks_needed,
    }

    return render(request, "siteapp/exams/exam_results.html", context)


@login_required(login_url="siteapp:login")
def download_exam_report(request, attempt_id):
    """Download exam result report as PDF (student-only)"""
    # Verify student owns this attempt
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)

    try:
        pdf_buffer = generate_student_report(attempt)

        filename = (
            f"{attempt.student.first_name}_{attempt.exam.title}_{attempt.id}_report.pdf"
        )
        filename = filename.replace(" ", "_")

        response = FileResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect("siteapp:exam_results", attempt_id=attempt_id)
    response = FileResponse(resource.file.open("rb"))
    response["Content-Disposition"] = f'attachment; filename="{resource.file.name}"'
    return response


@login_required(login_url="siteapp:login")
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def announcements(request):
    """View all announcements - returns partial HTML"""
    announcements = Announcement.objects.filter(is_active=True).order_by(
        "-priority", "-created_at"
    )

    context = {
        "announcements": announcements,
    }

    # Return partial template for AJAX requests
    if is_ajax(request):
        return render(request, "siteapp/student/partials/announcements.html", context)

    return render(request, "siteapp/student/dashboard.html", context)


@login_required(login_url="siteapp:login")
def download_resource(request, resource_id):
    """Download a resource"""
    resource = get_object_or_404(DownloadResource, id=resource_id, is_active=True)

    if resource.file:
        response = FileResponse(
            resource.file.open("rb"), content_type="application/octet-stream"
        )
        response["Content-Disposition"] = f'attachment; filename="{resource.file.name}"'
        return response

    messages.error(request, "File not found.")
    return redirect("siteapp:downloads")


# ================blog feature================#
def blog_list(request):
    query = request.GET.get("q")
    posts = BlogPost.objects.all().order_by("-created_at")

    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(content__icontains=query))

    carousel_posts = BlogPost.objects.all().order_by("-created_at")[:4]

    return render(
        request,
        "siteapp/blog.html",
        {
            "posts": posts,
            "carousel_posts": carousel_posts,
        },
    )


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)

    if request.method == "POST":
        guest_name = request.POST.get("name")
        guest_body = request.POST.get("body")

        Comment.objects.create(post=post, name=guest_name, body=guest_body)
        return redirect("siteapp:blog_detail", slug=slug)

    return render(request, "siteapp/blog_detail.html", {"post": post})


def like_post(request, slug):
    if request.method == "POST":
        post = get_object_or_404(BlogPost, slug=slug)
        post.likes_count += 1
        post.save()
        return JsonResponse({"new_count": post.likes_count})
    return JsonResponse({"error": "invalid request"}, status=400)


# ============= CUSTOM PASSWORD RESET VIEWS =============


class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view with proper success URL"""

    form_class = CustomPasswordResetForm
    template_name = "siteapp/password_reset.html"
    email_template_name = "siteapp/password_reset_email.html"
    subject_template_name = "siteapp/password_reset_subject.txt"
    success_url = reverse_lazy("siteapp:password_reset_done")


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Custom password reset confirm view with proper success URL"""

    form_class = CustomSetPasswordForm
    template_name = "siteapp/password_reset_confirm.html"
    success_url = reverse_lazy("siteapp:password_reset_complete")
