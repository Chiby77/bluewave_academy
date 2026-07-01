from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import admin_views
from . import examinator_views
from . import zuri_views
from . import tutorial_views
from . import api_views
from .forms import CustomPasswordResetForm, CustomSetPasswordForm

app_name = "siteapp"

urlpatterns = [
    # Zuri AI assistant
    path("zuri/chat/", zuri_views.zuri_chat, name="zuri_chat"),
    # Public pages
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("terms-of-service/", views.terms_of_service, name="terms_of_service"),
    path("privacy-policy/", views.privacy_policy, name="privacy_policy"),
    path("downloads/", views.downloads, name="downloads"),
    path("contact/", views.contact, name="contact"),
    # Blog Pages
    path("blog/", views.blog_list, name="blog"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),
    # AJAX Like Endpoint
    path("blog/like/<slug:slug>/", views.like_post, name="like_post"),
    # Authentication
    path("register/", views.register, name="register"),
    path("login/", views.student_login, name="login"),
    path("logout/", views.student_logout, name="logout"),
    # Password Reset
    path(
        "password-reset/",
        views.CustomPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="siteapp/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        views.CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="siteapp/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    # Student Portal
    path("portal/", views.student_dashboard, name="portal"),
    path("student/dashboard/", views.student_dashboard, name="dashboard"),
    path("student/results/", views.student_results, name="student_results"),
    path("student/announcements/", views.student_announcements, name="student_announcements"),
    path("student/analytics/", views.analytics, name="analytics"),
    path("student/profile/", views.profile, name="profile"),
    path("student/profile/edit/", views.edit_profile, name="edit_profile"),
    path("student/logout-page/", views.logout_page, name="logout_page"),
    # Exams
    path("student/exams/", views.exam_list, name="exam_list"),  # Main exam list
    path("student/exam/<int:exam_id>/", views.exam_detail, name="exam_detail"),
    path("student/exam/<int:exam_id>/take/", views.take_exam, name="take_exam"),
    path("student/exam/<int:exam_id>/submit/", views.submit_exam, name="submit_exam"),
    path(
        "student/exam/results/<int:attempt_id>/",
        views.exam_results,
        name="exam_results",
    ),
    path(
        "student/exam/results/<int:attempt_id>/report/",
        views.download_exam_report,
        name="download_report",
    ),
    # Downloads
    path(
        "student/download/<int:resource_id>/",
        views.download_resource,
        name="download_resource",
    ),
    # Announcements (AJAX partial endpoint kept for backward compatibility)
    path("student/announcements/ajax/", views.announcements, name="announcements"),
    # Special Papers (Supabase)
    path(
        "downloads/special/<int:paper_id>/",
        examinator_views.special_paper_download,
        name="special_paper_download",
    ),
    # ==================== THE EXAMINATOR ====================
    # Student-facing
    path("examinator/", examinator_views.examinator_home, name="examinator_home"),
    path("examinator/browse/", examinator_views.browse_classrooms, name="browse_classrooms"),
    path("examinator/classroom/<slug:slug>/", examinator_views.classroom_detail, name="classroom_detail"),
    path("examinator/classroom/<slug:slug>/enroll/", examinator_views.enroll_classroom, name="enroll_classroom"),
    path("examinator/classroom/<slug:slug>/payment-required/", examinator_views.payment_required, name="payment_required"),
    path("examinator/assignment/<int:assignment_id>/take/", examinator_views.take_assignment, name="take_assignment"),
    path("examinator/submission/<int:submission_id>/result/", examinator_views.submission_result, name="submission_result"),
    # Admin Examinator
    path("administration/examinator/classrooms/", examinator_views.admin_classrooms, name="admin_classrooms"),
    path("administration/examinator/classrooms/create/", examinator_views.admin_create_classroom, name="admin_create_classroom"),
    path("administration/examinator/classrooms/<slug:slug>/", examinator_views.admin_classroom_detail, name="admin_classroom_detail"),
    path("administration/examinator/classrooms/<slug:slug>/assignment/create/", examinator_views.admin_create_assignment, name="admin_create_assignment"),
    path("administration/examinator/classrooms/<slug:slug>/material/upload/", examinator_views.admin_upload_material, name="admin_upload_material"),
    path("administration/examinator/material/<int:material_id>/delete/", examinator_views.admin_delete_material, name="admin_delete_material"),
    path("administration/examinator/enrollment/<int:enrollment_id>/fee/", examinator_views.admin_set_enrollment_fee, name="admin_set_enrollment_fee"),
    path("administration/examinator/assignment/<int:assignment_id>/submissions/", examinator_views.admin_submissions, name="admin_submissions"),
    path("administration/examinator/submission/<int:submission_id>/grade/", examinator_views.admin_grade_submission, name="admin_grade_submission"),
    path("administration/examinator/submission/<int:submission_id>/regrade/", examinator_views.admin_regrade_submission, name="admin_regrade_submission"),
    # ==================== VIDEO TUTORIALS (Student) ====================
    path("student/tutorials/", tutorial_views.tutorial_list, name="tutorial_list"),
    path("student/tutorials/progress/update/", tutorial_views.update_video_progress, name="update_video_progress"),
    path("student/tutorials/<slug:slug>/", tutorial_views.tutorial_detail, name="tutorial_detail"),

    # ==================== API ENDPOINTS ====================
    # Notifications
    path("api/notifications/", api_views.api_notifications_list, name="api_notifications"),
    path("api/notifications/<int:notification_id>/read/", api_views.api_notification_mark_read, name="api_notification_read"),
    path("api/notifications/mark-all-read/", api_views.api_notifications_mark_all_read, name="api_notifications_mark_all_read"),
    # AI Tutor
    path("api/tutor/conversation/", api_views.api_tutor_get_conversation, name="api_tutor_conversation"),
    path("api/tutor/send-message/", api_views.api_tutor_send_message, name="api_tutor_send_message"),
    # Video Tutorials (API)
    path("api/tutorials/", api_views.api_tutorials_list, name="api_tutorials_list"),
    path("api/tutorials/<slug:slug>/", api_views.api_tutorial_detail, name="api_tutorial_detail"),
    path("api/tutorials/progress/update/", api_views.api_tutorial_update_progress, name="api_tutorial_update_progress"),
    # Exams (API)
    path("api/exams/", api_views.api_exams_list, name="api_exams_list"),

    # ==================== ADMIN ROUTES ====================
    # Blog Management
    path("administration/blog/", admin_views.admin_blog_list, name="admin_blog_list"),
    path("administration/blog/create/", admin_views.admin_blog_create, name="admin_blog_create"),
    path("administration/blog/<int:post_id>/edit/", admin_views.admin_blog_edit, name="admin_blog_edit"),
    path("administration/blog/<int:post_id>/delete/", admin_views.admin_blog_delete, name="admin_blog_delete"),
    # Tutorial Management
    path("administration/tutorials/", admin_views.admin_tutorial_list, name="admin_tutorial_list"),
    path("administration/tutorials/create/", admin_views.admin_tutorial_create, name="admin_tutorial_create"),
    path("administration/tutorials/<int:tutorial_id>/edit/", admin_views.admin_tutorial_edit, name="admin_tutorial_edit"),
    path("administration/tutorials/<int:tutorial_id>/delete/", admin_views.admin_tutorial_delete, name="admin_tutorial_delete"),
    path("administration/tutorials/<int:tutorial_id>/toggle/", admin_views.admin_tutorial_toggle_status, name="admin_tutorial_toggle"),
    # Student Management
    path("administration/students/", admin_views.admin_students, name="admin_students"),
    # Hidden Admin Login
    path("administration/login/", admin_views.admin_login, name="admin_login"),
    # Admin Dashboard
    path(
        "administration/dashboard/", admin_views.admin_dashboard, name="admin_dashboard"
    ),
    # Exam Management
    path("administration/exams/", admin_views.exam_list_admin, name="exam_list_admin"),
    path("administration/exam/create/", admin_views.create_exam, name="create_exam"),
    path(
        "administration/exam/<int:exam_id>/edit/",
        admin_views.edit_exam,
        name="edit_exam",
    ),
    path(
        "administration/exam/<int:exam_id>/delete/",
        admin_views.delete_exam,
        name="delete_exam",
    ),
    path(
        "administration/exam/<int:exam_id>/preview/",
        admin_views.preview_exam,
        name="preview_exam",
    ),
    # Question Management
    path(
        "administration/exam/<int:exam_id>/question/add/",
        admin_views.add_question,
        name="add_question",
    ),
    path(
        "administration/exam/<int:exam_id>/question/<int:question_id>/edit/",
        admin_views.edit_question,
        name="edit_question",
    ),
    path(
        "administration/exam/<int:exam_id>/question/<int:question_id>/delete/",
        admin_views.delete_question,
        name="delete_question",
    ),
    # Exam Hold/Resume
    path(
        "administration/exam/<int:exam_id>/hold/",
        admin_views.hold_exam,
        name="hold_exam",
    ),
    path(
        "administration/exam/<int:exam_id>/resume/",
        admin_views.resume_exam,
        name="resume_exam",
    ),
    # Attempt Management
    path("administration/attempts/", admin_views.view_attempts, name="view_attempts"),
    path(
        "administration/exam/<int:exam_id>/attempts/",
        admin_views.view_attempts,
        name="exam_attempts",
    ),
    path(
        "administration/attempt/<int:attempt_id>/grade/",
        admin_views.grade_attempt,
        name="grade_attempt",
    ),
    path(
        "administration/attempt/<int:attempt_id>/auto-grade/",
        admin_views.auto_grade_attempt,
        name="auto_grade_attempt",
    ),
    path(
        "administration/attempt/<int:attempt_id>/report/",
        admin_views.download_report,
        name="download_report",
    ),
    # Real-time AJAX Endpoints
    path(
        "administration/api/dashboard-stats/",
        admin_views.get_dashboard_stats,
        name="api_dashboard_stats",
    ),
    path(
        "administration/api/recent-attempts/",
        admin_views.get_recent_attempts,
        name="api_recent_attempts",
    ),
    path(
        "administration/api/exam/<int:exam_id>/stats/",
        admin_views.get_exam_statistics,
        name="api_exam_stats",
    ),
    path(
        "administration/api/exam/<int:exam_id>/hold/",
        admin_views.quick_hold_exam,
        name="api_hold_exam",
    ),
    path(
        "administration/api/exam/<int:exam_id>/resume/",
        admin_views.quick_resume_exam,
        name="api_resume_exam",
    ),
    # Announcements Management
    path(
        "administration/announcements/",
        admin_views.announcements_management,
        name="announcements_management",
    ),
    path(
        "administration/announcements/create/",
        admin_views.create_announcement,
        name="create_announcement",
    ),
    path(
        "administration/announcements/<int:announcement_id>/delete/",
        admin_views.delete_announcement,
        name="delete_announcement",
    ),
    path(
        "administration/announcements/<int:announcement_id>/update/",
        admin_views.update_announcement,
        name="update_announcement",
    ),
    path(
        "administration/api/announcements/",
        admin_views.get_announcements,
        name="api_announcements",
    ),
    # Submissions & Analytics
    path(
        "administration/submissions/",
        admin_views.student_submissions,
        name="student_submissions",
    ),
    path(
        "administration/submissions/<int:attempt_id>/",
        admin_views.submission_detail,
        name="submission_detail",
    ),
    path(
        "administration/analytics/exams/",
        admin_views.exam_analytics,
        name="exam_analytics",
    ),
    path(
        "administration/analytics/students/",
        admin_views.student_performance,
        name="student_performance",
    ),
    path(
        "administration/api/export-analytics/",
        admin_views.export_analytics,
        name="export_analytics",
    ),
]
