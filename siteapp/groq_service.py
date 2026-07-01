"""
groq_service.py — backwards-compatible re-export.
The unified Groq grading service now lives in examinator_service.py.
"""
from .examinator_service import GroqGradingService, get_grading_service

# Legacy alias kept for any code that imports GroqGradingService or get_groq_service
def get_groq_service():
    return get_grading_service()
