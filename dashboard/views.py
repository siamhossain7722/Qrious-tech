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

from .models import JobApplication, AgentRun, LinkedInAccount, Resume
from rest_framework import viewsets, permissions, serializers, filters


# ─── REST FRAMEWORK MODELVIEWSETS ─────────────────────────────────────────────

class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = '__all__'

class AgentRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRun
        fields = '__all__'

class LinkedInAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedInAccount
        fields = ['id', 'user', 'email', 'is_active', 'status', 'full_name', 'headline', 'location', 'profile_url', 'created_at', 'last_synced']

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ['id', 'user', 'account', 'name', 'file', 'is_active', 'file_size_kb', 'uploaded_at']

class JobApplicationViewSet(viewsets.ModelViewSet):
    """ModelViewSet for JobApplication with select_related('user')."""
    queryset = JobApplication.objects.select_related('user').order_by('-date_applied')
    serializer_class = JobApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'company', 'location', 'status']

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            return qs.filter(user=self.request.user)
        return qs

class AgentRunViewSet(viewsets.ModelViewSet):
    """ModelViewSet for AgentRun with select_related('user')."""
    queryset = AgentRun.objects.select_related('user').order_by('-started_at')
    serializer_class = AgentRunSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            return qs.filter(user=self.request.user)
        return qs

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

class ResumeViewSet(viewsets.ModelViewSet):
    """ModelViewSet for Resume with select_related('user', 'account')."""
    queryset = Resume.objects.select_related('user', 'account').order_by('-uploaded_at')
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            return qs.filter(user=self.request.user)
        return qs


