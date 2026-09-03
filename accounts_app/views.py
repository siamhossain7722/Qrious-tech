import datetime
import stripe
import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone

from .models import UserProfile, Subscription, UsageLog, StudentEnrollment, StudentPayment, CourseBatch, Notification

stripe.api_key = settings.STRIPE_SECRET_KEY


def _get_active_batches():
    """Returns all CourseBatch objects, ensuring default 'Batch - 01' exists if none present."""
    from .models import CourseBatch
    batches = CourseBatch.objects.all()
    if not batches.exists():
        CourseBatch.objects.get_or_create(name="Batch - 01", defaults={"description": "Default Batch 01"})
        batches = CourseBatch.objects.all()
    return batches


def _ensure_subscription(user):
    """Create free subscription if none exists."""
    sub, _ = Subscription.objects.get_or_create(user=user, defaults={'plan': 'free', 'status': 'active'})
    return sub


@login_required
def billing_home(request):
    """Billing / subscription management page."""
    sub = _ensure_subscription(request.user)
    usage_logs = UsageLog.objects.filter(user=request.user)[:20]
    plans = settings.PLAN_LIMITS

    context = {
        'subscription': sub,
        'usage_logs': usage_logs,
        'plans': plans,
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY,
        'apps_remaining': sub.applications_remaining(),
        'apps_used': sub.applications_this_month(),
    }
    return render(request, 'accounts_app/billing.html', context)


@login_required
def create_checkout_session(request):
    """Create a Stripe checkout session for plan upgrade."""
    plan = request.GET.get('plan', 'pro')
    price_map = {
        'pro': settings.STRIPE_PRICE_PRO,
        'business': settings.STRIPE_PRICE_BUSINESS,
    }
    price_id = price_map.get(plan)
    if not price_id or 'placeholder' in price_id:
        messages.warning(request, 'Payment not yet configured. Contact support to upgrade.')
        return redirect('billing:home')

    try:
        sub = _ensure_subscription(request.user)
        # Create or get Stripe customer
        if not sub.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.get_full_name() or request.user.email,
            )
            sub.stripe_customer_id = customer.id
            sub.save()

        session = stripe.checkout.Session.create(
            customer=sub.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=request.build_absolute_uri('/billing/success/'),
            cancel_url=request.build_absolute_uri('/billing/'),
            metadata={'user_id': request.user.id, 'plan': plan},
        )
        return redirect(session.url, code=303)
    except stripe.StripeError as e:
        messages.error(request, f'Payment error: {e.user_message}')
        return redirect('billing:home')


