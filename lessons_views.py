"""
Serializers and Views for Lessons app.
"""
# ── serializers ──────────────────────────────────────────────────────────────
from rest_framework import serializers, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.courses.models import Enrollment
from apps.courses.permissions import IsInstructorOrReadOnly, IsEnrolledOrInstructor
from .models import Lesson, LessonAttachment, VideoUploadRequest


class LessonAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonAttachment
        fields = ['id', 'title', 'file', 'file_size', 'created_at']


class LessonListSerializer(serializers.ModelSerializer):
    """Lightweight — no signed URL to keep list fast."""
    duration_formatted = serializers.CharField(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'lesson_type', 'order', 'duration_seconds',
            'duration_formatted', 'is_free_preview', 'is_published',
        ]


class LessonDetailSerializer(serializers.ModelSerializer):
    """Full detail — includes signed video URL (short-lived)."""
    duration_formatted = serializers.CharField(read_only=True)
    video_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    attachments = LessonAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'section', 'title', 'lesson_type', 'order', 'description',
            'content', 'duration_seconds', 'duration_formatted',
            'is_free_preview', 'is_published',
            'video_url', 'thumbnail_url', 'external_video_url',
            'attachments', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_video_url(self, obj: Lesson) -> str:
        """
        Return a signed S3 URL valid for 1 hour.
        Signed URLs are generated server-side; the client never sees
        the raw S3 key or bucket credentials.
        """
        return obj.generate_signed_video_url()

    def get_thumbnail_url(self, obj: Lesson) -> str:
        return obj.generate_signed_thumbnail_url()


class VideoUploadRequestSerializer(serializers.ModelSerializer):
    """Returned to instructors when they request a pre-signed upload URL."""
    class Meta:
        model = VideoUploadRequest
        fields = ['upload_id', 's3_key', 'presigned_upload_url', 'expires_at']
        read_only_fields = fields


# ── views ─────────────────────────────────────────────────────────────────────

class LessonViewSet(ModelViewSet):
    """
    Lessons nested under /<course-slug>/sections/<section-id>/lessons/.
    - Instructors: full CRUD.
    - Enrolled students: GET only (signed URL included in detail).
    - Free preview lessons: publicly readable.
    """
    permission_classes = [IsInstructorOrReadOnly]

    def get_queryset(self):
        return Lesson.objects.filter(
            section_id=self.kwargs['section_pk'],
            section__course__slug=self.kwargs['course_slug'],
        ).prefetch_related('attachments')

    def get_serializer_class(self):
        if self.action == 'list':
            return LessonListSerializer
        return LessonDetailSerializer

    def get_permissions(self):
        """
        Free-preview lessons are public.
        All other lessons require enrolment.
        """
        if self.action == 'retrieve':
            return [IsEnrolledOrFreePreview()]
        return super().get_permissions()

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def request_upload_url(self, request, **kwargs):
        """
        Instructor requests a pre-signed S3 PUT URL to upload a video.
        The browser then PUTs the file directly to S3 — no bandwidth cost to Django.
        """
        lesson = self.get_object()
        if lesson.section.course.instructor != request.user and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)

        upload_req = VideoUploadRequest.create_for_lesson(lesson)
        return Response(VideoUploadRequestSerializer(upload_req).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def confirm_upload(self, request, **kwargs):
        """
        Called after S3 PUT completes. Updates lesson with the new S3 key.
        """
        lesson = self.get_object()
        upload_req = getattr(lesson, 'upload_request', None)
        if not upload_req or upload_req.is_expired():
            return Response({'detail': 'Upload request invalid or expired.'}, status=400)

        lesson.video_s3_key = upload_req.s3_key
        lesson.save(update_fields=['video_s3_key'])
        upload_req.is_completed = True
        upload_req.save(update_fields=['is_completed'])

        return Response({'detail': 'Video confirmed.', 's3_key': lesson.video_s3_key})


# ── helper permission ──────────────────────────────────────────────────────────

from rest_framework.permissions import BasePermission


class IsEnrolledOrFreePreview(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.is_free_preview:
            return True
        if not request.user.is_authenticated:
            return False
        return Enrollment.objects.filter(
            student=request.user,
            course=obj.section.course,
            is_active=True,
        ).exists()
