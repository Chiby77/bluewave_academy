# Bluewave Academy - System Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Core Features](#core-features)
4. [Admin Dashboard](#admin-dashboard)
5. [Student Portal](#student-portal)
6. [Technical Stack](#technical-stack)
7. [API Reference](#api-reference)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [v2 Updates](#v2-updates)
10. [v3 Proposals](#v3-proposals)

---

## Introduction

Bluewave Academy is a comprehensive Learning Management System (LMS) built with Django. It features:
- Online exams with AI-powered grading
- Classroom and assignment management
- Video tutorials with progress tracking
- AI tutoring system
- Real-time notifications and chat
- Blog and announcements
- Special papers management with Supabase integration

### Purpose
This document serves as a complete reference for the Bluewave Academy system, covering all existing features, recent updates, and future plans.

---

## System Architecture

### Project Structure
```
bluewaveacademy/
├── siteapp/
│   ├── templates/
│   │   └── siteapp/
│   │       ├── admin/          # Admin interface templates
│   │       ├── student/        # Student portal templates
│   │       ├── exams/          # Exam-related templates
│   │       └── examinator/     # Classroom/assignment templates
│   ├── models.py               # Database models
│   ├── views.py                # Main views
│   ├── admin_views.py          # Admin-specific views
│   ├── examinator_views.py     # Classroom/assignment views
│   ├── tutorial_views.py       # Tutorial views
│   ├── consumers.py            # WebSocket consumers (real-time)
│   ├── notifications.py        # Notification utilities
│   ├── ai_tutor.py             # AI tutoring service
│   ├── examinator_service.py   # AI grading service
│   └── urls.py                 # URL routing
├── siteproject/
│   ├── settings.py             # Django settings
│   ├── urls.py                 # Project URLs
│   └── asgi.py                 # ASGI configuration (for WebSockets)
├── static/                     # CSS, JS, images
├── media/                      # Uploaded files
└── manage.py
```

### Database Schema Overview
| Model | Purpose |
|-------|---------|
| CustomUser | User/student profiles |
| Exam | Exams with questions |
| Question | Exam questions (MCQ, TF, short, essay, code) |
| ExamAttempt | Student exam attempts |
| Answer | Individual answers in attempts |
| ExamGrading | AI grading results |
| Classroom | Learning classrooms |
| Enrollment | Student enrollments |
| Assignment | Classroom assignments |
| Submission | Assignment submissions |
| Tutorial | Video tutorials |
| VideoProgress | Student progress tracking |
| BlogPost & Comment | Blog system |
| Announcement | System announcements |
| Notification | User notifications (real-time) |
| ChatMessage | Classroom chat messages |
| TutorConversation & TutorMessage | AI tutor chat history |
| Material | Classroom learning materials |
| SpecialPaper | Past papers via Supabase |
| DownloadResource | Downloadable resources |

---

## Core Features

### 1. Exam System
**What it does:**
- Create, manage, and grade online exams
- Multiple question types: MCQ, True/False, Short Answer, Essay, Code
- AI-powered auto-grading
- Exam scheduling and access control

**Key Features:**
- Question shuffling
- Answer key management
- Instant feedback option
- Exam holding/pausing
- Detailed analytics and reporting

**Example Workflow:**
1. Admin creates an exam with questions
2. Students take the exam
3. MCQ/TF auto-graded immediately
4. Non-MCQ auto-graded via Groq AI
5. Admin can review/override grades
6. Students see results

### 2. Classrooms & Assignments
**What it does:**
- Create and manage classrooms
- Enroll students
- Create assignments (multiple types)
- Students submit assignments (text, code, or PDF upload)
- AI auto-grades submissions
- Instructors can override grades

**Assignment Types:**
- Quiz (text-based)
- Coding assignment
- PDF upload (written work)
- Timed quiz

### 3. Video Tutorials
**What it does:**
- Upload or link video tutorials (YouTube supported)
- Track student watch progress
- Organize by category
- Thumbnail support
- Draft/published status

### 4. AI Tutor
**What it does:**
- Interactive AI chat tutoring
- Context-aware responses based on student profile
- Generates personalized learning paths
- Can analyze student performance

### 5. Real-time Features
**What it does:**
- Live notifications via WebSockets
- Classroom chat
- Real-time updates without page reload

### 6. Blog & Announcements
**What it does:**
- Publish blog posts
- Targeted announcements (by level)
- Likes and comments

---

## Admin Dashboard

### Access
URL: `/administration/`
Login credentials: Admin staff accounts

### Dashboard Overview
The admin dashboard provides a complete control panel with:

1. **Statistics KPIs**
   - Total exams
   - Active students
   - Exam attempts
   - Pass rate
   - AI-graded attempts
   - Held exams

2. **Quick Actions**
   - Create Exam
   - Create Classroom
   - Add Tutorial
   - Write Blog
   - Announcements
   - Grade Attempts
   - View Students
   - Analytics

3. **Navigation Menu**
   - Overview (Dashboard)
   - Exam System (All Exams, Create Exam, Grade Attempts)
   - The Examinator (Classrooms, Assignments)
   - Content (Video Tutorials, Blog Posts, Announcements)
   - People (Students, Submissions)
   - Analytics (Exam Analytics, Performance)
   - System (Django Admin, Student View)

### Managing Exams
**Path:** `/administration/exams/`

**Features:**
- Filter by category, level, status
- Create new exam
- Edit existing exam
- Add/remove questions
- Hold/resume exams
- Preview exams
- View attempts and analytics

**Creating an Exam:**
1. Go to "Create Exam"
2. Fill in basic info (title, description, category, level)
3. Set duration, total marks, passing marks
4. Schedule start/end dates
5. Configure options (instant grading, show answers, shuffle)
6. Add questions via the edit interface
7. Publish when ready

### Managing Classrooms
**Path:** `/administration/examinator/classrooms/`

**Features:**
- View all classrooms
- Create new classroom
- View classroom details (enrollments, assignments, materials)
- Create assignments
- Upload materials
- Manage enrollments and fees

**Creating a Classroom:**
1. Go to Classrooms → Create Classroom
2. Enter name, description
3. Select instructor
4. Choose cover color
5. Save

### Managing Assignments
**Assignment Creation:**
1. Navigate to a classroom
2. Click "Create Assignment"
3. Set title, description, type
4. Add grading rubric and answer key
5. Set total marks and passing threshold
6. Configure deadline and duration
7. Set options (allow resubmit, show results immediately)
8. Save

**Grading Assignments:**
- Submissions auto-graded via AI
- Instructors can view and override grades
- Provide feedback
- Re-run AI grading if needed

### Managing Tutorials
**Path:** `/administration/tutorials/`

**Features:**
- View all tutorials with stats (total, published, drafts)
- Create new tutorials
- Edit existing tutorials
- Toggle publish/draft status
- Delete tutorials

**Adding a Tutorial:**
1. Click "Add Tutorial"
2. Enter title and description
3. Select category and status
4. Choose video type (YouTube URL or file upload)
5. Enter URL or upload video
6. (Optional) Upload thumbnail
7. Save

### Managing Notifications
Via Django Admin: `/admin/siteapp/notification/`
- View all notifications
- Mark as read
- Filter by type, user, date

### Managing AI Tutor
Via Django Admin: `/admin/siteapp/tutorconversation/`
- View all conversations
- See chat history
- Monitor usage

---

## Student Portal

### Access
URL: `/student/`
Login via `/login/`

### Dashboard
**Features:**
- Personalized greeting
- Statistics overview
- Recent activity feed
- Recommended tutorials
- Quick links to main sections

### Exams
**Path:** `/student/exams/`
- View available exams
- Take exams
- View results and feedback

### Tutorials
**Path:** `/student/tutorials/`
- Browse tutorials by category
- Search functionality
- Watch tutorials
- Progress tracked automatically
- Continue watching where left off

### Classrooms & Assignments
**Path:** `/examinator/`
- Browse and enroll in classrooms
- View enrolled classrooms
- See pending assignments
- Submit assignments
- View results and feedback

### AI Tutor
(Student-facing UI coming soon - currently via backend)

### Profile
**Path:** `/student/profile/`
- View and edit profile
- Upload profile picture
- Update contact info

---

## Technical Stack

### Backend
- **Framework:** Django 5.2.1
- **Database:** SQLite (dev), PostgreSQL (prod-ready)
- **Real-time:** Django Channels 4.x + In-Memory Channel Layer (dev), Redis (prod)
- **ASGI Server:** Can use Daphne or Uvicorn

### AI/ML
- **Grading:** Groq API (llama-3.3-70b-versatile, moonshotai/kimi-k2-instruct)
- **Tutoring:** Groq API + Google Generative AI (fallback)

### Storage
- **Local:** Media files stored locally (dev)
- **Cloud:** Supabase integration for special papers
- **File Uploads:** Max 10MB default

### Frontend
- **Templates:** Django Templates
- **Styling:** Custom CSS (portal.css, unified-styles.css)
- **Icons:** Font Awesome 6.5
- **JavaScript:** Vanilla JS + WebSocket support

### Mobile App
- **Framework:** Taro 3.x
- **Platforms:** WeChat Mini-Program, H5, potentially others
- **Status:** Basic structure created (see /mobile-app/)

---

## API Reference

### Real-time WebSocket Endpoints

#### Notifications
```
Endpoint: ws://[host]/ws/notifications/
Authentication: Required (user must be logged in)
```

**Events:**
- `notification`: Received when a new notification arrives
  ```json
  {
    "type": "notification",
    "title": "Exam Graded",
    "message": "Your exam has been graded...",
    "url": "/exams/results/123/",
    "timestamp": "2025-01-15T10:30:00Z"
  }
  ```

#### Classroom Chat
```
Endpoint: ws://[host]/ws/chat/[classroom-slug]/
Authentication: Required
```

**Send Message:**
```json
{
  "message": "Hello everyone!"
}
```

**Receive Message:**
```json
{
  "type": "chat",
  "message": "Hello everyone!",
  "username": "John Doe",
  "user_id": 5,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### HTTP Endpoints (Selected)

#### Exams
- `GET /student/exams/` - List available exams
- `GET /student/exam/<id>/` - Exam detail
- `POST /student/exam/<id>/submit/` - Submit exam attempt

#### Tutorials
- `GET /student/tutorials/` - List tutorials
- `POST /student/tutorials/progress/update/` - Update watch progress

#### Classrooms
- `GET /examinator/` - Examinator home
- `GET /examinator/classroom/<slug>/` - Classroom detail
- `POST /examinator/assignment/<id>/take/` - Submit assignment

#### Admin
- `GET /administration/dashboard/` - Admin dashboard
- See `siteapp/urls.py` for complete list

---

## Troubleshooting Guide

### Common Issues

#### 1. Django Channels not working
**Symptoms:**
- WebSocket connections fail
- No real-time notifications

**Solutions:**
1. Check `asgi.py` configuration
2. Verify `INSTALLED_APPS` includes `channels`
3. Check `CHANNEL_LAYERS` in settings
4. Make sure to run with an ASGI server (not just `runserver`)

#### 2. AI grading fails
**Symptoms:**
- Submissions stuck in "grading" status
- Errors in logs

**Solutions:**
1. Verify `GROQ_API_KEY` is set in environment variables
2. Check API key validity
3. Look for errors in console/logs
4. Fallback to manual grading

#### 3. File upload fails
**Symptoms:**
- Uploads don't complete
- File size errors

**Solutions:**
1. Check `FILE_UPLOAD_MAX_MEMORY_SIZE` in settings (default: 10MB)
2. Verify `MEDIA_ROOT` permissions
3. Check file type restrictions

#### 4. Can't access admin dashboard
**Symptoms:**
- Login fails or redirects
- Permission denied

**Solutions:**
1. Verify user has `is_staff=True`
2. Check admin URL: `/administration/login/`
3. Clear browser cookies/cache

#### 5. Tutorial video won't play
**Symptoms:**
- YouTube videos won't embed
- Video errors

**Solutions:**
1. Check YouTube URL format
2. Verify video is embeddable
3. For uploaded videos: check file format and encoding

### Migration Issues
If you added new models (like Notification, ChatMessage, TutorConversation):

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# If needed - run custom migration
python manage.py migrate siteapp
```

---

## v2 Updates (Current Release)

### New Features in v2
1. **Django Channels & WebSockets**
   - Real-time notification system
   - Live classroom chat
   - Notification model and persistence

2. **AI Tutor System**
   - Complete AI tutoring service
   - Conversation history
   - Personalized learning paths
   - Student performance analysis

3. **Tutorial Management UI**
   - Updated templates to match admin theme
   - Better integration with admin navigation
   - Improved UX for managing tutorials

4. **Admin Dashboard Enhancements**
   - New quick actions: Create Classroom, Add Tutorial
   - Updated navigation with Tutorials, Classrooms, Assignments
   - Better organization

5. **Enhanced Models**
   - `Notification` - for real-time notifications
   - `ChatMessage` - for classroom chat
   - `TutorConversation` & `TutorMessage` - for AI tutor

6. **Mobile App Foundation**
   - Taro mini-program project structure
   - Basic app skeleton with pages
   - Component templates (home, exams, tutor, profile)

### Migration from v1 to v2
1. Install new dependencies:
   ```toml
   # In pyproject.toml
   django-channels>=4.1.0
   channels-redis>=4.2.0
   ```

2. Update settings:
   - Add `channels` to `INSTALLED_APPS`
   - Configure `ASGI_APPLICATION`
   - Set up `CHANNEL_LAYERS`

3. Update `asgi.py` to use ProtocolTypeRouter

4. Run migrations for new models

5. Restart with ASGI server

---

## v3 Proposals (Future Roadmap)

### Short-term Goals (v3.0)
1. **Advanced Analytics**
   - Learning analytics dashboard for students
   - Predictive performance insights
   - Instructor dashboards with class-level metrics

2. **Gamification**
   - Achievement system
   - Badges and rewards
   - Leaderboards
   - Points and streaks

3. **Enhanced AI Features**
   - AI-generated study plans
   - Smart question recommendations
   - Adaptive difficulty
   - Plagiarism detection for code/text

4. **Video Conferencing**
   - Integrate Zoom/Google Meet/Meetings
   - Live virtual classes
   - Session recording and playback

5. **Payment Integration**
   - Complete payment gateway (Stripe, PayPal, local options)
   - Enrollment fees
   - Course purchases
   - Subscription models

### Mid-term Goals (v3.5)
1. **Multi-language Support**
   - i18n / l10n
   - Multiple language interfaces
   - RTL support

2. **Mobile App Complete**
   - Full-featured Taro app
   - Push notifications
   - Offline capabilities

3. **Advanced Content Authoring**
   - SCORM/xAPI support
   - Interactive content
   - Quiz banks

### Long-term Vision (v4.0+)
1. **Multi-tenant SaaS**
   - Institutional onboarding
   - White-labeling
   - Separate instances per organization

2. **Machine Learning Pipeline**
   - Question generation AI
   - Automatic rubric creation
   - Student modeling

3. **AR/VR Learning**
   - Immersive learning experiences
   - Virtual labs
   - Simulations

---

## Appendices

### Environment Variables
```env
# Required
SECRET_KEY=your-secret-key-here
DEBUG=True  # Set to False in production

# AI Services
GROQ_API_KEY=your-groq-api-key
GOOGLE_API_KEY=your-google-api-key  # Optional fallback

# Database (PostgreSQL for production)
# DB_NAME=
# DB_USER=
# DB_PASSWORD=
# DB_HOST=
# DB_PORT=

# Supabase (for special papers)
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
SUPABASE_BUCKET=papers

# Email (production)
# EMAIL_HOST=
# EMAIL_PORT=
# EMAIL_HOST_USER=
# EMAIL_HOST_PASSWORD=
# DEFAULT_FROM_EMAIL=
```

### Security Best Practices
1. Keep `DEBUG=False` in production
2. Use HTTPS only
3. Set secure cookies
4. Rotate secrets regularly
5. Keep dependencies updated
6. Use environment variables for all secrets
7. Implement rate limiting
8. Regular backups

---

## Support & Contact

For issues, questions, or feature requests:
- Check this documentation first
- Review server logs (if applicable)
- Contact support team

---

Last Updated: June 2025
Version: 2.0.0
