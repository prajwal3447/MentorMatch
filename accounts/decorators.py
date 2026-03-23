"""
accounts/decorators.py

Role-based access control decorators + mutation guard.

student_required     — authenticated + has student_profile
guide_required       — authenticated + has guide_profile + profile_complete
guide_profile_required — authenticated + has guide_profile (profile may be incomplete)
require_POST_mutation  — state-changing views must be called via POST only

All denial events are written to the security audit log.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseNotAllowed


def student_required(view_func):
    """Allow access only to authenticated users with a student_profile."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('student_login')
        if not hasattr(request.user, 'student_profile'):
            from accounts.security_logger import sec_log
            sec_log.permission_denied(request, 'non-student accessing student-only view')
            messages.error(request, "This page is for students only.")
            if hasattr(request.user, 'guide_profile'):
                return redirect('guide_dashboard')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def guide_required(view_func):
    """Allow access only to authenticated guides with a completed profile."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('guide_login')
        if not hasattr(request.user, 'guide_profile'):
            from accounts.security_logger import sec_log
            sec_log.permission_denied(request, 'non-guide accessing guide-only view')
            messages.error(request, "This page is for guides only.")
            if hasattr(request.user, 'student_profile'):
                return redirect('student_dashboard')
            return redirect('home')
        guide = request.user.guide_profile
        if not guide.profile_complete:
            return redirect('guide_complete_profile')
        return view_func(request, *args, **kwargs)
    return wrapper


def guide_profile_required(view_func):
    """Like guide_required but allows incomplete profiles through."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('guide_login')
        if not hasattr(request.user, 'guide_profile'):
            from accounts.security_logger import sec_log
            sec_log.permission_denied(request, 'non-guide accessing guide profile setup')
            messages.error(request, "This page is for guides only.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_POST_mutation(view_func):
    """
    Guard state-mutating views so they only accept POST requests.

    GET-based mutations are a classic CSRF vector — an attacker can embed a
    link or img src that triggers the action when a victim visits their page.
    This decorator makes that impossible.

    Returns HTTP 405 Method Not Allowed for non-POST requests and logs the
    anomaly (legitimate browsers never issue GET to mutation endpoints).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method != 'POST':
            from accounts.security_logger import sec_log
            sec_log.invalid_method(request)
            return HttpResponseNotAllowed(['POST'])
        return view_func(request, *args, **kwargs)
    return wrapper
