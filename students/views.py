from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages

from .forms import StudentRegistrationForm
from accounts.rate_limiter import is_locked_out, record_failed_attempt, clear_attempts
from accounts.security_logger import sec_log


def student_register(request):
    """
    Student self-registration.

    Security:
      - Rate-limited per IP (same limiter as login) to prevent account-spam.
      - Session is flushed before login to prevent session fixation.
      - Security audit log entry on success.
    """
    if request.method == 'POST':
        # Prevent registration spam from a single IP
        if is_locked_out(request, 'register'):
            messages.error(request, "Too many registration attempts. Please wait before trying again.")
            return render(request, 'student/student_register.html', {'form': StudentRegistrationForm()})

        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            if User.objects.filter(username=username).exists():
                record_failed_attempt(request, 'register')
                messages.error(request, "Username already exists. Please choose another.")
                return render(request, 'student/student_register.html', {'form': form})

            user = User.objects.create_user(username=username, password=password)
            student = form.save(commit=False)
            student.user = user
            student.save()

            # Session fixation prevention
            request.session.flush()
            login(request, user)

            sec_log.registration(request, username)
            clear_attempts(request, 'register')
            messages.success(request, "Registration successful! Create a project or wait to be added by a teammate.")
            return redirect('student_dashboard')
        else:
            record_failed_attempt(request, 'register')
    else:
        form = StudentRegistrationForm()

    return render(request, 'student/student_register.html', {'form': form})
