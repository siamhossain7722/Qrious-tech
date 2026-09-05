import json
import asyncio
import threading
import os
from pathlib import Path
from datetime import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async

from .models import LinkedInAccount
from rest_framework import viewsets, permissions, serializers, filters


# ─── REST FRAMEWORK MODELVIEWSETS ─────────────────────────────────────────────

class LinkedInAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedInAccount
        fields = ['id', 'user', 'email', 'is_active', 'status', 'full_name', 'headline', 'location', 'profile_url', 'created_at', 'last_synced']

class LinkedInAccountViewSet(viewsets.ModelViewSet):
    """ModelViewSet for LinkedInAccount with select_related('user')."""
    queryset = LinkedInAccount.objects.select_related('user').order_by('-created_at')
    serializer_class = LinkedInAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            return qs.filter(user=self.request.user)
        return qs


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


@login_required
def dashboard(request):
    """Dashboard entry point — redirects to Student Dashboard or Super Admin Console."""
    if request.user.is_superuser:
        return redirect('/superadmin/')
    return redirect('/student/dashboard/')

    stats = {
        "total": jobs.count(),
        "applied": jobs.filter(status="applied").count(),
        "interview": jobs.filter(status="interview").count(),
        "offer": jobs.filter(status="offer").count(),
        "rejected": jobs.filter(status="rejected").count(),
        "dry_run": jobs.filter(status="dry_run").count(),
    }

    status_filter = request.GET.get("status", "")
    search_query = request.GET.get("q", "")
    date_filter = request.GET.get("date_range", "")
    match_filter = request.GET.get("match", "")

    if status_filter:
        jobs = jobs.filter(status=status_filter)
    if search_query:
        jobs = jobs.filter(Q(title__icontains=search_query) | Q(company__icontains=search_query))
    if date_filter == "today":
        today = timezone.now().date()
        jobs = jobs.filter(date_applied__date=today)
    elif date_filter == "past_7_days":
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        jobs = jobs.filter(date_applied__gte=seven_days_ago)
    elif date_filter == "this_month":
        now = timezone.now()
        jobs = jobs.filter(date_applied__year=now.year, date_applied__month=now.month)

    if match_filter == "70":
        jobs = jobs.filter(match_score__gte=70)

    jobs = jobs.order_by("-id")

    # Pagination: 10 jobs per page
    paginator = Paginator(jobs, 10)
    page_number = request.GET.get("page", 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Build query string preserving active filters (without 'page')
    query_dict = request.GET.copy()
    if "page" in query_dict:
        del query_dict["page"]
    query_string = query_dict.urlencode()

    can_apply, apply_reason = sub.can_apply()

    context = {
        "jobs": page_obj,
        "page_obj": page_obj,
        "paginator": paginator,
        "query_string": query_string,
        "runs": runs,
        "stats": stats,
        "status_filter": status_filter,
        "search_query": search_query,
        "date_filter": date_filter,
        "match_filter": match_filter,
        "status_choices": JobApplication.STATUS_CHOICES,
        "accounts": accounts,
        "active_resume": active_resume,
        "subscription": sub,
        "can_apply": can_apply,
        "apply_reason": apply_reason,
        "apps_remaining": sub.applications_remaining(),
    }
    return render(request, "dashboard/dashboard.html", context)


# ─── JOB MANAGEMENT ──────────────────────────────────────────────────────────

@login_required
def job_detail(request, pk):
    job = get_object_or_404(JobApplication, pk=pk, user=request.user)
    return render(request, "dashboard/job_detail.html", {"job": job})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def update_job_status(request, pk):
    job = get_object_or_404(JobApplication, pk=pk, user=request.user)
    data = json.loads(request.body)
    new_status = data.get("status")
    if new_status in [s[0] for s in JobApplication.STATUS_CHOICES]:
        job.status = new_status
        job.save()
        return JsonResponse({"success": True, "status": new_status})
    return JsonResponse({"success": False, "error": "Invalid status"}, status=400)


@csrf_exempt
@require_http_methods(["POST", "DELETE"])
@login_required
def delete_job(request, pk):
    """Delete a job application record from database."""
    job = get_object_or_404(JobApplication, pk=pk, user=request.user)
    job_title = job.title
    company_name = job.company
    job.delete()
    return JsonResponse({
        "success": True,
        "message": f"Successfully deleted '{job_title}' at '{company_name}'"
    })


# ─── AGENT RUN ────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
@login_required
@csrf_exempt
@require_http_methods(["POST"])
@login_required
def run_agent(request):
    """Trigger the LinkedIn agent — returns status."""
    return JsonResponse({
        "success": False,
        "message": "AI Agent automation engine is disabled.",
    }, status=400)


def _save_result_to_db(result: dict, user):
    job_id = result.get("job_id", "")
    defaults = {
        "title": result.get("title", ""),
        "company": result.get("company", ""),
        "url": result.get("url", ""),
        "status": result.get("status", "pending"),
        "notes": result.get("notes", ""),
        "user": user,
    }
    if job_id:
        JobApplication.objects.update_or_create(job_id=job_id, user=user, defaults=defaults)
    else:
        JobApplication.objects.create(**defaults)


@require_http_methods(["GET"])
@login_required
def run_status(request, run_id):
    run = get_object_or_404(AgentRun, id=run_id, user=request.user)
    return JsonResponse({
        "id": run.id,
        "status": run.status,
        "total_found": run.total_found,
        "total_applied": run.total_applied,
        "total_skipped": run.total_skipped,
        "total_failed": run.total_failed,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    })


@login_required
def api_stats(request):
    jobs = JobApplication.objects.filter(user=request.user)
    return JsonResponse({
        "total": jobs.count(),
        "applied": jobs.filter(status="applied").count(),
        "interview": jobs.filter(status="interview").count(),
        "offer": jobs.filter(status="offer").count(),
    })


# ─── LINKEDIN ACCOUNT MANAGEMENT ─────────────────────────────────────────────

@login_required
def accounts_page(request):
    """LinkedIn accounts management page."""
    sub = _get_subscription(request.user)
    accounts = LinkedInAccount.objects.filter(user=request.user)
    resumes = Resume.objects.filter(user=request.user)
    plan_limits = settings.PLAN_LIMITS.get(sub.plan, settings.PLAN_LIMITS['free'])
    return render(request, "dashboard/accounts.html", {
        "accounts": accounts,
        "resumes": resumes,
        "plan_limits": plan_limits,
        "subscription": sub,
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def add_account(request):
    sub = _get_subscription(request.user)
    plan_limits = settings.PLAN_LIMITS.get(sub.plan, settings.PLAN_LIMITS['free'])
    current_count = LinkedInAccount.objects.filter(user=request.user).count()

    if current_count >= plan_limits['linkedin_accounts']:
        return JsonResponse({
            "success": False,
            "error": f"Your {sub.plan} plan allows {plan_limits['linkedin_accounts']} LinkedIn account(s). Upgrade to add more.",
            "upgrade_required": True,
        }, status=403)

    data = json.loads(request.body)
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return JsonResponse({"success": False, "error": "Email and password are required."}, status=400)

    if LinkedInAccount.objects.filter(user=request.user, email=email).exists():
        return JsonResponse({"success": False, "error": "This account is already added."}, status=400)

    account = LinkedInAccount(email=email, user=request.user)
    account.password = password
    account.session_file = f"data/session_{request.user.id}_{email.replace('@','_').replace('.','_')}.json"
    account.save()

    return JsonResponse({"success": True, "account_id": account.id, "email": account.email,
                         "message": "Account added! Click 'Sync Profile' to read the LinkedIn profile."})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def delete_account(request, pk):
    account = get_object_or_404(LinkedInAccount, pk=pk, user=request.user)
    email = account.email
    if account.session_file and Path(account.session_file).exists():
        Path(account.session_file).unlink()
    account.delete()
    return JsonResponse({"success": True, "message": f"Account {email} deleted."})


@sync_to_async
def _async_save_account_status(account_id, status, session_file=None):
    try:
        acc = LinkedInAccount.objects.get(id=account_id)
        if status:
            acc.status = status
        if session_file:
            acc.session_file = session_file
        acc.last_synced = timezone.now()
        acc.save()
        return acc
    except Exception as e:
        print(f"Error saving account status async: {e}")
        return None

@sync_to_async
def _async_save_account_profile(account_id, profile):
    if not profile:
        return None
    try:
        acc = LinkedInAccount.objects.get(id=account_id)
        if profile.get("full_name") and profile.get("full_name") != "LinkedIn User":
            acc.full_name = profile.get("full_name")
        if profile.get("headline"):
            acc.headline = profile.get("headline")
        if profile.get("location"):
            acc.location = profile.get("location")
        if profile.get("about"):
            acc.about = profile.get("about")
        if profile.get("profile_url"):
            acc.profile_url = profile.get("profile_url")
        if profile.get("profile_photo_url"):
            acc.profile_photo_url = profile.get("profile_photo_url")
        if profile.get("connections"):
            acc.connections = profile.get("connections")
        if profile.get("skills"):
            acc.skills = json.dumps(profile.get("skills", []))
        if profile.get("experience"):
            acc.experience = json.dumps(profile.get("experience", []))
        if profile.get("education"):
            acc.education = json.dumps(profile.get("education", []))
        acc.status = "active"
        acc.last_synced = timezone.now()
        acc.save()
        return acc
    except Exception as e:
        print(f"Error saving account profile async: {e}")
        return None


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def sync_profile(request, pk):
    account = get_object_or_404(LinkedInAccount, pk=pk, user=request.user)
    return JsonResponse({"success": True, "message": "Profile sync status updated."})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def open_login(request, pk):
    account = get_object_or_404(LinkedInAccount, pk=pk, user=request.user)
    return JsonResponse({"success": True, "message": "Login status updated."})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def edit_account(request, pk):
    account = get_object_or_404(LinkedInAccount, pk=pk, user=request.user)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    account.full_name = data.get("full_name", account.full_name)
    account.headline = data.get("headline", account.headline)
    account.location = data.get("location", account.location)
    account.profile_url = data.get("profile_url", account.profile_url)
    
    skills_raw = data.get("skills", "")
    if isinstance(skills_raw, str):
        skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
    elif isinstance(skills_raw, list):
        skills_list = skills_raw
    else:
        skills_list = account.get_skills_list()
    account.skills = json.dumps(skills_list)

    status = data.get("status")
    if status in ["active", "inactive", "needs_verification", "syncing"]:
        account.status = status
    account.save()
    return JsonResponse({"success": True, "message": "Profile saved successfully."})


@require_http_methods(["GET"])
@login_required
def account_status(request, pk):
    account = get_object_or_404(LinkedInAccount, pk=pk, user=request.user)
    return JsonResponse({
        "id": account.id, "status": account.status,
        "full_name": account.full_name, "headline": account.headline,
        "location": account.location, "connections": account.connections,
        "skills_count": len(account.get_skills_list()),
        "experience_count": len(account.get_experience_list()),
        "education_count": len(account.get_education_list()),
        "last_synced": account.last_synced.isoformat() if account.last_synced else None,
        "profile_photo_url": account.profile_photo_url,
    })


@login_required
def account_profile(request, pk):
    account = get_object_or_404(LinkedInAccount, pk=pk, user=request.user)
    return render(request, "dashboard/profile.html", {"account": account})


# ─── RESUME MANAGEMENT ────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def upload_resume(request):
    sub = _get_subscription(request.user)
    plan_limits = settings.PLAN_LIMITS.get(sub.plan, settings.PLAN_LIMITS['free'])
    current_count = Resume.objects.filter(user=request.user).count()

    if current_count >= plan_limits['resumes']:
        return JsonResponse({
            "success": False,
            "error": f"Your {sub.plan} plan allows {plan_limits['resumes']} resume(s). Upgrade to add more.",
            "upgrade_required": True,
        }, status=403)

    if "file" not in request.FILES:
        return JsonResponse({"success": False, "error": "No file uploaded."}, status=400)

    uploaded_file = request.FILES["file"]
    name = request.POST.get("name", "").strip() or uploaded_file.name
    set_active = request.POST.get("set_active", "false") == "true"
    account_id = request.POST.get("account_id", "").strip()

    if not uploaded_file.name.lower().endswith(".pdf"):
        return JsonResponse({"success": False, "error": "Only PDF files are accepted."}, status=400)
    if uploaded_file.size > 10 * 1024 * 1024:
        return JsonResponse({"success": False, "error": "File too large. Maximum 10MB."}, status=400)

    # Ensure media directory exists
    media_dir = Path(settings.MEDIA_ROOT) / "resumes" / str(request.user.id)
    media_dir.mkdir(parents=True, exist_ok=True)

    account_obj = None
    if account_id:
        try:
            account_obj = LinkedInAccount.objects.get(id=account_id, user=request.user)
        except Exception:
            pass

    resume = Resume(name=name, user=request.user, is_active=set_active, account=account_obj)
    resume.file = uploaded_file
    resume.save()

    return JsonResponse({
        "success": True,
        "resume_id": resume.id,
        "name": resume.name,
        "filename": resume.filename,
        "size_kb": resume.file_size_kb,
        "is_active": resume.is_active,
        "message": f"Resume '{name}' uploaded successfully!",
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def set_active_resume(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    Resume.objects.filter(user=request.user).update(is_active=False)
    resume.is_active = True
    resume.save(update_fields=['is_active'])
    return JsonResponse({"success": True, "message": f"'{resume.name}' is now the active resume."})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def delete_resume(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    name = resume.name
    if resume.file:
        try:
            resume.file.delete(save=False)
        except Exception:
            pass
    resume.delete()
    return JsonResponse({"success": True, "message": f"Resume '{name}' deleted."})
