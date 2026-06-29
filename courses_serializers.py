"""
Serializers for Courses app.
"""
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from .models import Category, Course, Section, Enrollment, Tag, TaggedItem, Review


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'author', 'author_name', 'rating', 'title', 'body',
                  'is_approved', 'created_at']
        read_only_fields = ['author', 'is_approved', 'created_at']

    def get_author_name(self, obj):
        return obj.author.get_full_name()

    def create(self, validated_data):
        view = self.context['view']
        course = view.get_object()
        ct = ContentType.objects.get_for_model(Course)
        validated_data['content_type'] = ct
        validated_data['object_id'] = course.pk
        validated_data['author'] = self.context['request'].user
        return Review.objects.create(**validated_data)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'parent']


class SectionSerializer(serializers.ModelSerializer):
    lesson_count = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = ['id', 'title', 'description', 'order', 'lesson_count']

    def get_lesson_count(self, obj):
        return obj.lessons.count()


class CourseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for course listings."""
    instructor_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    total_enrolled = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'subtitle', 'thumbnail',
            'instructor_name', 'category_name', 'level', 'status',
            'effective_price', 'is_free', 'total_enrolled', 'average_rating',
            'language', 'certificate_enabled', 'created_at',
        ]

    def get_instructor_name(self, obj):
        return obj.instructor.get_full_name()

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None


class CourseDetailSerializer(serializers.ModelSerializer):
    """Full serializer for course detail view."""
    sections = SectionSerializer(many=True, read_only=True)
    instructor_name = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    reviews = ReviewSerializer(many=True, read_only=True, source='reviews.all')
    total_enrolled = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'subtitle', 'description',
            'instructor', 'instructor_name', 'category', 'level', 'status',
            'thumbnail', 'preview_video_url', 'price', 'discount_price',
            'effective_price', 'is_free', 'language', 'what_you_will_learn',
            'requirements', 'who_is_this_for', 'certificate_enabled',
            'enrollment_limit', 'published_at', 'created_at',
            'sections', 'tags', 'reviews', 'total_enrolled', 'average_rating',
            'is_enrolled',
        ]
        read_only_fields = ['slug', 'created_at', 'published_at']

    def get_instructor_name(self, obj):
        return obj.instructor.get_full_name()

    def get_tags(self, obj):
        tag_ids = obj.tags.values_list('tag_id', flat=True)
        tags = Tag.objects.filter(pk__in=tag_ids)
        return TagSerializer(tags, many=True).data

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.enrollments.filter(student=request.user, is_active=True).exists()
        return False


class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_thumbnail = serializers.ImageField(source='course.thumbnail', read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'course_title', 'course_thumbnail',
                  'enrolled_at', 'is_active', 'completed_at']
        read_only_fields = ['enrolled_at', 'completed_at']
