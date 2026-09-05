"""
Context processor to inject subscription info into all templates.
"""
from django.conf import settings


def subscription_context(request):
    """Inject subscription details into every template."""
    try:
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return {'plan': 'free', 'plan_limits': settings.PLAN_LIMITS['free']}

        sub = getattr(request.user, 'subscription', None)
        plan = sub.plan if sub and sub.is_active else 'free'
    except Exception:
        plan = 'free'

    return {
        'current_plan': plan,
        'plan_limits': settings.PLAN_LIMITS.get(plan, settings.PLAN_LIMITS['free']),
        'all_plans': settings.PLAN_LIMITS,
        'applications_remaining': _get_remaining(getattr(request, 'user', None), plan),
    }


def _get_remaining(user, plan):
    try:
        return user.subscription.applications_remaining()
    except Exception:
        limit = settings.PLAN_LIMITS[plan]['applications_per_month']
        return limit
