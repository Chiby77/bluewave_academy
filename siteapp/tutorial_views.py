"""
Student-facing views for the Video Tutorial section.
Login required — videos are stream-only (no download).
Progress is tracked per student per tutorial.
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Prefetch

from .models import Tutorial, VideoProgress


@login_required
def tutorial_list(request):
    tutorials = Tutorial.objects.filter(status="published")

    category = request.GET.get("category", "").strip()
    if category:
        tutorials = tutorials.filter(category=category)

    q = request.GET.get("q", "").strip()
    if q:
        tutorials = tutorials.filter(title__icontains=q)

    progress_map = {}
    if request.user.is_authenticated:
        for p in VideoProgress.objects.filter(student=request.user, tutorial__in=tutorials):
            progress_map[p.tutorial_id] = p

    tutorial_data = []
    for t in tutorials:
        prog = progress_map.get(t.id)
        tutorial_data.append({
            "tutorial": t,
            "progress": prog.progress_pct if prog else 0,
            "completed": prog.completed if prog else False,
        })

    categories = Tutorial.CATEGORY_CHOICES

    return render(request, "siteapp/student/tutorials.html", {
        "tutorial_data": tutorial_data,
        "categories": categories,
        "active_category": category,
        "q": q,
        "total": tutorials.count(),
    })


@login_required
def tutorial_detail(request, slug):
    tutorial = get_object_or_404(Tutorial, slug=slug, status="published")

    Tutorial.objects.filter(pk=tutorial.pk).update(view_count=tutorial.view_count + 1)

    progress_obj, _ = VideoProgress.objects.get_or_create(
        student=request.user,
        tutorial=tutorial,
        defaults={"progress_pct": 0, "completed": False},
    )

    related = Tutorial.objects.filter(
        status="published", category=tutorial.category
    ).exclude(pk=tutorial.pk)[:4]

    return render(request, "siteapp/student/tutorial_detail.html", {
        "tutorial": tutorial,
        "progress": progress_obj,
        "related": related,
        "embed_url": tutorial.get_embed_url() if tutorial.video_type == "url" else None,
    })


@login_required
@require_POST
def update_video_progress(request):
    try:
        data = json.loads(request.body)
        tutorial_id = int(data.get("tutorial_id", 0))
        pct = float(data.get("progress", 0))
        pct = max(0, min(100, pct))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "invalid data"}, status=400)

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

    # Recalculate progress for any course enrollments that include this tutorial
    for cl in tutorial.course_lessons.select_related("course"):
        try:
            enrollment = CourseEnrollment.objects.get(student=request.user, course=cl.course)
            enrollment.recalculate_progress()
        except CourseEnrollment.DoesNotExist:
            pass

    return JsonResponse({"ok": True, "progress": prog.progress_pct, "completed": prog.completed})


# ============================================================
# COURSE STUDENT VIEWS
# ============================================================

from .models import Course, CourseLesson, CourseEnrollment


@login_required
def course_list(request):
    """Browse all published courses with enrollment + progress."""
    courses = Course.objects.filter(status="published").prefetch_related("lessons")

    category = request.GET.get("category", "").strip()
    if category:
        courses = courses.filter(category=category)

    q = request.GET.get("q", "").strip()
    if q:
        courses = courses.filter(title__icontains=q)

    # Build enrollment map for this student
    enrollment_map = {}
    for e in CourseEnrollment.objects.filter(student=request.user, course__in=courses):
        enrollment_map[e.course_id] = e

    course_data = []
    for c in courses:
        enrollment = enrollment_map.get(c.id)
        course_data.append({
            "course": c,
            "lesson_count": c.lessons.count(),
            "enrolled": enrollment is not None,
            "progress": enrollment.progress_pct if enrollment else 0,
            "completed": enrollment.completed if enrollment else False,
        })

    return render(request, "siteapp/student/courses.html", {
        "course_data": course_data,
        "categories": Tutorial.CATEGORY_CHOICES,
        "active_category": category,
        "q": q,
    })


@login_required
def course_detail(request, slug):
    """Course overview: syllabus + enrol button."""
    course = get_object_or_404(Course, slug=slug, status="published")
    lessons = course.lessons.select_related("tutorial").order_by("order")

    enrollment = None
    try:
        enrollment = CourseEnrollment.objects.get(student=request.user, course=course)
    except CourseEnrollment.DoesNotExist:
        pass

    # Build completed set for tick marks
    completed_ids = set()
    if enrollment:
        tut_ids = lessons.values_list("tutorial_id", flat=True)
        completed_ids = set(
            VideoProgress.objects.filter(
                student=request.user, tutorial_id__in=tut_ids, completed=True
            ).values_list("tutorial_id", flat=True)
        )

    lesson_data = [
        {
            "lesson": l,
            "completed": l.tutorial_id in completed_ids,
        }
        for l in lessons
    ]

    return render(request, "siteapp/student/course_detail.html", {
        "course": course,
        "lesson_data": lesson_data,
        "enrollment": enrollment,
    })


@login_required
def course_enrol(request, slug):
    """POST — enrol student in course."""
    if request.method != "POST":
        return redirect("siteapp:course_detail", slug=slug)
    course = get_object_or_404(Course, slug=slug, status="published")
    _, created = CourseEnrollment.objects.get_or_create(student=request.user, course=course)
    if created:
        from django.contrib import messages as msg
        msg.success(request, f'You are now enrolled in "{course.title}"!')
    # Redirect to the first lesson
    first = course.lessons.order_by("order").first()
    if first:
        return redirect("siteapp:course_watch", slug=slug, lesson_num=1)
    return redirect("siteapp:course_detail", slug=slug)


@login_required
def course_watch(request, slug, lesson_num):
    """Main watch page: player + lesson playlist sidebar."""
    course = get_object_or_404(Course, slug=slug, status="published")

    # Must be enrolled
    try:
        enrollment = CourseEnrollment.objects.get(student=request.user, course=course)
    except CourseEnrollment.DoesNotExist:
        return redirect("siteapp:course_detail", slug=slug)

    lessons = list(course.lessons.select_related("tutorial").order_by("order"))
    total = len(lessons)
    if total == 0:
        return redirect("siteapp:course_detail", slug=slug)

    # Clamp lesson_num to valid range
    lesson_num = max(1, min(lesson_num, total))
    current_lesson = lessons[lesson_num - 1]
    tutorial = current_lesson.tutorial

    # Track view count
    Tutorial.objects.filter(pk=tutorial.pk).update(view_count=tutorial.view_count + 1)

    progress_obj, _ = VideoProgress.objects.get_or_create(
        student=request.user, tutorial=tutorial,
        defaults={"progress_pct": 0, "completed": False},
    )

    # Build playlist data with completion ticks
    tut_ids = [l.tutorial_id for l in lessons]
    completed_ids = set(
        VideoProgress.objects.filter(
            student=request.user, tutorial_id__in=tut_ids, completed=True
        ).values_list("tutorial_id", flat=True)
    )

    playlist = [
        {
            "lesson": l,
            "num": i + 1,
            "completed": l.tutorial_id in completed_ids,
            "is_current": (i + 1) == lesson_num,
        }
        for i, l in enumerate(lessons)
    ]

    next_num = lesson_num + 1 if lesson_num < total else None
    prev_num = lesson_num - 1 if lesson_num > 1 else None
    done_count = len(completed_ids)

    return render(request, "siteapp/student/course_watch.html", {
        "course": course,
        "enrollment": enrollment,
        "current_lesson": current_lesson,
        "tutorial": tutorial,
        "lesson_num": lesson_num,
        "total": total,
        "next_num": next_num,
        "prev_num": prev_num,
        "playlist": playlist,
        "progress": progress_obj,
        "done_count": done_count,
        "embed_url": tutorial.get_embed_url() if tutorial.video_type == "url" else None,
    })
