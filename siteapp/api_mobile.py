from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json
import threading

from siteapp.models import Exam, ExamAttempt, Question, Answer, TutorConversation, TutorMessage
from siteapp.examinator_service import submit_exam
from siteapp.ai_tutor import get_tutor_service

_DB_WRITE_LOCK = threading.RLock()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exam_take(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, is_published=True)
    
    # Check if there's an in-progress attempt
    attempt = ExamAttempt.objects.filter(exam=exam, student=request.user, status='in_progress').first()
    
    if not attempt:
        # Create a new attempt
        with _DB_WRITE_LOCK:
            attempt = ExamAttempt.objects.create(
                exam=exam,
                student=request.user,
                status='in_progress',
                started_at=timezone.now()
            )
            
    questions = exam.questions.order_by('order')
    q_data = []
    for q in questions:
        q_data.append({
            'id': q.id,
            'text': q.text,
            'question_type': q.question_type,
            'options': q.get_options_list() if q.question_type == 'multiple_choice' else []
        })
        
    return Response({
        'attempt_id': attempt.id,
        'exam': {
            'id': exam.id,
            'title': exam.title,
            'duration_minutes': exam.duration_minutes
        },
        'questions': q_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_exam_submit(request, exam_id):
    """
    Expects JSON:
    {
       "attempt_id": 123,
       "answers": {
          "question_id": "answer_text",
          ...
       }
    }
    """
    exam = get_object_or_404(Exam, id=exam_id)
    attempt_id = request.data.get('attempt_id')
    answers_data = request.data.get('answers', {})
    
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user, exam=exam)
    
    if attempt.status != 'in_progress':
        return Response({'error': 'Attempt is not in progress'}, status=status.HTTP_400_BAD_REQUEST)
        
    with _DB_WRITE_LOCK:
        # Convert dictionary to lists for bulk creation
        # We need to map Question objects
        questions_qs = Question.objects.filter(exam=exam)
        question_map = {str(q.id): q for q in questions_qs}
        
        answers_to_create = []
        for q_id_str, text_val in answers_data.items():
            q_obj = question_map.get(q_id_str)
            if q_obj:
                answers_to_create.append(Answer(
                    attempt=attempt,
                    question=q_obj,
                    student_text=str(text_val)
                ))
                
        if answers_to_create:
            Answer.objects.bulk_create(answers_to_create)
            
        attempt.status = 'submitted'
        attempt.submitted_at = timezone.now()
        attempt.save(update_fields=['status', 'submitted_at'])
        
    # Kick off asynchronous grading
    threading.Thread(target=submit_exam, args=(attempt.id,)).start()
    
    return Response({'message': 'Exam submitted successfully for grading', 'attempt_id': attempt.id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exam_status(request, attempt_id):
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)
    
    return Response({
        'id': attempt.id,
        'status': attempt.status,
        'score': attempt.score,
        'total_possible_score': attempt.total_possible_score,
        'feedback': attempt.feedback
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_dashboard(request):
    """Mobile dashboard data: enrolled classrooms, recent exams, stats"""
    user = request.user
    
    # Very simplified dashboard
    exams = Exam.objects.filter(is_published=True).order_by('-created_at')[:5]
    recent_attempts = ExamAttempt.objects.filter(student=user).order_by('-started_at')[:5]
    
    return Response({
        'user': {
            'first_name': user.first_name,
        },
        'available_exams': [
            {'id': e.id, 'title': e.title, 'duration_minutes': e.duration_minutes}
            for e in exams
        ],
        'recent_attempts': [
            {
                'id': a.id, 
                'exam_title': a.exam.title, 
                'status': a.status, 
                'score': a.score
            }
            for a in recent_attempts
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_mobile_tutor_conversation(request):
    """Get or create a tutor conversation for the mobile user."""
    conversation, created = TutorConversation.objects.get_or_create(user=request.user)
    messages = conversation.messages.all().order_by("timestamp")
    message_data = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in messages
    ]
    return Response({
        "conversation_id": conversation.id,
        "messages": message_data,
        "created_at": conversation.created_at.isoformat(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_mobile_tutor_send_message(request):
    """Send a message to AI tutor from mobile app."""
    user_message = request.data.get("message", "").strip()
    if not user_message:
        return Response({"error": "Message is required"}, status=400)

    conversation, _ = TutorConversation.objects.get_or_create(user=request.user)

    # Save user message
    user_msg = TutorMessage.objects.create(
        conversation=conversation,
        role="user",
        content=user_message,
    )

    # Get AI response
    tutor_service = get_tutor_service()
    response = tutor_service.chat_with_tutor(
        user=request.user,
        message=user_message,
    )

    # Save AI message
    ai_msg = TutorMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content=response["response"],
    )

    return Response({
        "ok": True,
        "user_message": {
            "id": user_msg.id,
            "role": "user",
            "content": user_msg.content,
            "timestamp": user_msg.timestamp.isoformat(),
        },
        "ai_message": {
            "id": ai_msg.id,
            "role": "assistant",
            "content": ai_msg.content,
            "timestamp": ai_msg.timestamp.isoformat(),
        },
        "suggestions": response.get("suggestions", []),
    })
