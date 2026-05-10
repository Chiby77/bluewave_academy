from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import admin_views
from .forms import CustomPasswordResetForm, CustomSetPasswordForm

app_name = "siteapp"

urlpatterns = [
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
    path("student/exams/", views.exam_list, name="exams"),  # AJAX endpoint
    path("student/analytics/", views.analytics, name="analytics"),  # AJAX endpoint
    path(
        "student/announcements/", views.announcements, name="announcements"
    ),  # AJAX endpoint
    path("student/profile/", views.profile, name="profile"),  # AJAX endpoint
    path("student/profile/edit/", views.edit_profile, name="edit_profile"),
    path("student/logout-page/", views.logout_page, name="logout_page"),
    # Exams
    path("student/exam-list/", views.exam_list, name="exam_list"),  # Legacy support
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
    # Announcements
    path("student/announcements/", views.announcements, name="announcements"),
    # ==================== ADMIN ROUTES ====================
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
