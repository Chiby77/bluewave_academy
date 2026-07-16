"""
Management command: seed_vb_exam
Creates the Visual Basic Console Applications Exam and seeds it to the database.

Usage:
    python manage.py seed_vb_exam
    python manage.py seed_vb_exam --force   # re-create if already exists
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
import datetime


class Command(BaseCommand):
    help = "Seed the Visual Basic Console Applications Exam (20 questions)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete existing exam with the same title and re-create it",
        )

    def handle(self, *args, **options):
        from siteapp.models import Exam, Question

        User = get_user_model()

        # ── Pick the first superuser as creator ──────────────────────────────
        creator = User.objects.filter(is_superuser=True).first()
        if not creator:
            creator = User.objects.filter(is_staff=True).first()
        if not creator:
            self.stderr.write(self.style.ERROR(
                "No superuser or staff user found. Create one first with "
                "'python manage.py createsuperuser'."
            ))
            return

        TITLE = "Visual Basic Console Applications: Comprehensive Assessment"

        # ── Guard: don't duplicate ────────────────────────────────────────────
        if Exam.objects.filter(title=TITLE).exists():
            if not options["force"]:
                self.stdout.write(self.style.WARNING(
                    f'Exam "{TITLE}" already exists. Use --force to recreate it.'
                ))
                return
            Exam.objects.filter(title=TITLE).delete()
            self.stdout.write("Deleted existing exam.")

        # ── Exam window: today and active for next week ───────────────────────
        now = timezone.now()
        start_date = now - datetime.timedelta(minutes=30)  # Active 30 mins ago
        end_date = now + datetime.timedelta(days=7)

        # ── Create exam ───────────────────────────────────────────────────────
        exam = Exam.objects.create(
            title=TITLE,
            description=(
                "A comprehensive Visual Basic .NET Console Application exam. "
                "Covers Variables, Operators, Selection Statements (If/Select Case), "
                "and Loops. The exam contains Multiple Choice, Short Answer, and "
                "Programming questions. Duration: 90 minutes. Total marks: 100. "
                "Passing mark: 50."
            ),
            category="Vb.net",
            level="beginner",
            duration_minutes=90,
            total_marks=100,
            passing_marks=50,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            is_held=False,
            enable_instant_grading=True,
            show_answers_after_submit=True,
            shuffle_questions=False,
            shuffle_options=False,
            created_by=creator,
        )

        # ── Questions ─────────────────────────────────────────────────────────
        # Format: (type, text, marks, option_a, option_b, option_c, option_d,
        #          correct_answer, explanation)
        # For short_answer / code: options are blank, correct_answer = model answer

        questions = [
            # Section A: Multiple Choice (Q1-5)
            {
                "type": "mcq",
                "text": "Which keyword is used to declare a variable that cannot be changed once initialized?",
                "marks": 5,
                "option_a": "Dim",
                "option_b": "Static",
                "option_c": "Const",
                "option_d": "Fixed",
                "answer": "C",
                "explanation": "The `Const` keyword in Visual Basic declares a constant variable, whose value cannot be changed after initialization.",
            },
            {
                "type": "mcq",
                "text": "What is the result of the expression `17 \\ 5` in Visual Basic?",
                "marks": 5,
                "option_a": "3.4",
                "option_b": "3",
                "option_c": "2",
                "option_d": "0.4",
                "answer": "B",
                "explanation": "The `\\` operator performs integer division in Visual Basic, discarding the remainder. 17 divided by 5 is 3 with a remainder of 2, so 17 \\ 5 = 3.",
            },
            {
                "type": "mcq",
                "text": "Which logical operator in VB.NET performs \"short-circuiting\" for a logical AND operation?",
                "marks": 5,
                "option_a": "And",
                "option_b": "AndAlso",
                "option_c": "&",
                "option_d": "&&",
                "answer": "B",
                "explanation": "`AndAlso` is the short-circuiting AND operator. If the first condition is false, it skips evaluating the second condition.",
            },
            {
                "type": "mcq",
                "text": "In a `Select Case` statement, which clause is used to handle values that do not match any specified cases?",
                "marks": 5,
                "option_a": "Case Else",
                "option_b": "Default",
                "option_c": "Case Other",
                "option_d": "Otherwise",
                "answer": "A",
                "explanation": "`Case Else` is used in a `Select Case` statement to handle any values that did not match the previous `Case` clauses.",
            },
            {
                "type": "mcq",
                "text": "Which loop structure is guaranteed to execute at least once?",
                "marks": 5,
                "option_a": "For...Next",
                "option_b": "While...End While",
                "option_c": "Do...Loop Until",
                "option_d": "Do While...Loop",
                "answer": "C",
                "explanation": "The `Do...Loop Until` structure checks the condition after the loop body has executed once, so the body runs at least once.",
            },

            # Section B: Short Answer (Q6-15)
            {
                "type": "short_answer",
                "text": "Explain the difference between the `/` operator and the `\\` operator.",
                "marks": 5,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "`/` performs standard floating-point division (returns a Double), while `\\` performs integer division (returns an Integer), discarding any remainder."
                ),
                "explanation": "`/` = floating-point division; `\\` = integer division.",
            },
            {
                "type": "short_answer",
                "text": "What is the default value of an uninitialized `Integer` variable in VB.NET?",
                "marks": 5,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": "0",
                "explanation": "In VB.NET, the default value for an Integer (and all numeric value types) is 0.",
            },
            {
                "type": "short_answer",
                "text": "Write the syntax for declaring a variable named `userName` that stores text.",
                "marks": 5,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": "Dim userName As String",
                "explanation": "`Dim` declares a variable, `As String` specifies the String data type.",
            },
            {
                "type": "short_answer",
                "text": "What does the `Mod` operator calculate?",
                "marks": 5,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": "It returns the remainder of a division operation.",
                "explanation": "`Mod` computes the remainder from dividing two numbers.",
            },
            {
                "type": "short_answer",
                "text": "How do you increment a variable `counter` by 1 using a shorthand assignment operator?",
                "marks": 5,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": "counter += 1",
                "explanation": "`+=` is the shorthand assignment operator for addition in VB.NET.",
            },
            {
                "type": "short_answer",
                "text": "Describe the purpose of the `Step` keyword in a `For...Next` loop.",
                "marks": 5,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": "It specifies the increment (or decrement) value for the loop counter variable after each iteration.",
                "explanation": "`Step` sets how much the counter changes each loop iteration.",
            },
            {
                "type": "short_answer",
                "text": "Which comparison operator is used to represent \"Not Equal To\" in Visual Basic?",
                "marks": 5,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": "<>",
                "explanation": "In VB.NET, `<>` is the \"not equal to\" comparison operator.",
            },
            {
                "type": "short_answer",
                "text": "What is the result of the Boolean expression `(5 > 3) Or (10 < 2)`?",
                "marks": 5,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": "True",
                "explanation": "The first condition `5 > 3` is true, so the entire `Or` expression is true (short-circuiting).",
            },
            {
                "type": "short_answer",
                "text": "Can a `Select Case` statement evaluate a range of numbers (e.g., 1 to 10)? If so, how?",
                "marks": 5,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": "Yes, using the keyword `To`, for example: `Case 1 To 10`.",
                "explanation": "`Case [start] To [end]` matches a range of values.",
            },
            {
                "type": "short_answer",
                "text": "What happens if the condition in a `While...End While` loop is false before the first iteration?",
                "marks": 5,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": "The code inside the loop is never executed; the program skips directly to the line following `End While`.",
                "explanation": "`While...End While` checks the condition first, so if it's false, the body never runs.",
            },

            # Section C: Programming (Q16-20)
            {
                "type": "code",
                "text": "Write a single line of code to declare three integer variables (`x`, `y`, and `z`) and initialize `z` to 100.",
                "marks": 10,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": "Dim x, y As Integer, z As Integer = 100",
                "explanation": "Declares x, y as Integer, and z as Integer initialized to 100.",
            },
            {
                "type": "code",
                "text": ("Write an `If...Then...Else` block that checks if a variable `age` is 18 or older. "
                        "If true, print \"Adult\"; otherwise, print \"Minor\"."),
                "marks": 10,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": ("If age >= 18 Then\n"
                          "    Console.WriteLine(\"Adult\")\n"
                          "Else\n"
                          "    Console.WriteLine(\"Minor\")\n"
                          "End If"),
                "explanation": "Simple If/Else condition checking age >= 18.",
            },
            {
                "type": "code",
                "text": "Write a `For...Next` loop that prints all even numbers from 2 to 20 (inclusive).",
                "marks": 10,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": ("For i As Integer = 2 To 20 Step 2\n"
                          "    Console.WriteLine(i)\n"
                          "Next"),
                "explanation": "Uses Step 2 to increment by 2 each time, starting at 2, ending at 20.",
            },
            {
                "type": "code",
                "text": ("Write a `Select Case` block for a variable `score`:\n"
                        "- If 90-100: \"A\"\n"
                        "- If 80-89: \"B\"\n"
                        "- Default: \"F\""),
                "marks": 10,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": ("Select Case score\n"
                          "    Case 90 To 100\n"
                          "        Console.WriteLine(\"A\")\n"
                          "    Case 80 To 89\n"
                          "        Console.WriteLine(\"B\")\n"
                          "    Case Else\n"
                          "        Console.WriteLine(\"F\")\n"
                          "End Select"),
                "explanation": "Uses Select Case with ranges and Case Else.",
            },
            {
                "type": "code",
                "text": ("Write a `Do...Loop Until` structure that repeatedly asks the user for a password "
                        "until they enter \"Secret123\"."),
                "marks": 10,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": ("Dim input As String\n"
                          "Do\n"
                          "    Console.Write(\"Enter password: \")\n"
                          "    input = Console.ReadLine()\n"
                          "Loop Until input = \"Secret123\""),
                "explanation": "Do Loop Until runs at least once, checks condition at end.",
            },
        ]

        # ── Verify total marks add up ─────────────────────────────────────────
        total = sum(q["marks"] for q in questions)
        assert total == 100, f"Questions total {total} marks, expected 100."

        # ── Insert questions ──────────────────────────────────────────────────
        for order, q in enumerate(questions, start=1):
            Question.objects.create(
                exam=exam,
                question_text=q["text"],
                question_type=q["type"],
                marks=q["marks"],
                order=order,
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                correct_answer=q["answer"],
                explanation=q["explanation"],
            )

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Created exam: "{exam.title}"\n'
            f'  Questions : {len(questions)}\n'
            f'  Total marks: {total}\n'
            f'  Passing mark: {exam.passing_marks}\n'
            f'  Active from: {start_date.strftime("%d %b %Y %H:%M")} '
            f'to {end_date.strftime("%d %b %Y %H:%M")}\n'
        ))

        # Summary breakdown
        from collections import Counter
        type_counts = Counter(q["type"] for q in questions)
        for qtype, count in type_counts.items():
            self.stdout.write(f'  {qtype:<15} {count} questions')
