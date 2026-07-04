"""
Management command: seed_js_exam
Creates the A-Level JavaScript Foundation exam with 20 mixed questions
(MCQ, short answer, coding) and seeds it to the database.

Usage:
    python manage.py seed_js_exam
    python manage.py seed_js_exam --force   # re-create if already exists
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
import datetime


class Command(BaseCommand):
    help = "Seed the A-Level JavaScript Foundation exam (20 questions)"

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

        TITLE = "A-Level JavaScript Foundation Exam"

        # ── Guard: don't duplicate ────────────────────────────────────────────
        if Exam.objects.filter(title=TITLE).exists():
            if not options["force"]:
                self.stdout.write(self.style.WARNING(
                    f'Exam "{TITLE}" already exists. Use --force to recreate it.'
                ))
                return
            Exam.objects.filter(title=TITLE).delete()
            self.stdout.write("Deleted existing exam.")

        # ── Exam window: today 18:00 → Wednesday 17:30 ───────────────────────
        # Today is Wednesday 2026-07-01 18:00 Africa/Harare
        # End date: next Wednesday 2026-07-08 17:30
        start_date = timezone.make_aware(
            datetime.datetime(2026, 7, 1, 18, 0, 0),
            timezone.get_current_timezone(),
        )
        end_date = timezone.make_aware(
            datetime.datetime(2026, 7, 8, 17, 30, 0),
            timezone.get_current_timezone(),
        )

        # ── Create exam ───────────────────────────────────────────────────────
        exam = Exam.objects.create(
            title=TITLE,
            description=(
                "A comprehensive JavaScript foundation exam for A-Level students. "
                "Covers Days 01–04 of the curriculum: Introduction to JavaScript, "
                "Variables & Data Types, Operators & Expressions, and Control Flow. "
                "The exam contains Multiple Choice, Short Answer, and Coding questions. "
                "Duration: 90 minutes. Total marks: 50. Passing mark: 25."
            ),
            category="web",
            level="beginner",
            duration_minutes=90,
            total_marks=50,
            passing_marks=25,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            is_held=False,
            enable_instant_grading=True,
            show_answers_after_submit=True,
            shuffle_questions=True,
            shuffle_options=True,
            created_by=creator,
        )

        # ── Questions ─────────────────────────────────────────────────────────
        # Format: (type, text, marks, option_a, option_b, option_c, option_d,
        #          correct_answer, explanation)
        # For short_answer / code: options are blank, correct_answer = model answer

        questions = [

            # ══════════════════════════════════════════════════
            # DAY 01 — Introduction to JavaScript (Q1–Q4)
            # ══════════════════════════════════════════════════

            {
                "type": "mcq",
                "text": "Which HTML tag is used to embed JavaScript code directly inside a webpage?",
                "marks": 2,
                "option_a": "<js>",
                "option_b": "<script>",
                "option_c": "<javascript>",
                "option_d": "<code>",
                "answer": "B",
                "explanation": "The <script> tag is the standard HTML element used to include or embed JavaScript code in a web page.",
            },
            {
                "type": "mcq",
                "text": "Where is the best place to put a <script> tag to avoid blocking the HTML from rendering?",
                "marks": 2,
                "option_a": "Inside the <head> with no attributes",
                "option_b": "At the very top of the file before <html>",
                "option_c": "Just before the closing </body> tag",
                "option_d": "Inside the <style> block",
                "answer": "C",
                "explanation": "Placing the <script> tag just before </body> ensures all HTML elements are loaded before the script runs, preventing blocking.",
            },
            {
                "type": "short_answer",
                "text": "What does the browser console function `console.log()` do? Give one practical use case for it during development.",
                "marks": 2,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "console.log() prints a value or message to the browser's developer console. "
                    "During development it is used for debugging — e.g. logging variable values to "
                    "check that they hold the expected data at a certain point in the program."
                ),
                "explanation": "console.log() is the primary debugging tool in JavaScript, outputting information to the browser DevTools console.",
            },
            {
                "type": "mcq",
                "text": "JavaScript is primarily used for which of the following?",
                "marks": 2,
                "option_a": "Styling web pages",
                "option_b": "Structuring web page content",
                "option_c": "Adding interactivity and logic to web pages",
                "option_d": "Compiling server-side code",
                "answer": "C",
                "explanation": "JavaScript is the scripting language of the web, responsible for interactivity — responding to user events, updating the DOM, fetching data, etc.",
            },

            # ══════════════════════════════════════════════════
            # DAY 02 — Variables & Data Types (Q5–Q9)
            # ══════════════════════════════════════════════════

            {
                "type": "mcq",
                "text": "Which of the following correctly declares a constant in JavaScript?",
                "marks": 2,
                "option_a": "var PI = 3.14;",
                "option_b": "let PI = 3.14;",
                "option_c": "const PI = 3.14;",
                "option_d": "constant PI = 3.14;",
                "answer": "C",
                "explanation": "The `const` keyword declares a block-scoped variable whose value cannot be reassigned after it is initialised.",
            },
            {
                "type": "mcq",
                "text": "What is the data type of the value produced by: `typeof null`?",
                "marks": 2,
                "option_a": '"null"',
                "option_b": '"object"',
                "option_c": '"undefined"',
                "option_d": '"boolean"',
                "answer": "B",
                "explanation": 'typeof null returns "object" — this is a well-known quirk in JavaScript that has existed since the language\'s first version.',
            },
            {
                "type": "mcq",
                "text": "Which statement about `let` and `var` is TRUE?",
                "marks": 2,
                "option_a": "`let` is function-scoped; `var` is block-scoped",
                "option_b": "`let` is block-scoped; `var` is function-scoped",
                "option_c": "Both `let` and `var` are block-scoped",
                "option_d": "Both `let` and `var` are global-scoped",
                "answer": "B",
                "explanation": "`let` (ES6) is block-scoped, meaning it only exists within the nearest enclosing {}. `var` is function-scoped and gets hoisted to the top of the function.",
            },
            {
                "type": "short_answer",
                "text": (
                    "Consider the following code:\n\n"
                    "    let age = 17;\n"
                    "    let name = 'Alice';\n"
                    "    let isEnrolled = true;\n"
                    "    let score = null;\n\n"
                    "State the data type of each variable and explain what `null` represents."
                ),
                "marks": 3,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "age → number; name → string; isEnrolled → boolean; score → null (object type via typeof). "
                    "null is an intentional absence of any object value — it means 'no value' has been assigned on purpose, "
                    "as opposed to undefined which means a variable has been declared but not yet given a value."
                ),
                "explanation": "Understanding data types and the distinction between null and undefined is foundational in JavaScript.",
            },
            {
                "type": "coding",
                "text": (
                    "Write JavaScript code that:\n"
                    "1. Declares a variable `firstName` using `let` and assigns your first name.\n"
                    "2. Declares a constant `SCHOOL` and assigns the string 'Bluewave Academy'.\n"
                    "3. Uses `console.log` to print the message: 'Hello, [firstName]! Welcome to [SCHOOL].'\n\n"
                    "Use a template literal (backtick string) for the final console.log statement."
                ),
                "marks": 3,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "let firstName = 'Alice';\n"
                    "const SCHOOL = 'Bluewave Academy';\n"
                    "console.log(`Hello, ${firstName}! Welcome to ${SCHOOL}.`);"
                ),
                "explanation": "Tests let vs const, string assignment, and template literal syntax (ES6).",
            },

            # ══════════════════════════════════════════════════
            # DAY 03 — Operators & Expressions (Q10–Q14)
            # ══════════════════════════════════════════════════

            {
                "type": "mcq",
                "text": "What is the output of: `console.log(10 % 3);`",
                "marks": 2,
                "option_a": "3",
                "option_b": "1",
                "option_c": "0",
                "option_d": "3.33",
                "answer": "B",
                "explanation": "The % operator returns the remainder of division. 10 ÷ 3 = 3 remainder 1, so 10 % 3 === 1.",
            },
            {
                "type": "mcq",
                "text": "What does the strict equality operator `===` check that `==` does NOT?",
                "marks": 2,
                "option_a": "Value only",
                "option_b": "Type only",
                "option_c": "Both value AND type",
                "option_d": "Reference equality",
                "answer": "C",
                "explanation": "`===` (strict equality) checks both the value and the data type, while `==` (loose equality) performs type coercion before comparing.",
            },
            {
                "type": "mcq",
                "text": "What is the result of: `console.log('5' + 3);`",
                "marks": 2,
                "option_a": "8",
                "option_b": "53",
                "option_c": "NaN",
                "option_d": "Error",
                "answer": "B",
                "explanation": "When + is used with a string and a number, JavaScript converts the number to a string and concatenates them: '5' + 3 = '53'.",
            },
            {
                "type": "short_answer",
                "text": (
                    "Evaluate the following expressions and state the result AND the reason:\n\n"
                    "a) `5 == '5'`\n"
                    "b) `5 === '5'`\n"
                    "c) `true && false`\n"
                    "d) `!false`"
                ),
                "marks": 4,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "a) true — loose equality coerces '5' to number 5 before comparing, so 5 == 5 is true.\n"
                    "b) false — strict equality checks type too; number 5 and string '5' have different types.\n"
                    "c) false — logical AND returns true only when BOTH operands are truthy; false makes it false.\n"
                    "d) true — the NOT operator inverts the boolean; !false === true."
                ),
                "explanation": "Reinforces the difference between == and ===, logical AND, and the NOT operator.",
            },
            {
                "type": "coding",
                "text": (
                    "Write a JavaScript expression using the ternary operator that:\n"
                    "- Takes a variable `score` (assume it is already declared with a number value).\n"
                    "- Assigns the string 'Pass' to a variable `result` if `score >= 50`, otherwise assigns 'Fail'.\n"
                    "- Logs `result` to the console.\n\n"
                    "Show the complete code for all three steps."
                ),
                "marks": 3,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "let score = 72;  // example value\n"
                    "let result = score >= 50 ? 'Pass' : 'Fail';\n"
                    "console.log(result);"
                ),
                "explanation": "Ternary operator syntax: condition ? valueIfTrue : valueIfFalse.",
            },

            # ══════════════════════════════════════════════════
            # DAY 04 — Control Flow / Conditionals (Q15–Q20)
            # ══════════════════════════════════════════════════

            {
                "type": "mcq",
                "text": "What will the following code output?\n\n    let x = 10;\n    if (x > 5) {\n        console.log('Big');\n    } else {\n        console.log('Small');\n    }",
                "marks": 2,
                "option_a": "Small",
                "option_b": "Big",
                "option_c": "Nothing — there is a syntax error",
                "option_d": "BigSmall",
                "answer": "B",
                "explanation": "x is 10, which is greater than 5, so the if-block runs and prints 'Big'.",
            },
            {
                "type": "mcq",
                "text": "In a `switch` statement, what is the purpose of the `break` keyword?",
                "marks": 2,
                "option_a": "It stops the entire script from running",
                "option_b": "It exits the switch block so the next case does not run",
                "option_c": "It returns a value from the switch",
                "option_d": "It declares a new variable inside the case",
                "answer": "B",
                "explanation": "Without `break`, execution falls through to the next case. `break` exits the switch block after a matching case runs.",
            },
            {
                "type": "mcq",
                "text": "Which of the following correctly uses `else if` to check three conditions?",
                "marks": 2,
                "option_a": "if (a) { } elseif (b) { } else { }",
                "option_b": "if (a) { } else if (b) { } else { }",
                "option_c": "if (a) { } elif (b) { } else { }",
                "option_d": "if (a) { } or if (b) { } else { }",
                "answer": "B",
                "explanation": "JavaScript uses `else if` (two separate words) to chain multiple conditions. `elseif` and `elif` are not valid JavaScript keywords.",
            },
            {
                "type": "short_answer",
                "text": (
                    "A student's mark is stored in a variable called `mark`. "
                    "Write the logic (in words or pseudocode) for an if/else-if/else chain that:\n\n"
                    "- Prints 'A' if mark >= 80\n"
                    "- Prints 'B' if mark >= 65\n"
                    "- Prints 'C' if mark >= 50\n"
                    "- Prints 'Fail' otherwise\n\n"
                    "Then explain why the order of the conditions matters."
                ),
                "marks": 3,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "if (mark >= 80) { console.log('A'); }\n"
                    "else if (mark >= 65) { console.log('B'); }\n"
                    "else if (mark >= 50) { console.log('C'); }\n"
                    "else { console.log('Fail'); }\n\n"
                    "Order matters because JavaScript evaluates conditions top to bottom and stops at the first true one. "
                    "If we put mark >= 50 first, a student with 90 would match that and get 'C' instead of 'A'."
                ),
                "explanation": "Tests understanding of if/else-if chains and the importance of condition ordering.",
            },
            {
                "type": "coding",
                "text": (
                    "Write a JavaScript function called `dayName` that takes a number (1–7) "
                    "and uses a `switch` statement to return the name of the day "
                    "(1 = 'Monday', 2 = 'Tuesday', ... 7 = 'Sunday'). "
                    "If the number is outside 1–7, return 'Invalid day'.\n\n"
                    "Call the function with the value 3 and log the result."
                ),
                "marks": 4,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "function dayName(num) {\n"
                    "    switch (num) {\n"
                    "        case 1: return 'Monday';\n"
                    "        case 2: return 'Tuesday';\n"
                    "        case 3: return 'Wednesday';\n"
                    "        case 4: return 'Thursday';\n"
                    "        case 5: return 'Friday';\n"
                    "        case 6: return 'Saturday';\n"
                    "        case 7: return 'Sunday';\n"
                    "        default: return 'Invalid day';\n"
                    "    }\n"
                    "}\n\n"
                    "console.log(dayName(3));  // Wednesday"
                ),
                "explanation": "Tests switch statement syntax, cases, default, return, and function declaration.",
            },
            {
                "type": "coding",
                "text": (
                    "Write a complete JavaScript program that:\n"
                    "1. Declares a variable `temperature` and sets it to 38.\n"
                    "2. Uses an if/else-if/else chain to classify the temperature:\n"
                    "   - >= 35: 'Hot'\n"
                    "   - >= 20: 'Warm'\n"
                    "   - >= 10: 'Cool'\n"
                    "   - Below 10: 'Cold'\n"
                    "3. Stores the classification in a variable `weather`.\n"
                    "4. Logs: 'The weather is: [weather]' using a template literal."
                ),
                "marks": 4,
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "let temperature = 38;\n"
                    "let weather;\n\n"
                    "if (temperature >= 35) {\n"
                    "    weather = 'Hot';\n"
                    "} else if (temperature >= 20) {\n"
                    "    weather = 'Warm';\n"
                    "} else if (temperature >= 10) {\n"
                    "    weather = 'Cool';\n"
                    "} else {\n"
                    "    weather = 'Cold';\n"
                    "}\n\n"
                    "console.log(`The weather is: ${weather}`);"
                ),
                "explanation": "Combines variable declaration, if/else-if/else, and template literals in a single program.",
            },
        ]

        # ── Verify total marks add up ─────────────────────────────────────────
        total = sum(q["marks"] for q in questions)
        assert total == 50, f"Questions total {total} marks, expected 50."

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
