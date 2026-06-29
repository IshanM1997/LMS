"""
Views for Courses app.
"""
from django.utils import timezone
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Course, Section, Enrollment
from .serializers import (
    CategorySerializer,
    CourseListSerializer,
    CourseDetailSerializer,
    SectionSerializer,
    EnrollmentSerializer,
    ReviewSerializer,
)
from .permissions import IsInstructorOrReadOnly, IsEnrolledOrInstructor


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsInstructorOrReadOnly]
    lookup_field = 'slug'


class CourseViewSet(ModelViewSet):
    """
    Full CRUD for courses.
    - list / retrieve: public (published only for non-staff)
    - create / update / delete: instructor who owns the course or admin
    """
    permission_classes = [IsInstructorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['level', 'status', 'category', 'language', 'is_free']
    search_fields = ['title', 'subtitle', 'description', 'instructor__first_name']
    ordering_fields = ['created_at', 'price', 'total_enrolled']
    lookup_field = 'slug'

    def get_queryset(self):
        qs = Course.objects.select_related('instructor', 'category').prefetch_related(
            'sections', 'enrollments'
        )
        if not self.request.user.is_staff:
            qs = qs.filter(status=Course.Status.PUBLISHED)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        return CourseDetailSerializer

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def enroll(self, request, slug=None):
        """Enroll the current user in this course."""
        course = self.get_object()
        if Enrollment.objects.filter(student=request.user, course=course).exists():
            return Response({'detail': 'Already enrolled.'}, status=status.HTTP_400_BAD_REQUEST)
        enrollment = Enrollment.objects.create(student=request.user, course=course)
        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def publish(self, request, slug=None):
        """Publish a draft course (instructor/admin only)."""
        course = self.get_object()
        if course.instructor != request.user and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        course.status = Course.Status.PUBLISHED
        course.published_at = timezone.now()
        course.save()
        return Response({'detail': 'Course published.'})

    @action(detail=True, methods=['get', 'post'],
            permission_classes=[permissions.IsAuthenticated])
    def reviews(self, request, slug=None):
        """List or create reviews for a course."""
        course = self.get_object()
        if request.method == 'GET':
            qs = course.reviews.filter(is_approved=True)
            serializer = ReviewSerializer(qs, many=True)
            return Response(serializer.data)
        serializer = ReviewSerializer(data=request.data, context={'request': request, 'view': self})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SectionViewSet(ModelViewSet):
    serializer_class = SectionSerializer
    permission_classes = [IsInstructorOrReadOnly]

    def get_queryset(self):
        return Section.objects.filter(course__slug=self.kwargs['course_slug'])

    def perform_create(self, serializer):
        course = Course.objects.get(slug=self.kwargs['course_slug'])
        serializer.save(course=course)


class EnrollmentListView(generics.ListAPIView):
    """My enrollments."""
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Enrollment.objects.filter(
            student=self.request.user, is_active=True
        ).select_related('course')
