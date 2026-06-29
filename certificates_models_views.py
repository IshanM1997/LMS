"""
Certificate models, Celery task, and views for LMS.
"""
import uuid
import os
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework import serializers, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from celery import shared_task


# ── Model ──────────────────────────────────────────────────────────────────────

class Certificate(models.Model):
    """Issued certificate for a completed course."""

    certificate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificates',
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='certificates',
    )
    enrollment = models.OneToOneField(
        'courses.Enrollment',
        on_delete=models.CASCADE,
        related_name='certificate',
    )
    issued_at = models.DateTimeField(default=timezone.now)

    # The generated PDF is stored in S3
    pdf_s3_key = models.CharField(max_length=500, blank=True)

    # Optional: HTML snapshot or verification URL
    verification_url = models.URLField(blank=True)

    class Meta:
        unique_together = ('student', 'course')
        ordering = ['-issued_at']

    def __str__(self):
        return f"Certificate {self.certificate_id} — {self.student.email} [{self.course.title}]"

    def get_download_url(self, expiry_seconds: int = 3600) -> str:
        """Return a signed S3 URL for the certificate PDF."""
        if not self.pdf_s3_key:
            return ''
        import boto3
        client = boto3.client(
            's3',
            region_name=settings.AWS_S3_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        return client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': self.pdf_s3_key},
            ExpiresIn=expiry_seconds,
        )


# ── Celery task ─────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def generate_certificate(self, enrollment_id: int):
    """
    Celery task: generate a PDF certificate and upload it to S3.
    Triggered automatically when CourseProgress.percentage reaches 100.
    """
    from apps.courses.models import Enrollment

    try:
        enrollment = Enrollment.objects.select_related('student', 'course').get(pk=enrollment_id)
    except Enrollment.DoesNotExist:
        return

    # Idempotent: skip if already issued
    if Certificate.objects.filter(enrollment=enrollment).exists():
        return

    pdf_bytes = _render_certificate_pdf(enrollment)
    s3_key = f"certificates/{enrollment.course.slug}/{enrollment.student.id}/{uuid.uuid4()}.pdf"

    _upload_to_s3(pdf_bytes, s3_key)

    cert = Certificate.objects.create(
        student=enrollment.student,
        course=enrollment.course,
        enrollment=enrollment,
        pdf_s3_key=s3_key,
        verification_url=f"{settings.FRONTEND_URL}/verify/{uuid.uuid4()}",
    )

    _send_certificate_email(cert)
    return str(cert.certificate_id)


def _render_certificate_pdf(enrollment) -> bytes:
    """
    Render a PDF certificate using ReportLab.
    In production, replace with a branded template using WeasyPrint or similar.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import landscape, A4

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(A4))
        width, height = landscape(A4)

        c.setFont('Helvetica-Bold', 36)
        c.drawCentredString(width / 2, height - 150, 'Certificate of Completion')

        c.setFont('Helvetica', 18)
        c.drawCentredString(width / 2, height - 220, 'This certifies that')

        c.setFont('Helvetica-Bold', 24)
        c.drawCentredString(width / 2, height - 270, enrollment.student.get_full_name())

        c.setFont('Helvetica', 18)
        c.drawCentredString(width / 2, height - 320, 'has successfully completed')

        c.setFont('Helvetica-Bold', 22)
        c.drawCentredString(width / 2, height - 370, enrollment.course.title)

        c.setFont('Helvetica', 14)
        c.drawCentredString(
            width / 2, height - 430,
            f"Issued on {timezone.now().strftime('%B %d, %Y')}"
        )

        c.save()
        return buffer.getvalue()
    except ImportError:
        # reportlab not installed — return placeholder bytes
        return b'%PDF-placeholder'


def _upload_to_s3(pdf_bytes: bytes, s3_key: str):
    import boto3
    client = boto3.client(
        's3',
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    client.put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=s3_key,
        Body=pdf_bytes,
        ContentType='application/pdf',
    )


def _send_certificate_email(cert: Certificate):
    from django.core.mail import send_mail
    download_url = cert.get_download_url()
    send_mail(
        subject=f'Your certificate for {cert.course.title}',
        message=(
            f"Congratulations {cert.student.get_full_name()}!\n\n"
            f"You've completed {cert.course.title}.\n"
            f"Download your certificate here (link valid for 1 hour):\n{download_url}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[cert.student.email],
        fail_silently=True,
    )


# ── Serializers ────────────────────────────────────────────────────────────────

class CertificateSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    student_name = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = ['certificate_id', 'course', 'course_title', 'student_name',
                  'issued_at', 'download_url', 'verification_url']

    def get_student_name(self, obj):
        return obj.student.get_full_name()

    def get_download_url(self, obj):
        return obj.get_download_url()


# ── Views ──────────────────────────────────────────────────────────────────────

class MyCertificatesView(generics.ListAPIView):
    """GET /api/v1/certificates/ — list my certificates."""
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(
            student=self.request.user
        ).select_related('course')


class CertificateVerifyView(generics.RetrieveAPIView):
    """GET /api/v1/certificates/<certificate_id>/verify/ — public verification."""
    serializer_class = CertificateSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Certificate.objects.all()
    lookup_field = 'certificate_id'


class CertificateDownloadView(APIView):
    """GET /api/v1/certificates/<certificate_id>/download/ — signed PDF URL."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, certificate_id):
        try:
            cert = Certificate.objects.get(
                certificate_id=certificate_id,
                student=request.user,
            )
        except Certificate.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)

        url = cert.get_download_url()
        if not url:
            return Response({'detail': 'Certificate PDF not yet generated.'}, status=404)

        return Response({'download_url': url, 'expires_in': 3600})
