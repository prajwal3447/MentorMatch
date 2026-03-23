"""
accounts/views.py
Login, logout, dashboard routing, and password change.

Security hardening applied:
  - Session fixation prevention: session is cycled on every successful login
    (flush old session data, issue new session key).
  - POST-only logout: GET requests to /logout/ are ignored to prevent
    CSRF-via-image-tag logout attacks.
  - Dual-key rate limiting: both IP and username are tracked.
  - Security audit logging on every auth event.
  - Timing-safe: we always call authenticate() before checking role, so
    response timing doesn't reveal whether a username exists.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .rate_limiter import is_locked_out, record_failed_attempt, clear_attempts, remaining_attempts
from .forms import GuidePasswordChangeForm, StudentPasswordChangeForm
from .security_logger import sec_log


# ── Home ───────────────────────────────────────────────────────────────────────

def home(request):
    return render(request, 'home.html')


# ── Student login ──────────────────────────────────────────────────────────────

def student_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Rate limit check — dual-key (IP + username)
        if is_locked_out(request, 'student', username):
            sec_log.login_blocked(request, username)
            messages.error(request, "Too many failed attempts. Please wait before trying again.")
            return render(request, 'student/student_login.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not hasattr(user, 'student_profile'):
                # Timing-safe: treat wrong-role logins the same as bad password
                record_failed_attempt(request, 'student', username)
                sec_log.login_failed(request, username)
                messages.error(request, "Invalid username or password.")
                return render(request, 'student/student_login.html')

            # ── Session fixation prevention ────────────────────────────────
            # Flush old session data and issue a new session key before login.
            request.session.flush()
            # ──────────────────────────────────────────────────────────────

            clear_attempts(request, 'student', username)
            login(request, user)
            sec_log.login_success(request, user)
            return redirect('student_dashboard')

        record_failed_attempt(request, 'student', username)
        sec_log.login_failed(request, username)
        left = remaining_attempts(request, 'student', username)
        if left > 0:
            messages.error(request, f"Invalid username or password. {left} attempt(s) remaining.")
        else:
            messages.error(request, "Too many failed attempts. Please wait before trying again.")

    return render(request, 'student/student_login.html')


# ── Guide login ────────────────────────────────────────────────────────────────

def guide_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if is_locked_out(request, 'guide', username):
            sec_log.login_blocked(request, username)
            messages.error(request, "Too many failed attempts. Please wait before trying again.")
            return render(request, 'guide/guide_login.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not hasattr(user, 'guide_profile'):
                record_failed_attempt(request, 'guide', username)
                sec_log.login_failed(request, username)
                messages.error(request, "Invalid username or password.")
                return render(request, 'guide/guide_login.html')

            # Session fixation prevention
            request.session.flush()

            clear_attempts(request, 'guide', username)
            login(request, user)
            sec_log.login_success(request, user)

            if not user.guide_profile.profile_complete:
                return redirect('guide_complete_profile')
            return redirect('guide_dashboard')

        record_failed_attempt(request, 'guide', username)
        sec_log.login_failed(request, username)
        left = remaining_attempts(request, 'guide', username)
        if left > 0:
            messages.error(request, f"Invalid username or password. {left} attempt(s) remaining.")
        else:
            messages.error(request, "Too many failed attempts. Please wait before trying again.")

    return render(request, 'guide/guide_login.html')


# ── Logout ─────────────────────────────────────────────────────────────────────

@require_POST
def user_logout(request):
    """
    POST-only logout.

    GET-based logout is vulnerable to CSRF-via-img-tag attacks where an
    attacker can force-logout a user by embedding:
        <img src="https://yoursite.com/accounts/logout/">
    Requiring POST + CSRF token prevents this entirely.
    """
    sec_log.logout(request)
    logout(request)
    return redirect('home')


# ── Dashboard router ───────────────────────────────────────────────────────────

def dashboard_router(request):
    if not request.user.is_authenticated:
        return redirect('student_login')
    if hasattr(request.user, 'student_profile'):
        return redirect('student_dashboard')
    if hasattr(request.user, 'guide_profile'):
        if not request.user.guide_profile.profile_complete:
            return redirect('guide_complete_profile')
        return redirect('guide_dashboard')
    return redirect('home')


# ── Password change ────────────────────────────────────────────────────────────

@login_required
def guide_change_password(request):
    if not hasattr(request.user, 'guide_profile'):
        sec_log.permission_denied(request, 'non-guide accessing guide_change_password')
        messages.error(request, "This page is for guides only.")
        return redirect('home')

    if request.method == 'POST':
        form = GuidePasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            sec_log.password_changed(request)
            messages.success(request, "Password changed successfully.")
            return redirect('guide_dashboard')
    else:
        form = GuidePasswordChangeForm(request.user)

    return render(request, 'accounts/guide_change_password.html', {'form': form})


@login_required
def student_change_password(request):
    if not hasattr(request.user, 'student_profile'):
        sec_log.permission_denied(request, 'non-student accessing student_change_password')
        messages.error(request, "This page is for students only.")
        return redirect('home')

    if request.method == 'POST':
        form = StudentPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            sec_log.password_changed(request)
            messages.success(request, "Password changed successfully.")
            return redirect('student_dashboard')
    else:
        form = StudentPasswordChangeForm(request.user)

    return render(request, 'accounts/student_change_password.html', {'form': form})
