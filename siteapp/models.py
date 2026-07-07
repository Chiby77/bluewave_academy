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

    # For MCQ questions — TextField so options can hold lengthy technical content
    option_a = models.TextField(blank=True)
    option_b = models.TextField(blank=True)
    option_c = models.TextField(blank=True)
    option_d = models.TextField(blank=True)
    correct_answer = models.TextField(help_text="Correct answer or answer key")

    explanation = models.TextField(blank=True, help_text="Explanation for the answer")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Question"
        verbose_name_plural = "Questions"

    def __str__(self):
        return f"{self.exam.title} - Q{self.order}"

    @property
    def get_choices(self):
        """Return list of (letter, text) tuples for non-empty MCQ options."""
        return [
            (letter, text)
            for letter, text in [
                ("A", self.option_a),
                ("B", self.option_b),
                ("C", self.option_c),
                ("D", self.option_d),
            ]
            if text
        ]


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

    attempt_number = models.PositiveSmallIntegerField(
        default=1, help_text="1 = first attempt, 2 = second attempt"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Exam Attempt"
        verbose_name_plural = "Exam Attempts"
        unique_together = ["student", "exam", "attempt_number"]

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
    CATEGORY_CHOICES = [
        ("Programming", "Programming"),
        ("Web Development", "Web Development"),
        ("Database", "Database"),
        ("Algorithms", "Algorithms"),
        ("Career Tips", "Career Tips"),
        ("Academy News", "Academy News"),
        ("Other", "Other"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    image = models.ImageField(upload_to="blog_pics/", blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, default="Other")
    author = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="blog_posts"
    )
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


# =============================================
# SPECIAL PAPERS (Supabase Bucket Integration)
# =============================================

class SpecialPaper(models.Model):
    CATEGORY_CHOICES = [
        ("zimsec_cs", "ZIMSEC Computer Science"),
        ("zimsec_math", "ZIMSEC Mathematics"),
        ("zimsec_phy", "ZIMSEC Physics"),
        ("alevel_cs", "A-Level CS"),
        ("olevel_cs", "O-Level CS"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="zimsec_cs")
    year = models.IntegerField(blank=True, null=True)
    paper_number = models.CharField(max_length=20, blank=True, help_text="e.g. Paper 1, Paper 2, Solutions")
    supabase_path = models.CharField(max_length=500, help_text="Path in Supabase storage bucket, e.g. papers/2023/cs-p1.pdf")
    is_public = models.BooleanField(default=False, help_text="If False, login is required to download")
    is_active = models.BooleanField(default=True)
    download_count = models.IntegerField(default=0)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="special_papers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "category", "paper_number"]
        verbose_name = "Special Paper"
        verbose_name_plural = "Special Papers"

    def __str__(self):
        return f"{self.title} ({self.year or 'N/A'})"


# =============================================
# CLASSROOM MATERIALS
# =============================================

class Material(models.Model):
    TYPE_CHOICES = [
        ("note", "Notes / Document"),
        ("video", "Video"),
        ("link", "External Link"),
    ]

    classroom = models.ForeignKey(
        "Classroom", on_delete=models.CASCADE, related_name="materials"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="note")

    # For uploaded files (notes/PDFs)
    file = models.FileField(upload_to="classroom/materials/", blank=True, null=True)
    # For videos — can be a local file or an external URL
    video_url = models.URLField(blank=True, help_text="YouTube or direct video URL")
    # For external links
    external_url = models.URLField(blank=True)

    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Sort order within classroom")
    uploaded_by = models.ForeignKey(
        "CustomUser", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="uploaded_materials"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]
        verbose_name = "Material"
        verbose_name_plural = "Materials"

    def __str__(self):
        return f"{self.classroom.name} — {self.title}"

    def get_embed_url(self):
        """Convert YouTube watch URL to embed URL."""
        import re
        url = self.video_url or ""
        match = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url)
        if match:
            return f"https://www.youtube-nocookie.com/embed/{match.group(1)}?rel=0&modestbranding=1"
        return url


# =============================================
# THE EXAMINATOR — Digital Assessment Engine
# =============================================

class Classroom(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="taught_classrooms",
        limit_choices_to={"is_staff": True}
    )
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    cover_color = models.CharField(max_length=7, default="#2563eb", help_text="Hex color for classroom card")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Classroom"
        verbose_name_plural = "Classrooms"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Classroom.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def enrolled_count(self):
        return self.enrollments.filter(is_active=True).count()

    def active_assignments(self):
        return self.assignments.filter(is_active=True)


class Enrollment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("paid", "Paid"),
        ("waived", "Waived"),
    ]

    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="enrollments")
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Financial gating
    enrollment_fee = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Fee amount in USD. Leave blank if free."
    )
    payment_due_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Deadline by which student must pay to retain access."
    )
    payment_status = models.CharField(
        max_length=10, choices=PAYMENT_STATUS_CHOICES, default="unpaid"
    )
    fee_notification_sent = models.BooleanField(
        default=False,
        help_text="True after the fee-assignment email has been sent."
    )

    class Meta:
        unique_together = ["student", "classroom"]
        ordering = ["-enrolled_at"]
        verbose_name = "Enrollment"
        verbose_name_plural = "Enrollments"

    def __str__(self):
        return f"{self.student.get_full_name()} in {self.classroom.name}"

    def is_payment_overdue(self):
        """Return True when unpaid AND past the due date."""
        from django.utils import timezone
        if self.payment_status == "paid" or self.payment_status == "waived":
            return False
        if self.payment_due_date and timezone.now() > self.payment_due_date:
            return True
        return False

    def requires_fee(self):
        """True when a non-zero fee has been set by admin."""
        return self.enrollment_fee is not None and self.enrollment_fee > 0


