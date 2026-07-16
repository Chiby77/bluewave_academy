"""
Celery tasks for Bluewave Academy.

All tasks are decorated with @shared_task so they work regardless of how
Celery is initialised (useful for testing without a running broker).
"""
import logging

try:
    from celery import shared_task
    HAS_CELERY = True
except ImportError:
    HAS_CELERY = False

    # Create dummy decorator that does nothing
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from django.core.cache import cache
from django.db.models import Avg, Count, F, Q

logger = logging.getLogger(__name__)

# The Redis key where pre-computed dashboard stats live.
DASHBOARD_STATS_KEY = "bwa:dashboard_stats"
# TTL slightly longer than the 5-min schedule so there is always a value
# in the cache even if Celery is delayed by a few seconds.
DASHBOARD_STATS_TTL = 360  # 6 minutes


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def refresh_dashboard_stats(self=None):
    """
    Pre-compute all Admin Dashboard aggregations and push them to Redis.

    Runs every 5 minutes via Celery Beat. Because we write to Redis on a
    schedule the dashboard view never triggers a direct database query —
    completely eliminating cache-stampede risk.
    """
    try:
        from .models import CustomUser, Exam, ExamAttempt

        total_exams = Exam.objects.count()
        total_students = CustomUser.objects.filter(is_active_student=True).count()
        total_attempts = ExamAttempt.objects.count()
        total_graded = ExamAttempt.objects.filter(status="graded").count()

        if total_graded > 0:
            passed = ExamAttempt.objects.filter(
                status="graded",
                score__gte=F("exam__passing_marks"),
            ).count()
            pass_rate = round((passed / total_graded) * 100, 2)
        else:
            pass_rate = 0.0

        held_exams = Exam.objects.filter(is_held=True).count()

        # Serialise to plain Python types so we can JSON-pickle into Redis.
        category_stats = list(
            Exam.objects.values("category")
            .annotate(count=Count("id"), avg_score=Avg("attempts__score"))
            .order_by("category")
        )

        stats = {
            "total_exams": total_exams,
            "total_students": total_students,
            "total_attempts": total_attempts,
            "total_graded": total_graded,
            "pass_rate": pass_rate,
            "held_exams": held_exams,
            "category_stats": category_stats,
        }

        cache.set(DASHBOARD_STATS_KEY, stats, timeout=DASHBOARD_STATS_TTL)
        logger.info("Dashboard stats refreshed and cached (key=%s)", DASHBOARD_STATS_KEY)
        return stats

    except Exception as exc:
        logger.error("refresh_dashboard_stats failed: %s", exc)
        if HAS_CELERY and self:
            raise self.retry(exc=exc)