@login_required
def checkout_success(request):
    """Handle successful Stripe checkout redirect."""
    messages.success(request, '🎉 Subscription activated! Welcome to the new plan.')
    return render(request, 'accounts_app/checkout_success.html')


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        return HttpResponse(status=200)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        _handle_checkout_complete(session)
    elif event['type'] == 'customer.subscription.updated':
        _handle_subscription_updated(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        _handle_subscription_cancelled(event['data']['object'])

    return HttpResponse(status=200)


def _handle_checkout_complete(session):
    user_id = session.get('metadata', {}).get('user_id')
    plan = session.get('metadata', {}).get('plan', 'pro')
    stripe_sub_id = session.get('subscription')
    try:
        user = User.objects.get(id=user_id)
        sub = _ensure_subscription(user)
        sub.plan = plan
        sub.status = 'active'
        sub.stripe_subscription_id = stripe_sub_id or ''
        sub.save()
    except User.DoesNotExist:
        pass


def _handle_subscription_updated(stripe_sub):
    stripe_sub_id = stripe_sub.get('id')
    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
        sub.status = stripe_sub.get('status', 'active')
        sub.save()
    except Subscription.DoesNotExist:
        pass


def _handle_subscription_cancelled(stripe_sub):
    stripe_sub_id = stripe_sub.get('id')
    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
        sub.plan = 'free'
        sub.status = 'active'
        sub.stripe_subscription_id = ''
        sub.save()
    except Subscription.DoesNotExist:
        pass


@login_required
def cancel_subscription(request):
    """Cancel subscription at period end."""
    try:
        sub = request.user.subscription
        if sub.stripe_subscription_id and 'placeholder' not in settings.STRIPE_SECRET_KEY:
            stripe.Subscription.modify(sub.stripe_subscription_id, cancel_at_period_end=True)
            sub.cancel_at_period_end = True
            sub.save()
        messages.info(request, 'Your subscription will be cancelled at the end of the billing period.')
    except Exception as e:
        messages.error(request, f'Error: {e}')
    return redirect('billing:home')


@login_required
def profile_settings(request):
    """User profile and subscription settings page."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    sub, _ = Subscription.objects.get_or_create(
        user=request.user,
        defaults={'plan': 'free', 'status': 'active'}
    )

    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.save()

        profile.phone = request.POST.get('phone', '').strip()
        profile.company = request.POST.get('company', '').strip()
        profile.bio = request.POST.get('bio', '').strip()

        # Handle avatar upload
        if 'avatar' in request.FILES:
            avatar_file = request.FILES['avatar']
            if avatar_file.size > 5 * 1024 * 1024:
                messages.error(request, 'Profile picture file size too large. Maximum 5MB allowed.')
                return redirect('profile_settings')
            try:
                import base64
                file_bytes = avatar_file.read()
                encoded = base64.b64encode(file_bytes).decode('utf-8')
                mime = avatar_file.content_type or 'image/png'
                profile.avatar_data = f"data:{mime};base64,{encoded}"
                profile.avatar = avatar_file
            except Exception as ex:
                pass

        # Handle remove avatar
        if request.POST.get('remove_avatar') == 'true':
            profile.avatar_data = ""
            if profile.avatar:
                try:
                    profile.avatar.delete(save=False)
                except Exception:
                    pass
                profile.avatar = None

        try:
            profile.save()
        except OSError:
            # If filesystem is read-only, clear avatar file handle and save profile base64 & fields
            profile.avatar = None
            profile.save()

        messages.success(request, 'Profile information updated successfully!')
        return redirect('profile_settings')

    from dashboard.models import JobApplication, LinkedInAccount, Resume

    plan_limits = settings.PLAN_LIMITS.get(sub.plan, settings.PLAN_LIMITS['free'])
    apps_used = sub.applications_this_month()
    apps_remaining = sub.applications_remaining()
    accounts_count = LinkedInAccount.objects.filter(user=request.user).count()
    resumes_count = Resume.objects.filter(user=request.user).count()
    active_resume = Resume.objects.filter(user=request.user, is_active=True).first()
    total_jobs = JobApplication.objects.filter(user=request.user).count()

    context = {
        'profile': profile,
        'subscription': sub,
        'plan_limits': plan_limits,
        'apps_used': apps_used,
        'apps_remaining': apps_remaining,
        'accounts_count': accounts_count,
        'resumes_count': resumes_count,
        'active_resume': active_resume,
        'total_jobs': total_jobs,
    }
    return render(request, 'accounts_app/settings.html', context)


# ─── SUPER ADMIN USER MANAGEMENT ─────────────────────────────────────────────

def _is_superuser(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


@user_passes_test(_is_superuser)
def admin_users_list(request):
    """Super Admin view: List all registered users, subscriptions, and metrics."""
    from dashboard.models import JobApplication, LinkedInAccount, Resume

    query = request.GET.get('q', '').strip()
    plan_filter = request.GET.get('plan', '')
    status_filter = request.GET.get('status', '')

    users = User.objects.all().select_related('profile', 'subscription').order_by('-date_joined')

    if query:
        users = users.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )

    if plan_filter:
        users = users.filter(subscription__plan=plan_filter)

    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'disabled':
        users = users.filter(is_active=False)
    elif status_filter == 'superuser':
        users = users.filter(is_superuser=True)

    # Calculate global platform stats
    total_users = User.objects.count()
    free_users = Subscription.objects.filter(plan='free').count()
    pro_users = Subscription.objects.filter(plan='pro').count()
    biz_users = Subscription.objects.filter(plan='business').count()
    total_applications = JobApplication.objects.count()
    total_accounts = LinkedInAccount.objects.count()

    # Annotate user list with metrics
    users_data = []
    for u in users:
        try:
            sub = u.subscription
        except Exception:
            sub, _ = Subscription.objects.get_or_create(user=u, defaults={'plan': 'free', 'status': 'active'})

        users_data.append({
            'user': u,
            'profile': getattr(u, 'profile', None),
            'subscription': sub,
            'jobs_count': JobApplication.objects.filter(user=u).count(),
            'accounts_count': LinkedInAccount.objects.filter(user=u).count(),
            'resumes_count': Resume.objects.filter(user=u).count(),
        })

    context = {
        'users_data': users_data,
        'query': query,
        'plan_filter': plan_filter,
        'status_filter': status_filter,
        'total_users': total_users,
        'free_users': free_users,
        'pro_users': pro_users,
        'biz_users': biz_users,
        'total_applications': total_applications,
        'total_accounts': total_accounts,
        'plans': settings.PLAN_LIMITS,
    }
    return render(request, 'accounts_app/admin_users.html', context)


@user_passes_test(_is_superuser)
def admin_user_detail(request, user_id):
    """Super Admin view: View and edit any user's profile, subscription, and permissions."""
    from dashboard.models import JobApplication, LinkedInAccount, Resume

    target_user = get_object_or_404(User, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    sub, _ = Subscription.objects.get_or_create(user=target_user, defaults={'plan': 'free', 'status': 'active'})

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            target_user.first_name = request.POST.get('first_name', '').strip()
            target_user.last_name = request.POST.get('last_name', '').strip()
            target_user.email = request.POST.get('email', '').strip() or target_user.email
            target_user.is_active = request.POST.get('is_active') == 'on'
            target_user.is_staff = request.POST.get('is_staff') == 'on'
            target_user.is_superuser = request.POST.get('is_superuser') == 'on'
            target_user.save()

            profile.phone = request.POST.get('phone', '').strip()
            profile.company = request.POST.get('company', '').strip()
            profile.bio = request.POST.get('bio', '').strip()
            profile.save()

            messages.success(request, f"Updated user settings for {target_user.email}!")

        elif action == 'update_subscription':
            new_plan = request.POST.get('plan', 'free')
            new_status = request.POST.get('status', 'active')
            sub.plan = new_plan
            sub.status = new_status
            sub.save()
            messages.success(request, f"Subscription plan for {target_user.email} set to {new_plan.upper()}!")

        return redirect('billing:admin_user_detail', user_id=target_user.id)

    jobs = JobApplication.objects.filter(user=target_user)[:50]
    accounts = LinkedInAccount.objects.filter(user=target_user)
    resumes = Resume.objects.filter(user=target_user)

    context = {
        'target_user': target_user,
        'profile': profile,
        'subscription': sub,
        'jobs': jobs,
        'accounts': accounts,
        'resumes': resumes,
        'plans': settings.PLAN_LIMITS,
    }
    return render(request, 'accounts_app/admin_user_detail.html', context)


@csrf_exempt
@require_http_methods(['POST'])
@user_passes_test(_is_superuser)
def admin_update_user_plan(request, user_id):
    """Super Admin Quick Action: Upgrade/Downgrade a user's subscription plan directly."""
    target_user = get_object_or_404(User, id=user_id)
    sub, _ = Subscription.objects.get_or_create(user=target_user, defaults={'plan': 'free', 'status': 'active'})

    data = json.loads(request.body) if request.body else request.POST
    new_plan = data.get('plan', 'free')

    if new_plan in settings.PLAN_LIMITS:
        sub.plan = new_plan
        sub.status = 'active'
        sub.save()
        return JsonResponse({
            'success': True,
            'message': f"User {target_user.email} plan updated to {new_plan.upper()}",
            'plan': new_plan,
        })
    return JsonResponse({'success': False, 'error': 'Invalid plan'}, status=400)


@csrf_exempt
@require_http_methods(['POST'])
@user_passes_test(_is_superuser)
def admin_delete_user(request, user_id):
    """Super Admin Quick Action: Delete a user account."""
    if request.user.id == user_id:
        return JsonResponse({'success': False, 'error': 'You cannot delete your own account.'}, status=400)

    target_user = get_object_or_404(User, id=user_id)
    if target_user.enrollments.filter(is_completed=True).exists():
        return JsonResponse({'success': False, 'error': 'Cannot delete user: Student has completed course and earned a verified certificate.'}, status=400)

    email = target_user.email
    target_user.delete()
    return JsonResponse({'success': True, 'message': f"User account '{email}' deleted successfully."})


# ─── MASTER SUPER ADMIN DASHBOARD & COURSE MANAGEMENT ──────────────────────────

import io
import base64
import qrcode
from .models import ServiceBooking, StudentEnrollment

@login_required
@user_passes_test(_is_superuser)
def superadmin_master_dashboard(request):
    """Master Super Admin Console for managing users, courses, student progress, and service bookings."""
    from dashboard.models import JobApplication
    from django.core.paginator import Paginator
    from django.db.models import Q, F

    from django.db.models import Sum, Value, DecimalField
    from django.db.models.functions import Coalesce

    total_users_count = User.objects.count()
    total_bookings_count = ServiceBooking.objects.count()
    users = User.objects.select_related('profile').order_by('-date_joined')[:10]
    enrollments_qs = StudentEnrollment.objects.all().select_related('user', 'user__profile', 'batch').annotate(
        paid_sum=Coalesce(Sum('payments__amount'), Value(0.0), output_field=DecimalField())
    ).order_by('-created_at')
    bookings = ServiceBooking.objects.all().order_by('-created_at')[:10]

    # Search & Filter Query Params
    q_search = request.GET.get('q', '').strip()
    due_filter = request.GET.get('due_status', '').strip()
    course_filter = request.GET.get('course', '').strip()
    progress_filter = request.GET.get('progress_status', '').strip()

    if q_search:
        enrollments_qs = enrollments_qs.filter(
            Q(student_id__icontains=q_search) |
            Q(user__email__icontains=q_search) |
            Q(user__first_name__icontains=q_search) |
            Q(user__last_name__icontains=q_search) |
            Q(course_name__icontains=q_search)
        )

    if due_filter == 'due':
        enrollments_qs = enrollments_qs.filter(total_fee__gt=F('paid_sum'))
    elif due_filter == 'paid':
        enrollments_qs = enrollments_qs.filter(total_fee__lte=F('paid_sum'))

    if course_filter:
        enrollments_qs = enrollments_qs.filter(course_name__icontains=course_filter)

    if progress_filter == 'completed':
        enrollments_qs = enrollments_qs.filter(is_completed=True)
    elif progress_filter == 'in_progress':
        enrollments_qs = enrollments_qs.filter(is_completed=False)

    # Unique list of courses for filter dropdown
    available_courses = StudentEnrollment.objects.values_list('course_name', flat=True).distinct()
    batches = CourseBatch.objects.all()

    # Pagination: 10 items per page
    paginator = Paginator(enrollments_qs, 10)
    page_number = request.GET.get('page', 1)
    enrollments_page = paginator.get_page(page_number)

    context = {
        'total_users': total_users_count,
        'total_enrollments': StudentEnrollment.objects.count(),
        'completed_certificates': StudentEnrollment.objects.filter(is_completed=True).count(),
        'total_bookings': total_bookings_count,
        'total_applications': JobApplication.objects.count(),
        'users': users,
        'enrollments': enrollments_page,
        'bookings': bookings,
        'batches': batches,
        'q_search': q_search,
        'due_filter': due_filter,
        'course_filter': course_filter,
        'progress_filter': progress_filter,
        'available_courses': available_courses,
        'created_credentials': request.session.pop('created_student_credentials', None),
        'pending_payments': StudentPayment.objects.filter(status='pending').select_related('enrollment', 'enrollment__user').order_by('-created_at'),
    }
    return render(request, 'accounts_app/superadmin_dashboard.html', context)


@login_required
@user_passes_test(_is_superuser)
def superadmin_users_list(request):
    """Super Admin: All Registered Users & Subscriptions management console."""
    from django.core.paginator import Paginator
    from django.db.models import Q
    from django.utils import timezone
    from datetime import timedelta
    from .models import Subscription, UserProfile

    q_search = request.GET.get('q', '').strip()
    enrollment_filter = request.GET.get('enrollment', '').strip()
    date_filter = request.GET.get('date_joined', '').strip()
    status_filter = request.GET.get('contact_status', '').strip()

    users_qs = User.objects.all().select_related('profile').prefetch_related('enrollments', 'enrollments__batch').order_by('-date_joined')

    seven_days_ago = timezone.now() - timedelta(days=7)

    if q_search:
        users_qs = users_qs.filter(
            Q(username__icontains=q_search) |
            Q(email__icontains=q_search) |
            Q(first_name__icontains=q_search) |
            Q(last_name__icontains=q_search) |
            Q(profile__phone__icontains=q_search)
        )

    if enrollment_filter == 'enrolled':
        users_qs = users_qs.filter(enrollments__isnull=False).distinct()
    elif enrollment_filter == 'not_enrolled':
        users_qs = users_qs.filter(enrollments__isnull=True)

    if date_filter == 'over_7_days':
        users_qs = users_qs.filter(date_joined__lte=seven_days_ago)
    elif date_filter == 'within_7_days':
        users_qs = users_qs.filter(date_joined__gt=seven_days_ago)

    if status_filter == 'need_contact':
        users_qs = users_qs.filter(date_joined__lte=seven_days_ago, profile__is_contacted=False)
    elif status_filter == 'completed':
        users_qs = users_qs.filter(profile__is_contacted=True)

    paginator = Paginator(users_qs, 10)
    page_number = request.GET.get('page', 1)
    users_page = paginator.get_page(page_number)

    need_contact_count = User.objects.filter(date_joined__lte=seven_days_ago, profile__is_contacted=False).count()

    context = {
        'users_page': users_page,
        'q_search': q_search,
        'enrollment_filter': enrollment_filter,
        'date_filter': date_filter,
        'status_filter': status_filter,
        'total_users_count': User.objects.count(),
        'active_subscriptions': Subscription.objects.filter(status='active').count(),
        'need_contact_count': need_contact_count,
    }
    return render(request, 'accounts_app/superadmin_users_list.html', context)


@login_required
@user_passes_test(_is_superuser)
def toggle_user_contact(request, user_id):
    """Super Admin: Toggle user contact status (Complete / Pending)."""
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=user_id)
        profile, _ = UserProfile.objects.get_or_create(user=target_user)
        desired_status = request.POST.get('status')
        if desired_status == 'completed':
            profile.is_contacted = True
        elif desired_status == 'pending':
            profile.is_contacted = False
        else:
            profile.is_contacted = not profile.is_contacted
        profile.save()
        status_label = "Contact Completed ✅" if profile.is_contacted else "Pending Contact 📞"
        messages.success(request, f"Updated contact status for '{target_user.email}': {status_label}")
    return redirect('/admin-users/')


@login_required
@user_passes_test(_is_superuser)
def export_users_csv(request):
    """Export filtered registered users list as CSV spreadsheet."""
    import csv
    from django.http import HttpResponse
    from django.utils import timezone
    from datetime import timedelta

    q_search = request.GET.get('q', '').strip()
    enrollment_filter = request.GET.get('enrollment', '').strip()
    date_filter = request.GET.get('date_joined', '').strip()
    status_filter = request.GET.get('contact_status', '').strip()

    users_qs = User.objects.all().select_related('profile').prefetch_related('enrollments', 'enrollments__batch').order_by('-date_joined')
    seven_days_ago = timezone.now() - timedelta(days=7)

    if q_search:
        users_qs = users_qs.filter(
            Q(username__icontains=q_search) |
            Q(email__icontains=q_search) |
            Q(first_name__icontains=q_search) |
            Q(last_name__icontains=q_search) |
            Q(profile__phone__icontains=q_search)
        )

    if enrollment_filter == 'enrolled':
        users_qs = users_qs.filter(enrollments__isnull=False).distinct()
    elif enrollment_filter == 'not_enrolled':
        users_qs = users_qs.filter(enrollments__isnull=True)

    if date_filter == 'over_7_days':
        users_qs = users_qs.filter(date_joined__lte=seven_days_ago)
    elif date_filter == 'within_7_days':
        users_qs = users_qs.filter(date_joined__gt=seven_days_ago)

    if status_filter == 'need_contact':
        users_qs = users_qs.filter(date_joined__lte=seven_days_ago, profile__is_contacted=False)
    elif status_filter == 'completed':
        users_qs = users_qs.filter(profile__is_contacted=True)

    response = HttpResponse(content_type='text/csv')
    filename = f"users_report_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['#', 'User ID', 'Full Name', 'Email', 'Phone/WhatsApp', 'Enrolled Batch', 'Date Joined', 'Over 7 Days', 'Contact Status'])

    for idx, u in enumerate(users_qs, 1):
        is_over = u.date_joined <= seven_days_ago
        c_status = "Completed" if u.profile.is_contacted else ("Need Contact (>7D)" if is_over else "New (<7D)")
        batch_names = ", ".join([e.batch.name if e.batch else e.course_name for e in u.enrollments.all()]) or "Not Enrolled"
        writer.writerow([
            idx,
            u.id,
            u.get_full_name() or u.email,
            u.email,
            u.profile.phone or 'N/A',
            batch_names,
            u.date_joined.strftime('%Y-%m-%d %H:%M'),
            'YES' if is_over else 'NO',
            c_status
        ])

    return response


@login_required
@user_passes_test(_is_superuser)
def export_users_pdf(request):
    """Export filtered registered users list as PDF document."""
    from django.http import HttpResponse
    from django.utils import timezone
    from datetime import timedelta
    from .pdf_utils import generate_users_report_pdf

    q_search = request.GET.get('q', '').strip()
    enrollment_filter = request.GET.get('enrollment', '').strip()
    date_filter = request.GET.get('date_joined', '').strip()
    status_filter = request.GET.get('contact_status', '').strip()

    users_qs = User.objects.all().select_related('profile').prefetch_related('enrollments', 'enrollments__batch').order_by('-date_joined')
    seven_days_ago = timezone.now() - timedelta(days=7)

    if q_search:
        users_qs = users_qs.filter(
            Q(username__icontains=q_search) |
            Q(email__icontains=q_search) |
            Q(first_name__icontains=q_search) |
            Q(last_name__icontains=q_search) |
            Q(profile__phone__icontains=q_search)
        )

    if enrollment_filter == 'enrolled':
        users_qs = users_qs.filter(enrollments__isnull=False).distinct()
    elif enrollment_filter == 'not_enrolled':
        users_qs = users_qs.filter(enrollments__isnull=True)

    if date_filter == 'over_7_days':
        users_qs = users_qs.filter(date_joined__lte=seven_days_ago)
    elif date_filter == 'within_7_days':
        users_qs = users_qs.filter(date_joined__gt=seven_days_ago)

    if status_filter == 'need_contact':
        users_qs = users_qs.filter(date_joined__lte=seven_days_ago, profile__is_contacted=False)
    elif status_filter == 'completed':
        users_qs = users_qs.filter(profile__is_contacted=True)

    pdf_binary = generate_users_report_pdf(users_qs)
    filename = f"users_report_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(pdf_binary, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@csrf_exempt
@login_required
@user_passes_test(_is_superuser)
def superadmin_delete_user(request, user_id):
    """Super Admin: Delete registered user account (Supports Form POST & AJAX JSON)."""
    is_json = 'application/json' in request.META.get('HTTP_ACCEPT', '') or request.content_type == 'application/json'

    if request.user.id == user_id:
        if is_json:
            return JsonResponse({'success': False, 'error': 'You cannot delete your own superadmin account.'}, status=400)
        messages.error(request, "You cannot delete your own superadmin account.")
        return redirect('/admin-users/')

    target_user = get_object_or_404(User, id=user_id)
    if target_user.enrollments.filter(is_completed=True).exists():
        err_msg = f"🔒 Cannot delete '{target_user.email}': Student has completed their course and earned a verified certificate."
        if is_json:
            return JsonResponse({'success': False, 'error': err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect('/admin-users/')

    user_email = target_user.email
    target_user.delete()

    if is_json:
        return JsonResponse({'success': True, 'message': f"User account '{user_email}' deleted successfully."})

    messages.success(request, f"🗑️ User account '{user_email}' deleted successfully.")
    return redirect('/admin-users/')


@login_required
@user_passes_test(_is_superuser)
def superadmin_bookings_list(request):
    """Super Admin: Service Booking Requests management console."""
    from django.core.paginator import Paginator
    from django.db.models import Q
    from .models import ServiceBooking

    q_search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    bookings_qs = ServiceBooking.objects.all().order_by('-created_at')

    if q_search:
        bookings_qs = bookings_qs.filter(
            Q(name__icontains=q_search) |
            Q(email__icontains=q_search) |
            Q(phone__icontains=q_search) |
            Q(service_category__icontains=q_search) |
            Q(service_type__icontains=q_search) |
            Q(notes__icontains=q_search)
        )

    if status_filter:
        bookings_qs = bookings_qs.filter(status=status_filter)

    paginator = Paginator(bookings_qs, 10)
    page_number = request.GET.get('page', 1)
    bookings_page = paginator.get_page(page_number)

    total_bookings_count = ServiceBooking.objects.count()
    pending_bookings_count = ServiceBooking.objects.filter(status='pending').count()
    confirmed_bookings_count = ServiceBooking.objects.filter(status='confirmed').count()
    completed_bookings_count = ServiceBooking.objects.filter(status='completed').count()

    context = {
        'bookings_page': bookings_page,
        'q_search': q_search,
        'status_filter': status_filter,
        'total_bookings_count': total_bookings_count,
        'pending_bookings_count': pending_bookings_count,
        'confirmed_bookings_count': confirmed_bookings_count,
        'completed_bookings_count': completed_bookings_count,
        'status_choices': ServiceBooking.STATUS_CHOICES,
    }
    return render(request, 'accounts_app/superadmin_bookings_list.html', context)


@login_required
@user_passes_test(_is_superuser)
def superadmin_delete_booking(request, booking_id):
    """Super Admin: Delete service booking request."""
    if request.method == 'POST':
        booking = get_object_or_404(ServiceBooking, id=booking_id)
        booking_info = f"Booking #{booking.id} ({booking.name})"
        booking.delete()
        messages.success(request, f"Permanently deleted {booking_info}.")
    return redirect('/admin-bookings/')


@login_required
@user_passes_test(_is_superuser)
def export_bookings_csv(request):
    """Export filtered service bookings as CSV file."""
    import csv
    from django.http import HttpResponse
    from django.utils import timezone
    from django.db.models import Q
    from .models import ServiceBooking

    q_search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    bookings_qs = ServiceBooking.objects.all().order_by('-created_at')

    if q_search:
        bookings_qs = bookings_qs.filter(
            Q(name__icontains=q_search) |
            Q(email__icontains=q_search) |
            Q(phone__icontains=q_search) |
            Q(service_category__icontains=q_search) |
            Q(service_type__icontains=q_search) |
            Q(notes__icontains=q_search)
        )

    if status_filter:
        bookings_qs = bookings_qs.filter(status=status_filter)

    response = HttpResponse(content_type='text/csv')
    filename = f"service_bookings_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['#', 'Booking ID', 'Client Name', 'Email', 'Phone/WhatsApp', 'Category', 'Service Type', 'Status', 'Date'])

    for idx, b in enumerate(bookings_qs, 1):
        writer.writerow([
            idx,
            b.id,
            b.name,
            b.email or 'N/A',
            b.phone or 'N/A',
            b.service_category,
            b.service_type or 'N/A',
            b.status.upper(),
            b.created_at.strftime('%Y-%m-%d %H:%M')
        ])

    return response


@login_required
@user_passes_test(_is_superuser)
def export_bookings_pdf(request):
    """Export filtered service bookings as PDF document."""
    from django.http import HttpResponse
    from django.utils import timezone
    from django.db.models import Q
    from .models import ServiceBooking
    from .pdf_utils import generate_bookings_report_pdf

    q_search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    bookings_qs = ServiceBooking.objects.all().order_by('-created_at')

    if q_search:
        bookings_qs = bookings_qs.filter(
            Q(name__icontains=q_search) |
            Q(email__icontains=q_search) |
            Q(phone__icontains=q_search) |
            Q(service_category__icontains=q_search) |
            Q(service_type__icontains=q_search) |
            Q(notes__icontains=q_search)
        )

    if status_filter:
        bookings_qs = bookings_qs.filter(status=status_filter)

    pdf_binary = generate_bookings_report_pdf(bookings_qs)
    filename = f"service_bookings_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(pdf_binary, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@user_passes_test(_is_superuser)
def superadmin_payments_list(request):
    """Super Admin: All Student Payments & Proof Verifications Management Console."""
    from django.core.paginator import Paginator
    from django.db.models import Q
    from .models import StudentPayment

    q_search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    method_filter = request.GET.get('method', '').strip()

    payments_qs = StudentPayment.objects.select_related('enrollment', 'enrollment__user').order_by('-created_at')

    if q_search:
        payments_qs = payments_qs.filter(
            Q(invoice_id__icontains=q_search) |
            Q(transaction_ref__icontains=q_search) |
            Q(enrollment__user__email__icontains=q_search) |
            Q(enrollment__user__first_name__icontains=q_search) |
            Q(enrollment__user__last_name__icontains=q_search) |
            Q(enrollment__student_id__icontains=q_search) |
            Q(notes__icontains=q_search) |
            Q(admin_notes__icontains=q_search)
        )

    if status_filter:
        payments_qs = payments_qs.filter(status=status_filter)

    if method_filter:
        payments_qs = payments_qs.filter(payment_method=method_filter)

    paginator = Paginator(payments_qs, 15)
    page_number = request.GET.get('page', 1)
    payments_page = paginator.get_page(page_number)

    # Financial Summary Stats
    approved_payments = StudentPayment.objects.filter(status='approved')
    total_approved_amount = sum(p.amount for p in approved_payments) if approved_payments.exists() else Decimal('0.00')

    pending_payments = StudentPayment.objects.filter(status='pending')
    pending_count = pending_payments.count()
    pending_amount = sum(p.amount for p in pending_payments) if pending_payments.exists() else Decimal('0.00')

    total_payments_count = StudentPayment.objects.count()
    approved_count = approved_payments.count()
    rejected_count = StudentPayment.objects.filter(status='rejected').count()

    context = {
        'payments_page': payments_page,
        'q_search': q_search,
        'status_filter': status_filter,
        'method_filter': method_filter,
        'total_payments_count': total_payments_count,
        'total_approved_amount': total_approved_amount,
        'pending_count': pending_count,
        'pending_amount': pending_amount,
        'rejected_count': rejected_count,
        'status_choices': StudentPayment.STATUS_CHOICES,
    }

    if request.headers.get('HX-Request') or request.META.get('HTTP_HX_REQUEST'):
        return render(request, 'accounts_app/_payments_table_partial.html', context)

    return render(request, 'accounts_app/superadmin_payments_list.html', context)


@login_required
@user_passes_test(_is_superuser)
def export_payments_csv(request):
    """Export student payments & verifications as CSV file."""
    import csv
    from django.http import HttpResponse
    from django.db.models import Q
    from .models import StudentPayment

    q_search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    payments_qs = StudentPayment.objects.select_related('enrollment', 'enrollment__user').order_by('-created_at')

    if q_search:
        payments_qs = payments_qs.filter(
            Q(invoice_id__icontains=q_search) |
            Q(transaction_ref__icontains=q_search) |
            Q(enrollment__user__email__icontains=q_search) |
            Q(enrollment__student_id__icontains=q_search)
        )
    if status_filter:
        payments_qs = payments_qs.filter(status=status_filter)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="student_payments_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Invoice ID', 'Student Email', 'Student ID', 'Amount (BDT)',
        'Payment Method', 'Transaction Ref', 'Status', 'Date Submitted', 'Verified At'
    ])

    for p in payments_qs:
        writer.writerow([
            p.invoice_id,
            p.enrollment.user.email,
            p.enrollment.student_id,
            f"{p.amount:.2f}",
            p.payment_method,
            p.transaction_ref,
            p.status,
            p.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            p.verified_at.strftime('%Y-%m-%d %H:%M:%S') if p.verified_at else 'N/A'
        ])

    return response


@login_required
@user_passes_test(_is_superuser)
def export_payments_pdf(request):
    """Export filtered student payments & verifications as PDF document."""
    from django.http import HttpResponse
    from django.utils import timezone
    from .models import StudentPayment
    from .pdf_utils import generate_payments_report_pdf

    q_search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    payments_qs = StudentPayment.objects.select_related('enrollment', 'enrollment__user').order_by('-created_at')

    if q_search:
        payments_qs = payments_qs.filter(
            Q(invoice_id__icontains=q_search) |
            Q(transaction_ref__icontains=q_search) |
            Q(enrollment__user__email__icontains=q_search) |
            Q(enrollment__student_id__icontains=q_search)
        )
    if status_filter:
        payments_qs = payments_qs.filter(status=status_filter)

    pdf_binary = generate_payments_report_pdf(payments_qs)
    filename = f"payments_report_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(pdf_binary, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@csrf_exempt
@login_required
@user_passes_test(_is_superuser)
def superadmin_delete_payment(request, payment_id):
    """Super Admin: Delete payment verification record (Supports Form POST & AJAX JSON)."""
    from .models import StudentPayment
    payment = get_object_or_404(StudentPayment, pk=payment_id)
    is_json = 'application/json' in request.META.get('HTTP_ACCEPT', '') or request.content_type == 'application/json'

    invoice_id = payment.invoice_id
    payment.delete()

    if is_json:
        return JsonResponse({'success': True, 'message': f"Deleted payment record #{invoice_id}"})

    messages.success(request, f"🗑 Deleted payment record #{invoice_id} successfully.")
    return redirect('/admin-payments/')


@csrf_exempt
@login_required
@user_passes_test(_is_superuser)
def admin_create_student_user(request):
    """Super Admin: Create a new user specifically for courses & auto-enroll in selected course & batch."""
    from .models import CourseBatch
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        course_name = request.POST.get('course_name', '').strip()
        batch_id = request.POST.get('batch_id')
        progress = int(request.POST.get('progress_percent', 0))

        if not email or not password:
            messages.error(request, "Email and Password are required.")
            return redirect('billing:superadmin_dashboard')

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            messages.info(request, f"User with email '{email}' already exists. Enrolling existing user.")
        else:
            first_name = full_name.split()[0] if full_name else ''
            last_name = ' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            UserProfile.objects.get_or_create(user=user)
            Subscription.objects.get_or_create(user=user, defaults={'plan': 'free', 'status': 'active'})

        total_fee = request.POST.get('total_fee', '').strip()
        defaults_dict = {'progress_percent': progress}
        if batch_id:
            defaults_dict['batch_id'] = batch_id
        if total_fee:
            try:
                defaults_dict['total_fee'] = Decimal(total_fee)
            except Exception:
                pass

        enrollment, created = StudentEnrollment.objects.get_or_create(
            user=user,
            course_name=course_name,
            defaults=defaults_dict
        )
        if not created:
            if batch_id:
                enrollment.batch_id = batch_id
            enrollment.progress_percent = progress
            if total_fee:
                try:
                    enrollment.total_fee = Decimal(total_fee)
                except Exception:
                    pass
            enrollment.save()

        from .whatsapp_service import send_whatsapp_credentials

        phone = request.POST.get('phone', '').strip()
        whatsapp_result = None
        if phone:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.phone = phone
            profile.save()

            whatsapp_result = send_whatsapp_credentials(phone, {
                'student_id': enrollment.student_id,
                'full_name': user.get_full_name() or email,
                'email': email,
                'password': password,
                'course_name': course_name,
                'login_url': request.build_absolute_uri('/login/')
            })

        import re, urllib.parse
        clean_phone = re.sub(r'\D', '', phone)
        whatsapp_url = ""
        if clean_phone:
            msg_text = (
                f"🎓 *Qrious Tech Academy - Student Account Credentials*\n"
                f"--------------------------------------------------\n"
                f"👤 *Student ID:* {enrollment.student_id}\n"
                f"👤 *Name:* {user.get_full_name() or email}\n"
                f"📧 *Email:* {email}\n"
                f"🔑 *Password:* {password}\n"
                f"📚 *Course:* {course_name}\n"
                f"🏷️ *Batch:* {enrollment.batch.name if enrollment.batch else 'Batch 01'}\n"
                f"🔗 *Login Portal:* {request.build_absolute_uri('/login/')}\n"
                f"--------------------------------------------------\n"
                f"Welcome to Qrious Tech Academy!"
            )
            whatsapp_url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={urllib.parse.quote(msg_text)}"

        request.session['created_student_credentials'] = {
            'full_name': user.get_full_name() or email,
            'email': email,
            'password': password,
            'student_id': enrollment.student_id,
            'course_name': course_name,
            'batch_name': enrollment.batch.name if enrollment.batch else 'Batch 01',
            'phone': phone,
            'clean_phone': clean_phone,
            'whatsapp_url': whatsapp_url,
            'auto_sent': True if (whatsapp_result and whatsapp_result.get('success')) else False
        }

    return redirect('/superadmin/')


@csrf_exempt
@login_required
@user_passes_test(_is_superuser)
def admin_enroll_student(request):
    """Super Admin: Enroll user in a course and auto-create Student ID."""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        course_name = request.POST.get('course_name', '').strip()
        batch_id = request.POST.get('batch_id')
        progress = int(request.POST.get('progress_percent', 0))
        is_completed = request.POST.get('is_completed') == 'true'

        user = get_object_or_404(User, id=user_id)
        if course_name:
            defaults_dict = {'progress_percent': progress, 'is_completed': is_completed}
            if batch_id:
                defaults_dict['batch_id'] = batch_id
            enrollment, created = StudentEnrollment.objects.get_or_create(
                user=user,
                course_name=course_name,
                defaults=defaults_dict
            )
            if not created:
                if batch_id:
                    enrollment.batch_id = batch_id
                enrollment.progress_percent = progress
                enrollment.is_completed = is_completed
                enrollment.save()

            # Notification
            create_notification(
                user=user,
                title=f"🎓 Enrolled in {course_name}",
                message=f"You have been enrolled in '{course_name}'. Your Student ID is {enrollment.student_id}.",
                notification_type='course',
                category='success',
                link='/student/dashboard/'
            )

            messages.success(request, f"Student {user.email} enrolled in '{course_name}' with ID {enrollment.student_id}")

    return redirect('/superadmin/')


@login_required
@user_passes_test(_is_superuser)
def admin_student_profile(request, enrollment_id):
    """Detailed Individual Student Profile & Financial Course Management Console for Super Admin."""
    from .models import CourseBatch
    enrollment = get_object_or_404(StudentEnrollment, id=enrollment_id)
    student_user = enrollment.user
    student_profile = getattr(student_user, 'profile', None)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_enrollment':
            try:
                total_fee = Decimal(request.POST.get('total_fee', str(enrollment.total_fee)))
                enrollment.total_fee = max(Decimal('0.00'), total_fee)
            except Exception:
                pass

            batch_id = request.POST.get('batch_id')
            if batch_id:
                enrollment.batch_id = batch_id

            progress = int(request.POST.get('progress_percent', enrollment.progress_percent))
            is_completed = request.POST.get('is_completed') == 'true'

            # 🛑 STRICT GUARD CHECK: Cannot mark completed if student has unpaid due balance!
            if is_completed:
                if enrollment.due_amount > 0:
                    messages.error(
                        request,
                        f"⛔ CANNOT ISSUE CERTIFICATE! Student {student_user.get_full_name() or student_user.email} has a remaining due balance of ৳{enrollment.due_amount:,.2f} BDT. Full payment of ৳{enrollment.total_fee:,.2f} BDT is required before marking course as completed!"
                    )
                    is_completed = False
                    progress = min(99, progress)

            enrollment.progress_percent = min(100, max(0, progress))
            enrollment.is_completed = is_completed
            if is_completed:
                enrollment.progress_percent = 100
            enrollment.save()

            if is_completed:
                messages.success(request, f"🎉 Course Marked Completed for Student ID {enrollment.student_id}! Certificate issued.")
            elif not messages.get_messages(request):
                messages.success(request, f"Updated enrollment details for Student ID {enrollment.student_id}")

            return redirect('/superadmin/student/' + str(enrollment.id) + '/profile/')

        elif action == 'record_payment':
            try:
                amount = Decimal(request.POST.get('amount', '0'))
            except Exception:
                amount = Decimal('0')

            payment_method = request.POST.get('payment_method', 'bKash').strip()
            transaction_ref = request.POST.get('transaction_ref', '').strip()
            notes = request.POST.get('notes', '').strip()

            if amount > 0:
                payment = StudentPayment.objects.create(
                    enrollment=enrollment,
                    amount=amount,
                    payment_method=payment_method,
                    transaction_ref=transaction_ref,
                    notes=notes,
                    status='approved',
                    verified_at=timezone.now()
                )

                # Send Official PDF Invoice Email
                send_invoice_email_helper(payment, request)

                messages.success(
                    request,
                    f"💳 Recorded payment of ৳{amount:,.2f} BDT for {student_user.email} (Invoice #{payment.invoice_id}). Invoice email sent to {student_user.email}!"
                )
            else:
                messages.error(request, "Payment amount must be greater than 0.")

            return redirect('/superadmin/student/' + str(enrollment.id) + '/profile/')

    payments = enrollment.payments.all()
    batches = CourseBatch.objects.all()
    context = {
        'enrollment': enrollment,
        'student_user': student_user,
        'student_profile': student_profile,
        'payments': payments,
        'batches': batches,
    }
    return render(request, 'accounts_app/admin_student_profile.html', context)


@login_required
@user_passes_test(_is_superuser)
def admin_update_student(request, enrollment_id):
    """Super Admin: Update student progress or completion status with payment guard check."""
    enrollment = get_object_or_404(StudentEnrollment, id=enrollment_id)
    if request.method == 'POST':
        progress = int(request.POST.get('progress_percent', enrollment.progress_percent))
        is_completed = request.POST.get('is_completed') == 'true'

        # 🛑 STRICT GUARD CHECK: Cannot mark completed if student has unpaid due balance!
        if is_completed:
            if enrollment.due_amount > 0:
                messages.error(
                    request,
                    f"⛔ CANNOT ISSUE CERTIFICATE! Student {enrollment.user.get_full_name() or enrollment.user.email} has a remaining due balance of ৳{enrollment.due_amount:,.2f} BDT. Full payment of ৳{enrollment.total_fee:,.2f} BDT is required before marking course as completed!"
                )
                is_completed = False
                progress = min(99, progress)

        enrollment.progress_percent = min(100, max(0, progress))
        enrollment.is_completed = is_completed
        if is_completed:
            enrollment.progress_percent = 100
        enrollment.save()

        if is_completed:
            messages.success(request, f"Updated progress for Student ID {enrollment.student_id}")

    return redirect('/superadmin/')


@login_required
@user_passes_test(_is_superuser)
def admin_update_booking_status(request, booking_id):
    """Super Admin: Update service booking status."""
    booking = get_object_or_404(ServiceBooking, id=booking_id)
    if request.method == 'POST':
        new_status = request.POST.get('status', 'pending')
        if new_status in dict(ServiceBooking.STATUS_CHOICES):
            booking.status = new_status
            booking.save()

            if booking.user:
                create_notification(
                    user=booking.user,
                    title=f"✨ Booking Status Updated: {new_status.title()}",
                    message=f"Your service booking for '{booking.service_category}' has been updated to '{new_status.title()}'.",
                    notification_type="booking",
                    category="info",
                    link="#"
                )

            messages.success(request, f"Booking #{booking.id} status updated to {new_status.title()}")
    return redirect('/superadmin/')


def recalculate_enrollment_progress(enrollment):
    """
    Recalculates progress percentage based on total modules in the student's enrolled course track.
    Returns (progress_percent, completed_modules_count, total_modules_count).
    """
    from .models import CourseModule, StudentLessonProgress

    if not enrollment:
        return 0, 0, 12

    c_lower = enrollment.course_name.lower()
    if 'web' in c_lower or 'python' in c_lower or 'full' in c_lower or 'software' in c_lower:
        course_slug = 'web-development'
    else:
        course_slug = 'digital-marketing'

    modules = list(CourseModule.objects.filter(course_slug=course_slug).prefetch_related('lessons').all())
    total_modules_count = max(1, len(modules))

    completed_lesson_ids = set(
        StudentLessonProgress.objects.filter(
            enrollment=enrollment, is_completed=True
        ).values_list('lesson_id', flat=True)
    )

    total_module_fraction = 0.0
    completed_modules_count = 0

    for m in modules:
        m_lessons = list(m.lessons.all())
        if m_lessons:
            completed_in_m = sum(1 for l in m_lessons if l.pk in completed_lesson_ids)
            fraction = completed_in_m / len(m_lessons)
            total_module_fraction += fraction
            if completed_in_m == len(m_lessons):
                completed_modules_count += 1

    progress_percent = int((total_module_fraction / total_modules_count) * 100)
    progress_percent = min(100, max(0, progress_percent))

    need_save = False
    if enrollment.progress_percent != progress_percent:
        enrollment.progress_percent = progress_percent
        need_save = True

    if progress_percent >= 100 and not enrollment.is_completed:
        enrollment.is_completed = True
        from django.utils import timezone
        enrollment.completed_at = timezone.now()
        need_save = True

        create_notification(
            user=enrollment.user,
            title="🏆 Course Completed & Certificate Unlocked",
            message=f"Congratulations! You have completed 100% of your course video lectures for '{enrollment.course_name}'! Your verified certificate of completion is unlocked.",
            notification_type="course",
            category="success",
            link=f"/certificate/{enrollment.certificate_id}/"
        )
    elif progress_percent < 100 and enrollment.is_completed:
        enrollment.is_completed = False
        enrollment.completed_at = None
        need_save = True

    if need_save:
        enrollment.save()

    return progress_percent, completed_modules_count, total_modules_count


@login_required
def student_dashboard(request):
    """Dynamic Student Dashboard view for enrolled course students."""
    enrollments = StudentEnrollment.objects.filter(user=request.user).select_related('user', 'batch').prefetch_related('lesson_progresses')
    for e in enrollments:
        recalculate_enrollment_progress(e)

    dm_modules = [
        {"num": 1, "title": "Introduction to Digital Marketing", "desc": "Foundations, ecosystem overview & strategy frameworks", "icon": "🚀"},
        {"num": 2, "title": "Copywriting Mastery", "desc": "High-converting ad copy, landing page headlines & email sequences", "icon": "✍️"},
        {"num": 3, "title": "Content Creation & Customer Psychology", "desc": "Buyer personas, hook formulas & psychological triggers", "icon": "🧠"},
        {"num": 4, "title": "Design & AI OVC Creation", "desc": "Visual branding with Canva, AI video generation & Voiceovers", "icon": "🎨"},
        {"num": 5, "title": "Portfolio Development", "desc": "Building a high-impact personal agency portfolio site", "icon": "💼"},
        {"num": 6, "title": "Marketing Strategy & Campaign Execution", "desc": "Omnichannel campaign setup, budgets & KPI tracking", "icon": "📊"},
        {"num": "★", "title": "Live Support & Q&A Session", "desc": "1-on-1 mentor guidance & portfolio review", "icon": "💬"},
        {"num": 7, "title": "AI Content Generation", "desc": "Prompts for ChatGPT, Claude & Midjourney automation", "icon": "🤖"},
        {"num": 8, "title": "AI Chatbot Engineering", "desc": "Building automated lead gen bots for WhatsApp & FB Messenger", "icon": "💬"},
        {"num": 9, "title": "WordPress Web Building", "desc": "Building full agency websites with Elementor & WooCommerce", "icon": "🌐"},
        {"num": 10, "title": "SWOT Analysis & Audit", "desc": "Competitor intelligence, SEO audit & growth opportunities", "icon": "🔍"},
        {"num": 11, "title": "Facebook & Instagram Ads Mastery", "desc": "Pixel tracking, Custom Audiences & CBO scaling campaigns", "icon": "🎯"},
        {"num": 12, "title": "High-Ticket Sales & Client Closing", "desc": "Cold outreach, client discovery calls & closing ৳100k+ deals", "icon": "💰"},
        {"num": 13, "title": "Growth Marathon & Graduation", "desc": "24-Hour live campaign sprint & capstone project evaluation", "icon": "🏆"},
    ]

    student_batch = enrollments.first().batch if enrollments.exists() and enrollments.first().batch else None
    upcoming_live_classes = []
    assignments_list = []
    student_submissions_dict = {}

    try:
        if student_batch or request.user.is_superuser:
            from .models import LiveClassSchedule, CourseAssignment, AssignmentSubmission
            if student_batch:
                upcoming_live_classes = list(LiveClassSchedule.objects.filter(batch=student_batch, is_active=True).select_related('batch'))
                assignments_qs = CourseAssignment.objects.filter(batch=student_batch, is_active=True).select_related('batch')
            else:
                assignments_qs = CourseAssignment.objects.filter(is_active=True).select_related('batch')
            
            assignments_list = list(assignments_qs)

            primary_enrollment = enrollments.first()
            if primary_enrollment:
                user_submissions = AssignmentSubmission.objects.filter(enrollment=primary_enrollment).select_related('assignment')
                for sub in user_submissions:
                    student_submissions_dict[sub.assignment_id] = sub

        for assign in assignments_list:
            assign.user_submission = student_submissions_dict.get(assign.id, None)
    except Exception as ex:
        print(f"[WARN] student_dashboard assignments fetch info: {ex}")

    context = {
        'enrollments': enrollments,
        'dm_modules': dm_modules,
        'profile': getattr(request.user, 'profile', None),
        'upcoming_live_classes': upcoming_live_classes,
        'assignments': assignments_list,
    }
    return render(request, 'accounts_app/student_dashboard.html', context)


@login_required
def student_courses(request):
    """Student dashboard viewing enrolled courses, progress, and certificate download."""
    return student_dashboard(request)


@login_required
def student_classroom(request, lesson_id=None):
    """Full LMS Recorded Video Class Learning Portal view for enrolled students scoped strictly by course track and batch."""
    from .models import CourseModule, CourseLesson, StudentLessonProgress, StudentEnrollment, CourseBatch
    from django.db.models import Prefetch, Q

    enrollment = StudentEnrollment.objects.filter(user=request.user).first()
    if not enrollment and not request.user.is_superuser:
        messages.error(request, "Enrollment required to access student classroom portal.")
        return redirect('/')

    # Determine course track slug for enrollment
    course_slug = 'digital-marketing'
    if enrollment:
        c_lower = enrollment.course_name.lower()
        if 'web' in c_lower or 'python' in c_lower or 'full' in c_lower or 'software' in c_lower:
            course_slug = 'web-development'
        else:
            course_slug = 'digital-marketing'

    batches = list(CourseBatch.objects.all())
    default_batch = CourseBatch.objects.first()

    # Determine batch for classroom view:
    student_batch = None
    if enrollment and enrollment.batch:
        student_batch = enrollment.batch
    elif default_batch:
        student_batch = default_batch

    # Allow batch query override if provided:
    req_batch_id = request.GET.get('batch_id')
    if req_batch_id:
        student_batch = get_object_or_404(CourseBatch, pk=req_batch_id)

    # Filter lessons for target batch (or null batch) AND course_slug
    lesson_filter = Q(module__course_slug=course_slug)
    if student_batch:
        lesson_filter &= (Q(batch=student_batch) | Q(batch__isnull=True))

    if not request.user.is_superuser:
        lesson_filter &= (Q(is_published=True) | Q(scheduled_at__lte=timezone.now()) | Q(scheduled_at__isnull=True))

    all_lessons = list(CourseLesson.objects.filter(lesson_filter).select_related('module', 'batch').all())
    modules = CourseModule.objects.filter(course_slug=course_slug).prefetch_related(
        Prefetch('lessons', queryset=CourseLesson.objects.filter(lesson_filter))
    ).all()

    if not all_lessons:
        messages.info(request, f"No recorded video classes uploaded yet for {student_batch.name if student_batch else 'this batch'}.")
        return redirect('/student/dashboard/')

    # Active lesson selection
    active_lesson = None
    if lesson_id:
        active_lesson = get_object_or_404(CourseLesson, pk=lesson_id)
    else:
        active_lesson = all_lessons[0]

    # Calculate prev & next lessons
    prev_lesson = None
    next_lesson = None
    for idx, l in enumerate(all_lessons):
        if l.pk == active_lesson.pk:
            if idx > 0:
                prev_lesson = all_lessons[idx - 1]
            if idx < len(all_lessons) - 1:
                next_lesson = all_lessons[idx + 1]
            break

    # Student completion status & 12-module progress calculation
    completed_lesson_ids = set()
    progress_percent, completed_modules_count, total_modules_count = 0, 0, 12
    if enrollment:
        completed_lesson_ids = set(
            StudentLessonProgress.objects.filter(
                enrollment=enrollment, is_completed=True
            ).values_list('lesson_id', flat=True)
        )
        progress_percent, completed_modules_count, total_modules_count = recalculate_enrollment_progress(enrollment)

    is_active_completed = active_lesson.pk in completed_lesson_ids if active_lesson else False
    has_pending_due = (enrollment.due_amount > 0) if enrollment else False
    due_amount = enrollment.due_amount if enrollment else Decimal('0.00')

    context = {
        'enrollment': enrollment,
        'modules': modules,
        'all_lessons': all_lessons,
        'active_lesson': active_lesson,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'completed_lesson_ids': completed_lesson_ids,
        'is_active_completed': is_active_completed,
        'progress_percent': progress_percent,
        'total_lessons': len(all_lessons),
        'completed_count': len(completed_lesson_ids),
        'completed_modules_count': completed_modules_count,
        'total_modules': total_modules_count,
        'has_pending_due': has_pending_due,
        'due_amount': due_amount,
        'student_batch': student_batch,
        'batches': batches,
    }
    return render(request, 'accounts_app/student_classroom.html', context)


@login_required
def toggle_lesson_completion(request, lesson_id):
    """API endpoint / view to toggle completion status of a video lesson."""
    from .models import CourseLesson, StudentLessonProgress, StudentEnrollment
    from django.http import JsonResponse

    enrollment = StudentEnrollment.objects.filter(user=request.user).first()
    if not enrollment:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Enrollment required'}, status=403)
        return redirect('/student/dashboard/')

    lesson = get_object_or_404(CourseLesson, pk=lesson_id)
    progress_obj = StudentLessonProgress.objects.filter(
        enrollment=enrollment, lesson=lesson
    ).first()

    if not progress_obj:
        StudentLessonProgress.objects.create(enrollment=enrollment, lesson=lesson, is_completed=True)
        is_completed = True
    else:
        progress_obj.delete()
        is_completed = False

    # Recalculate progress % based on 12 total modules
    progress_percent, completed_modules_count, total_modules_count = recalculate_enrollment_progress(enrollment)

    if is_completed:
        create_notification(
            user=request.user,
            title="▶️ Class Lesson Completed",
            message=f"Completed lesson '{lesson.title}'. Overall course progress is now {progress_percent}%.",
            notification_type="course",
            category="info",
            link=f"/student/classroom/lesson/{lesson.id}/"
        )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'is_completed': is_completed,
            'progress_percent': progress_percent,
            'completed_count': StudentLessonProgress.objects.filter(enrollment=enrollment, is_completed=True).count(),
            'total_lessons': CourseLesson.objects.count(),
            'completed_modules_count': completed_modules_count,
            'total_modules': total_modules_count
        })

    next_url = request.GET.get('next', f'/student/classroom/lesson/{lesson_id}/')
    return redirect(next_url)


