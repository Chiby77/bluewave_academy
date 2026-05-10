# 🛠️ BLUEWAVE ACADEMY - ADMIN SYSTEM DOCUMENTATION

## Complete Real-Time Admin Dashboard & Exam Management System

This comprehensive guide covers the complete admin system for exam management, instant grading with Groq AI, PDF report generation, and real-time analytics.

---

## 📋 TABLE OF CONTENTS

1. [System Overview](#system-overview)
2. [Installation & Setup](#installation--setup)
3. [Admin Dashboard](#admin-dashboard)
4. [Exam Management](#exam-management)
5. [Grading System](#grading-system)
6. [PDF Report Generation](#pdf-report-generation)
7. [Real-Time Features](#real-time-features)
8. [API Endpoints](#api-endpoints)
9. [Database Models](#database-models)
10. [Troubleshooting](#troubleshooting)

---

## SYSTEM OVERVIEW

### Features

✅ **Real-Time Admin Dashboard**
- Live statistics (exams, students, attempts, pass rate)
- Auto-refreshing data every 30 seconds
- Category-wise analytics
- Recent attempts list

✅ **Complete Exam Management**
- Create/Edit/Delete exams
- Configure exam timing (start/end dates, duration)
- Set marks distribution
- Control exam features (shuffling, instant grading)
- Hold/pause exams instantly
- Preview exams before publishing

✅ **Advanced Grading System**
- Auto-grade MCQ/True-False instantly
- Groq AI for essay/code answers
- Admin override capability
- Detailed feedback system
- Real-time grading status

✅ **Professional PDF Reports**
- Student exam results PDF
- Complete answer review
- Marking breakdown
- Teacher feedback
- Beautiful professional design

✅ **Real-Time Operations**
- Live exam hold/resume
- Instant statistics updates
- Real-time attempt monitoring
- Live grading dashboard

---

## INSTALLATION & SETUP

### Step 1: Install Required Packages

```bash
pip install groq reportlab django
```

### Step 2: Configure Groq API

Add your Groq API key to environment variables:

```bash
# Linux/Mac
export GROQ_API_KEY='your-api-key-here'

# Windows PowerShell
$env:GROQ_API_KEY='your-api-key-here'

# Or add to .env file
GROQ_API_KEY=your-api-key-here
```

### Step 3: Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 4: Create Admin User

```bash
python manage.py createsuperuser
```

### Step 5: Access Admin Dashboard

Navigate to: `http://localhost:8000/admin/dashboard/`

### Step 6: Configure Admin User

Go to Django Admin (`/admin/`) and mark your user as `staff=True` and `superuser=True`

---

## ADMIN DASHBOARD

### Location

`/admin/dashboard/`

### Features

#### 1. **Dashboard Statistics**
- Total Exams: Number of exams created
- Active Students: Count of enrolled students
- Total Attempts: All exam submissions
- Pass Rate: Success percentage of graded exams
- Held Exams: Alert for paused exams

#### 2. **Real-Time Updates**
- Statistics refresh every 30 seconds
- Recent attempts list updates automatically
- Category performance tracking
- Live metrics AJAX endpoints

#### 3. **Quick Access Cards**
```
📊 4 Stat Cards (Exams, Students, Attempts, Pass Rate)
📋 Category breakdown with performance
📝 Recent exam attempts list
⚡ Quick action buttons
```

#### 4. **Quick Actions**
- Create New Exam
- Manage Exams
- Grade Attempts
- Django Admin

### Code Example: Accessing Dashboard

```python
# URL: /admin/dashboard/
# Requires: Staff/Super user access
# View: admin_views.admin_dashboard()

def admin_dashboard(request):
    """Real-time dashboard with auto-refreshing stats"""
    # Returns context with:
    # - total_exams
    # - total_students
    # - total_attempts
    # - pass_rate
    # - recent_attempts
    # - category_stats
    # - held_exams
```

---

## EXAM MANAGEMENT

### Creating Exams

**URL:** `/admin/exam/create/`

**Required Fields:**
- Exam Title
- Category (Python, Java, Web, Database, Algorithms, Networks, VB.NET, OS, Other)
- Difficulty Level (Beginner, Intermediate, Advanced)
- Duration (in minutes)
- Total Marks
- Passing Marks
- Start Date & Time
- End Date & Time

**Optional Features:**
- Description
- Enable Instant Grading (Groq AI)
- Show Answers After Submit
- Randomize Question Order
- Randomize MCQ Options
- Make Active (available to students)

**Example:**

```python
POST /admin/exam/create/
{
    "title": "Python Midterm Exam",
    "category": "python",
    "level": "intermediate",
    "duration_minutes": 90,
    "total_marks": 100,
    "passing_marks": 50,
    "start_date": "2026-02-20 10:00",
    "end_date": "2026-02-20 12:00",
    "is_active": "on",
    "enable_instant_grading": "on",
    "show_answers_after_submit": "on",
}
```

### Editing Exams

**URL:** `/admin/exam/<exam_id>/edit/`

- Modify any exam parameters
- Add new questions
- View all questions with edit capability
- Set exam settings

### Previewing Exams

**URL:** `/admin/exam/<exam_id>/preview/`

- View complete exam as students see it
- Test question display
- Verify exam structure
- Check timing and instructions

### Holding/Pausing Exams

**URL:** `/admin/exam/<exam_id>/hold/`

- Temporarily prevent students from taking exam
- Set auto-resume time (optional)
- Specify hold reason
- Held exams appear with 🔒 badge

**AJAX Endpoint:**
```javascript
POST /admin/api/exam/<exam_id>/hold/
// Instantly holds exam, students see error
```

### Resuming Exams

**URL:** `/admin/exam/<exam_id>/resume/`

- Make held exam available again
- Instant resumption
- Auto-resume can be scheduled

**AJAX Endpoint:**
```javascript
POST /admin/api/exam/<exam_id>/resume/
// Instantly resumes exam
```

### Deleting Exams

**Requirements:**
- No student has attempted the exam
- Permanent deletion

**Protection:** Cannot delete exams with attempts

---

## GRADING SYSTEM

### Automatic Grading (MCQ/True-False)

MCQ and True/False answers are graded instantly:

```python
# Automatic upon exam submission
answer.check_answer()  # Compares with correct_answer
answer.is_correct = True/False
answer.marks_obtained = question.marks or 0
```

### Groq AI Grading (Essay/Code)

#### Enabling Groq AI

1. Set environment variable `GROQ_API_KEY`
2. Enable "Instant Grading" when creating exam
3. Groq service auto-initializes

#### Grading Essay Answers

```python
from siteapp.groq_service import get_groq_service

groq = get_groq_service()
result = groq.grade_answer(
    question_text="Explain OOP principles",
    correct_answer="Model answer here...",
    student_answer="Student's essay...",
    total_marks=10,
    question_type="essay"
)

# Returns:
{
    'score': Decimal('8.5'),           # 0-10
    'feedback': 'Well explained...',
    'reasoning': 'Detailed analysis...',
    'is_correct': True,
    'strengths': ['Good examples'],
    'improvements': ['Add more detail']
}
```

#### Grading Code Answers

```python
result = groq.grade_code_answer(
    question_text="Write a function to sort array",
    expected_behavior="Should sort in ascending order",
    student_code="def sort_array(arr): ...",
    total_marks=15
)

# Checks for:
# - Syntax errors
# - Logic correctness
# - Algorithm efficiency
# - Edge case handling
```

### Manual Grading

**URL:** `/admin/attempt/<attempt_id>/grade/`

- Displays all non-MCQ answers
- Shows expected vs student answer
- Admin can override AI grading
- Add custom feedback per question
- Manual score assignment

**Steps:**

1. Go to View Attempts
2. Find submitted attempt
3. Click "Grade" button
4. Review each answer
5. Enter score (0 to question marks)
6. Enter feedback
7. Submit grades

### Auto-Grade with Groq

**URL:** `/admin/attempt/<attempt_id>/auto-grade/`

- Groq AI grades all essay/code answers at once
- Creates ExamGrading records
- Updates answer scores
- Changes status to "graded"

---

## PDF REPORT GENERATION

### Features

✅ Professional report design
✅ Student information
✅ Exam details
✅ Score summary
✅ Performance breakdown
✅ Detailed answer review
✅ Teacher feedback
✅ Correct vs incorrect answers
✅ Marks breakdown

### Downloading Report

**URL:** `/admin/attempt/<attempt_id>/report/`

**Returns:** PDF file download

**Filename Format:** `{student_id}_{exam_id}_{attempt_id}_report.pdf`

### Report Sections

#### 1. Header
```
- Exam Results Report
- Student name and ID
- Exam title and category
- Exam level
- Submission date and time
```

#### 2. Score Summary
```
- Score: X / Y
- Percentage: XX%
- Passing marks required
- Status (PASSED/NOT PASSED)
- Time taken
```

#### 3. Performance Breakdown
```
- Total questions
- Correct answers
- Incorrect answers
- Accuracy percentage
```

#### 4. Detailed Answer Review (Per Question)
```
- Question number and text
- Question type
- Marks: Earned / Total
- Status (✓ Correct / ✗ Incorrect)
- Expected answer
- Student answer
- Explanation
- Teacher feedback
```

#### 5. Color Coding
```
- Correct: Green (#dcfce7)
- Incorrect: Red (#fee2e2)
- Header: Blue (#eff6ff)
- Neutral: Gray (#f9fafb)
```

### Generating Report Programmatically

```python
from siteapp.pdf_generator import generate_student_report

attempt = ExamAttempt.objects.get(id=1)
pdf_buffer = generate_student_report(attempt)

# Save to file
with open('report.pdf', 'wb') as f:
    f.write(pdf_buffer.getvalue())

# Or use in response
response = FileResponse(pdf_buffer, content_type='application/pdf')
response['Content-Disposition'] = 'attachment; filename="report.pdf"'
return response
```

---

## REAL-TIME FEATURES

### AJAX Endpoints

#### 1. Get Dashboard Stats

```javascript
GET /admin/api/dashboard-stats/

// Response:
{
    "total_exams": 15,
    "total_students": 250,
    "total_attempts": 1200,
    "graded_attempts": 900,
    "pass_rate": 72.5
}

// Auto-refresh every 30 seconds
setInterval(function() {
    fetch('/admin/api/dashboard-stats/')
        .then(r => r.json())
        .then(data => updateDashboard(data));
}, 30000);
```

#### 2. Get Recent Attempts

```javascript
GET /admin/api/recent-attempts/

// Response:
{
    "attempts": [
        {
            "id": 123,
            "student": "John Doe",
            "exam": "Python Midterm",
            "status": "graded",
            "score": 85.5,
            "percentage": 85.5,
            "date": "2026-02-16 14:30"
        }
    ]
}

// Updates every 30 seconds
```

#### 3. Get Exam Statistics

```javascript
GET /admin/api/exam/5/stats/

// Response:
{
    "total_attempts": 120,
    "graded_attempts": 100,
    "passed": 75,
    "average_score": 82.3,
    "pass_rate": 75.0
}
```

#### 4. Quick Hold Exam

```javascript
POST /admin/api/exam/5/hold/

// Response:
{
    "success": true,
    "message": "Exam held successfully"
}

// No page reload required
```

#### 5. Quick Resume Exam

```javascript
POST /admin/api/exam/5/resume/

// Response:
{
    "success": true,
    "message": "Exam resumed successfully"
}
```

### JavaScript Implementation

```javascript
// Real-time dashboard update
function refreshDashboard() {
    fetch('/admin/api/dashboard-stats/')
        .then(response => response.json())
        .then(data => {
            document.getElementById('stat-exams').textContent = data.total_exams;
            document.getElementById('stat-students').textContent = data.total_students;
            document.getElementById('stat-attempts').textContent = data.total_attempts;
            document.getElementById('stat-pass-rate').textContent = data.pass_rate + '%';
        })
        .catch(error => console.error('Error:', error));
}

// Auto-refresh every 30 seconds
setInterval(refreshDashboard, 30000);
```

---

## API ENDPOINTS

### Exam Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/admin/exams/` | GET | List all exams |
| `/admin/exam/create/` | POST | Create new exam |
| `/admin/exam/<id>/edit/` | POST | Edit exam |
| `/admin/exam/<id>/delete/` | POST | Delete exam |
| `/admin/exam/<id>/preview/` | GET | Preview exam |
| `/admin/exam/<id>/hold/` | POST | Hold exam |
| `/admin/exam/<id>/resume/` | POST | Resume exam |

### Attempt Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/admin/attempts/` | GET | List attempts |
| `/admin/exam/<id>/attempts/` | GET | Attempts for exam |
| `/admin/attempt/<id>/grade/` | GET/POST | Grade attempt |
| `/admin/attempt/<id>/auto-grade/` | POST | Auto-grade with Groq |
| `/admin/attempt/<id>/report/` | GET | Download PDF report |

### Real-Time AJAX

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/admin/api/dashboard-stats/` | GET | Current stats |
| `/admin/api/recent-attempts/` | GET | Latest attempts |
| `/admin/api/exam/<id>/stats/` | GET | Exam statistics |
| `/admin/api/exam/<id>/hold/` | POST | Quick hold |
| `/admin/api/exam/<id>/resume/` | POST | Quick resume |

---

## DATABASE MODELS

### ExamGrading Model

```python
class ExamGrading(models.Model):
    """Track AI grading for non-MCQ answers"""
    
    attempt = ForeignKey(ExamAttempt)
    question = ForeignKey(Question)
    student_answer = TextField()
    
    # Groq AI Results
    groq_score = DecimalField()
    groq_feedback = TextField()
    groq_reasoning = TextField()
    
    # Admin Override
    admin_score = DecimalField(null=True)
    admin_feedback = TextField(blank=True)
    admin_overridden = BooleanField(default=False)
    overridden_by = ForeignKey(CustomUser, null=True)
    
    graded_at = DateTimeField(auto_now_add=True)
```

**Methods:**
```python
grading.get_final_score()      # Admin override or Groq
grading.get_final_feedback()   # Precedence: Admin > Groq
```

### ExamHold Model

```python
class ExamHold(models.Model):
    """Track exam holds/pauses"""
    
    exam = OneToOneField(Exam)
    held_by = ForeignKey(CustomUser)
    reason = TextField()
    
    # Auto-resume scheduling
    resume_at = DateTimeField(null=True)
    is_active = BooleanField(default=True)
    
    held_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

# Methods
hold.should_auto_resume()  # Check if time to auto-resume
```

### Exam Model Additions

```python
class Exam(models.Model):
    # ... existing fields ...
    
    # Admin Controls
    is_held = BooleanField(default=False)
    hold_reason = TextField(blank=True)
    
    # Grading Settings
    enable_instant_grading = BooleanField(default=True)
    show_answers_after_submit = BooleanField(default=True)
    
    # Randomization
    shuffle_questions = BooleanField(default=False)
    shuffle_options = BooleanField(default=False)
```

---

## TROUBLESHOOTING

### Groq API Not Working

**Symptom:** Exams don't auto-grade, "Groq service not enabled"

**Solution:**
1. Install groq: `pip install groq`
2. Set API key: `export GROQ_API_KEY='your-key'`
3. Restart Django server
4. Check: `from siteapp.groq_service import get_groq_service; print(get_groq_service().is_enabled())`

### PDF Generation Failing

**Symptom:** Can't download reports, ImportError

**Solution:**
1. Install reportlab: `pip install reportlab`
2. Check file permissions
3. Ensure temp directory writable
4. Try: `python -c "from reportlab.lib.pagesizes import A4; print('OK')"`

### Admin Access Denied

**Problem:** "You do not have permission"

**Solution:**
1. Ensure user is staff: `python manage.py shell`
   ```python
   from django.contrib.auth import get_user_model
   User = get_user_model()
   user = User.objects.get(username='youruser')
   user.is_staff = True
   user.is_superuser = True
   user.save()
   ```
2. Refresh page
3. Clear cache if needed

### Real-Time Updates Not Working

**Problem:** Dashboard stats not refreshing

**Solution:**
1. Check browser console for JS errors
2. Verify AJAX endpoints return valid JSON
3. Clear browser cache
4. Try different browser
5. Check if fetch/AJAX is blocked

### Exam Hold Not Working

**Problem:** Students still can access held exam

**Solution:**
1. Check `exam.is_held = True` in database
2. Clear session cache
3. Verify ExamHold record created
4. Check take_exam view for hold check:
   ```python
   if exam.is_held:
       messages.error(request, 'This exam is temporarily held')
       return redirect('siteapp:exam_detail')
   ```

---

## BEST PRACTICES

### Creating Exams

✅ Set realistic time windows
✅ Include clear instructions
✅ Proof-read all questions
✅ Test with preview function
✅ Set appropriate passing marks (40-60%)
✅ Use Groq AI for essay exams

### Grading Essays

✅ Use Groq AI first for consistency
✅ Override only when necessary
✅ Provide constructive feedback
✅ Download PDF reports for records
✅ Archive grading decisions

### Security

✅ Only staff can access admin
✅ Hold suspicious exams
✅ Monitor unusual patterns
✅ Regular backups
✅ Audit changes

---

## PERFORMANCE TIPS

- Limit View Attempts to 100 per page
- Cache dashboard stats for 30 seconds
- Use pagination for large datasets
- Optimize database queries with `select_related()`
- Monitor Groq API rate limits

---

## SUPPORT & RESOURCES

- **Groq API Docs:** https://console.groq.com/docs/
- **ReportLab Docs:** https://www.reportlab.com/docs/
- **Django Admin:** https://docs.djangoproject.com/

---

## CHANGELOG

**v1.0.0** (2026-02-16)
- Real-time admin dashboard
- Groq AI grading system
- PDF report generation
- Exam hold/resume
- Complete AJAX endpoints
- Professional styling

---

**Status:** ✅ Production Ready

All features tested and documented. Ready for deployment and student use.
