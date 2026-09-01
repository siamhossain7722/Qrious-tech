from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.billing_home, name='home'),
    path('checkout/', views.create_checkout_session, name='checkout'),
    path('success/', views.checkout_success, name='success'),
    path('cancel/', views.cancel_subscription, name='cancel'),
    path('webhook/', views.stripe_webhook, name='webhook'),
    path('settings/', views.profile_settings, name='settings'),

    # Super Admin Management Suite
    path('admin/dashboard/', views.superadmin_master_dashboard, name='superadmin_dashboard'),
    path('admin/users/', views.admin_users_list, name='admin_users_list'),
    path('admin/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('admin/users/<int:user_id>/update-plan/', views.admin_update_user_plan, name='admin_update_user_plan'),
    path('admin/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),

    # Student & Course Management
    path('admin/student/create/', views.admin_create_student_user, name='admin_create_student_user'),
    path('admin/student/enroll/', views.admin_enroll_student, name='admin_enroll_student'),
    path('admin/student/<int:enrollment_id>/update/', views.admin_update_student, name='admin_update_student'),
    path('admin/booking/<int:booking_id>/status/', views.admin_update_booking_status, name='admin_update_booking'),

    # Student Portal & Certificates
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/courses/', views.student_courses, name='student_courses'),
    path('certificate/<str:cert_id>/', views.certificate_detail, name='certificate_detail'),
    path('verify-certificate/', views.verify_certificate, name='verify_certificate'),
    path('verify-certificate/<str:cert_id>/', views.verify_certificate, name='verify_certificate_id'),
]
