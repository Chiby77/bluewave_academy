"""
Management command: seed_js_event_listeners

Creates the JavaScript Event Listeners Assessment Test exactly as per the
Bluewave Academy | CodeWave — Web Development Series PDF.

Spec:
  - 10 Questions (5 MCQ, 3 Short Answer, 2 Code)
  - 40 Total Marks
  - 45 Minutes
  - Intermediate Level
  - Active immediately (no end date restriction — open until manually closed)

Usage:
    python manage.py seed_js_event_listeners
    python manage.py seed_js_event_listeners --force   # re-create if exists
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime


class Command(BaseCommand):
    help = "Seed the JS Event Listeners Assessment Test (10 questions, 40 marks)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete existing exam with the same title and re-create it",
        )

    def handle(self, *args, **options):
        from siteapp.models import Exam, Question
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # ── Pick creator ─────────────────────────────────────────────────────
        creator = (
            User.objects.filter(is_superuser=True).first()
            or User.objects.filter(is_staff=True).first()
        )
        if not creator:
            self.stderr.write(self.style.ERROR(
                "No superuser or staff user found. "
                "Run 'python manage.py createsuperuser' first."
            ))
            return

        TITLE = "JavaScript Event Listeners — Assessment Test"

        # ── Guard ─────────────────────────────────────────────────────────────
        if Exam.objects.filter(title=TITLE).exists():
            if not options["force"]:
                self.stdout.write(self.style.WARNING(
                    f'Exam "{TITLE}" already exists. Use --force to recreate it.'
                ))
                return
            deleted, _ = Exam.objects.filter(title=TITLE).delete()
            self.stdout.write(f"Deleted existing exam ({deleted} record(s)).")

        # ── Timing: active now, no hard end date (set 1 year window) ─────────
        now = timezone.now()
        end_date = now + datetime.timedelta(days=365)

        # ── Create exam ───────────────────────────────────────────────────────
        exam = Exam.objects.create(
            title=TITLE,
            description=(
                "This test assesses your understanding of JavaScript event listeners, "
                "the event object, delegation, propagation, and real-world DOM interaction. "
                "Answer all questions. Code snippets must be syntactically correct.\n\n"
                "INSTRUCTIONS: MCQ = select best answer | Short answer = 2–4 sentences | "
                "Code = write valid JS | Marks shown per question.\n\n"
                "Bluewave Academy | CodeWave — Web Development Series | 2026 Edition"
            ),
            category="web",
            level="intermediate",
            duration_minutes=45,
            total_marks=40,
            passing_marks=20,
            start_date=now,
            end_date=end_date,
            is_active=True,
            is_held=False,
            enable_instant_grading=True,
            show_answers_after_submit=True,
            shuffle_questions=False,   # keep the PDF order
            shuffle_options=False,     # keep A/B/C/D order from PDF
            created_by=creator,
        )

        # ── Questions — exactly as per the PDF ───────────────────────────────
        questions = [

            # ── Q1 — MCQ [2 marks] ────────────────────────────────────────────
            {
                "order": 1,
                "type": "mcq",
                "marks": 2,
                "text": (
                    "Which of the following is the correct way to attach an event listener "
                    "to a button element?"
                ),
                "option_a": "button.onClick = function() { }",
                "option_b": "button.addEventListener('click', function() { })",
                "option_c": "button.addEvent('click', function() { })",
                "option_d": "button.on('click', function() { })",
                "answer": "B",
                "explanation": (
                    "addEventListener() is the standard, modern way to attach events. "
                    "onClick (capital C) is a property, not a method. "
                    "addEvent() and .on() do not exist in vanilla JavaScript."
                ),
            },

            # ── Q2 — MCQ [2 marks] ────────────────────────────────────────────
            {
                "order": 2,
                "type": "mcq",
                "marks": 2,
                "text": (
                    "What does calling event.preventDefault() do inside a form submit listener?"
                ),
                "option_a": "Stops the event from bubbling up to parent elements",
                "option_b": "Removes the event listener permanently",
                "option_c": "Prevents the browser's default action, such as the page reloading",
                "option_d": "Converts the event into a custom event",
                "answer": "C",
                "explanation": (
                    "event.preventDefault() stops the browser's built-in behaviour for that event. "
                    "For a form submit, that means preventing the page from refreshing. "
                    "Use event.stopPropagation() to stop bubbling instead."
                ),
            },

            # ── Q3 — MCQ [2 marks] ────────────────────────────────────────────
            {
                "order": 3,
                "type": "mcq",
                "marks": 2,
                "text": (
                    "Study the code snippet below:\n\n"
                    "const btn = document.querySelector('#btn');\n"
                    "btn.addEventListener('click', (e) => {\n"
                    "    console.log(e.target.id);\n"
                    "});\n\n"
                    "What will be logged to the console when the button is clicked?"
                ),
                "option_a": "click",
                "option_b": "undefined",
                "option_c": "btn",
                "option_d": "e.target",
                "answer": "C",
                "explanation": (
                    "e.target refers to the element that was actually clicked. "
                    "e.target.id gives its id attribute value, which is 'btn'."
                ),
            },

            # ── Q4 — MCQ [2 marks] ────────────────────────────────────────────
            {
                "order": 4,
                "type": "mcq",
                "marks": 2,
                "text": (
                    "Which event fires continuously as the user types into an input field?"
                ),
                "option_a": "change",
                "option_b": "keyup",
                "option_c": "input",
                "option_d": "type",
                "answer": "C",
                "explanation": (
                    "The 'input' event fires on every change to the value, including each keystroke, "
                    "paste, and speech input. 'change' only fires when the element loses focus. "
                    "'keyup' fires per key but misses paste and speech input."
                ),
            },

            # ── Q5 — MCQ [3 marks] ────────────────────────────────────────────
            {
                "order": 5,
                "type": "mcq",
                "marks": 3,
                "text": (
                    "Study the code snippet below:\n\n"
                    "document.body.addEventListener('click', () => console.log('body'));\n"
                    "document.querySelector('#box').addEventListener('click', () => console.log('box'));\n"
                    "document.querySelector('#btn').addEventListener('click', () => console.log('btn'));\n"
                    "// #btn is inside #box, which is inside body\n\n"
                    "What is the output order when the button (#btn) is clicked?\n\n"
                    "Note: This tests your understanding of event bubbling."
                ),
                "option_a": "body → box → btn",
                "option_b": "btn → box → body",
                "option_c": "btn → body → box",
                "option_d": "All fire simultaneously",
                "answer": "B",
                "explanation": (
                    "Event bubbling travels from the innermost target upward through ancestors. "
                    "The click hits #btn first, then bubbles up to #box, then body. "
                    "Capturing (top-down) is the reverse but is not the default behaviour of addEventListener."
                ),
            },

            # ── Q6 — Short Answer [4 marks] ───────────────────────────────────
            {
                "order": 6,
                "type": "short_answer",
                "marks": 4,
                "text": (
                    "Explain the difference between event bubbling and event capturing. "
                    "In which phase does addEventListener operate by default?"
                ),
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "Bubbling: after an event fires on the target element, it propagates UP through "
                    "ancestor elements (child → parent → grandparent → document).\n\n"
                    "Capturing: the opposite — the event travels DOWN from the document root to the "
                    "target before the event fires on the target itself.\n\n"
                    "addEventListener uses BUBBLING by default (third argument is false by default). "
                    "To use capturing, pass true as the third argument: "
                    "addEventListener('click', fn, true)."
                ),
                "explanation": (
                    "Award 1 mark each for: bubbling definition, capturing definition, "
                    "correct default phase identification (bubbling), and the third-argument syntax."
                ),
            },

            # ── Q7 — Short Answer [4 marks] ───────────────────────────────────
            {
                "order": 7,
                "type": "short_answer",
                "marks": 4,
                "text": (
                    "What is event delegation and why is it preferred over attaching individual "
                    "listeners to each list item? Give one practical use case."
                ),
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "Event delegation means attaching ONE listener to a parent element instead of "
                    "individual listeners to every child element. When a child is clicked, the event "
                    "bubbles up to the parent listener, which uses e.target to identify which child "
                    "fired it.\n\n"
                    "It is preferred because it is more memory-efficient (one listener vs many), "
                    "works for dynamically added elements (elements added after page load are "
                    "automatically covered), and requires less code.\n\n"
                    "Practical use case: a single listener on a <ul> handles clicks on any <li>, "
                    "even list items added dynamically after the page loaded."
                ),
                "explanation": (
                    "Award 1 mark: definition, 1 mark: why preferred (memory/efficiency), "
                    "1 mark: dynamic elements benefit, 1 mark: valid practical use case."
                ),
            },

            # ── Q8 — Short Answer [4 marks] ───────────────────────────────────
            {
                "order": 8,
                "type": "short_answer",
                "marks": 4,
                "text": (
                    "The code below has a common mistake. Identify it and explain how to fix it.\n\n"
                    "const btn = document.querySelector('#submit');\n"
                    "btn.addEventListener('click', handleClick());\n\n"
                    "function handleClick() {\n"
                    "    console.log('Button clicked!');\n"
                    "}"
                ),
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "The mistake is handleClick() — the parentheses immediately CALL the function "
                    "when the code runs and pass its return value (undefined) to addEventListener "
                    "instead of passing the function itself as a callback.\n\n"
                    "Fix: remove the parentheses so a function reference is passed, not its result:\n\n"
                    "// WRONG — calls the function immediately at registration time\n"
                    "btn.addEventListener('click', handleClick());\n\n"
                    "// CORRECT — passes the function reference to be called on click\n"
                    "btn.addEventListener('click', handleClick);"
                ),
                "explanation": (
                    "Award 2 marks for correctly identifying the bug (invocation vs reference). "
                    "Award 2 marks for the correct fix with a clear explanation."
                ),
            },

            # ── Q9 — Code [9 marks] ───────────────────────────────────────────
            {
                "order": 9,
                "type": "code",
                "marks": 9,
                "text": (
                    "Write the JavaScript for a colour-switcher.\n\n"
                    "When the user clicks any of the three colour buttons "
                    "(#red-btn, #blue-btn, #green-btn), the document.body background colour "
                    "should change to match.\n\n"
                    "Use a SINGLE event listener with event delegation attached to a parent "
                    "#colour-panel div.\n\n"
                    "Marking breakdown:\n"
                    "- Correct delegation — single listener on #colour-panel (3 marks)\n"
                    "- Correctly reading e.target to identify which button was clicked (3 marks)\n"
                    "- Correct background colour assignment syntax and clean code (3 marks)"
                ),
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "const panel = document.querySelector('#colour-panel');\n\n"
                    "panel.addEventListener('click', (e) => {\n"
                    "    const id = e.target.id;\n"
                    "    if (id === 'red-btn')   document.body.style.backgroundColor = 'red';\n"
                    "    else if (id === 'blue-btn')  document.body.style.backgroundColor = 'blue';\n"
                    "    else if (id === 'green-btn') document.body.style.backgroundColor = 'green';\n"
                    "});\n\n"
                    "// Alternative using data attributes (also full marks):\n"
                    "panel.addEventListener('click', (e) => {\n"
                    "    const colour = e.target.dataset.colour;\n"
                    "    if (colour) document.body.style.backgroundColor = colour;\n"
                    "});"
                ),
                "explanation": (
                    "3 marks: single listener on parent element (delegation pattern). "
                    "3 marks: correctly reading e.target.id (or dataset) to identify the clicked button. "
                    "3 marks: correct backgroundColor assignment syntax and clean, readable code."
                ),
            },

            # ── Q10 — Code [8 marks] ──────────────────────────────────────────
            {
                "order": 10,
                "type": "code",
                "marks": 8,
                "text": (
                    "Build a character counter.\n\n"
                    "Given an HTML textarea with id 'bio' and a paragraph with id 'counter', "
                    "write JavaScript that:\n\n"
                    "(a) Listens for user input in real time\n"
                    "(b) Updates the counter paragraph to show 'X / 150 characters' "
                    "(where X is the current character count)\n"
                    "(c) Changes the counter text colour to red when the limit of 150 "
                    "is reached or exceeded, and resets the colour when below the limit\n\n"
                    "Marking breakdown:\n"
                    "- Correct 'input' event listener (2 marks)\n"
                    "- Counter paragraph updated with correct 'X / 150 characters' format (3 marks)\n"
                    "- Colour changes to red at/above limit and resets below limit (3 marks)"
                ),
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "answer": (
                    "const bio     = document.querySelector('#bio');\n"
                    "const counter = document.querySelector('#counter');\n"
                    "const MAX     = 150;\n\n"
                    "bio.addEventListener('input', () => {\n"
                    "    const len = bio.value.length;\n"
                    "    counter.textContent = `${len} / ${MAX} characters`;\n\n"
                    "    if (len >= MAX) {\n"
                    "        counter.style.color = 'red';\n"
                    "    } else {\n"
                    "        counter.style.color = '';  // reset to default\n"
                    "    }\n"
                    "});"
                ),
                "explanation": (
                    "2 marks: correct 'input' event listener on the textarea. "
                    "3 marks: textContent updated with correct format (X / 150 characters) using a template literal. "
                    "3 marks: colour changes to red at/above the 150 limit and resets to default below it."
                ),
            },
        ]

        # ── Sanity check ──────────────────────────────────────────────────────
        total = sum(q["marks"] for q in questions)
        assert total == 40, f"Mark total is {total}, expected 40."
        assert len(questions) == 10, f"Question count is {len(questions)}, expected 10."

        # ── Insert questions ──────────────────────────────────────────────────
        for q in questions:
            Question.objects.create(
                exam=exam,
                question_text=q["text"],
                question_type=q["type"],
                marks=q["marks"],
                order=q["order"],
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                # Normalise to lowercase so check_answer() comparison always works.
                # The template submits lowercase values (a/b/c/d) and check_answer()
                # does .lower() on both sides, but storing lowercase avoids any
                # edge case when the admin edits the question directly.
                correct_answer=q["answer"].lower(),
                explanation=q["explanation"],
            )

        # ── Summary ───────────────────────────────────────────────────────────
        from collections import Counter
        type_counts = Counter(q["type"] for q in questions)

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Exam created: "{exam.title}"\n'
            f'  Questions  : {len(questions)}\n'
            f'  Total marks: {total}\n'
            f'  Pass mark  : {exam.passing_marks}\n'
            f'  Duration   : {exam.duration_minutes} minutes\n'
            f'  Level      : {exam.level}\n'
            f'  Active from: {now.strftime("%d %b %Y %H:%M")} (live now)\n'
        ))
        for qtype, count in sorted(type_counts.items()):
            label = {"mcq": "MCQ", "short_answer": "Short Answer", "code": "Code"}.get(qtype, qtype)
            self.stdout.write(f'  {label:<15} {count} question(s)')
