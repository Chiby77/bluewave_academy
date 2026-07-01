from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
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
    SpecialPaper,
    Classroom,
    Enrollment,
    Assignment,
    Submission,
    Notification,
    ChatMessage,
    TutorConversation,
    TutorMessage,
    Tutorial,
    VideoProgress,
    Material,
    ExamGrading,
    ExamHold,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin interface for CustomUser"""

    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "student_id",
        "school",
        "is_active_student",
    ]
    list_filter = ["is_active_student", "current_level", "enrollment_date"]
    search_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
        "student_id",
        "phone",
        "school",
    ]

    fieldsets = UserAdmin.fieldsets + (
        (
            "Student Information",
            {
                "fields": (
                    "phone",
                    "school",
                    "student_id",
                    "date_of_birth",
                    "profile_picture",
                )
            },
        ),
        (
            "Academic Information",
            {"fields": ("enrollment_date", "current_level", "is_active_student")},
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Additional Info",
            {"fields": ("email", "first_name", "last_name", "phone", "school")},
        ),
    )


class QuestionInline(admin.TabularInline):
    """Inline questions for Exam admin"""

    model = Question
    extra = 1
    fields = ["question_text", "question_type", "marks", "order"]


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    """Admin interface for Exam"""

    list_display = [
        "title",
        "category",
        "level",
        "duration_minutes",
        "total_marks",
        "is_active",
        "start_date",
        "end_date",
    ]
    list_filter = ["category", "level", "is_active", "start_date"]
    search_fields = ["title", "description"]
    inlines = [QuestionInline]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "description", "category", "level")},
        ),
        (
            "Exam Settings",
            {
                "fields": (
                    "duration_minutes",
                    "total_marks",
                    "passing_marks",
                    "is_active",
                )
            },
        ),
        ("Schedule", {"fields": ("start_date", "end_date")}),
        ("Metadata", {"fields": ("created_by",)}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin interface for Question"""

    list_display = ["exam", "question_type", "marks", "order"]
    list_filter = ["question_type", "exam"]
    search_fields = ["question_text", "exam__title"]

    fieldsets = (
        (
            "Question Details",
            {"fields": ("exam", "question_text", "question_type", "marks", "order")},
        ),
        (
            "Options (for MCQ)",
            {
                "fields": ("option_a", "option_b", "option_c", "option_d"),
                "classes": ("collapse",),
            },
        ),
        ("Answer", {"fields": ("correct_answer", "explanation")}),
    )


