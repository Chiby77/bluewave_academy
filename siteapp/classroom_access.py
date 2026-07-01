"""
classroom_access.py — Payment-gating decorator & fee notification signal.

Usage in views:
    @classroom_access_required
    def my_view(request, slug, ...):
        ...

The decorator resolves the classroom from the 'slug' kwarg, checks the
student's Enrollment for payment status, and redirects to the
payment-required page if overdue.

The post_save signal fires once when an admin first sets an enrollment fee,
sending a single automated email to the student.
"""

from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.conf import settings


def classroom_access_required(view_func):
    """
    Decorator for any classroom-scoped view.

    Resolves the classroom via the 'slug' URL kwarg (or 'assignment_id' for
    assignment views by looking up the classroom from the assignment).

    Blocks access when:
        enrollment.payment_status == 'unpaid'  AND
        current datetime  >  enrollment.payment_due_date
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Skip check for staff — admins always have access
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)

        from django.utils import timezone
        from .models import Enrollment, Classroom, Assignment

        classroom = None

        # Resolve classroom from 'slug' kwarg (classroom detail / enroll views)
        if "slug" in kwargs:
            classroom = get_object_or_404(Classroom, slug=kwargs["slug"], is_active=True)

        # Resolve classroom from 'assignment_id' (take_assignment view)
        elif "assignment_id" in kwargs:
            assignment = get_object_or_404(Assignment, id=kwargs["assignment_id"], is_active=True)
            classroom = assignment.classroom

        if classroom is None:
            return view_func(request, *args, **kwargs)

        try:
            enrollment = Enrollment.objects.get(
                student=request.user,
                classroom=classroom,
                is_active=True,
            )
        except Enrollment.DoesNotExist:
            # Not enrolled — let the view handle its own redirect/error
            return view_func(request, *args, **kwargs)

        if enrollment.is_payment_overdue():
            messages.error(
                request,
                f"Your access to \"{classroom.name}\" is suspended. "
                f"Please complete your payment of "
                f"${enrollment.enrollment_fee} to regain access."
            )
            return redirect("siteapp:payment_required", slug=classroom.slug)

        return view_func(request, *args, **kwargs)

    return wrapper


# ──────────────────────────────────────────────────────────────
# Signal: send one email when admin first assigns a fee
# ──────────────────────────────────────────────────────────────

@receiver(post_save, sender="siteapp.Enrollment")
def send_fee_notification(sender, instance, created, **kwargs):
    """
    Fire once when an enrollment fee is set for the first time.
    Uses the fee_notification_sent flag to prevent duplicate emails.
    """
    # Only trigger when a fee exists and we haven't notified yet
    if not instance.enrollment_fee or instance.fee_notification_sent:
        return

    student = instance.student
    classroom = instance.classroom
    fee = instance.enrollment_fee
    due = instance.payment_due_date

    due_str = due.strftime("%d %B %Y at %H:%M") if due else "as soon as possible"

    subject = f"Payment Required — {classroom.name} | Bluewave Academy"
    body = f"""Dear {student.get_full_name()},

Your instructor has set an enrollment fee for the classroom: {classroom.name}.

Fee: ${fee}
Payment Deadline: {due_str}

Please arrange payment before the deadline to maintain uninterrupted access
to your classroom materials and assignments.

If you have already paid or believe this is an error, please contact your
instructor or Bluewave Academy support.

Log in to your student portal to check your enrollment status.

Bluewave Academy
"""
    try:
        EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email],
        ).send(fail_silently=True)

        # Mark as sent so this block never fires again for this enrollment
        sender.objects.filter(pk=instance.pk).update(fee_notification_sent=True)
    except Exception as e:
        print(f"[ClassroomAccess] Fee notification email error: {e}")