@never_cache
@login_required
@user_passes_test(_is_superuser)
def admin_manage_modules(request):
    """Super Admin console to add/edit modules, create batches, and upload/edit recorded video classes per batch."""
    from .models import CourseModule, CourseLesson, CourseBatch

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_batch':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            if name:
                try:
                    batch = CourseBatch.objects.create(name=name, description=description)
                    messages.success(request, f"🎉 New Batch '{batch.name}' created successfully!")
                except Exception as ex:
                    messages.error(request, f"Could not create batch: {ex}")

        elif action == 'add_module':
            title = request.POST.get('title', '').strip()
            module_number = request.POST.get('module_number', 1)
            description = request.POST.get('description', '').strip()
            course_slug = request.POST.get('course_slug', 'digital-marketing').strip()
            if title:
                CourseModule.objects.create(
                    title=title, module_number=module_number, description=description, order=module_number, course_slug=course_slug
                )
                messages.success(request, f"Module '{title}' created successfully for {course_slug} track!")

        elif action == 'edit_module':
            module_id = request.POST.get('module_id')
            module = get_object_or_404(CourseModule, pk=module_id)
            module.title = request.POST.get('title', '').strip()
            module.module_number = request.POST.get('module_number', module.module_number)
            module.description = request.POST.get('description', '').strip()
            module.save()
            messages.success(request, f"Module '{module.title}' updated successfully!")

        elif action == 'delete_module':
            module_id = request.POST.get('module_id')
            module = get_object_or_404(CourseModule, pk=module_id)
            module.delete()
            messages.success(request, "Module deleted successfully!")

        elif action == 'add_lesson':
            module_id = request.POST.get('module_id')
            batch_id = request.POST.get('batch_id')
            title = request.POST.get('title', '').strip()
            video_url = request.POST.get('video_url', '').strip()
            duration = request.POST.get('duration', '01:00:00').strip()
            notes = request.POST.get('notes', '').strip()

            batch = get_object_or_404(CourseBatch, pk=batch_id) if batch_id else None

            if module_id and title and video_url:
                module = get_object_or_404(CourseModule, pk=module_id)
                new_lesson = CourseLesson.objects.create(
                    module=module,
                    batch=batch,
                    title=title,
                    video_url=video_url,
                    duration=duration,
                    notes=notes,
                    scheduled_at=None,
                    is_published=True,
                    auto_email_sent=True
                )
                messages.success(request, f"🎉 Recorded Class '{title}' uploaded & published! Enrolled students have been notified via email & dashboard.")
                notify_students_new_lesson(new_lesson)

        elif action == 'edit_lesson':
            lesson_id = request.POST.get('lesson_id')
            lesson = get_object_or_404(CourseLesson, pk=lesson_id)
            module_id = request.POST.get('module_id')
            batch_id = request.POST.get('batch_id')
            if module_id:
                lesson.module = get_object_or_404(CourseModule, pk=module_id)
            if batch_id:
                lesson.batch = get_object_or_404(CourseBatch, pk=batch_id)
            else:
                lesson.batch = None
            lesson.title = request.POST.get('title', '').strip()
            lesson.video_url = request.POST.get('video_url', '').strip()
            lesson.duration = request.POST.get('duration', '01:00:00').strip()
            lesson.notes = request.POST.get('notes', '').strip()
            lesson.save()
            messages.success(request, f"Class '{lesson.title}' updated successfully!")
            notify_students_updated_lesson(lesson)

        elif action == 'delete_lesson':
            lesson_id = request.POST.get('lesson_id')
            lesson = get_object_or_404(CourseLesson, pk=lesson_id)
            lesson.delete()
            messages.success(request, "Recorded Class deleted successfully!")

        if request.headers.get('HX-Request') or request.META.get('HTTP_HX_REQUEST'):
            batches = CourseBatch.objects.all()
            selected_batch_id = request.GET.get('batch_id')
            active_batch = None
            if selected_batch_id:
                active_batch = get_object_or_404(CourseBatch, pk=selected_batch_id)
            modules = CourseModule.objects.prefetch_related('lessons').order_by('course_slug', 'order', 'module_number').all()
            return render(request, 'accounts_app/_modules_list_partial.html', {
                'modules': modules,
                'batches': batches,
                'active_batch': active_batch,
                'selected_batch_id': selected_batch_id,
            })

        return redirect('/student/classroom/admin/')

    from .models import CourseModule, CourseLesson, CourseBatch

    if CourseModule.objects.count() == 0:
        default_modules = [
            # Track 1: Web Development & AI Software Engineering
            (1, "Python Fundamentals & Data Structures", "Master Python syntax, variables, lists, dictionaries, functions, and control flow."),
            (2, "Object-Oriented Programming (OOP) & Design Patterns", "Deep dive into classes, inheritance, encapsulation, polymorphism, and modular architecture."),
            (3, "HTML5, Modern CSS3 & Responsive Web Design", "Build responsive layouts using Flexbox, CSS Grid, custom properties, and modern UI design principles."),
            (4, "JavaScript ES6+, DOM & Async Programming", "Learn interactive web programming, DOM manipulation, promises, fetch API, and async/await."),
            (5, "Django Web Framework Core & Routing", "Get started with Django, project architecture, MVT pattern, and URL routing."),
            (6, "Django Models, ORM & Database Design", "Design relational databases with SQLite/PostgreSQL, migrations, QuerySets, and relationships."),
            (7, "Django Forms, Authentication & AllAuth", "Implement secure user registration, login, session management, password resets, and user profiles."),
            (8, "REST APIs & Django REST Framework (DRF)", "Build RESTful APIs with serializers, viewsets, authentication permissions, and JSON responses."),
            (9, "AI Integration, LLM APIs & Automation", "Integrate OpenAI/Gemini AI APIs, prompt engineering, background tasks, and AI automation."),
            (10, "Full-Stack Capstone Project Deployment & DevOps", "Deploy production Django web applications with Gunicorn, Nginx, environment configs, and SSL."),
            
            # Track 2: Digital Marketing & Growth Hacking (Modules 01-13)
            (11, "Introduction to Digital Marketing", "Understand the digital marketing ecosystem, funnel architecture, audience segmentation, and channel strategies."),
            (12, "Copywriting Mastery", "Master the art of high-converting sales copy, persuasive headlines, and psychological frameworks that sell."),
            (13, "Content Creation & Customer Psychology", "Decode consumer behavior, emotional buying triggers, and build content calendars that engage audiences."),
            (14, "Design & AI OVC Creation", "Create professional visual assets, graphics, and AI-generated Short Videos/OVC (Online Video Clips)."),
            (15, "Portfolio Development", "Build your personal brand portfolio showcase to attract high-paying international clients and local agencies."),
            (16, "Marketing Strategy & Campaign Execution", "Plan end-to-end marketing campaigns, set KPIs, budget allocation, and execute under expert guidance."),
            (17, "AI Content Generation", "Leverage ChatGPT, Claude, and Gemini AI prompt engineering to write articles, emails, and ad copies 10x faster."),
            (18, "AI Chatbot Automation", "Build automated lead-generation and customer support chatbots for websites, Facebook Messenger, and WhatsApp."),
            (19, "WordPress Website Development", "Design and launch high-converting sales landing pages and e-commerce websites with WordPress & Elementor."),
            (20, "SWOT Analysis & Market Research", "Analyze competitors, evaluate business Strengths, Weaknesses, Opportunities, and Threats to gain market share."),
            (21, "FB Ads (Facebook & Meta Advertising)", "Master Meta Business Manager, Ads Manager, Pixel setup, Custom Audiences, Retargeting, and CBO campaigns."),
            (22, "Sales & Client Acquisition", "Learn how to pitch clients, handle objections, close high-ticket sales deals, and secure monthly retainer contracts."),
            (23, "Marketing Marathon & Real Budget Campaign (Capstone Marathon)", "Deploy live multi-channel marketing campaigns under mentor supervision.")
        ]
        for num, title, desc in default_modules:
            slug = 'web-development' if num <= 10 else 'digital-marketing'
            CourseModule.objects.create(module_number=num, order=num, title=title, description=desc, course_slug=slug)

    batches = CourseBatch.objects.all()
    selected_batch_id = request.GET.get('batch_id')
    active_batch = None
    if selected_batch_id:
        active_batch = get_object_or_404(CourseBatch, pk=selected_batch_id)

    modules = CourseModule.objects.prefetch_related('lessons').order_by('course_slug', 'order', 'module_number').all()

    if request.headers.get('HX-Request') or request.META.get('HTTP_HX_REQUEST'):
        return render(request, 'accounts_app/_modules_list_partial.html', {
            'modules': modules,
            'batches': batches,
            'active_batch': active_batch,
            'selected_batch_id': selected_batch_id,
        })

    return render(request, 'accounts_app/admin_manage_modules.html', {
        'modules': modules,
        'batches': batches,
        'active_batch': active_batch,
        'selected_batch_id': selected_batch_id,
    })


