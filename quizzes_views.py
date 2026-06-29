"""
Serializers and Views for Quizzes app.
"""
from django.utils import timezone
from rest_framework import serializers, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Quiz, Question, Choice, QuizAttempt, QuestionResponse


# ── Serializers ────────────────────────────────────────────────────────────────

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'order']
        # is_correct intentionally omitted for students


class ChoiceAdminSerializer(serializers.ModelSerializer):
    """Includes is_correct — only for instructors/admins."""
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'image', 'points', 'order', 'choices']


class QuestionAdminSerializer(serializers.ModelSerializer):
    choices = ChoiceAdminSerializer(many=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'explanation', 'image',
                  'points', 'order', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        question = Question.objects.create(**validated_data)
        for c in choices_data:
            Choice.objects.create(question=question, **c)
        return question


class QuizSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'course', 'lesson', 'title', 'description',
                  'pass_percentage', 'time_limit_minutes', 'max_attempts',
                  'randomize_questions', 'show_answers_after',
                  'is_published', 'question_count', 'created_at']
        read_only_fields = ['created_at']


class QuizDetailSerializer(QuizSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta(QuizSerializer.Meta):
        fields = QuizSerializer.Meta.fields + ['questions']


class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = ['attempt_id', 'quiz', 'status', 'score', 'total_points',
                  'earned_points', 'passed', 'started_at', 'submitted_at']
        read_only_fields = fields


class QuestionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionResponse
        fields = ['question', 'selected_choices', 'text_answer']


class SubmitAttemptSerializer(serializers.Serializer):
    responses = QuestionResponseSerializer(many=True)


# ── Views ──────────────────────────────────────────────────────────────────────

class QuizViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Quiz.objects.filter(
            course__slug=self.kwargs.get('course_slug')
        ).prefetch_related('questions__choices')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return QuizDetailSerializer
        return QuizSerializer

    @action(detail=True, methods=['post'])
    def start(self, request, **kwargs):
        """Start a new quiz attempt."""
        quiz = self.get_object()
        attempts_count = QuizAttempt.objects.filter(
            quiz=quiz, student=request.user
        ).count()

        if attempts_count >= quiz.max_attempts:
            return Response(
                {'detail': f'Maximum attempts ({quiz.max_attempts}) reached.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cancel any in-progress attempt
        QuizAttempt.objects.filter(
            quiz=quiz, student=request.user, status=QuizAttempt.Status.IN_PROGRESS
        ).update(status=QuizAttempt.Status.TIMED_OUT)

        attempt = QuizAttempt.objects.create(quiz=quiz, student=request.user)
        return Response(QuizAttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='submit/(?P<attempt_id>[^/.]+)')
    def submit(self, request, attempt_id=None, **kwargs):
        """Submit answers and score the attempt."""
        quiz = self.get_object()
        try:
            attempt = QuizAttempt.objects.get(
                attempt_id=attempt_id,
                quiz=quiz,
                student=request.user,
                status=QuizAttempt.Status.IN_PROGRESS,
            )
        except QuizAttempt.DoesNotExist:
            return Response({'detail': 'Attempt not found.'}, status=404)

        serializer = SubmitAttemptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for resp_data in serializer.validated_data['responses']:
            choices = resp_data.pop('selected_choices', [])
            qr, _ = QuestionResponse.objects.get_or_create(
                attempt=attempt,
                question=resp_data['question'],
                defaults={'text_answer': resp_data.get('text_answer', '')},
            )
            qr.selected_choices.set(choices)

        attempt.status = QuizAttempt.Status.SUBMITTED
        attempt.submitted_at = timezone.now()
        attempt.save()
        attempt.calculate_score()

        return Response(QuizAttemptSerializer(attempt).data)

    @action(detail=True, methods=['get'], url_path='my-attempts')
    def my_attempts(self, request, **kwargs):
        quiz = self.get_object()
        attempts = QuizAttempt.objects.filter(quiz=quiz, student=request.user)
        return Response(QuizAttemptSerializer(attempts, many=True).data)
