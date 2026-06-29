"""
URL patterns for Courses app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, CourseViewSet, SectionViewSet, EnrollmentListView

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'', CourseViewSet, basename='course')

section_router = DefaultRouter()
section_router.register(r'sections', SectionViewSet, basename='section')

urlpatterns = [
    path('', include(router.urls)),
    path('<slug:course_slug>/', include(section_router.urls)),
    path('enrollments/my/', EnrollmentListView.as_view(), name='my-enrollments'),
]
