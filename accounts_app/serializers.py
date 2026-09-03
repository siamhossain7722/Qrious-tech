from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile, StudentEnrollment,
    StudentPayment, CourseModule, CourseLesson,
    Notification, LiveClassSchedule
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'date_joined']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'avatar', 'phone', 'company', 'bio', 'is_contacted', 'created_at']


class CourseLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseLesson
        fields = ['id', 'title', 'video_url', 'duration', 'order', 'description', 'created_at']


class CourseModuleSerializer(serializers.ModelSerializer):
    lessons = CourseLessonSerializer(many=True, read_only=True)

    class Meta:
        model = CourseModule
        fields = ['id', 'title', 'order', 'description', 'created_at', 'lessons']


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentEnrollment
        fields = [
            'id', 'user', 'student_id', 'course_name', 'batch',
            'progress_percent', 'is_completed', 'certificate_id',
            'created_at'
        ]


class StudentPaymentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentPayment
        fields = [
            'id', 'user', 'invoice_id', 'course_name', 'total_amount',
            'paid_amount', 'due_amount', 'status', 'payment_method',
            'transaction_id', 'created_at'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'title', 'message', 'notification_type', 'is_read', 'link_url', 'created_at']


class LiveClassScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveClassSchedule
        fields = ['id', 'title', 'batch', 'scheduled_at', 'meeting_link', 'duration', 'agenda', 'instructor_name', 'is_active', 'created_at']
