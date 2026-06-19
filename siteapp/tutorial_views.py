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

    return JsonResponse({"ok": True, "progress": prog.progress_pct, "completed": prog.completed})
