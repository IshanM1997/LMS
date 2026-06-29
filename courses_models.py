"""
Course models for LMS.
Uses Django's content-type framework to attach tags and reviews
to multiple model types generically.
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# Generic Tag (uses Content Type framework)
# ---------------------------------------------------------------------------

class Tag(models.Model):
    """A tag that can be attached to any model via GenericForeignKey."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TaggedItem(models.Model):
    """
    Through-model linking a Tag to any object via the Content Type framework.

    e.g.:
        ct = ContentType.objects.get_for_model(Course)
        TaggedItem.objects.create(tag=tag, content_type=ct, object_id=course.pk)
    """

    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='items')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        unique_together = ('tag', 'content_type', 'object_id')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.tag.name} → {self.content_type.model}:{self.object_id}"


# ---------------------------------------------------------------------------
# Generic Review (uses Content Type framework)
# ---------------------------------------------------------------------------

class Review(models.Model):
    """A rating & review that can be attached to any model."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)]
    )
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('author', 'content_type', 'object_id')
        indexes = [models.Index(fields=['content_type', 'object_id'])]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}★ by {self.author_id} on {self.content_type.model}:{self.object_id}"


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)   # e.g. FontAwesome class
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='children'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------

class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER = 'beginner', _('Beginner')
        INTERMEDIATE = 'intermediate', _('Intermediate')
        ADVANCED = 'advanced', _('Advanced')
        ALL = 'all', _('All Levels')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PUBLISHED = 'published', _('Published')
        ARCHIVED = 'archived', _('Archived')

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    subtitle = models.CharField(max_length=500, blank=True)
    description = models.TextField()
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses_taught',
        limit_choices_to={'role': 'instructor'},
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='courses'
    )
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.ALL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    thumbnail = models.ImageField(upload_to='course_thumbnails/', null=True, blank=True)
    preview_video_url = models.URLField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    language = models.CharField(max_length=10, default='en')
    what_you_will_learn = models.JSONField(default=list)
    requirements = models.JSONField(default=list)
    who_is_this_for = models.TextField(blank=True)
    is_free = models.BooleanField(default=False)
    certificate_enabled = models.BooleanField(default=True)
    enrollment_limit = models.PositiveIntegerField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Generic relations — enables Course to have tags and reviews
    tags = GenericRelation(TaggedItem)
    reviews = GenericRelation(Review)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'level']),
            models.Index(fields=['instructor']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def total_enrolled(self):
        return self.enrollments.filter(is_active=True).count()

    @property
    def average_rating(self):
        from django.db.models import Avg
        result = self.reviews.filter(is_approved=True).aggregate(Avg('rating'))
        return round(result['rating__avg'] or 0, 1)


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    payment_id = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ('student', 'course')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.email} → {self.course.title}"


# ---------------------------------------------------------------------------
# Section (grouping of lessons within a course)
# ---------------------------------------------------------------------------

class Section(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ('course', 'order')

    def __str__(self):
        return f"{self.course.title} › {self.title}"
