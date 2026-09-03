from rest_framework import viewsets, permissions, filters
from django.contrib.auth.models import User
from .models import (
    UserProfile, StudentEnrollment,
    StudentPayment, CourseModule, CourseLesson,
    Notification, LiveClassSchedule
)
from .serializers import (
    UserSerializer, UserProfileSerializer,
    StudentEnrollmentSerializer, StudentPaymentSerializer,
    CourseModuleSerializer, CourseLessonSerializer,
    NotificationSerializer, LiveClassScheduleSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """ModelViewSet for Django Users with prefetch_related for profile."""
    queryset = User.objects.all().prefetch_related('profile', 'enrollments').order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'username']


class UserProfileViewSet(viewsets.ModelViewSet):
    """ModelViewSet for UserProfile with select_related('user')."""
    queryset = UserProfile.objects.select_related('user').order_by('-created_at')
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__email', 'user__username', 'company', 'phone']

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            return qs.filter(user=self.request.user)
        return qs


class CourseModuleViewSet(viewsets.ModelViewSet):
    """ModelViewSet for CourseModule with prefetch_related('lessons')."""
    queryset = CourseModule.objects.all().prefetch_related('lessons').order_by('order')
    serializer_class = CourseModuleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class CourseLessonViewSet(viewsets.ModelViewSet):
    """ModelViewSet for CourseLesson with select_related('module')."""
    queryset = CourseLesson.objects.select_related('module').order_by('module__order', 'order')
    serializer_class = CourseLessonSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class StudentEnrollmentViewSet(viewsets.ModelViewSet):
    """ModelViewSet for StudentEnrollment with select_related('user') and prefetch_related('lesson_progresses')."""
    queryset = StudentEnrollment.objects.select_related('user').prefetch_related('lesson_progresses').order_by('-created_at')
    serializer_class = StudentEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            return qs.filter(user=self.request.user)
        return qs


class StudentPaymentViewSet(viewsets.ModelViewSet):
    """ModelViewSet for StudentPayment with select_related('user')."""
    queryset = StudentPayment.objects.select_related('user').order_by('-created_at')
    serializer_class = StudentPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            return qs.filter(user=self.request.user)
        return qs


class NotificationViewSet(viewsets.ModelViewSet):
    """ModelViewSet for Notifications with select_related('user')."""
    queryset = Notification.objects.select_related('user').order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class LiveClassScheduleViewSet(viewsets.ModelViewSet):
    """ModelViewSet for LiveClassSchedule with select_related('batch')."""
    queryset = LiveClassSchedule.objects.select_related('batch').order_by('-scheduled_at')
    serializer_class = LiveClassScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
