from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone


class CustomUser(AbstractUser):
    # Phone validator
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+263712345678'. Up to 15 digits allowed.",
    )

    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        unique=True,
        blank=True,
        null=True,
        help_text="Phone number with country code",
    )

    school = models.CharField(max_length=200, help_text="School/Institution name")
    student_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="profile_pics/", blank=True, null=True
    )
    date_of_birth = models.DateField(blank=True, null=True)

    # academic info
    enrollment_date = models.DateField(default=timezone.now)
    current_level = models.CharField(
        max_length=50,
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ],
        default="beginner",
    )
    is_active_student = models.BooleanField(default=True)

    # metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        return f"{self.get_full_name()} ({self.student_id})"

    def save(self, *args, **kwargs):
        # auto-generate student ID if not exists
        if not self.student_id:
            year = timezone.now().year
            prefix = f"BW{year}"
            last_student = (
                CustomUser.objects.filter(student_id__startswith=prefix)
                .order_by("student_id")
                .last()
            )

            if last_student:
                try:
                    last_number = int(last_student.student_id[-3:])
                    new_number = last_number + 1
                except (ValueError, TypeError):
                    new_number = 1
            else:
                new_number = 1
            self.student_id = f"{prefix}{new_number:03d}"
        super().save(*args, **kwargs)


class Exam(models.Model):
    """Model for storing exams"""

    title = models.CharField(max_length=200)
    description = models.TextField()
    duration_minutes = models.IntegerField(help_text="Exam duration in minutes")
    total_marks = models.IntegerField(default=100)
    passing_marks = models.IntegerField(default=50)

    # Exam settings
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    # Admin controls
    is_held = models.BooleanField(
        default=False, help_text="Hold exam from being taken by students"
    )
    hold_reason = models.TextField(blank=True, help_text="Reason for holding the exam")
    enable_instant_grading = models.BooleanField(
        default=True, help_text="Enable instant grading with Groq AI"
    )
    show_answers_after_submit = models.BooleanField(
        default=True, help_text="Show correct answers after submission"
    )
    shuffle_questions = models.BooleanField(
        default=False, help_text="Randomize question order for each student"
    )
    shuffle_options = models.BooleanField(
        default=False, help_text="Randomize answer options for MCQs"
    )

    # categories

    CATEGORY_CHOICES = [
        ("python", "Python Programming"),
        ("java", "Java Programming"),
        ("web", "Web Development"),
        ("database", "Database Management"),
        ("Algorithms", "Data Structures & Algorithms"),
        ("Networks", "Computer Networks"),
        ("Vb.net", "Visual Basic Programming"),
        ("os", "Operating Systems"),
        ("other", "Other"),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    # difficulty level
    LEVEL_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="beginner")
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="created_exams"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Exam"
        verbose_name_plural = "Exams"

    def __str__(self):
        return self.title

    def is_available(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date


class Question(models.Model):
    """Model for exam questions"""

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()

    QUESTION_TYPE_CHOICES = [
        ("mcq", "Multiple Choice"),
        ("true_false", "True/False"),
        ("short_answer", "Short Answer"),
        ("essay", "Essay"),
        ("code", "programming"),
    ]
    question_type = models.CharField(
        max_length=20, choices=QUESTION_TYPE_CHOICES, default="mcq"
    )

    marks = models.IntegerField(default=1)
    order = models.IntegerField(default=0, help_text="Question order in exam")

    # For MCQ questions
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    correct_answer = models.CharField(
        max_length=500, help_text="Correct answer or answer key"
    )

    explanation = models.TextField(blank=True, help_text="Explanation for the answer")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Question"
        verbose_name_plural = "Questions"

    def __str__(self):
        return f"{self.exam.title} - Q{self.order}"


class ExamAttempt(models.Model):
    """Model for tracking student exam attempts"""

    student = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="exam_attempts"
    )
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="attempts")

    # Attempt details
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    time_taken_minutes = models.IntegerField(null=True, blank=True)

    # Results
    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("submitted", "Submitted"),
        ("graded", "Graded"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="in_progress"
    )
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    # AI Grading (for essay/short/programming answer questions)
    ai_graded = models.BooleanField(default=False)
    ai_feedback = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Exam Attempt"
        verbose_name_plural = "Exam Attempts"
        unique_together = ["student", "exam"]  # One attempt per student per exam

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.exam.title}"

    def calculate_score(self):
        """Calculate total score from answers"""
        answers = self.answers.all()
        total_score = sum(
            answer.marks_obtained for answer in answers if answer.marks_obtained
        )
        self.score = total_score

        # Calculate percentage
        if self.exam.total_marks > 0:
            self.percentage = (total_score / self.exam.total_marks) * 100

        self.save()
        return self.score

    def is_passed(self):
        """Check if student passed the exam"""
        return self.score >= self.exam.passing_marks if self.score else False


