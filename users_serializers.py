"""
Serializers for Users app.
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import UserProfile

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        exclude = ['user']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name',
                  'password', 'password_confirm', 'role']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user)
        return user


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name',
                  'full_name', 'role', 'bio', 'avatar', 'is_email_verified',
                  'created_at', 'profile']
        read_only_fields = ['id', 'is_email_verified', 'created_at']

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserUpdateSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'bio', 'avatar',
                  'phone', 'date_of_birth', 'profile']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data and hasattr(instance, 'profile'):
            for attr, value in profile_data.items():
                setattr(instance.profile, attr, value)
            instance.profile.save()

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password': 'Passwords do not match.'})
        return attrs