def send_live_class_notifications(live_class, request=None):
    """
    Dispatches real-time bell notifications AND sends HTML email invitations to target batch students or registered students.
    """
    from .models import StudentEnrollment
    from django.contrib.auth.models import User
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.conf import settings

    batch = live_class.batch
    enrollments = StudentEnrollment.objects.filter(batch=batch).select_related('user')

    target_users = []
    if enrollments.exists():
        for e in enrollments:
            if e.user and e.user.email and e.user not in target_users:
                target_users.append(e.user)

    # Fallback: If no specific enrollments exist for this batch, notify active student users
    if not target_users:
        target_users = list(User.objects.filter(is_active=True, is_superuser=False).exclude(email=''))

    sent_emails_count = 0
    notifications_count = 0

    formatted_time = live_class.scheduled_at.strftime('%A, %b %d, %Y at %I:%M %p')

    for student_user in target_users:
        student_name = student_user.get_full_name() or student_user.username or student_user.email

        # 1. Real-time Dashboard Bell & Hub Notification
        try:
            create_notification(
                user=student_user,
                title=f"🎥 Live Class Scheduled: {live_class.title}",
                message=f"Live class session for '{batch.name}' is scheduled on {formatted_time}. Click to join Google Meet / Zoom!",
                notification_type="course",
                category="info",
                link=live_class.meeting_link
            )
            notifications_count += 1
        except Exception as ex:
            print(f"Error creating notification for {student_user.email}: {ex}")

        # 2. HTML Email Invitation
        try:
            email_subject = f"[Live Class Invitation] {live_class.title} — {batch.name}"
            
            context = {
                'student_name': student_name,
                'batch_name': batch.name,
                'class_title': live_class.title,
                'scheduled_time': formatted_time,
                'duration': live_class.duration,
                'instructor_name': live_class.instructor_name,
                'agenda': live_class.agenda,
                'meeting_link': live_class.meeting_link,
            }

            html_content = render_to_string('account/email/live_class_invitation.html', context)
            text_content = f"Dear {student_name},\n\nYou are invited to join a Live Class for {batch.name}.\nTitle: {live_class.title}\nDate & Time: {formatted_time}\nMeeting Link: {live_class.meeting_link}\n\nQrious Tech Academy"

            msg = EmailMultiAlternatives(
                subject=email_subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[student_user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)
            sent_emails_count += 1
            print(f"[OK] Successfully sent live class invitation email to {student_user.email}")
        except Exception as ex:
            print(f"[ERROR] Error sending live class email to {student_user.email}: {ex}")

    return notifications_count, sent_emails_count


def send_class_recording_notifications(live_class, request=None):
    """
    Dispatches real-time bell notifications AND sends HTML email notifications to target batch students or registered students.
    """
    from .models import StudentEnrollment
    from django.contrib.auth.models import User
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.conf import settings

    batch = live_class.batch
    enrollments = StudentEnrollment.objects.filter(batch=batch).select_related('user')

    target_users = []
    if enrollments.exists():
        for e in enrollments:
            if e.user and e.user.email and e.user not in target_users:
                target_users.append(e.user)

    if not target_users:
        target_users = list(User.objects.filter(is_active=True, is_superuser=False).exclude(email=''))

    sent_emails_count = 0
    notifications_count = 0

    recording_link = live_class.recording_url or live_class.meeting_link

    for student_user in target_users:
        student_name = student_user.get_full_name() or student_user.username or student_user.email

        # 1. Real-time Dashboard Bell Notification
        try:
            create_notification(
                user=student_user,
                title=f"🎥 Class Video Recording Available: {live_class.title}",
                message=f"The video recording for '{live_class.title}' ({batch.name}) is now live! Click to watch recorded class video.",
                notification_type="course",
                category="info",
                link=recording_link
            )
            notifications_count += 1
        except Exception as ex:
            print(f"Error creating notification for {student_user.email}: {ex}")

        # 2. HTML Email Notification to Target Batch
        try:
            email_subject = f"[Class Recording Available] 🎥 {live_class.title} — {batch.name}"
            
            context = {
                'student_name': student_name,
                'batch_name': batch.name,
                'class_title': live_class.title,
                'instructor_name': live_class.instructor_name,
                'agenda': live_class.agenda,
                'recording_url': recording_link,
            }

            html_content = render_to_string('account/email/class_recording_notification.html', context)
            text_content = f"Dear {student_name},\n\nThe class video recording for '{live_class.title}' ({batch.name}) is now available.\nWatch Video: {recording_link}\n\nQrious Tech Academy"

            msg = EmailMultiAlternatives(
                subject=email_subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[student_user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)
            sent_emails_count += 1
            print(f"[OK] Successfully sent class recording email to {student_user.email}")
        except Exception as ex:
            print(f"[ERROR] Error sending class recording email to {student_user.email}: {ex}")

    return notifications_count, sent_emails_count


@never_cache
@user_passes_test(lambda u: u.is_superuser or u.is_staff, login_url='/auth/login/')
def admin_manage_live_classes(request):
    """Super Admin Console to schedule live video class sessions and upload class recordings for target batches."""
    from .models import LiveClassSchedule, CourseBatch
    from django.utils import timezone
    import datetime

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_live_class':
            batch_id = request.POST.get('batch_id')
            title = request.POST.get('title', '').strip()
            meeting_link = request.POST.get('meeting_link', '').strip()
            recording_url = request.POST.get('recording_url', '').strip()
            scheduled_date_str = request.POST.get('scheduled_date', '').strip()
            scheduled_time_str = request.POST.get('scheduled_time', '').strip()
            duration = request.POST.get('duration', '1 Hour').strip()
            instructor_name = request.POST.get('instructor_name', 'Qrious Tech Senior Mentor').strip()
            agenda = request.POST.get('agenda', '').strip()

            batch = get_object_or_404(CourseBatch, pk=batch_id)

            if title and meeting_link and scheduled_date_str and scheduled_time_str:
                try:
                    dt_str = f"{scheduled_date_str} {scheduled_time_str}"
                    scheduled_at = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                    scheduled_at = timezone.make_aware(scheduled_at)

                    live_class = LiveClassSchedule.objects.create(
                        batch=batch,
                        title=title,
                        meeting_link=meeting_link,
                        scheduled_at=scheduled_at,
                        duration=duration,
                        instructor_name=instructor_name,
                        agenda=agenda
                    )

                    notif_cnt, email_cnt = send_live_class_notifications(live_class, request)
                    live_class.auto_email_sent = True
                    live_class.save()

                    if email_cnt > 0:
                        messages.success(
                            request,
                            f"🚀 Live Class '{title}' scheduled for {batch.name} on {scheduled_at.strftime('%b %d, %Y @ %I:%M %p')}! Sent {notif_cnt} dashboard alerts & {email_cnt} HTML email invitations."
                        )
                    else:
                        messages.success(
                            request,
                            f"📅 Live Class '{title}' scheduled for {batch.name} on {scheduled_at.strftime('%b %d, %Y @ %I:%M %p')}! (Note: {notif_cnt} dashboard alerts sent, 0 email invitations sent — check if students are enrolled in {batch.name})."
                        )

                    if getattr(settings, 'EMAIL_BACKEND', '').endswith('console.EmailBackend'):
                        messages.warning(
                            request,
                            "⚠️ REAL EMAIL DELIVERY NOTICE: Emails are currently printed in server terminal because EMAIL_HOST_PASSWORD is not set in .env. To send real emails to Gmail inboxes, set EMAIL_HOST_PASSWORD=your_app_password in .env!"
                        )

                    # Redirect with created ID so template shows WhatsApp share modal
                    return redirect(f'/superadmin/live-classes/?created={live_class.id}')
                except Exception as ex:
                    messages.error(request, f"Could not schedule live class: {ex}")
            else:
                messages.error(request, "Please fill in all required fields (Batch, Title, Meeting Link, Date, Time).")

        elif action == 'resend_invitation':
            class_id = request.POST.get('class_id')
            live_class = get_object_or_404(LiveClassSchedule, pk=class_id)
            notif_cnt, email_cnt = send_live_class_notifications(live_class, request)
            messages.success(
                request,
                f"📢 Re-sent invitations for '{live_class.title}'! Dispatched {notif_cnt} notifications & {email_cnt} HTML emails."
            )
            if getattr(settings, 'EMAIL_BACKEND', '').endswith('console.EmailBackend'):
                messages.warning(
                    request,
                    "⚠️ REAL EMAIL DELIVERY NOTICE: Real emails were NOT delivered to Gmail inboxes because EMAIL_HOST_PASSWORD is missing in your .env file (emails printed to terminal instead). Add EMAIL_HOST_PASSWORD=your_gmail_app_password to .env to send real emails!"
                )

        elif action == 'toggle_status':
            class_id = request.POST.get('class_id')
            live_class = get_object_or_404(LiveClassSchedule, pk=class_id)
            live_class.is_active = not live_class.is_active
            live_class.save()
            messages.info(request, f"Updated status of '{live_class.title}' to {'Active' if live_class.is_active else 'Cancelled'}.")

        elif action == 'delete_live_class':
            class_id = request.POST.get('class_id')
            live_class = get_object_or_404(LiveClassSchedule, pk=class_id)
            title = live_class.title
            live_class.delete()
            messages.success(request, f"Deleted live class '{title}'.")

        return redirect('/superadmin/live-classes/')

    live_classes = LiveClassSchedule.objects.select_related('batch').all()
    batches = CourseBatch.objects.all()

    # WhatsApp share text — shown in modal after scheduling a new class
    whatsapp_text = ''
    whatsapp_created_class = None
    created_id = request.GET.get('created')
    if created_id:
        try:
            whatsapp_created_class = LiveClassSchedule.objects.select_related('batch').get(pk=created_id)
            lc = whatsapp_created_class
            time_str = lc.scheduled_at.strftime('%I:%M %p').lstrip('0')
            date_str = lc.scheduled_at.strftime('%d %B %Y')
            whatsapp_text = (
                f"📡 {lc.batch.name} — {lc.title}\n\n"
                f"Hello Learner! 👋\n"
                f"Your live class *\"{lc.title}\"* will be held on *{date_str}* at *{time_str}*.\n\n"
                f"🔗 Meeting Link: {lc.meeting_link}\n\n"
                f"⏱ Duration: {lc.duration}\n"
                f"👨‍🏫 Mentor: {lc.instructor_name}\n"
            )
            if lc.agenda:
                whatsapp_text += f"\n📌 Agenda:\n{lc.agenda}\n"
            whatsapp_text += "\nPlease join on time. Looking forward to seeing you in the class! 🎓\n— *Qrious Tech Academy*"
        except LiveClassSchedule.DoesNotExist:
            pass

    context = {
        'live_classes': live_classes,
        'batches': batches,
        'whatsapp_text': whatsapp_text,
        'whatsapp_created_class': whatsapp_created_class,
    }
    return render(request, 'accounts_app/admin_manage_live_classes.html', context)


def certificate_detail(request, cert_id):
    """Render printable certificate with student credentials and dynamic scannable QR Code."""
    enrollment = get_object_or_404(StudentEnrollment, certificate_id=cert_id)

    # Security Lock: If student has pending tuition due and user is not superuser, block certificate view & download!
    if enrollment.due_amount > 0 and not (request.user.is_authenticated and request.user.is_superuser):
        context = {
            'enrollment': enrollment,
            'locked_due': enrollment.due_amount,
        }
        return render(request, 'accounts_app/certificate_locked.html', context)

    # Generate QR Code image for certificate verification URL
    verify_url = request.build_absolute_uri(f"/verify-certificate/{cert_id}/")
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    context = {
        'enrollment': enrollment,
        'verify_url': verify_url,
        'qr_base64': qr_base64,
    }
    return render(request, 'accounts_app/certificate.html', context)


def verify_certificate(request, cert_id=None):
    """Public certificate verification system supporting GET and POST searches."""
    query_cert = cert_id or request.GET.get('cert_id', '').strip() or request.POST.get('cert_id', '').strip()
    enrollment = None
    searched = False

    if query_cert:
        searched = True
        enrollment = StudentEnrollment.objects.filter(
            Q(certificate_id__iexact=query_cert) | Q(student_id__iexact=query_cert)
        ).first()

    return render(request, 'accounts_app/verify_certificate.html', {
        'enrollment': enrollment,
        'query_cert': query_cert,
        'searched': searched,
    })


def download_invoice_pdf(request, invoice_id):
    """Generate and serve official PDF invoice file for download."""
    payment = get_object_or_404(StudentPayment, invoice_id=invoice_id)

    if not request.user.is_superuser and request.user != payment.enrollment.user:
        messages.error(request, "Permission denied.")
        return redirect('/')

    from .pdf_utils import generate_invoice_pdf
    pdf_bytes = generate_invoice_pdf(payment)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Invoice_{payment.invoice_id}.pdf"'
    return response


def view_invoice_detail(request, invoice_id):
    """View printable online HTML invoice receipt."""
    payment = get_object_or_404(StudentPayment, invoice_id=invoice_id)
    enrollment = payment.enrollment
    student_user = enrollment.user

    context = {
        'payment': payment,
        'enrollment': enrollment,
        'student_user': student_user,
    }
    return render(request, 'accounts_app/invoice_detail.html', context)


# ─── STUDENT PAYMENT UPLOAD & SUPER ADMIN VERIFICATION SYSTEM ─────────────────────────

def send_invoice_email_helper(payment, request=None):
    """Generates PDF invoice and emails official HTML receipt to student."""
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings
        from .pdf_utils import generate_invoice_pdf

        enrollment = payment.enrollment
        student_user = enrollment.user
        pdf_bytes = generate_invoice_pdf(payment)

        if request:
            invoice_url = request.build_absolute_uri(f"/invoice/{payment.invoice_id}/")
        else:
            invoice_url = f"http://127.0.0.1:8001/invoice/{payment.invoice_id}/"

        email_subject = f"[Official Invoice Receipt] Payment Verified #{payment.invoice_id} — Qrious Tech Academy"
        
        text_body = f"""Dear {student_user.get_full_name() or student_user.email},

Your payment of ৳{payment.amount:,.2f} BDT has been successfully verified and approved by Qrious Tech Academy!

Invoice ID: #{payment.invoice_id}
Amount Paid: ৳{payment.amount:,.2f} BDT
Payment Method: {payment.payment_method}
Transaction Ref: {payment.transaction_ref or 'N/A'}
Course: {enrollment.course_name}
Remaining Due Balance: ৳{enrollment.due_amount:,.2f} BDT

View Online Invoice: {invoice_url}

Warm regards,
Qrious Tech Academy Engineering & Billing Team
Email: mdsiamh77@gmail.com | Phone / WhatsApp: +971 566631501
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#070913;font-family:'Inter',sans-serif;color:#f8fafc;">
<table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#070913;padding:40px 10px;">
<tr><td align="center">
<table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width:600px;background-color:#0d1222;border:1px solid rgba(255,255,255,0.12);border-radius:20px;overflow:hidden;box-shadow:0 25px 50px -12px rgba(0,0,0,0.7);">
<tr><td style="height:5px;background:linear-gradient(90deg,#059669,#10b981,#0284c7);"></td></tr>
<tr>
<td style="padding:28px 32px;border-bottom:1px solid rgba(255,255,255,0.08);">
    <table width="100%">
    <tr>
        <td>
            <table role="presentation" border="0" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="vertical-align: middle; padding-right: 12px;">
                        <img src="http://127.0.0.1:8001/static/images/logo.png" alt="Qrious Tech Academy" width="38" height="38" style="width: 38px; height: 38px; display: block; border: 0; object-fit: contain;">
                    </td>
                    <td style="vertical-align: middle;">
                        <div style="font-size:20px;font-weight:900;color:#ffffff;line-height:1.2;">Qrious Tech <span style="color:#0284c7;font-size:13px;display:block;">Academy</span></div>
                    </td>
                </tr>
            </table>
        </td>
        <td align="right" style="vertical-align: middle;"><span style="font-size:11px;font-weight:700;color:#10b981;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);padding:5px 14px;border-radius:20px;">✅ PAYMENT VERIFIED</span></td>
    </tr>
    </table>
</td>
</tr>
<tr>
<td style="padding:36px 32px;">
    <h1 style="font-size:22px;font-weight:800;color:#ffffff;margin:0 0 16px 0;">Payment Approved & Invoice Issued 🎉</h1>
    <p style="font-size:15px;color:#94a3b8;line-height:1.6;margin:0 0 24px 0;">Dear <strong style="color:#ffffff;">{student_user.get_full_name() or student_user.email}</strong>, your payment of <strong style="color:#10b981;">৳{payment.amount:,.2f} BDT</strong> has been successfully verified and approved!</p>
    
    <div style="background-color:#131b2e;border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:20px;margin-bottom:24px;">
        <table width="100%" style="font-size:13.5px;color:#cbd5e1;">
            <tr><td style="padding:6px 0;color:#64748b;">Invoice ID:</td><td align="right" style="font-weight:800;color:#0284c7;font-family:monospace;">#{payment.invoice_id}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Amount Paid:</td><td align="right" style="font-weight:800;color:#10b981;">৳{payment.amount:,.2f} BDT</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Payment Method:</td><td align="right" style="font-weight:700;color:#ffffff;">{payment.payment_method}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">TrxID / Reference:</td><td align="right" style="font-weight:700;color:#38bdf8;font-family:monospace;">{payment.transaction_ref or 'N/A'}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Enrolled Course:</td><td align="right" style="font-weight:700;color:#ffffff;">{enrollment.course_name}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Remaining Due:</td><td align="right" style="font-weight:800;color:#f59e0b;">৳{enrollment.due_amount:,.2f} BDT</td></tr>
        </table>
    </div>

    <p style="font-size:14px;color:#94a3b8;margin:0 0 24px 0;">📄 Your official PDF invoice receipt is attached to this email. You can also view or download your invoice online anytime:</p>

    <div align="center" style="margin-bottom:28px;">
        <a href="{invoice_url}" target="_blank" style="background:linear-gradient(135deg,#2563eb,#0284c7);color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:12px;font-size:14px;font-weight:700;display:inline-block;">📄 View Official Online Invoice ↗</a>
    </div>
</td>
</tr>
<tr>
<td style="padding:20px 32px;background-color:#070913;text-align:center;font-size:11px;color:#64748b;">
    Qrious Tech Academy Engineering & Billing Support<br>
    Email: mdsiamh77@gmail.com | WhatsApp: +971 566631501
</td>
</tr>
</table>
</td></tr>
</table>
</body>
</html>"""

        msg = EmailMultiAlternatives(
            subject=email_subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student_user.email]
        )
        msg.attach_alternative(html_body, "text/html")
        msg.attach(f"Invoice_{payment.invoice_id}.pdf", pdf_bytes, "application/pdf")
        msg.send(fail_silently=True)
        return True
    except Exception as ex:
        print(f"Error sending invoice email: {ex}")
        return False


def send_payment_decline_email_helper(payment, admin_notes='', request=None):
    """Sends an official notification HTML email to the student when their payment submission is declined."""
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings

        enrollment = payment.enrollment
        student_user = enrollment.user

        email_subject = f"[Payment Submission Declined] Invoice #{payment.invoice_id} — Qrious Tech Academy"
        remarks_str = admin_notes if admin_notes else "Please verify your transaction reference ID (TrxID), payment method, or uploaded screenshot proof and re-submit your payment details from your student dashboard."

        text_body = f"""Dear {student_user.get_full_name() or student_user.email},

We are writing to inform you that your payment submission #{payment.invoice_id} of ৳{payment.amount:,.2f} BDT was DECLINED by our billing verification team.

Invoice ID: #{payment.invoice_id}
Submitted Amount: ৳{payment.amount:,.2f} BDT
Remarks: {remarks_str}

Please log into your Student Dashboard at http://127.0.0.1:8001/student/dashboard/#invoices to re-submit your payment proof.

Warm regards,
Qrious Tech Academy Billing & Support Team
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#070913;font-family:'Inter',sans-serif;color:#f8fafc;">
<table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#070913;padding:40px 10px;">
<tr><td align="center">
<table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width:600px;background-color:#0d1222;border:1px solid rgba(255,255,255,0.12);border-radius:20px;overflow:hidden;box-shadow:0 25px 50px -12px rgba(0,0,0,0.7);">
<tr><td style="height:5px;background:linear-gradient(90deg,#ef4444,#f59e0b,#8b5cf6);"></td></tr>
<tr>
<td style="padding:28px 32px;border-bottom:1px solid rgba(255,255,255,0.08);">
    <table width="100%">
    <tr>
        <td>
            <table role="presentation" border="0" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="vertical-align: middle; padding-right: 12px;">
                        <img src="http://127.0.0.1:8001/static/images/logo.png" alt="Qrious Tech Academy" width="38" height="38" style="width: 38px; height: 38px; display: block; border: 0; object-fit: contain;">
                    </td>
                    <td style="vertical-align: middle;">
                        <div style="font-size:20px;font-weight:900;color:#ffffff;line-height:1.2;">Qrious Tech <span style="color:#0284c7;font-size:13px;display:block;">Academy</span></div>
                    </td>
                </tr>
            </table>
        </td>
        <td align="right" style="vertical-align: middle;"><span style="font-size:11px;font-weight:700;color:#ef4444;background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);padding:5px 14px;border-radius:20px;">❌ SUBMISSION DECLINED</span></td>
    </tr>
    </table>
</td>
</tr>
<tr>
<td style="padding:36px 32px;">
    <h1 style="font-size:22px;font-weight:800;color:#ffffff;margin:0 0 16px 0;">Payment Proof Declined ⚠️</h1>
    <p style="font-size:15px;color:#94a3b8;line-height:1.6;margin:0 0 24px 0;">Dear <strong style="color:#ffffff;">{student_user.get_full_name() or student_user.email}</strong>, your recent payment submission of <strong style="color:#ef4444;">৳{payment.amount:,.2f} BDT</strong> was declined by our billing team.</p>
    
    <div style="background-color:#131b2e;border:1px solid rgba(239,68,68,0.3);border-radius:14px;padding:20px;margin-bottom:24px;">
        <div style="font-size:11px;font-weight:700;color:#ef4444;text-transform:uppercase;margin-bottom:6px;">⚠️ Reason / Admin Remarks</div>
        <div style="font-size:13.5px;color:#f8fafc;line-height:1.5;">{remarks_str}</div>
    </div>

    <div style="background-color:#131b2e;border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:20px;margin-bottom:24px;">
        <table width="100%" style="font-size:13.5px;color:#cbd5e1;">
            <tr><td style="padding:6px 0;color:#64748b;">Invoice ID:</td><td align="right" style="font-weight:800;color:#0284c7;font-family:monospace;">#{payment.invoice_id}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Submitted Amount:</td><td align="right" style="font-weight:800;color:#ef4444;">৳{payment.amount:,.2f} BDT</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Payment Method:</td><td align="right" style="font-weight:700;color:#ffffff;">{payment.payment_method}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">TrxID / Reference:</td><td align="right" style="font-weight:700;color:#38bdf8;font-family:monospace;">{payment.transaction_ref or 'N/A'}</td></tr>
        </table>
    </div>

    <div align="center" style="margin-bottom:28px;">
        <a href="http://127.0.0.1:8001/student/dashboard/#invoices" target="_blank" style="background:linear-gradient(135deg,#2563eb,#0284c7);color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:12px;font-size:14px;font-weight:700;display:inline-block;">🔄 Re-Submit Payment Proof ↗</a>
    </div>
</td>
</tr>
<tr>
<td style="padding:20px 32px;background-color:#070913;text-align:center;font-size:11px;color:#64748b;">
    Qrious Tech Academy Engineering & Billing Support<br>
    Email: mdsiamh77@gmail.com | WhatsApp: +971 566631501
</td>
</tr>
</table>
</td></tr>
</table>
</body>
</html>"""

        msg = EmailMultiAlternatives(
            subject=email_subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student_user.email]
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=True)
        return True
    except Exception as ex:
        print(f"Error sending payment decline email: {ex}")
        return False


