from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('job-agent/', views.job_agent_landing, name='job_agent'),
    path('ai-solutions/job-agent/', views.job_agent_landing, name='ai_job_agent'),
    path('about/', views.about_us, name='about'),
    path('contact/', views.contact_us, name='contact'),
    path('book-service/', views.book_service, name='book_service'),
    path('services/', views.services_overview, name='services'),
    path('courses/', views.courses_overview, name='courses'),
    path('courses/digital-marketing/', views.digital_marketing_detail, name='digital_marketing_detail'),
    path('courses/full-stack-web/', views.full_stack_web_detail, name='full_stack_web_detail'),
    path('courses/full-stack/', views.full_stack_web_detail, name='full_stack_web_detail_alias'),
    path('pricing/', views.pricing, name='pricing'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap_xml'),
    path('api/run-migrations-setup/', views.run_migrations_setup_view, name='run_migrations_setup'),
]
