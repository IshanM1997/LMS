"""
Custom User model and related models for LMS.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Extended user model with LMS-specific fields."""

    class Role(models.TextChoices):
        STUDENT = 'student', _('Student')
        INSTRUCTOR = 'instructor', _('Instructor')
        ADMIN = 'admin', _('Admin')

    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT


class UserProfile(models.Model):
    """Extended profile data for users."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    website = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    twitter = models.CharField(max_length=50, blank=True)
    headline = models.CharField(max_length=200, blank=True)
    expertise = models.JSONField(default=list, blank=True)
    preferred_language = models.CharField(max_length=10, default='en')
    timezone = models.CharField(max_length=50, default='UTC')
    newsletter_subscribed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.email}"