def send_admin_payment_notification_email_helper(payment, request=None):
    """
    Sends an automated HTML email alert to Super Admin(s) when a student submits a payment for verification,
    complete with payment details, student info, and direct link to the admin verification console route.
    """
    try:
        from django.contrib.auth.models import User
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings

        enrollment = payment.enrollment
        student_user = enrollment.user

        # Admin verification URL (with query filter so admin sees this specific payment)
        if request:
            admin_verify_url = request.build_absolute_uri(f'/admin-payments/?q={payment.invoice_id}')
        else:
            admin_verify_url = f"https://qrious-tech.vercel.app/admin-payments/?q={payment.invoice_id}"

        # Target superadmins / staff users
        admin_emails = list(
            User.objects.filter(is_active=True, is_superuser=True)
            .exclude(email='')
            .values_list('email', flat=True)
        )
        if not admin_emails:
            admin_emails = ['mdsiamh77@gmail.com']

        email_subject = f"[Action Required] 💳 New Payment Submission #{payment.invoice_id} — {student_user.get_full_name() or student_user.email}"
        
        submitted_at_str = payment.created_at.strftime('%A, %b %d, %Y at %I:%M %p')

        context = {
            'student_name': student_user.get_full_name() or student_user.username or student_user.email,
            'student_email': student_user.email,
            'student_id': enrollment.student_id,
            'course_name': enrollment.course_name,
            'batch_name': enrollment.batch.name if enrollment.batch else 'Batch 01',
            'invoice_id': payment.invoice_id,
            'amount': payment.amount,
            'payment_method': payment.payment_method,
            'transaction_ref': payment.transaction_ref,
            'submitted_at': submitted_at_str,
            'student_notes': payment.notes,
            'admin_verify_url': admin_verify_url,
        }

        html_body = render_to_string('account/email/admin_payment_submission_alert.html', context)
        text_body = f"""New Payment Submission Pending Verification:
Invoice ID: #{payment.invoice_id}
Student: {student_user.get_full_name() or student_user.email} ({student_user.email})
Amount: BDT {payment.amount:,.2f}
Method: {payment.payment_method}
TrxID: {payment.transaction_ref or 'N/A'}
Date: {submitted_at_str}

Verify Payment in Admin Console: {admin_verify_url}
"""

        for admin_email in set(admin_emails):
            try:
                msg = EmailMultiAlternatives(
                    subject=email_subject,
                    body=text_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[admin_email]
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send(fail_silently=False)
                print(f"[OK] Sent admin payment notification email to {admin_email}")
            except Exception as ex:
                print(f"[ERROR] Error sending payment notification email to admin {admin_email}: {ex}")

        return True
    except Exception as ex:
        print(f"[ERROR] Error in send_admin_payment_notification_email_helper: {ex}")
        return False


@login_required
def student_upload_payment(request):
    """Student: Upload payment proof screenshot / record transaction for verification."""
    if request.method == 'POST':
        enrollment = StudentEnrollment.objects.filter(user=request.user).first()
        if not enrollment:
            messages.error(request, "No active course enrollment found.")
            return redirect('/student/dashboard/')

        try:
            amount_raw = request.POST.get('amount', '0').strip()
            amount = Decimal(amount_raw)
            payment_method = request.POST.get('payment_method', 'bKash').strip()
            transaction_ref = request.POST.get('transaction_ref', '').strip()
            notes = request.POST.get('notes', '').strip()
            payment_proof = request.FILES.get('payment_proof', None)
            proof_image_data = None
            if payment_proof:
                try:
                    import base64
                    file_bytes = payment_proof.read()
                    encoded = base64.b64encode(file_bytes).decode('utf-8')
                    mime = getattr(payment_proof, 'content_type', None) or 'image/png'
                    proof_image_data = f"data:{mime};base64,{encoded}"
                    payment_proof.seek(0)
                except Exception:
                    pass

            if amount <= Decimal('0'):
                messages.error(request, "Please enter a valid payment amount greater than 0.")
                return redirect('/student/dashboard/#invoices')

            payment = StudentPayment.objects.create(
                enrollment=enrollment,
                amount=amount,
                payment_method=payment_method,
                transaction_ref=transaction_ref,
                notes=notes,
                payment_proof=payment_proof,
                proof_image_data=proof_image_data,
                status='pending'
            )

            # 📧 Send Automated Email Notification to Super Admin for Verification
            send_admin_payment_notification_email_helper(payment, request)

            # Notifications
            create_notification(
                user=request.user,
                title="💳 Payment Proof Submitted",
                message=f"Payment submission of ৳{amount:,.2f} BDT received (Invoice #{payment.invoice_id}). Verification pending.",
                notification_type="payment",
                category="info",
                link="/student/dashboard/#invoices"
            )
            create_notification(
                user=None,
                title=f"📥 New Payment Proof: {request.user.email}",
                message=f"Student {request.user.get_full_name() or request.user.email} submitted ৳{amount:,.2f} BDT via {payment_method} (Ref: {transaction_ref or 'N/A'}).",
                notification_type="payment",
                category="warning",
                link=f"/superadmin/student/{enrollment.id}/profile/"
            )

            messages.success(
                request,
                f"🎉 Payment submission of ৳{amount:,.2f} BDT received (Ref: #{payment.invoice_id})! Our billing team will verify your payment proof and send your official invoice to your email."
            )
        except Exception as e:
            messages.error(request, f"Error submitting payment proof: {str(e)}")

    return redirect('/student/dashboard/#invoices')


@login_required
@user_passes_test(_is_superuser)
def superadmin_verify_payment(request, payment_id):
    """Super Admin: Approve or Reject a student's pending payment proof submission."""
    payment = get_object_or_404(StudentPayment, id=payment_id)
    enrollment = payment.enrollment
    student_user = enrollment.user

    if request.method == 'POST':
        action = request.POST.get('action', 'approve')
        admin_notes = request.POST.get('admin_notes', '').strip()

        if action == 'approve':
            payment.status = 'approved'
            payment.verified_at = timezone.now()
            payment.admin_notes = admin_notes
            payment.save()

            # Email official PDF invoice to student
            send_invoice_email_helper(payment, request)

            # Notifications
            create_notification(
                user=student_user,
                title="✅ Payment Approved & Invoice Issued",
                message=f"Your payment #{payment.invoice_id} of ৳{payment.amount:,.2f} BDT has been verified & approved! Invoice emailed.",
                notification_type="payment",
                category="success",
                link=f"/invoice/{payment.invoice_id}/"
            )
            create_notification(
                user=request.user,
                title="✅ Payment Approved",
                message=f"Approved payment #{payment.invoice_id} (৳{payment.amount:,.2f} BDT) for student '{student_user.email}'.",
                notification_type="payment",
                category="success",
                link=f"/superadmin/student/{enrollment.id}/profile/"
            )

            messages.success(
                request,
                f"✅ Approved payment #{payment.invoice_id} (৳{payment.amount:,.2f} BDT) for student '{student_user.email}'. Official PDF invoice has been emailed to {student_user.email}!"
            )
        elif action == 'reject':
            payment.status = 'rejected'
            payment.admin_notes = admin_notes
            payment.save()

            # Email decline notification to student
            send_payment_decline_email_helper(payment, admin_notes, request)

            # Notifications
            create_notification(
                user=student_user,
                title="❌ Payment Submission Declined",
                message=f"Your payment submission #{payment.invoice_id} was declined. Remarks: {admin_notes or 'Please recheck details'}",
                notification_type="payment",
                category="error",
                link="/student/dashboard/#invoices"
            )

            messages.warning(
                request,
                f"❌ Payment submission #{payment.invoice_id} for '{student_user.email}' has been declined and notification email sent to student."
            )

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect(f'/superadmin/student/{enrollment.id}/profile/')


# ==============================================================================
# NOTIFICATION SYSTEM HELPER & API ENDPOINTS
# ==============================================================================

def create_notification(user, title, message, notification_type='system', category='info', link=''):
    """Helper to create real-time notifications for a specific user or all superadmins (if user is None)."""
    try:
        if user is not None:
            return Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                category=category,
                link=link
            )
        else:
            admins = User.objects.filter(is_superuser=True)
            notifs = [
                Notification(
                    user=admin,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    category=category,
                    link=link
                ) for admin in admins
            ]
            if notifs:
                return Notification.objects.bulk_create(notifs)
    except Exception as e:
        print(f"Error creating notification: {e}")


