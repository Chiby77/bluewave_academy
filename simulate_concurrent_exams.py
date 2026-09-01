import os
import sys
import time
import django
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "siteproject.settings")
django.setup()

from django.test import Client
from django.utils import timezone
from django.db import connection
from siteapp.models import CustomUser, Exam, Question, ExamAttempt, Answer, ExamGrading


def setup_simulation_data():
    """Create 4 diverse exams and 30 student test users."""
    print("=" * 70)
    print("STEP 1: Setting up Simulation Exams and Questions")
    print("=" * 70)
    
    admin, _ = CustomUser.objects.get_or_create(
        username="sim_admin",
        defaults={"email": "sim_admin@bluewave.com", "is_staff": True, "is_superuser": True}
    )
    admin.set_password("AdminPass123!")
    admin.save()

    now = timezone.now()

    # Exam 1: Pure MCQ
    exam_mcq, _ = Exam.objects.get_or_create(
        title="Sim 1: Computer Science Fundamentals (MCQ)",
        defaults={
            "description": "5 Multiple Choice and True/False questions",
            "category": "programming",
            "level": "beginner",
            "duration_minutes": 30,
            "total_marks": 50,
            "passing_marks": 25,
            "is_active": True,
            "is_held": False,
            "start_date": now - timezone.timedelta(days=1),
            "end_date": now + timezone.timedelta(days=5),
            "created_by": admin,
        }
    )
    # Questions for Exam 1
    if not exam_mcq.questions.exists():
        Question.objects.create(
            exam=exam_mcq, question_text="What is the time complexity of binary search?",
            question_type="mcq", option_a="O(n)", option_b="O(log n)", option_c="O(n^2)", option_d="O(1)",
            correct_answer="B", marks=10, order=1
        )
        Question.objects.create(
            exam=exam_mcq, question_text="HTTP status code 404 means 'Internal Server Error'.",
            question_type="true_false", correct_answer="false", marks=10, order=2
        )
        Question.objects.create(
            exam=exam_mcq, question_text="Which data structure uses FIFO (First In First Out)?",
            question_type="mcq", option_a="Stack", option_b="Queue", option_c="Tree", option_d="Graph",
            correct_answer="B", marks=10, order=3
        )
        Question.objects.create(
            exam=exam_mcq, question_text="In Python, lists are immutable.",
            question_type="true_false", correct_answer="false", marks=10, order=4
        )
        Question.objects.create(
            exam=exam_mcq, question_text="Which SQL clause is used to group rows that have the same values?",
            question_type="mcq", option_a="ORDER BY", option_b="WHERE", option_c="GROUP BY", option_d="HAVING",
            correct_answer="C", marks=10, order=5
        )

    # Exam 2: Short Answer / Essay
    exam_essay, _ = Exam.objects.get_or_create(
        title="Sim 2: Software Engineering & Architecture (Essay)",
        defaults={
            "description": "3 Short Answer & Conceptual questions",
            "category": "programming",
            "level": "intermediate",
            "duration_minutes": 45,
            "total_marks": 60,
            "passing_marks": 30,
            "is_active": True,
            "is_held": False,
            "start_date": now - timezone.timedelta(days=1),
            "end_date": now + timezone.timedelta(days=5),
            "created_by": admin,
        }
    )
    if not exam_essay.questions.exists():
        Question.objects.create(
            exam=exam_essay, question_text="Explain the purpose of database indexing and how B-Trees improve query lookup times.",
            question_type="essay",
            correct_answer="Indexes speed up search queries using balanced tree (B-Tree) traversal with O(log n) time complexity, reducing disk I/O.",
            marks=20, order=1
        )
        Question.objects.create(
            exam=exam_essay, question_text="What is the difference between synchronous and asynchronous request processing in web servers?",
            question_type="short_answer",
            correct_answer="Synchronous blocks until the operation completes; asynchronous uses non-blocking I/O or event loops to handle other tasks concurrently.",
            marks=20, order=2
        )
        Question.objects.create(
            exam=exam_essay, question_text="Explain ACID properties in relational database transactions.",
            question_type="essay",
            correct_answer="Atomicity ensures all-or-nothing execution, Consistency enforces data constraints, Isolation ensures transactions don't interfere, Durability guarantees saved data persists.",
            marks=20, order=3
        )

    # Exam 3: Coding Practical
    exam_code, _ = Exam.objects.get_or_create(
        title="Sim 3: Algorithms & Data Structures Coding Practical",
        defaults={
            "description": "2 Practical coding challenges",
            "category": "programming",
            "level": "advanced",
            "duration_minutes": 60,
            "total_marks": 50,
            "passing_marks": 25,
            "is_active": True,
            "is_held": False,
            "start_date": now - timezone.timedelta(days=1),
            "end_date": now + timezone.timedelta(days=5),
            "created_by": admin,
        }
    )
    if not exam_code.questions.exists():
        Question.objects.create(
            exam=exam_code, question_text="Write a Python function `two_sum(nums, target)` that returns the indices of the two numbers such that they add up to target.",
            question_type="code",
            correct_answer="def two_sum(nums, target):\n    lookup = {}\n    for i, num in enumerate(nums):\n        diff = target - num\n        if diff in lookup:\n            return [lookup[diff], i]\n        lookup[num] = i\n    return []",
            marks=25, order=1
        )
        Question.objects.create(
            exam=exam_code, question_text="Write a Python function `is_palindrome(s)` that checks if a string is a palindrome ignoring case and non-alphanumeric characters.",
            question_type="code",
            correct_answer="def is_palindrome(s):\n    cleaned = [c.lower() for c in s if c.isalnum()]\n    return cleaned == cleaned[::-1]",
            marks=25, order=2
        )

    # Exam 4: Mixed Comprehensive
    exam_mixed, _ = Exam.objects.get_or_create(
        title="Sim 4: Full-Stack Engineering (Mixed)",
        defaults={
            "description": "2 MCQ, 1 Short Answer, 1 Coding",
            "category": "web",
            "level": "intermediate",
            "duration_minutes": 45,
            "total_marks": 50,
            "passing_marks": 25,
            "is_active": True,
            "is_held": False,
            "start_date": now - timezone.timedelta(days=1),
            "end_date": now + timezone.timedelta(days=5),
            "created_by": admin,
        }
    )
    if not exam_mixed.questions.exists():
        Question.objects.create(
            exam=exam_mixed, question_text="What HTTP status code is returned for a successful resource creation?",
            question_type="mcq", option_a="200 OK", option_b="201 Created", option_c="204 No Content", option_d="301 Moved",
            correct_answer="B", marks=10, order=1
        )
        Question.objects.create(
            exam=exam_mixed, question_text="WebSockets provide full-duplex communication channels over a single TCP connection.",
            question_type="true_false", correct_answer="true", marks=10, order=2
        )
        Question.objects.create(
            exam=exam_mixed, question_text="Describe the difference between JWT authentication and session-based authentication.",
            question_type="short_answer",
            correct_answer="JWT is stateless with signed tokens verified by the server without database lookup; session auth stores session state on the server (e.g. in Redis/DB) with a session ID cookie.",
            marks=15, order=3
        )
        Question.objects.create(
            exam=exam_mixed, question_text="Write a Python function `flatten_list(nested_list)` that flattens an arbitrarily nested list.",
            question_type="code",
            correct_answer="def flatten_list(nested_list):\n    result = []\n    for item in nested_list:\n        if isinstance(item, list):\n            result.extend(flatten_list(item))\n        else:\n            result.append(item)\n    return result",
            marks=15, order=4
        )

    print(f"Exams configured:")
    print(f" - [1] {exam_mcq.title} ({exam_mcq.questions.count()} questions)")
    print(f" - [2] {exam_essay.title} ({exam_essay.questions.count()} questions)")
    print(f" - [3] {exam_code.title} ({exam_code.questions.count()} questions)")
    print(f" - [4] {exam_mixed.title} ({exam_mixed.questions.count()} questions)")

    # Create 30 test students
    students = []
    for i in range(1, 31):
        username = f"sim_student_{i:02d}"
        email = f"sim_student_{i:02d}@bluewave.ac"
        user, _ = CustomUser.objects.get_or_create(
            username=username,
            defaults={"email": email, "first_name": f"Student", "last_name": f"#{i:02d}", "school": "Harare Tech"}
        )
        user.set_password("StudentPass123!")
        user.save()
        students.append(user)

    print(f"Created {len(students)} student accounts for simulation.")
    return [exam_mcq, exam_essay, exam_code, exam_mixed], students


