"""
Qrious Tech Academy — Main URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


from rest_framework.routers import DefaultRouter
from accounts_app.api_views import (
    UserViewSet, UserProfileViewSet, SubscriptionViewSet,
    StudentEnrollmentViewSet, StudentPaymentViewSet,
    CourseModuleViewSet, CourseLessonViewSet,
    NotificationViewSet, LiveClassScheduleViewSet
)
from dashboard.views import (
    JobApplicationViewSet, AgentRunViewSet,
    LinkedInAccountViewSet, ResumeViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='userprofile')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'enrollments', StudentEnrollmentViewSet, basename='studentenrollment')
router.register(r'payments', StudentPaymentViewSet, basename='studentpayment')
router.register(r'modules', CourseModuleViewSet, basename='coursemodule')
router.register(r'lessons', CourseLessonViewSet, basename='courselesson')
router.register(r'user-notifications', NotificationViewSet, basename='usernotification')
router.register(r'live-sessions', LiveClassScheduleViewSet, basename='liveclasssession')

# Dashboard & Agent ViewSets
router.register(r'job-applications', JobApplicationViewSet, basename='jobapplication')
router.register(r'agent-runs', AgentRunViewSet, basename='agentrun')
router.register(r'linkedin-accounts', LinkedInAccountViewSet, basename='linkedinaccount')
router.register(r'resumes', ResumeViewSet, basename='resume')


def logout_view(request):
    auth_logout(request)
    return redirect('/')

def smart_login_redirect(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect('/auth/login/')
    if request.user.is_superuser:
        return redirect('/superadmin/')
    from accounts_app.models import StudentEnrollment
    if StudentEnrollment.objects.filter(user=request.user).exists():
        return redirect('/student/dashboard/')
    return redirect('/student/dashboard/')

from accounts_app import views as accounts_views

urlpatterns = [
    # Master Super Admin Console & Custom Management Routes (Must be before Django admin catch-all)
    path('superadmin/', accounts_views.superadmin_master_dashboard, name='superadmin_dashboard'),
    path('superadmin/users/', accounts_views.superadmin_users_list, name='superadmin_users_list'),
    path('admin-users/', accounts_views.superadmin_users_list, name='admin_users'),
    path('admin-users/<int:user_id>/delete/', accounts_views.superadmin_delete_user, name='superadmin_delete_user'),
    path('superadmin/users/<int:user_id>/delete/', accounts_views.superadmin_delete_user),
    path('admin-users/<int:user_id>/toggle-contact/', accounts_views.toggle_user_contact, name='toggle_user_contact'),
    path('superadmin/users/<int:user_id>/toggle-contact/', accounts_views.toggle_user_contact),
    path('admin-users/export/csv/', accounts_views.export_users_csv, name='export_users_csv'),
    path('admin-users/export/pdf/', accounts_views.export_users_pdf, name='export_users_pdf'),
    path('superadmin/users/export/csv/', accounts_views.export_users_csv),
    path('superadmin/users/export/pdf/', accounts_views.export_users_pdf),
    path('admin-bookings/', accounts_views.superadmin_bookings_list, name='admin_bookings'),
    path('superadmin/bookings/', accounts_views.superadmin_bookings_list, name='superadmin_bookings_list'),
    path('admin-bookings/<int:booking_id>/delete/', accounts_views.superadmin_delete_booking, name='superadmin_delete_booking'),
    path('superadmin/bookings/<int:booking_id>/delete/', accounts_views.superadmin_delete_booking),
    path('admin-bookings/export/csv/', accounts_views.export_bookings_csv, name='export_bookings_csv'),
    path('admin-bookings/export/pdf/', accounts_views.export_bookings_pdf, name='export_bookings_pdf'),
    path('superadmin/bookings/export/csv/', accounts_views.export_bookings_csv),
    path('superadmin/bookings/export/pdf/', accounts_views.export_bookings_pdf),

    # All Student Payments & Proof Verifications Routes
    path('admin-payments/', accounts_views.superadmin_payments_list, name='admin_payments'),
    path('superadmin/payments/', accounts_views.superadmin_payments_list, name='superadmin_payments_list'),
    path('admin-payments/export/csv/', accounts_views.export_payments_csv, name='export_payments_csv'),
    path('superadmin/payments/export/csv/', accounts_views.export_payments_csv),
    path('superadmin/student/create/', accounts_views.admin_create_student_user, name='admin_create_student_user'),
    path('superadmin/student/enroll/', accounts_views.admin_enroll_student, name='admin_enroll_student'),
    path('superadmin/student/<int:enrollment_id>/profile/', accounts_views.admin_student_profile, name='admin_student_profile'),
    path('superadmin/student/<int:enrollment_id>/update/', accounts_views.admin_update_student, name='admin_update_student'),
    path('superadmin/booking/<int:booking_id>/status/', accounts_views.admin_update_booking_status, name='admin_update_booking'),

    # Super Admin Live Class Schedule & Meeting Link Management
    path('superadmin/live-classes/', accounts_views.admin_manage_live_classes, name='admin_manage_live_classes'),
    path('admin-live-classes/', accounts_views.admin_manage_live_classes),

    # Aliases for admin/ student routes
    path('admin/student/create/', accounts_views.admin_create_student_user),
    path('admin/student/enroll/', accounts_views.admin_enroll_student),
    path('admin/student/<int:enrollment_id>/profile/', accounts_views.admin_student_profile),
    path('admin/student/<int:enrollment_id>/update/', accounts_views.admin_update_student),
    path('admin/booking/<int:booking_id>/status/', accounts_views.admin_update_booking_status),

    # Built-in Django Admin
    path('admin/', admin.site.urls),

    # Public Certificate & Verification System (Clean Root URLs without /billing/)
    path('verify-certificate/', accounts_views.verify_certificate, name='verify_certificate'),
    path('verify-certificate/<str:cert_id>/', accounts_views.verify_certificate, name='verify_certificate_id'),
    path('certificate/<str:cert_id>/', accounts_views.certificate_detail, name='certificate_detail'),

    # Invoice & PDF Download & Payment Submission System
    path('invoice/<str:invoice_id>/', accounts_views.view_invoice_detail, name='view_invoice_detail'),
    path('invoice/<str:invoice_id>/pdf/', accounts_views.download_invoice_pdf, name='download_invoice_pdf'),
    path('student/upload-payment/', accounts_views.student_upload_payment, name='student_upload_payment'),
    path('superadmin/payment/<int:payment_id>/verify/', accounts_views.superadmin_verify_payment, name='superadmin_verify_payment'),
    path('superadmin/assignments/', accounts_views.admin_manage_assignments, name='admin_manage_assignments'),
    path('student/assignments/', accounts_views.student_assignments_portal, name='student_assignments_portal'),
    path('student/assignments/submit/', accounts_views.student_submit_assignment, name='student_submit_assignment'),
    path('student/assignments/<int:submission_id>/card/', accounts_views.download_grade_card, name='download_grade_card'),
    path('student/invoices/', accounts_views.student_invoices_portal, name='student_invoices_portal'),
    path('student/payment/<int:payment_id>/delete/', accounts_views.student_delete_payment, name='student_delete_payment'),

    # Student Portal (Clean Root URLs without /billing/)
    path('student/dashboard/', accounts_views.student_dashboard, name='student_dashboard'),
    path('student/courses/', accounts_views.student_dashboard, name='student_courses'),
    path('student/classroom/', accounts_views.student_classroom, name='student_classroom'),
    path('student/classroom/lesson/<int:lesson_id>/', accounts_views.student_classroom, name='student_classroom_lesson'),
    path('student/classroom/toggle/<int:lesson_id>/', accounts_views.toggle_lesson_completion, name='toggle_lesson_completion'),
    path('student/classroom/admin/', accounts_views.admin_manage_modules, name='admin_manage_modules'),
    path('settings/', accounts_views.profile_settings, name='profile_settings'),

    # Real-Time Notification System APIs & Hub
    path('notifications/', accounts_views.notifications_hub_view, name='notifications_hub'),
    path('api/notifications/', accounts_views.notifications_api_list, name='notifications_api_list'),
    path('api/notifications/<int:notification_id>/read/', accounts_views.notifications_api_read, name='notifications_api_read'),
    path('api/notifications/read-all/', accounts_views.notifications_api_read_all, name='notifications_api_read_all'),
    path('api/notifications/<int:notification_id>/delete/', accounts_views.notifications_api_delete, name='notifications_api_delete'),

    # JWT Authentication REST API Endpoints
    path('api/jwt/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/jwt/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/jwt/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Landing & Public pages (Must match root / first)
    path('', include('landing.urls')),

    # REST Framework ModelViewSet Router Endpoints
    path('api/v1/', include(router.urls)),

    # Shortcuts
    path('logout/', logout_view),
    path('login/', lambda request: redirect('/auth/login/')),
    path('signup/', lambda request: redirect('/auth/signup/')),

    # Authentication (AllAuth)
    path('auth/redirect/', smart_login_redirect),
    path('auth/', include('allauth.urls')),

    # Legacy Dashboard & Billing Redirection (Removed legacy job/LinkedIn pages & APIs)
    path('billing/', smart_login_redirect),
    path('billing/<path:subpath>', smart_login_redirect),
    path('dashboard/', smart_login_redirect),
    path('dashboard/<path:subpath>', smart_login_redirect),
]

# Serve media in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