def notify_students_new_lesson(lesson):
    """
    Sends real-time bell notifications AND dispatches HTML email notifications
    to all enrolled students in the target batch when a new recorded video class lesson is uploaded.
    """
    try:
        from .models import StudentEnrollment
        from django.contrib.auth import get_user_model
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings

        User = get_user_model()

        if lesson.batch:
            enrollments = StudentEnrollment.objects.filter(batch=lesson.batch).select_related('user')
            batch_name = lesson.batch.name
        else:
            enrollments = StudentEnrollment.objects.select_related('user').all()
            batch_name = "All Enrolled Batches"

        target_users = set(e.user for e in enrollments if e.user)
        if not target_users:
            target_users = set(User.objects.filter(is_superuser=False))

        sent_count = 0
        for user in target_users:
            student_name = user.get_full_name() or user.username or user.email
            classroom_url = f"https://qrious-tech.vercel.app/student/classroom/lesson/{lesson.id}/"
            recording_url = lesson.video_url or classroom_url

            # 1. Real-time Dashboard Bell Notification
            create_notification(
                user=user,
                title=f"🎬 New Recorded Class: {lesson.title}",
                message=f"A new recorded video class '{lesson.title}' was published under Module {lesson.module.module_number}: {lesson.module.title}. Watch now!",
                notification_type="course",
                category="info",
                link=f"/student/classroom/lesson/{lesson.id}/"
            )

            # 2. HTML Email Notification to Target Batch Students
            try:
                email_subject = f"[New Recorded Class] 🎬 {lesson.title} — Module {lesson.module.module_number}"
                
                context = {
                    'student_name': student_name,
                    'batch_name': batch_name,
                    'class_title': f"Module {lesson.module.module_number}: {lesson.title}",
                    'instructor_name': "Qrious Tech Senior Mentor",
                    'agenda': lesson.notes or f"Module: {lesson.module.title} | Duration: {lesson.duration}",
                    'recording_url': recording_url,
                }

                html_content = render_to_string('account/email/class_recording_notification.html', context)
                text_content = f"Dear {student_name},\n\nA new recorded video class '{lesson.title}' is now available for {batch_name}.\nModule: {lesson.module.title}\nWatch Video: {recording_url}\n\nQrious Tech Academy"

                msg = EmailMultiAlternatives(
                    subject=email_subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=True)
                sent_count += 1
            except Exception as email_err:
                print(f"Error sending recorded class email to {user.email}: {email_err}")

        print(f"Dispatched {sent_count} HTML emails for new lesson '{lesson.title}'.")
        return sent_count
    except Exception as ex:
        print(f"Error notifying students for new lesson: {ex}")
        return 0


