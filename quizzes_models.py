"""
Quiz models for LMS.
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Quiz(models.Model):
    """A quiz attached to a course section or standalone lesson."""

    lesson = models.OneToOneField(
        'lessons.Lesson', on_delete=models.CASCADE,
        related_name='quiz', null=True, blank=True,
    )
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, related_name='quizzes',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    pass_percentage = models.PositiveSmallIntegerField(default=70)
    time_limit_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    randomize_questions = models.BooleanField(default=False)
    show_answers_after = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Quiz: {self.title} [{self.course.title}]"

    @property
    def question_count(self):
        return self.questions.count()


class Question(models.Model):
    class QuestionType(models.TextChoices):
        SINGLE = 'single', _('Single Choice')
        MULTIPLE = 'multiple', _('Multiple Choice')
        TRUE_FALSE = 'true_false', _('True / False')
        SHORT_ANSWER = 'short_answer', _('Short Answer')

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(
        max_length=20, choices=QuestionType.choices, default=QuestionType.SINGLE
    )
    explanation = models.TextField(blank=True, help_text='Shown after answering')
    image = models.ImageField(upload_to='quiz_images/', null=True, blank=True)
    points = models.PositiveSmallIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"

    @property
    def correct_answers(self):
        return self.choices.filter(is_correct=True)


class Choice(models.Model):
    """An answer choice for a Question."""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{'✓' if self.is_correct else '✗'} {self.text[:60]}"


class QuizAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', _('In Progress')
        SUBMITTED = 'submitted', _('Submitted')
        TIMED_OUT = 'timed_out', _('Timed Out')

    attempt_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_points = models.PositiveSmallIntegerField(default=0)
    earned_points = models.PositiveSmallIntegerField(default=0)
    passed = models.BooleanField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.email} — {self.quiz.title} [{self.status}]"

    def calculate_score(self):
        """Calculate and persist score after submission."""
        responses = self.responses.select_related('question').prefetch_related('selected_choices')
        total = sum(r.question.points for r in responses)
        earned = 0

        for response in responses:
            question = response.question
            if question.question_type == 'short_answer':
                if response.is_correct:
                    earned += question.points
            else:
                correct_ids = set(question.correct_answers.values_list('id', flat=True))
                selected_ids = set(response.selected_choices.values_list('id', flat=True))
                if correct_ids == selected_ids:
                    earned += question.points

        self.total_points = total
        self.earned_points = earned
        self.score = round((earned / total) * 100, 2) if total else 0
        self.passed = self.score >= self.quiz.pass_percentage
        self.save(update_fields=['total_points', 'earned_points', 'score', 'passed'])
        return self.score


class QuestionResponse(models.Model):
    """A student's answer to one question in an attempt."""
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choices = models.ManyToManyField(Choice, blank=True)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = ('attempt', 'question')
