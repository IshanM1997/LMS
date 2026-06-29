"""
Custom permissions for Courses app.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsInstructorOrReadOnly(BasePermission):
    """
    - SAFE_METHODS (GET, HEAD, OPTIONS): allowed for everyone.
    - Mutations: allowed only for instructors or admins.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and (
            request.user.is_staff or getattr(request.user, 'role', '') == 'instructor'
        )

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        # Admin can do anything; instructor can only edit own course
        if request.user.is_staff:
            return True
        instructor = getattr(obj, 'instructor', None) or getattr(obj, 'course', None) and obj.course.instructor
        return instructor == request.user


class IsEnrolledOrInstructor(BasePermission):
    """Only enrolled students or the course instructor may access."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        course = getattr(obj, 'course', obj)
        if course.instructor == user:
            return True
        return course.enrollments.filter(student=user, is_active=True).exists()
