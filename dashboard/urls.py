from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # Dashboard home
    path("", views.dashboard, name="dashboard"),

    # Job management
    path("job/<int:pk>/", views.job_detail, name="job_detail"),
    path("job/<int:pk>/update-status/", views.update_job_status, name="update_job_status"),
    path("job/<int:pk>/delete/", views.delete_job, name="delete_job"),

    # Agent control
    path("run-agent/", views.run_agent, name="run_agent"),
    path("run-status/<int:run_id>/", views.run_status, name="run_status"),
    path("api/stats/", views.api_stats, name="api_stats"),

    # LinkedIn Accounts
    path("accounts/", views.accounts_page, name="accounts"),
    path("accounts/add/", views.add_account, name="add_account"),
    path("accounts/<int:pk>/delete/", views.delete_account, name="delete_account"),
    path("accounts/<int:pk>/sync/", views.sync_profile, name="sync_profile"),
    path("accounts/<int:pk>/open-login/", views.open_login, name="open_login"),
    path("accounts/<int:pk>/edit/", views.edit_account, name="edit_account"),
    path("accounts/<int:pk>/status/", views.account_status, name="account_status"),
    path("accounts/<int:pk>/profile/", views.account_profile, name="account_profile"),

    # Resumes
    path("resumes/upload/", views.upload_resume, name="upload_resume"),
    path("resumes/<int:pk>/activate/", views.set_active_resume, name="activate_resume"),
    path("resumes/<int:pk>/delete/", views.delete_resume, name="delete_resume"),
]