class Answer(models.Model):
    """Model for storing student answers"""

    attempt = models.ForeignKey(
        ExamAttempt, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="student_answers"
    )
    answer_text = models.TextField()
    is_correct = models.BooleanField(null=True, blank=True)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # AI grading for subjective answers
    ai_graded = models.BooleanField(default=False)
    ai_feedback = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["question__order"]
        verbose_name = "Answer"
        verbose_name_plural = "Answers"
        unique_together = ["attempt", "question"]

    def __str__(self):
        return f"{self.attempt.student.get_full_name()} - {self.question}"

    def check_answer(self):
        """Check if answer is correct (for MCQ/True-False)"""
        if self.question.question_type in ["mcq", "true_false"]:
            self.is_correct = (
                self.answer_text.strip().lower()
                == self.question.correct_answer.strip().lower()
            )
            self.marks_obtained = self.question.marks if self.is_correct else 0
            self.save()
        return self.is_correct


class Announcement(models.Model):
    """Model for announcements"""

    title = models.CharField(max_length=200)
    content = models.TextField()

    # Target audience
    TARGET_CHOICES = [
        ("all", "All Students"),
        ("beginner", "Beginner Level"),
        ("intermediate", "Intermediate Level"),
        ("advanced", "Advanced Level"),
    ]
    target_audience = models.CharField(
        max_length=20, choices=TARGET_CHOICES, default="all"
    )

    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(
        default=0,
        choices=[
            (0, "Normal"),
            (1, "Important"),
            (2, "Urgent"),
        ],
    )
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="announcements"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "-created_at"]
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"

    def __str__(self):
        return self.title


class DownloadResource(models.Model):
    """Model for downloadable resources"""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    CATEGORY_CHOICES = [
        ("programming_notes", "Programming Notes"),
        ("paper_1", "Question Papers - Paper 1"),
        ("paper_2", "Question Papers - Paper 2"),
        ("cs_books", "Computer Science Books"),
        ("qa", "Questions & Answers"),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    file = models.FileField(upload_to="downloads/")
    file_size = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    download_count = models.IntegerField(default=0)

    uploaded_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="uploaded_resources"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Download Resource"
        verbose_name_plural = "Download Resources"

    def __str__(self):
        return self.title


# blog feature(22/01/2026)


class ExamGrading(models.Model):
    """Track AI grading by Groq for non-MCQ answers"""

    attempt = models.ForeignKey(
        ExamAttempt, on_delete=models.CASCADE, related_name="groq_gradings"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    student_answer = models.TextField()

    # Groq AI Results
    groq_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    groq_feedback = models.TextField(blank=True)
    groq_reasoning = models.TextField(
        blank=True, help_text="Detailed reasoning from Groq"
    )

    # Admin override
    admin_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    admin_feedback = models.TextField(blank=True)
    admin_overridden = models.BooleanField(default=False)
    overridden_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grading_overrides",
    )

    graded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-graded_at"]
        unique_together = ["attempt", "question"]
        verbose_name = "Exam Grading"
        verbose_name_plural = "Exam Gradings"

    def __str__(self):
        return f"Grading: {self.attempt} - Q{self.question.order}"

    def get_final_score(self):
        """Get the final score (admin override or Groq score)"""
        if self.admin_overridden:
            return self.admin_score
        return self.groq_score or 0

    def get_final_feedback(self):
        """Get the final feedback (admin override or Groq feedback)"""
        if self.admin_overridden:
            return self.admin_feedback
        return self.groq_feedback


class ExamHold(models.Model):
    """Track exam holds/pauses"""

    exam = models.OneToOneField(Exam, on_delete=models.CASCADE, related_name="hold")
    held_at = models.DateTimeField(auto_now_add=True)
    held_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="exam_holds"
    )
    reason = models.TextField()

    # Auto-resume
    resume_at = models.DateTimeField(
        null=True, blank=True, help_text="Automatically resume exam at this time"
    )
    is_active = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-held_at"]
        verbose_name = "Exam Hold"
        verbose_name_plural = "Exam Holds"

    def __str__(self):
        return f"{self.exam.title} - Held"

    def should_auto_resume(self):
        """Check if exam should auto-resume"""
        if self.resume_at and timezone.now() >= self.resume_at:
            return True
        return False


# blog feature (22/01/2026)


class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    image = models.ImageField(upload_to="blog_pics/")
    created_at = models.DateTimeField(auto_now_add=True)
    likes_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("siteapp:blog_detail", kwargs={"slug": self.slug})


class Comment(models.Model):
    post = models.ForeignKey(
        BlogPost, related_name="comments", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    body = models.TextField()
    dated_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} on {self.post.title}"
