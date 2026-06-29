"""
Progress tracking models and views for LMS.
"""
from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from rest_framework import serializers, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView


# ── Models ─────────────────────────────────────────────────────────────────────

class LessonProgress(models.Model):
    """Tracks a student's progress through individual lessons."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_progress',
    )
    lesson = models.ForeignKey(
        'lessons.Lesson',
        on_delete=models.CASCADE,
        related_name='progress_records',
    )
    is_completed = models.BooleanField(default=False)
    watch_time_seconds = models.PositiveIntegerField(default=0)
    last_position_seconds = models.PositiveIntegerField(default=0, help_text='Playback resume point')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'lesson')
        ordering = ['-updated_at']

    def __str__(self):
        status = 'completed' if self.is_completed else 'in progress'
        return f"{self.student.email} — {self.lesson.title} [{status}]"


class CourseProgress(models.Model):
    """
    Aggregate progress for a student's enrolment in a course.
    Recomputed whenever a LessonProgress is saved.
    """
    enrollment = models.OneToOneField(
        'courses.Enrollment',
        on_delete=models.CASCADE,
        related_name='progress',
    )
    total_lessons = models.PositiveIntegerField(default=0)
    completed_lessons = models.PositiveIntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_accessed_lesson = models.ForeignKey(
        'lessons.Lesson', null=True, blank=True, on_delete=models.SET_NULL
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.enrollment} — {self.percentage}%"

    def recompute(self):
        """Recalculate progress from LessonProgress records."""
        from apps.lessons.models import Lesson
        course = self.enrollment.course
        student = self.enrollment.student

        total = Lesson.objects.filter(
            section__course=course, is_published=True
        ).count()

        completed = LessonProgress.objects.filter(
            student=student,
            lesson__section__course=course,
            is_completed=True,
        ).count()

        self.total_lessons = total
        self.completed_lessons = completed
        self.percentage = round((completed / total) * 100, 2) if total else 0
        self.save(update_fields=['total_lessons', 'completed_lessons', 'percentage', 'updated_at'])

        # Trigger certificate if 100%
        if self.percentage >= 100:
            self._trigger_certificate()

    def _trigger_certificate(self):
        from apps.certificates.tasks import generate_certificate
        generate_certificate.delay(self.enrollment.id)


# ── Serializers ────────────────────────────────────────────────────────────────

class LessonProgressSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)

    class Meta:
        model = LessonProgress
        fields = ['id', 'lesson', 'lesson_title', 'is_completed',
                  'watch_time_seconds', 'last_position_seconds',
                  'completed_at', 'updated_at']
        read_only_fields = ['completed_at', 'updated_at']


class CourseProgressSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='enrollment.course.title', read_only=True)
    course_slug = serializers.CharField(source='enrollment.course.slug', read_only=True)

    class Meta:
        model = CourseProgress
        fields = ['id', 'course_title', 'course_slug', 'total_lessons',
                  'completed_lessons', 'percentage', 'last_accessed_lesson', 'updated_at']


# ── Views ──────────────────────────────────────────────────────────────────────

class UpdateLessonProgressView(generics.UpdateAPIView):
    """PATCH /api/v1/progress/lessons/<lesson_id>/ — update watch time / mark complete."""
    serializer_class = LessonProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj, _ = LessonProgress.objects.get_or_create(
            student=self.request.user,
            lesson_id=self.kwargs['lesson_id'],
        )
        return obj

    def perform_update(self, serializer):
        from django.utils import timezone
        instance = serializer.instance
        data = serializer.validated_data

        if data.get('is_completed') and not instance.is_completed:
            data['completed_at'] = timezone.now()

        serializer.save(**data)

        # Recompute course-level progress
        from apps.courses.models import Enrollment
        enrollment = Enrollment.objects.filter(
            student=self.request.user,
            course=instance.lesson.section.course,
        ).first()
        if enrollment and hasattr(enrollment, 'progress'):
            enrollment.progress.recompute()


class MyCourseProgressView(generics.ListAPIView):
    """GET /api/v1/progress/courses/ — list progress for all enrolled courses."""
    serializer_class = CourseProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CourseProgress.objects.filter(
            enrollment__student=self.request.user,
            enrollment__is_active=True,
        ).select_related('enrollment__course')


class CourseLessonProgressView(generics.ListAPIView):
    """GET /api/v1/progress/courses/<course_slug>/lessons/ — lesson-level progress."""
    serializer_class = LessonProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LessonProgress.objects.filter(
            student=self.request.user,
            lesson__section__course__slug=self.kwargs['course_slug'],
        ).select_related('lesson')
