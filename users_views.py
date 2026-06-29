"""
Views for Users app.
"""
from django.contrib.auth import get_user_model
from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Public endpoint to register a new user."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the currently authenticated user."""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    """Change password for authenticated user."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': 'Wrong password.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'detail': 'Password updated successfully.'})


class UserViewSet(ModelViewSet):
    """Admin-facing ViewSet for managing all users."""
    queryset = User.objects.select_related('profile').all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    search_fields = ['email', 'username', 'first_name', 'last_name']
    filterset_fields = ['role', 'is_email_verified', 'is_active']
    ordering_fields = ['created_at', 'email']

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        return UserSerializer