def notify_students_updated_lesson(lesson):
    """Sends real-time notifications & HTML emails to enrolled students when an existing class lesson is updated."""
    try:
        from .models import StudentEnrollment
        from django.contrib.auth import get_user_model
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings

        User = get_user_model()

        if lesson.batch:
            enrollments = StudentEnrollment.objects.filter(batch=lesson.batch).select_related('user')
            batch_name = lesson.batch.name
        else:
            enrollments = StudentEnrollment.objects.select_related('user').all()
            batch_name = "All Enrolled Batches"

        target_users = set(e.user for e in enrollments if e.user)
        if not target_users:
            target_users = set(User.objects.filter(is_superuser=False))

        sent_count = 0
        for user in target_users:
            student_name = user.get_full_name() or user.username or user.email
            classroom_url = f"https://qrious-tech.vercel.app/student/classroom/lesson/{lesson.id}/"
            recording_url = lesson.video_url or classroom_url

            create_notification(
                user=user,
                title=f"📝 Class Updated: {lesson.title}",
                message=f"The recorded video class '{lesson.title}' under Module {lesson.module.module_number} has been updated with new content.",
                notification_type="course",
                category="info",
                link=f"/student/classroom/lesson/{lesson.id}/"
            )

            try:
                email_subject = f"[Class Updated] 📝 {lesson.title} — Module {lesson.module.module_number}"
                context = {
                    'student_name': student_name,
                    'batch_name': batch_name,
                    'class_title': f"Module {lesson.module.module_number}: {lesson.title} (Updated)",
                    'instructor_name': "Qrious Tech Senior Mentor",
                    'agenda': lesson.notes or f"Module: {lesson.module.title} | Duration: {lesson.duration}",
                    'recording_url': recording_url,
                }
                html_content = render_to_string('account/email/class_recording_notification.html', context)
                text_content = f"Dear {student_name},\n\nThe class '{lesson.title}' has been updated.\nWatch Video: {recording_url}\n\nQrious Tech Academy"

                msg = EmailMultiAlternatives(
                    subject=email_subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=True)
                sent_count += 1
            except Exception as email_err:
                print(f"Error sending updated lesson email to {user.email}: {email_err}")

        return sent_count
    except Exception as ex:
        print(f"Error notifying students for updated lesson: {ex}")
        return 0