class Assignment(models.Model):
    TYPE_CHOICES = [
        ("quiz", "Online Quiz (MCQ / Short Answer)"),
        ("coding", "Coding Practical"),
        ("pdf_upload", "Written / PDF Upload"),
        ("timed_quiz", "Timed Quiz"),
    ]

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=200)
    description = models.TextField()
    assignment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="quiz")

    # Grading
    rubric = models.TextField(blank=True, help_text="Grading rubric shown to the AI grader")
    answer_key = models.TextField(blank=True, help_text="Model answer or expected output")
    total_marks = models.IntegerField(default=100)
    passing_marks = models.IntegerField(default=50)

    # Timing
    deadline = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60, help_text="Time limit in minutes (0 = no limit)")

    # Settings
    is_active = models.BooleanField(default=True)
    allow_resubmit = models.BooleanField(default=False)
    show_results_immediately = models.BooleanField(default=True)
    programming_language = models.CharField(
        max_length=30, blank=True,
        help_text="For coding assignments: python, java, javascript, etc."
    )

    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="created_assignments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Assignment"
        verbose_name_plural = "Assignments"

    def __str__(self):
        return f"{self.classroom.name} — {self.title}"

    def is_past_deadline(self):
        from django.utils import timezone
        return timezone.now() > self.deadline

    def is_coding(self):
        return self.assignment_type == "coding"

    def is_pdf_upload(self):
        return self.assignment_type == "pdf_upload"