def run_student_worker(student_idx, student_user, exam, barrier, results_list):
    """
    Simulates a student taking an exam and submitting at the exact moment the barrier drops.
    """
    # Clean old attempts for fresh run
    ExamAttempt.objects.filter(student=student_user, exam=exam).delete()

    client = Client()
    client.login(username=student_user.username, password="StudentPass123!")

    # Start attempt
    attempt = ExamAttempt.objects.create(
        student=student_user,
        exam=exam,
        attempt_number=1,
        status="in_progress",
        start_time=timezone.now(),
    )

    questions = list(exam.questions.all())
    post_payload = {"attempt_id": attempt.id}

    for q in questions:
        field_name = f"question_{q.id}"
        if q.question_type == "mcq":
            # Simulate realistic student accuracy: 80% correct
            post_payload[field_name] = q.correct_answer if (student_idx % 5 != 0) else "A"
        elif q.question_type == "true_false":
            post_payload[field_name] = q.correct_answer if (student_idx % 4 != 0) else ("true" if q.correct_answer == "false" else "false")
        elif q.question_type in ["short_answer", "essay"]:
            if student_idx % 6 == 0:
                # Blank / minimal answer
                post_payload[field_name] = "I don't know the exact answer to this."
            else:
                post_payload[field_name] = f"Student {student_idx} analysis: {q.correct_answer} Furthermore, it provides strong reliability and optimal resource scaling across modern cloud systems."
        elif q.question_type == "code":
            if student_idx % 7 == 0:
                # Syntax error code
                post_payload[field_name] = "def invalid_func():\n    return 10 / 0"
            else:
                post_payload[field_name] = q.correct_answer

    # Wait for ALL 30 students to finish answering and synchronize on the barrier
    barrier.wait()

    start_time = time.time()
    try:
        res = client.post(f"/student/exam/{exam.id}/submit/", data=post_payload)
        latency = time.time() - start_time
        
        attempt.refresh_from_db()
        status_code = res.status_code
        json_resp = res.json() if res.headers.get("Content-Type", "").startswith("application/json") else {}

        results_list.append({
            "student_id": student_idx,
            "username": student_user.username,
            "exam_title": exam.title,
            "status_code": status_code,
            "latency_sec": round(latency, 2),
            "attempt_status": attempt.status,
            "ai_graded": attempt.ai_graded,
            "score": float(attempt.score or 0),
            "total_marks": exam.total_marks,
            "percentage": float(attempt.percentage or 0),
            "json_success": json_resp.get("success", False),
            "error": None,
        })
    except Exception as e:
        latency = time.time() - start_time
        results_list.append({
            "student_id": student_idx,
            "username": student_user.username,
            "exam_title": exam.title,
            "status_code": 500,
            "latency_sec": round(latency, 2),
            "attempt_status": "error",
            "ai_graded": False,
            "score": 0,
            "total_marks": exam.total_marks,
            "percentage": 0,
            "json_success": False,
            "error": str(e),
        })