class AnswerInline(admin.TabularInline):
    """Inline answers for ExamAttempt admin"""

    model = Answer
    extra = 0
    readonly_fields = ["question", "answer_text", "is_correct", "marks_obtained"]
    can_delete = False


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    """Admin interface for ExamAttempt"""

    list_display = [
        "student",
        "exam",
        "status",
        "score",
        "percentage",
        "start_time",
        "end_time",
    ]
    list_filter = ["status", "exam", "start_time"]
    search_fields = ["student__username", "student__email", "exam__title"]
    readonly_fields = [
        "start_time",
        "end_time",
        "time_taken_minutes",
        "score",
        "percentage",
    ]
    inlines = [AnswerInline]

    fieldsets = (
        ("Attempt Information", {"fields": ("student", "exam", "status")}),
        ("Timing", {"fields": ("start_time", "end_time", "time_taken_minutes")}),
        ("Results", {"fields": ("score", "percentage", "ai_graded", "ai_feedback")}),
    )

    def has_add_permission(self, request):
        return False


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    """Admin interface for Answer"""

    list_display = ["attempt", "question", "is_correct", "marks_obtained", "ai_graded"]
    list_filter = ["is_correct", "ai_graded", "attempt__exam"]
    search_fields = ["attempt__student__username", "question__question_text"]
    readonly_fields = ["attempt", "question", "created_at"]

    fieldsets = (
        ("Answer Details", {"fields": ("attempt", "question", "answer_text")}),
        (
            "Grading",
            {"fields": ("is_correct", "marks_obtained", "ai_graded", "ai_feedback")},
        ),
    )


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    """Admin interface for Announcement"""

    list_display = ["title", "target_audience", "priority", "is_active", "created_at"]
    list_filter = ["target_audience", "priority", "is_active", "created_at"]
    search_fields = ["title", "content"]

    fieldsets = (
        ("Announcement Details", {"fields": ("title", "content")}),
        ("Settings", {"fields": ("target_audience", "priority", "is_active")}),
        ("Metadata", {"fields": ("created_by",), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DownloadResource)
class DownloadResourceAdmin(admin.ModelAdmin):
    """Admin interface for DownloadResource"""

    list_display = ["title", "category", "is_active", "download_count", "created_at"]
    list_filter = ["category", "is_active", "created_at"]
    search_fields = ["title", "description"]
    readonly_fields = ["download_count", "created_at", "updated_at"]

    fieldsets = (
        ("Resource Details", {"fields": ("title", "description", "category")}),
        ("File", {"fields": ("file", "file_size")}),
        ("Settings", {"fields": ("is_active",)}),
        (
            "Statistics",
            {
                "fields": ("download_count", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
        ("Metadata", {"fields": ("uploaded_by",), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user

        if obj.file:
            size_bytes = obj.file.size
            if size_bytes < 1024:
                obj.file_size = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                obj.file_size = f"{size_bytes / 1024:.2f} KB"
            else:
                obj.file_size = f"{size_bytes / (1024 * 1024):.2f} MB"

        super().save_model(request, obj, form, change)


admin.site.register(Comment)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = ("title", "created_at", "likes_count")


# =============================================
# SPECIAL PAPERS
# =============================================

@admin.register(SpecialPaper)
class SpecialPaperAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "year", "paper_number", "is_public", "is_active", "download_count"]
    list_filter = ["category", "is_public", "is_active", "year"]
    search_fields = ["title", "description"]
    readonly_fields = ["download_count", "created_at"]
    list_editable = ["is_public", "is_active"]

    fieldsets = (
        ("Paper Details", {"fields": ("title", "description", "category", "year", "paper_number")}),
        ("Storage", {"fields": ("supabase_path",)}),
        ("Access Control", {"fields": ("is_public", "is_active")}),
        ("Statistics", {"fields": ("download_count", "created_at", "uploaded_by"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


# =============================================
# THE EXAMINATOR
# =============================================

class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    readonly_fields = ["enrolled_at"]
    fields = ["student", "is_active", "enrolled_at"]


class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 0
    fields = ["title", "assignment_type", "total_marks", "deadline", "is_active"]


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ["name", "instructor", "enrolled_count", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "instructor__username"]
    readonly_fields = ["slug", "created_at", "updated_at"]
    inlines = [AssignmentInline, EnrollmentInline]

    fieldsets = (
        ("Classroom Details", {"fields": ("name", "description", "instructor", "cover_color", "slug")}),
        ("Settings", {"fields": ("is_active",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ["student", "classroom", "enrolled_at", "is_active"]
    list_filter = ["is_active", "classroom"]
    search_fields = ["student__username", "student__email", "classroom__name"]
    readonly_fields = ["enrolled_at"]


class SubmissionInline(admin.TabularInline):
    model = Submission
    extra = 0
    readonly_fields = ["student", "submitted_at", "status", "ai_score", "ai_percentage"]
    fields = ["student", "status", "ai_score", "ai_percentage", "final_score"]
    can_delete = False


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["title", "classroom", "assignment_type", "total_marks", "deadline", "is_active"]
    list_filter = ["assignment_type", "is_active", "classroom"]
    search_fields = ["title", "classroom__name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [SubmissionInline]

    fieldsets = (
        ("Assignment Details", {"fields": ("classroom", "title", "description", "assignment_type")}),
        ("Grading", {"fields": ("rubric", "answer_key", "total_marks", "passing_marks")}),
        ("Settings", {"fields": ("deadline", "duration_minutes", "is_active", "allow_resubmit", "show_results_immediately", "programming_language")}),
        ("Metadata", {"fields": ("created_by", "created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ["student", "assignment", "status", "ai_score", "final_score", "submitted_at"]
    list_filter = ["status", "assignment__classroom", "submitted_at"]
    search_fields = ["student__username", "student__email", "assignment__title"]
    readonly_fields = ["submitted_at", "graded_at"]

    fieldsets = (
        ("Submission", {"fields": ("student", "assignment", "text_answer", "code_text", "pdf_file", "time_taken_seconds")}),
        ("AI Grading", {"fields": ("status", "ai_score", "ai_percentage", "ai_feedback", "ai_strengths", "ai_improvements", "ai_improvement_tips", "ai_reasoning")}),
        ("Instructor Override", {"fields": ("final_score", "instructor_feedback", "graded_by", "graded_at")}),
        ("Timestamps", {"fields": ("submitted_at", "report_sent"), "classes": ("collapse",)}),
    )


# =============================================
# NOTIFICATIONS & CHAT
# =============================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "notification_type", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["user__username", "title", "message"]
    readonly_fields = ["created_at"]
    list_editable = ["is_read"]

    fieldsets = (
        ("Notification", {"fields": ("user", "title", "message", "notification_type", "url")}),
        ("Status", {"fields": ("is_read", "created_at")}),
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["user", "classroom", "content", "created_at"]
    list_filter = ["classroom", "created_at"]
    search_fields = ["user__username", "content"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Message", {"fields": ("classroom", "user", "content")}),
        ("Timestamp", {"fields": ("created_at",)}),
    )


# =============================================
# AI TUTOR
# =============================================

class TutorMessageInline(admin.TabularInline):
    model = TutorMessage
    extra = 0
    readonly_fields = ["role", "content", "timestamp"]
    can_delete = False


@admin.register(TutorConversation)
class TutorConversationAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "updated_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [TutorMessageInline]


@admin.register(TutorMessage)
class TutorMessageAdmin(admin.ModelAdmin):
    list_display = ["conversation", "role", "timestamp"]
    list_filter = ["role", "timestamp"]
    search_fields = ["conversation__user__username", "content"]
    readonly_fields = ["timestamp"]


# =============================================
# VIDEO TUTORIALS
# =============================================

class VideoProgressInline(admin.TabularInline):
    model = VideoProgress
    extra = 0
    readonly_fields = ["student", "progress_pct", "completed", "last_watched"]
    can_delete = False


@admin.register(Tutorial)
class TutorialAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = ["title", "category", "status", "view_count", "created_at"]
    list_filter = ["category", "status", "created_at"]
    search_fields = ["title", "description"]
    readonly_fields = ["view_count", "created_at", "updated_at"]
    inlines = [VideoProgressInline]

    fieldsets = (
        ("Tutorial Details", {"fields": ("title", "slug", "description", "category", "status")}),
        ("Video", {"fields": ("video_type", "video_url", "video_file", "thumbnail")}),
        ("Statistics", {"fields": ("view_count", "created_at", "updated_at", "created_by"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(VideoProgress)
class VideoProgressAdmin(admin.ModelAdmin):
    list_display = ["student", "tutorial", "progress_pct", "completed", "last_watched"]
    list_filter = ["completed", "tutorial", "last_watched"]
    search_fields = ["student__username", "tutorial__title"]
    readonly_fields = ["last_watched"]


# =============================================
# CLASSROOM MATERIALS
# =============================================

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ["classroom", "title", "material_type", "is_active", "order", "created_at"]
    list_filter = ["classroom", "material_type", "is_active", "created_at"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at"]


# =============================================
# EXAM GRADING & HOLDS
# =============================================

@admin.register(ExamGrading)
class ExamGradingAdmin(admin.ModelAdmin):
    list_display = ["attempt", "question", "groq_score", "admin_overridden", "graded_at"]
    list_filter = ["admin_overridden", "graded_at"]
    search_fields = ["attempt__student__username", "question__question_text"]
    readonly_fields = ["graded_at", "updated_at"]


@admin.register(ExamHold)
class ExamHoldAdmin(admin.ModelAdmin):
    list_display = ["exam", "held_by", "held_at", "is_active", "resume_at"]
    list_filter = ["is_active", "held_at", "resume_at"]
    search_fields = ["exam__title", "held_by__username"]
    readonly_fields = ["held_at", "updated_at"]