class Submission(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("grading", "Grading in Progress"),
        ("graded", "Graded"),
        ("failed", "Grading Failed"),
        ("manual_review", "Needs Manual Review"),
    ]

    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="submissions")
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")

    # Submission content
    text_answer = models.TextField(blank=True, help_text="Text / short-answer / essay response")
    code_text = models.TextField(blank=True, help_text="Code submission for coding practicals")
    pdf_file = models.FileField(upload_to="submissions/pdfs/", blank=True, null=True, help_text="PDF for written/handwritten submissions")

    # Timing
    submitted_at = models.DateTimeField(auto_now_add=True)
    time_taken_seconds = models.IntegerField(null=True, blank=True)

    # Grading results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    ai_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ai_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ai_feedback = models.TextField(blank=True)
    ai_strengths = models.JSONField(default=list, blank=True)
    ai_improvements = models.JSONField(default=list, blank=True)
    ai_improvement_tips = models.JSONField(default=list, blank=True)
    ai_reasoning = models.TextField(blank=True)

    # Admin / instructor override
    final_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    instructor_feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="graded_submissions"
    )
    graded_at = models.DateTimeField(null=True, blank=True)

    # Report
    report_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-submitted_at"]
        unique_together = ["student", "assignment"]
        verbose_name = "Submission"
        verbose_name_plural = "Submissions"

    def __str__(self):
        return f"{self.student.get_full_name()} — {self.assignment.title}"

    def get_score(self):
        return self.final_score if self.final_score is not None else self.ai_score

    def get_percentage(self):
        score = self.get_score()
        if score is None:
            return None
        total = self.assignment.total_marks
        return round((float(score) / total) * 100, 1) if total > 0 else 0

    def is_passed(self):
        score = self.get_score()
        return float(score) >= self.assignment.passing_marks if score is not None else False


# =============================================
# VIDEO TUTORIALS
# =============================================

class Tutorial(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
    ]
    CATEGORY_CHOICES = [
        ("Programming", "Programming"),
        ("Web Development", "Web Development"),
        ("Database", "Database"),
        ("Algorithms", "Algorithms"),
        ("Computer Science", "Computer Science"),
        ("Career Tips", "Career Tips"),
        ("Other", "Other"),
    ]
    VIDEO_TYPE_CHOICES = [
        ("file", "Uploaded File"),
        ("url", "YouTube / External URL"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to="tutorials/thumbnails/", blank=True, null=True)
    video_type = models.CharField(max_length=10, choices=VIDEO_TYPE_CHOICES, default="url")
    video_file = models.FileField(upload_to="tutorials/videos/", blank=True, null=True)
    video_url = models.URLField(blank=True, help_text="YouTube or other embed-compatible URL")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="Other")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tutorials"
    )
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tutorial"
        verbose_name_plural = "Tutorials"

    def __str__(self):
        return self.title

    def get_embed_url(self):
        import re
        url = self.video_url or ""
        yt_match = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url)
        if yt_match:
            vid = yt_match.group(1)
            return f"https://www.youtube-nocookie.com/embed/{vid}?rel=0&modestbranding=1&enablejsapi=1"
        return url


class VideoProgress(models.Model):
    student = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="video_progress"
    )
    tutorial = models.ForeignKey(
        Tutorial, on_delete=models.CASCADE, related_name="progress_records"
    )
    progress_pct = models.FloatField(default=0, help_text="0-100 percent watched")
    completed = models.BooleanField(default=False)
    last_watched = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["student", "tutorial"]
        verbose_name = "Video Progress"
        verbose_name_plural = "Video Progress Records"

    def __str__(self):
        return f"{self.student.get_full_name()} — {self.tutorial.title} ({self.progress_pct:.0f}%)"


# =============================================
# REAL-TIME NOTIFICATIONS & CHAT
# =============================================

class Notification(models.Model):
    TYPE_CHOICES = [
        ("exam", "Exam"),
        ("assignment", "Assignment"),
        ("announcement", "Announcement"),
        ("chat", "Chat"),
        ("grading", "Grading"),
        ("system", "System"),
    ]

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="system")
    url = models.URLField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title}"


class ChatMessage(models.Model):
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="chat_messages"
    )
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="chat_messages"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"

    def __str__(self):
        return f"{self.user.get_full_name()} in {self.classroom.name}"


# =============================================
# AI TUTOR
# =============================================

class TutorConversation(models.Model):
    """Model to store AI tutor conversation history."""

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="tutor_conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tutor Conversation"
        verbose_name_plural = "Tutor Conversations"

    def __str__(self):
        return f"Conversation with {self.user.get_full_name()} - {self.created_at}"


class TutorMessage(models.Model):
    """Individual message in a tutor conversation."""

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    conversation = models.ForeignKey(TutorConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Tutor Message"
        verbose_name_plural = "Tutor Messages"

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