def main():
    exams, students = setup_simulation_data()
    
    # Assign 30 students across the 4 exams:
    # Students 1-10: Exam 1 (MCQ)
    # Students 11-18: Exam 2 (Essay)
    # Students 19-24: Exam 3 (Coding)
    # Students 25-30: Exam 4 (Mixed)
    exam_assignment = []
    for i, s in enumerate(students, 1):
        if i <= 10:
            exam_assignment.append((i, s, exams[0]))
        elif i <= 18:
            exam_assignment.append((i, s, exams[1]))
        elif i <= 24:
            exam_assignment.append((i, s, exams[2]))
        else:
            exam_assignment.append((i, s, exams[3]))

    NUM_STUDENTS = len(exam_assignment)
    barrier = threading.Barrier(NUM_STUDENTS)
    results = []

    print("\n" + "=" * 70)
    print(f"STEP 2: Launching 30 Concurrent Students — Synchronized Submit via Barrier")
    print("=" * 70)
    print(f"All {NUM_STUDENTS} threads will arm and hit /student/exam/<id>/submit/ simultaneously...")

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=NUM_STUDENTS) as executor:
        futures = [
            executor.submit(run_student_worker, idx, user, exam, barrier, results)
            for idx, user, exam in exam_assignment
        ]
        for f in as_completed(futures):
            pass
    total_time = time.time() - t0

    print("\n" + "=" * 70)
    print("STEP 3: Simulation Results Analysis")
    print("=" * 70)
    print(f"Total Simulation Elapsed Time: {total_time:.2f} seconds")
    print(f"Total Submissions: {len(results)}/{NUM_STUDENTS}\n")

    print(f"{'ID':<4} | {'Exam Category':<22} | {'Status':<7} | {'Code':<5} | {'Latency':<7} | {'Score':<10} | {'AI Graded':<9} | {'Error'}")
    print("-" * 95)
    
    success_count = 0
    error_count = 0
    graded_count = 0
    latencies = []

    # Sort by student_id
    results.sort(key=lambda x: x["student_id"])

    for r in results:
        latencies.append(r["latency_sec"])
        if r["status_code"] == 200 and r["json_success"]:
            success_count += 1
        else:
            error_count += 1
        
        if r["attempt_status"] == "graded":
            graded_count += 1

        exam_short = r["exam_title"].split(":")[1].split("(")[0].strip() if ":" in r["exam_title"] else r["exam_title"][:20]
        score_str = f"{r['score']}/{r['total_marks']} ({r['percentage']:.0f}%)"
        error_str = str(r["error"]) if r["error"] else "None"
        print(f"{r['student_id']:<4} | {exam_short:<22} | {r['attempt_status']:<7} | {r['status_code']:<5} | {r['latency_sec']:>5.2f}s | {score_str:<10} | {str(r['ai_graded']):<9} | {error_str}")

    avg_lat = sum(latencies) / len(latencies) if latencies else 0
    max_lat = max(latencies) if latencies else 0
    min_lat = min(latencies) if latencies else 0

    print("-" * 95)
    print(f"Summary Statistics:")
    print(f"  - Total Successful Submissions: {success_count}/{NUM_STUDENTS} ({success_count/NUM_STUDENTS*100:.1f}%)")
    print(f"  - Total Graded Attempts:        {graded_count}/{NUM_STUDENTS} ({graded_count/NUM_STUDENTS*100:.1f}%)")
    print(f"  - Total Errors/Failures:        {error_count}/{NUM_STUDENTS}")
    print(f"  - Average Submission Latency:   {avg_lat:.2f}s (Min: {min_lat:.2f}s, Max: {max_lat:.2f}s)")
    print("=" * 70)


if __name__ == "__main__":
    main()
