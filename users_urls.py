"""
URL patterns for Users app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, MeView, ChangePasswordView, UserViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='user-register'),
    path('me/', MeView.as_view(), name='user-me'),
    path('me/change-password/', ChangePasswordView.as_view(), name='user-change-password'),
    path('', include(router.urls)),
]
