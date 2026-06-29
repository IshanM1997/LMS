"""
Lesson models for LMS.
Covers video streaming with AWS S3 signed URLs.
"""
import uuid
import boto3
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def video_upload_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1]
    return f"videos/{instance.section.course.slug}/{uuid.uuid4()}.{ext}"


class Lesson(models.Model):
    class LessonType(models.TextChoices):
        VIDEO = 'video', _('Video')
        TEXT = 'text', _('Text / Article')
        QUIZ = 'quiz', _('Quiz')
        ASSIGNMENT = 'assignment', _('Assignment')

    section = models.ForeignKey(
        'courses.Section', on_delete=models.CASCADE, related_name='lessons'
    )
    title = models.CharField(max_length=255)
    lesson_type = models.CharField(max_length=20, choices=LessonType.choices, default=LessonType.VIDEO)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    content = models.TextField(blank=True, help_text='Rich text content for text lessons')
    duration_seconds = models.PositiveIntegerField(default=0, help_text='Duration in seconds')
    is_free_preview = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)

    # S3 key for the stored video file (NOT a public URL)
    video_s3_key = models.CharField(max_length=500, blank=True)

    # Thumbnail stored in S3
    thumbnail_s3_key = models.CharField(max_length=500, blank=True)

    # External video (e.g. YouTube embed) — used when no S3 key
    external_video_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ('section', 'order')

    def __str__(self):
        return f"{self.section.course.title} › {self.section.title} › {self.title}"

    @property
    def duration_formatted(self):
        """Return HH:MM:SS string."""
        h, rem = divmod(self.duration_seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def generate_signed_video_url(self, expiry_seconds: int | None = None) -> str:
        """
        Generate a time-limited, signed S3 URL for the video.
        The URL expires after `expiry_seconds` (defaults to settings.AWS_SIGNED_URL_EXPIRY).

        Using signed URLs means:
        - The S3 bucket remains PRIVATE (no public access).
        - Clients cannot share or scrape a permanent link.
        - Each request re-validates enrolment server-side before issuing a new URL.
        """
        if not self.video_s3_key:
            return self.external_video_url

        expiry = expiry_seconds or getattr(settings, 'AWS_SIGNED_URL_EXPIRY', 3600)

        s3_client = boto3.client(
            's3',
            region_name=settings.AWS_S3_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': self.video_s3_key,
            },
            ExpiresIn=expiry,
        )
        return url

    def generate_signed_thumbnail_url(self, expiry_seconds: int | None = None) -> str:
        if not self.thumbnail_s3_key:
            return ''
        expiry = expiry_seconds or 86400  # thumbnails last longer
        s3_client = boto3.client(
            's3',
            region_name=settings.AWS_S3_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        return s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': self.thumbnail_s3_key},
            ExpiresIn=expiry,
        )


class VideoUploadRequest(models.Model):
    """
    Represents a pre-signed S3 PUT URL issued to an instructor
    so they can upload a video directly from the browser to S3
    without routing through the Django server.
    """
    lesson = models.OneToOneField(
        Lesson, on_delete=models.CASCADE,
        related_name='upload_request', null=True, blank=True
    )
    upload_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    s3_key = models.CharField(max_length=500)
    presigned_upload_url = models.URLField(max_length=2000)
    expires_at = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    @classmethod
    def create_for_lesson(cls, lesson: Lesson, content_type: str = 'video/mp4') -> 'VideoUploadRequest':
        """
        Issue a pre-signed S3 PUT URL so the browser can upload
        the video file directly to S3.
        """
        s3_key = f"videos/{lesson.section.course.slug}/{uuid.uuid4()}.mp4"
        expiry = 3600  # 1 hour to complete upload

        s3_client = boto3.client(
            's3',
            region_name=settings.AWS_S3_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': s3_key,
                'ContentType': content_type,
            },
            ExpiresIn=expiry,
        )

        return cls.objects.create(
            lesson=lesson,
            s3_key=s3_key,
            presigned_upload_url=presigned_url,
            expires_at=timezone.now() + timedelta(seconds=expiry),
        )


class LessonAttachment(models.Model):
    """Downloadable file attached to a lesson (PDFs, source code, etc.)."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='attachments')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='lesson_attachments/')
    file_size = models.PositiveBigIntegerField(default=0)  # bytes
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lesson.title} — {self.title}"