def notify_students_new_assignment(assignment):
    """
    Sends real-time bell notifications AND dispatches HTML email notifications
    to all enrolled students in the target batch when a new homework or exam assignment is published.
    """
    try:
        from .models import StudentEnrollment
        from django.contrib.auth import get_user_model
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings

        User = get_user_model()

        if assignment.batch:
            enrollments = StudentEnrollment.objects.filter(batch=assignment.batch).select_related('user')
            batch_name = assignment.batch.name
        else:
            enrollments = StudentEnrollment.objects.select_related('user').all()
            batch_name = "All Enrolled Batches"

        target_users = set(e.user for e in enrollments if e.user)
        if not target_users:
            target_users = set(User.objects.filter(is_superuser=False))

        due_date_formatted = assignment.due_date.strftime("%a, %b %d, %Y @ %I:%M %p") if assignment.due_date else "N/A"
        assignments_url = "https://qrious-tech.vercel.app/student/assignments/"

        sent_count = 0
        for user in target_users:
            student_name = user.get_full_name() or user.username or user.email

            # 1. Real-time Bell Notification
            create_notification(
                user=user,
                title=f"📚 Week {assignment.week_number} Homework Posted: {assignment.title}",
                message=f"A new homework/exam assignment '{assignment.title}' for {batch_name} has been published. Due date: {due_date_formatted}. Maximum Marks: {assignment.total_marks}.",
                notification_type="course",
                category="warning",
                link="/student/assignments/"
            )

            # 2. HTML Email Notification
            try:
                email_subject = f"[Homework Posted] 📚 Week {assignment.week_number}: {assignment.title} — {batch_name}"
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #0b0f19; color: #f8fafc; margin: 0; padding: 20px;">
                  <div style="max-width: 600px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255,255,255,0.15); border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.5);">
                    <div style="background: linear-gradient(135deg, #0284c7, #7c3aed); padding: 24px; text-align: center;">
                      <h1 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: 800;">Qrious Tech Academy</h1>
                      <p style="color: rgba(255,255,255,0.9); margin: 6px 0 0 0; font-size: 14px;">🎓 Homework & Exam Assignment Published</p>
                    </div>
                    <div style="padding: 28px;">
                      <h2 style="color: #38bdf8; margin-top: 0; font-size: 18px;">Hello {student_name}, 👋</h2>
                      <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6;">
                        A new homework assignment has been published for your enrolled batch <strong>{batch_name}</strong>. Please review the details below and submit your text answer script before the deadline.
                      </p>

                      <div style="background: #1e293b; border-left: 4px solid #f59e0b; border-radius: 10px; padding: 18px; margin: 20px 0;">
                        <div style="font-size: 12px; font-weight: 700; color: #f59e0b; text-transform: uppercase; margin-bottom: 4px;">Week {assignment.week_number} Assignment</div>
                        <div style="font-size: 17px; font-weight: 800; color: #ffffff; margin-bottom: 10px;">{assignment.title}</div>
                        <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 6px;">📅 <strong>Due Deadline:</strong> {due_date_formatted}</div>
                        <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 6px;">🏆 <strong>Maximum Marks:</strong> {assignment.total_marks} Marks</div>
                        <div style="font-size: 13px; color: #94a3b8; margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px;">
                          <strong>Instructions:</strong><br>{assignment.description}
                        </div>
                      </div>

                      <div style="text-align: center; margin-top: 28px;">
                        <a href="{assignments_url}" style="background: linear-gradient(135deg, #0284c7, #2563eb); color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 10px; font-weight: 800; font-size: 14px; display: inline-block; box-shadow: 0 4px 14px rgba(2,132,199,0.4);">
                          📄 Open & Submit Homework
                        </a>
                      </div>
                    </div>
                    <div style="background: #090d16; padding: 16px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid rgba(255,255,255,0.08);">
                      © 2026 Qrious Tech Academy. All rights reserved.<br>
                      If you have questions, please reach out to your course mentor.
                    </div>
                  </div>
                </body>
                </html>
                """

                text_content = f"Dear {student_name},\n\nA new assignment '{assignment.title}' has been published for {batch_name}.\nWeek: {assignment.week_number}\nDue Date: {due_date_formatted}\nTotal Marks: {assignment.total_marks}\nSubmit here: {assignments_url}\n\nQrious Tech Academy"

                msg = EmailMultiAlternatives(
                    subject=email_subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=True)
                sent_count += 1
            except Exception as email_err:
                print(f"Error sending assignment email to {user.email}: {email_err}")

        print(f"Dispatched {sent_count} HTML emails for assignment '{assignment.title}'.")
        return sent_count
    except Exception as ex:
        print(f"Error notifying students for new assignment: {ex}")
        return 0


@login_required
def notifications_api_list(request):
    """API: Returns JSON list of notifications & unread count for current user."""
    if request.user.is_superuser:
        user_filter = Q(user=request.user) | Q(user__isnull=True)
    else:
        user_filter = Q(user=request.user)

    notifs = Notification.objects.filter(user_filter)[:30]
    unread_count = Notification.objects.filter(user_filter, is_read=False).count()

    data = []
    for n in notifs:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'category': n.category,
            'link': n.link or '#',
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%b %d, %H:%M'),
        })

    return JsonResponse({
        'unread_count': unread_count,
        'notifications': data
    })


@csrf_exempt
@login_required
def notifications_api_read(request, notification_id):
    """API: Mark single notification as read."""
    if request.method in ('POST', 'PUT'):
        if request.user.is_superuser:
            user_filter = Q(user=request.user) | Q(user__isnull=True)
        else:
            user_filter = Q(user=request.user)
        notif = get_object_or_404(Notification, user_filter, id=notification_id)
        notif.is_read = True
        notif.save()
        return JsonResponse({'status': 'ok', 'is_read': True})
    return JsonResponse({'error': 'Invalid method'}, status=405)


@csrf_exempt
@login_required
def notifications_api_read_all(request):
    """API: Mark all notifications as read for logged in user."""
    if request.method in ('POST', 'PUT'):
        if request.user.is_superuser:
            user_filter = Q(user=request.user) | Q(user__isnull=True)
        else:
            user_filter = Q(user=request.user)
        Notification.objects.filter(user_filter, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Invalid method'}, status=405)


@csrf_exempt
@login_required
def notifications_api_delete(request, notification_id):
    """API: Delete notification."""
    if request.method in ('POST', 'DELETE'):
        if request.user.is_superuser:
            user_filter = Q(user=request.user) | Q(user__isnull=True)
        else:
            user_filter = Q(user=request.user)
        notif = get_object_or_404(Notification, user_filter, id=notification_id)
        notif.delete()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Invalid method'}, status=405)


@login_required
def notifications_hub_view(request):
    """Full dedicated Notifications Center page."""
    filter_type = request.GET.get('type', 'all')
    filter_status = request.GET.get('status', 'all')

    if request.user.is_superuser:
        user_filter = Q(user=request.user) | Q(user__isnull=True)
    else:
        user_filter = Q(user=request.user)

    notifs_qs = Notification.objects.filter(user_filter)

    if filter_type != 'all':
        notifs_qs = notifs_qs.filter(notification_type=filter_type)
    if filter_status == 'unread':
        notifs_qs = notifs_qs.filter(is_read=False)
    elif filter_status == 'read':
        notifs_qs = notifs_qs.filter(is_read=True)

    unread_count = Notification.objects.filter(user_filter, is_read=False).count()

    context = {
        'notifications': notifs_qs[:100],
        'unread_count': unread_count,
        'filter_type': filter_type,
        'filter_status': filter_status,
    }
    return render(request, 'accounts_app/notifications.html', context)


def send_admin_submission_notification_email_helper(submission, request=None):
    """Sends HTML email notification to superadmins when a student submits homework/exam answer script."""
    try:
        from django.contrib.auth.models import User
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings

        enrollment = submission.enrollment
        student_user = enrollment.user
        assignment = submission.assignment

        admin_grade_url = request.build_absolute_uri('/superadmin/assignments/') if request else "https://qrious-tech.vercel.app/superadmin/assignments/"

        admin_emails = list(
            User.objects.filter(is_active=True, is_superuser=True)
            .exclude(email='')
            .values_list('email', flat=True)
        )
        if not admin_emails:
            admin_emails = ['mdsiamh77@gmail.com']

        email_subject = f"[Homework Submission] 📝 {student_user.get_full_name() or student_user.email} — Week {assignment.week_number}: {assignment.title}"
        submitted_at_str = submission.submitted_at.strftime('%A, %b %d, %Y at %I:%M %p')

        context = {
            'student_name': student_user.get_full_name() or student_user.username or student_user.email,
            'student_email': student_user.email,
            'student_id': enrollment.student_id,
            'week_number': assignment.week_number,
            'assignment_title': assignment.title,
            'batch_name': assignment.batch.name if assignment.batch else 'Batch 01',
            'submitted_at': submitted_at_str,
            'submission_text': submission.submission_text,
            'attachment_url': submission.attachment_url,
            'admin_grade_url': admin_grade_url,
        }

        html_body = render_to_string('account/email/admin_submission_notification.html', context)
        text_body = f"New Homework Submission from {student_user.email}:\nTitle: Week {assignment.week_number} - {assignment.title}\nSubmitted Answer:\n{submission.submission_text}\n"

        for admin_email in set(admin_emails):
            try:
                msg = EmailMultiAlternatives(
                    subject=email_subject,
                    body=text_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[admin_email]
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send(fail_silently=False)
                print(f"[OK] Sent admin submission notification email to {admin_email}")
            except Exception as ex:
                print(f"[ERROR] Failed to send submission email to admin {admin_email}: {ex}")
        return True
    except Exception as ex:
        print(f"[ERROR] Error in send_admin_submission_notification_email_helper: {ex}")
        return False


def send_student_graded_notification_email_helper(submission, request=None):
    """Sends HTML email notification to student when their homework/exam answer script is graded."""
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings

        enrollment = submission.enrollment
        student_user = enrollment.user
        assignment = submission.assignment

        student_portal_url = request.build_absolute_uri('/student/assignments/') if request else "https://qrious-tech.vercel.app/student/assignments/"

        percentage = int((submission.obtained_marks / max(1, assignment.total_marks)) * 100) if submission.obtained_marks else 0

        email_subject = f"[Homework Evaluated] 🌟 Score Released: {submission.obtained_marks}/{assignment.total_marks} — Week {assignment.week_number}: {assignment.title}"

        context = {
            'student_name': student_user.get_full_name() or student_user.username or student_user.email,
            'week_number': assignment.week_number,
            'assignment_title': assignment.title,
            'obtained_marks': submission.obtained_marks or 0,
            'total_marks': assignment.total_marks,
            'percentage': percentage,
            'mentor_feedback': submission.mentor_feedback,
            'student_portal_url': student_portal_url,
        }

        html_body = render_to_string('account/email/student_graded_notification.html', context)
        text_body = f"Your submission for Week {assignment.week_number}: {assignment.title} was evaluated!\nScore: {submission.obtained_marks}/{assignment.total_marks} ({percentage}%)\nMentor Remarks: {submission.mentor_feedback}\n"

        msg = EmailMultiAlternatives(
            subject=email_subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student_user.email]
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        print(f"[OK] Sent graded notification email to student {student_user.email}")
        return True
    except Exception as ex:
        print(f"[ERROR] Error sending graded email to student: {ex}")
        return False


@login_required
@user_passes_test(_is_superuser)
def admin_manage_assignments(request):
    """Super Admin Console: Create homework assignments per batch & grade student text submissions."""
    from .models import CourseBatch, CourseAssignment, AssignmentSubmission, StudentEnrollment

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_assignment':
            batch_id = request.POST.get('batch_id')
            week_number = int(request.POST.get('week_number', 1))
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            due_date_str = request.POST.get('due_date', '').strip()
            total_marks = int(request.POST.get('total_marks', 100))

            batch = get_object_or_404(CourseBatch, pk=batch_id)

            if title and description and due_date_str:
                try:
                    due_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M")
                    due_date = timezone.make_aware(due_date)
                except Exception:
                    due_date = timezone.now() + datetime.timedelta(days=7)

                assignment = CourseAssignment.objects.create(
                    batch=batch,
                    week_number=week_number,
                    title=title,
                    description=description,
                    due_date=due_date,
                    total_marks=total_marks
                )

                # Send real-time bell notifications & HTML emails to target batch students
                notif_count = notify_students_new_assignment(assignment)

                messages.success(
                    request,
                    f"🎉 Homework Assignment (Week {week_number}) '{title}' created for {batch.name}! Sent {notif_count} student notifications & HTML emails."
                )
            else:
                messages.error(request, "Please fill in all required fields (Batch, Title, Instructions, Due Date).")

        elif action == 'grade_submission':
            submission_id = request.POST.get('submission_id')
            submission = get_object_or_404(AssignmentSubmission, pk=submission_id)
            
            try:
                obtained_marks = int(request.POST.get('obtained_marks', 0))
            except Exception:
                obtained_marks = 0

            mentor_feedback = request.POST.get('mentor_feedback', '').strip()
            
            submission.obtained_marks = min(submission.assignment.total_marks, max(0, obtained_marks))
            submission.mentor_feedback = mentor_feedback
            submission.status = 'graded'
            submission.graded_at = timezone.now()
            submission.save()

            # 📧 Send Automated Email Notification to Student
            send_student_graded_notification_email_helper(submission, request)

            # Notify student in dashboard
            create_notification(
                user=submission.enrollment.user,
                title=f"🌟 Homework Graded: Week {submission.assignment.week_number} - {submission.assignment.title}",
                message=f"Your submission for '{submission.assignment.title}' was evaluated! Score: {submission.obtained_marks} / {submission.assignment.total_marks}.",
                notification_type="course",
                category="success",
                link="/student/assignments/"
            )

            messages.success(
                request,
                f"✅ Graded submission for {submission.enrollment.user.email}! Score: {submission.obtained_marks}/{submission.assignment.total_marks}."
            )

        elif action == 'delete_assignment':
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(CourseAssignment, pk=assignment_id)
            title = assignment.title
            assignment.delete()
            messages.success(request, f"🗑 Assignment '{title}' deleted successfully.")

        return redirect('/superadmin/assignments/')

    assignments = []
    batches = []
    submissions = []
    try:
        assignments = list(CourseAssignment.objects.select_related('batch').prefetch_related('submissions', 'submissions__enrollment__user').all())
        batches = list(_get_active_batches())
        submissions = list(AssignmentSubmission.objects.select_related('assignment', 'assignment__batch', 'enrollment', 'enrollment__user').order_by('-submitted_at'))
    except Exception as ex:
        print(f"[WARN] admin_manage_assignments query info: {ex}")

    pending_submissions_count = sum(1 for s in submissions if getattr(s, 'status', '') == 'submitted')
    graded_submissions_count = sum(1 for s in submissions if getattr(s, 'status', '') == 'graded')

    context = {
        'assignments': assignments,
        'batches': batches,
        'submissions': submissions,
        'total_assignments': len(assignments),
        'pending_submissions_count': pending_submissions_count,
        'graded_submissions_count': graded_submissions_count,
    }
    return render(request, 'accounts_app/admin_manage_assignments.html', context)


@login_required
def student_submit_assignment(request):
    """Student view: Submit text homework/exam answer script."""
    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        submission_text = request.POST.get('submission_text', '').strip()
        attachment_url = request.POST.get('attachment_url', '').strip()

        assignment = get_object_or_404(CourseAssignment, pk=assignment_id)
        enrollment = StudentEnrollment.objects.filter(user=request.user).first()

        if not enrollment:
            messages.error(request, "Enrollment required to submit homework.")
            return redirect('/student/dashboard/')

        if not submission_text:
            messages.error(request, "Please enter your text answer script / solution before submitting.")
            return redirect('/student/assignments/')

        submission, created = AssignmentSubmission.objects.get_or_create(
            assignment=assignment,
            enrollment=enrollment,
            defaults={
                'submission_text': submission_text,
                'attachment_url': attachment_url if attachment_url else None,
                'status': 'submitted'
            }
        )
        if not created:
            submission.submission_text = submission_text
            if attachment_url:
                submission.attachment_url = attachment_url
            submission.status = 'submitted'
            submission.submitted_at = timezone.now()
            submission.save()

        # 📧 Send Automated Email Notification to Super Admin
        send_admin_submission_notification_email_helper(submission, request)

        # Notify student
        create_notification(
            user=request.user,
            title=f"📥 Homework Submitted: Week {assignment.week_number} - {assignment.title}",
            message=f"Your solution for '{assignment.title}' was received successfully. Your mentor will evaluate it shortly.",
            notification_type="course",
            category="info",
            link="/student/assignments/"
        )
        # Notify admins
        create_notification(
            user=None,
            title=f"📥 New Homework Submission: {request.user.email}",
            message=f"Student {request.user.get_full_name() or request.user.email} submitted homework for Week {assignment.week_number}: '{assignment.title}'.",
            notification_type="course",
            category="warning",
            link=f"/superadmin/assignments/?assignment_id={assignment.id}"
        )

        messages.success(
            request,
            f"🎉 Homework for Week {assignment.week_number}: '{assignment.title}' submitted successfully! Your mentor will grade your text answer."
        )

    return redirect('/student/assignments/')


@login_required
def student_assignments_portal(request):
    """Dedicated Student Homework & Exam Portal Page."""
    from .models import StudentEnrollment, CourseAssignment, AssignmentSubmission

    enrollments = StudentEnrollment.objects.filter(user=request.user).select_related('user', 'batch')
    primary_enrollment = enrollments.first()

    student_batch = primary_enrollment.batch if primary_enrollment and primary_enrollment.batch else None

    assignments_list = []
    student_submissions_dict = {}

    try:
        if student_batch:
            assignments_qs = CourseAssignment.objects.filter(batch=student_batch, is_active=True).select_related('batch')
        else:
            assignments_qs = CourseAssignment.objects.filter(is_active=True).select_related('batch')

        selected_week = request.GET.get('week')
        if selected_week:
            try:
                w_int = int(selected_week)
                assignments_qs = assignments_qs.filter(week_number=w_int)
            except ValueError:
                pass

        assignments_list = list(assignments_qs)

        if primary_enrollment:
            user_submissions = AssignmentSubmission.objects.filter(enrollment=primary_enrollment).select_related('assignment')
            for sub in user_submissions:
                student_submissions_dict[sub.assignment_id] = sub

        for assign in assignments_list:
            assign.user_submission = student_submissions_dict.get(assign.id, None)
    except Exception as ex:
        print(f"[WARN] student_assignments_portal fetch info: {ex}")

    week_numbers = list(range(1, 13))
    selected_week = request.GET.get('week')

    context = {
        'enrollments': enrollments,
        'primary_enrollment': primary_enrollment,
        'assignments': assignments_list,
        'week_numbers': week_numbers,
        'selected_week': int(selected_week) if selected_week and selected_week.isdigit() else None,
    }
    return render(request, 'accounts_app/student_assignments.html', context)


@login_required
def download_grade_card(request, submission_id):
    """Renders high-res downloadable grade achievement card image for social media sharing."""
    from .models import AssignmentSubmission
    submission = get_object_or_404(AssignmentSubmission.objects.select_related('assignment', 'assignment__batch', 'enrollment', 'enrollment__user'), pk=submission_id)

    # Permission check: Student can view their own card; superadmin can view any card
    if submission.enrollment.user != request.user and not request.user.is_superuser:
        messages.error(request, "Permission denied to view grade card.")
        return redirect('/student/assignments/')

    context = {
        'submission': submission,
    }
    return render(request, 'accounts_app/grade_card_template.html', context)


@login_required
def student_invoices_portal(request):
    """Dedicated Standalone Student Tuition & Invoices Portal Page."""
    from .models import StudentEnrollment, StudentPayment
    
    enrollments = StudentEnrollment.objects.filter(user=request.user).select_related('user', 'batch')
    primary_enrollment = enrollments.first()
    
    payments = []
    try:
        if primary_enrollment:
            payments = list(primary_enrollment.payments.all())
    except Exception as ex:
        print(f"[WARN] student_invoices_portal query info: {ex}")

    context = {
        'enrollments': enrollments,
        'primary_enrollment': primary_enrollment,
        'payments': payments,
        'profile': getattr(request.user, 'profile', None),
    }
    return render(request, 'accounts_app/student_invoices.html', context)


@login_required
def student_delete_payment(request, payment_id):
    """Student View: Delete unverified/declined payment record from invoice ledger."""
    from .models import StudentPayment
    payment = get_object_or_404(StudentPayment.objects.select_related('enrollment'), pk=payment_id)

    # Permission check: Must belong to current student (or superuser)
    if payment.enrollment.user != request.user and not request.user.is_superuser:
        messages.error(request, "Permission denied.")
        return redirect('/student/invoices/')

    # Strict Rule: Verified approved payments CANNOT be deleted by student!
    if payment.status == 'approved' and not request.user.is_superuser:
        messages.error(request, "⛔ CANNOT DELETE VERIFIED INVOICE! Approved payments are part of your official course financial ledger and cannot be deleted.")
        return redirect('/student/invoices/')

    invoice_id = payment.invoice_id
    payment.delete()
    messages.success(request, f"🗑 Removed transaction record #{invoice_id} from your tuition ledger.")
    return redirect('/student/invoices/')






