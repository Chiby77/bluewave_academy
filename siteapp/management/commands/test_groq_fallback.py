
from django.core.management.base import BaseCommand
from siteapp.ai_tutor import get_tutor_service
from siteapp.examinator_service import get_grading_service
import os


class Command(BaseCommand):
    help = "Test Groq API connection and fallback mechanism"

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("Testing Groq API Connection & Fallback Mechanism")
        self.stdout.write("=" * 60)

        # 1. Test AI Tutor
        self.stdout.write("\n[1] Testing AI Tutor...")
        tutor = get_tutor_service()
        if not tutor.is_enabled():
            self.stderr.write(
                self.style.WARNING("AI Tutor not enabled: Check GROQ_API_KEY env var")
            )
        else:
            try:
                # Create a mock user with minimal data
                class MockUser:
                    def get_full_name(self):
                        return "Test User"
                    first_name = "Test"
                    current_level = "10th Grade"
                    username = "testuser"
                    school = "Test High School"
                    student_id = "12345"
                response = tutor.chat_with_tutor(
                    MockUser(),
                    "Hello! Just a quick test. Please reply in one sentence.",
                )
                self.stdout.write(
                    self.style.SUCCESS("[OK] AI Tutor Response: %s" % response['response'])
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR("[ERROR] AI Tutor Error: %s" % str(e)))

        # 2. Test Examinator Grading Service
        self.stdout.write("\n[2] Testing Examinator Grading Service...")
        examinator = get_grading_service()
        if not examinator.is_enabled():
            self.stderr.write(
                self.style.WARNING("Examinator not enabled: Check GROQ_API_KEY env var")
            )
        else:
            try:
                test_response = examinator._call_groq(
                    prompt="Hello! Just a quick test. Return JSON: {\"score\": 100, \"feedback\": \"Great!\"}",
                    total_marks=100,
                )
                self.stdout.write(
                    self.style.SUCCESS("[OK] Examinator Response: %s" % str(test_response))
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR("[ERROR] Examinator Error: %s" % str(e)))

        # Show configuration
        self.stdout.write("\n[3] Configuration Summary:")
        from siteapp.ai_tutor import AITutorService
        from siteapp.examinator_service import GROQ_PRIMARY_MODEL, GROQ_SECONDARY_MODEL, GROQ_FALLBACK_MODEL
        self.stdout.write("   Tutor Models: %s -> %s" % (AITutorService.PRIMARY_MODEL, AITutorService.FALLBACK_MODEL))
        self.stdout.write("   Examinator Models: %s -> %s -> %s" % (GROQ_PRIMARY_MODEL, GROQ_SECONDARY_MODEL, GROQ_FALLBACK_MODEL))
        
        has_key = bool(os.environ.get("GROQ_API_KEY"))
        key_status = "[OK] Set" if has_key else "[ERROR] Not set"
        self.stdout.write("   GROQ_API_KEY: %s" % key_status)
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Test Complete!")
        self.stdout.write("=" * 60)
