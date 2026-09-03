"""
Context processor to inject subscription info into all templates.
"""
from django.conf import settings


def subscription_context(request):
    """Inject subscription details into every template (with request-level caching)."""
    try:
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return {
                'current_plan': 'free',
                'plan_limits': settings.PLAN_LIMITS['free'],
                'all_plans': settings.PLAN_LIMITS,
                'applications_remaining': settings.PLAN_LIMITS['free']['applications_per_month']
            }

        if not hasattr(request, '_cached_sub_plan'):
            sub = getattr(user, 'subscription', None)
            plan = sub.plan if sub and getattr(sub, 'is_active', False) else 'free'
            remaining = _get_remaining(user, plan)
            request._cached_sub_plan = (plan, remaining)

        plan, remaining = request._cached_sub_plan
    except Exception:
        plan = 'free'
        remaining = settings.PLAN_LIMITS['free']['applications_per_month']

    return {
        'current_plan': plan,
        'plan_limits': settings.PLAN_LIMITS.get(plan, settings.PLAN_LIMITS['free']),
        'all_plans': settings.PLAN_LIMITS,
        'applications_remaining': remaining,
    }


def _get_remaining(user, plan):
    try:
        return user.subscription.applications_remaining()
    except Exception:
        return settings.PLAN_LIMITS.get(plan, settings.PLAN_LIMITS['free'])['applications_per_month']