def _get_subscription(user):
    """Get or create a free subscription for the user."""
    try:
        return user.subscription
    except Exception:
        from accounts_app.models import Subscription
        sub, _ = Subscription.objects.get_or_create(
            user=user, defaults={'plan': 'free', 'status': 'active'}
        )
        return sub


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
def run_agent(request):
    """Trigger the LinkedIn agent — checks subscription limits first."""
    sub = _get_subscription(request.user)
    can_apply, reason = sub.can_apply()

    data = json.loads(request.body) if request.body else {}
    dry_run = data.get("dry_run", True)

    if not dry_run and not can_apply:
        return JsonResponse({"success": False, "error": reason, "upgrade_required": True}, status=403)

    account_id = data.get("account_id")
    active_resume = Resume.objects.filter(user=request.user, is_active=True).first()
    resume_path = active_resume.file.path if active_resume and active_resume.file else ""

    account = None
    if account_id:
        try:
            account = LinkedInAccount.objects.get(id=account_id, user=request.user)
        except LinkedInAccount.DoesNotExist:
            pass

    run = AgentRun.objects.create(user=request.user, dry_run=dry_run, status="running")

    def run_agent_thread():
        from agent.main import LinkedInAgent

        async def _run():
            agent = LinkedInAgent()
            agent.dry_run = dry_run
            if account:
                os.environ["LINKEDIN_EMAIL"] = account.email
                os.environ["LINKEDIN_PASSWORD"] = account.password
            agent._resume_path = resume_path
            return await agent.run()

        try:
            results = asyncio.run(_run())
            for result in results:
                _save_result_to_db(result, request.user)

            applied = sum(1 for r in results if r.get("status") == "applied")
            skipped = sum(1 for r in results if r.get("status") == "skipped")
            failed = sum(1 for r in results if r.get("status") in ("failed", "error"))

            run.status = "completed"
            run.finished_at = datetime.now()
            run.total_found = len(results)
            run.total_applied = applied
            run.total_skipped = skipped
            run.total_failed = failed
            run.save()

            # Log usage event
            from accounts_app.models import UsageLog
            from accounts_app.views import create_notification
            UsageLog.objects.create(
                user=request.user,
                event='agent_run',
                metadata=json.dumps({'applied': applied, 'found': len(results), 'dry_run': dry_run})
            )
            create_notification(
                user=request.user,
                title="🤖 AI Agent Session Completed",
                message=f"AI Agent run completed! Applied to {applied} job(s) out of {len(results)} found ({'Dry Run' if dry_run else 'Live Run'}).",
                notification_type="agent",
                category="success",
                link="/dashboard/"
            )
        except Exception as e:
            run.status = "failed"
            run.log_output = str(e)
            run.finished_at = datetime.now()
            run.save()

            from accounts_app.views import create_notification
            create_notification(
                user=request.user,
                title="❌ AI Agent Run Failed",
                message=f"AI Agent run failed: {str(e)}",
                notification_type="agent",
                category="error",
                link="/dashboard/"
            )

    thread = threading.Thread(target=run_agent_thread, daemon=True)
    thread.start()

    return JsonResponse({
        "success": True,
        "run_id": run.id,
        "message": f"Agent started {'(Dry Run)' if dry_run else '(Live Mode)'}",
        "resume": active_resume.name if active_resume else None,
        "apps_remaining": sub.applications_remaining(),
    })


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
    account.status = "syncing"
    account.save()

    def sync_thread():
        import asyncio, json as _json
        from agent.browser import BrowserController
        from agent.linkedin_auth import LinkedInAuth
        from agent.profile_reader import ProfileReader

        async def _sync():
            os.environ["LINKEDIN_EMAIL"] = account.email
            os.environ["LINKEDIN_PASSWORD"] = account.password

            user_data_dir = account.session_file if (account.session_file and os.path.exists(account.session_file)) else f"data/browser_profiles/user_{request.user.id}_acc_{account.id}"
            os.makedirs(user_data_dir, exist_ok=True)
            await _async_save_account_status(account.id, "syncing", user_data_dir)

            browser = BrowserController(headless=False, slow_mo_ms=600, profile_dir=user_data_dir)
            try:
                await browser.launch()
                auth = LinkedInAuth(browser)
                logged_in = await auth.ensure_logged_in()
                if not logged_in:
                    await _async_save_account_status(account.id, "needs_verification")
                    return
                reader = ProfileReader(browser)
                profile = await reader.read_own_profile()
                await _async_save_account_profile(account.id, profile)
                await _async_save_account_status(account.id, "active", user_data_dir)
            except Exception as e:
                await _async_save_account_status(account.id, "inactive")
                print(f"Sync error: {e}")
            finally:
                try:
                    await browser.close()
                except Exception:
                    pass

        asyncio.run(_sync())

    threading.Thread(target=sync_thread, daemon=True).start()
    return JsonResponse({"success": True, "message": "Profile sync started. Check back in ~30 seconds."})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def open_login(request, pk):
    account = get_object_or_404(LinkedInAccount, pk=pk, user=request.user)
    account.status = "syncing"
    account.save()

    def login_thread():
        import asyncio, json as _json
        from agent.browser import BrowserController
        from agent.profile_reader import ProfileReader

        async def _login():
            user_data_dir = f"data/browser_profiles/user_{request.user.id}_acc_{account.id}"
            os.makedirs(user_data_dir, exist_ok=True)
            browser = BrowserController(headless=False, slow_mo_ms=500, profile_dir=user_data_dir)
            try:
                page = await browser.launch()
                try:
                    if not page or "linkedin.com" not in page.url:
                        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=12000)
                except Exception as nav_e:
                    print(f"Initial goto warning (continuing): {nav_e}")

                # Check periodically up to 5 minutes (300 seconds) if user completed login
                for _ in range(90):
                    await asyncio.sleep(2)
                    try:
                        # 1. Check cookies for li_at session cookie
                        cookies = await browser.context.cookies()
                        has_li_at = any(c.get("name") == "li_at" for c in cookies)

                        # 2. Check current page URL
                        url = page.url if (page and not page.is_closed()) else ""
                        is_logged_in_url = bool(url) and (
                            "feed" in url or "mynetwork" in url or "/in/" in url or "jobs" in url or "messaging" in url
                            or ("check/challenge" not in url and "login" not in url and "checkpoint" not in url and "signup" not in url)
                        )

                        if has_li_at or is_logged_in_url:
                            print("✅ Login detected! Updating account status to active...")
                            await _async_save_account_status(account.id, "active", str(browser.profile_dir))

                            # Scrape profile info safely without altering status if scraping errors occur
                            try:
                                reader = ProfileReader(browser)
                                profile = await reader.read_own_profile()
                                await _async_save_account_profile(account.id, profile)
                            except Exception as p_err:
                                print(f"Profile read error after login (ignoring): {p_err}")

                            break
                    except Exception as loop_err:
                        print(f"Login check iteration error: {loop_err}")
                        try:
                            cookies = await browser.context.cookies()
                            if any(c.get("name") == "li_at" for c in cookies):
                                await _async_save_account_status(account.id, "active", str(browser.profile_dir))
                                break
                        except Exception:
                            pass
                else:
                    await _async_save_account_status(account.id, "inactive")
            except Exception as e:
                print(f"Open login browser error: {e}")
                await _async_save_account_status(account.id, "inactive")
            finally:
                try:
                    await browser.close()
                except Exception:
                    pass

        asyncio.run(_login())

    threading.Thread(target=login_thread, daemon=True).start()
    return JsonResponse({"success": True, "message": "Interactive login browser launched. Complete Google / LinkedIn login in the opened window."})


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
