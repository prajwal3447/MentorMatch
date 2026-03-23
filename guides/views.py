from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import GuideProfileForm
from .models import Guide
from accounts.decorators import guide_profile_required, guide_required


def _get_guide_or_redirect(request):
    """Return the guide for the logged-in user, or None if not a guide."""
    try:
        return request.user.guide_profile
    except Guide.DoesNotExist:
        return None


@guide_profile_required
def complete_profile(request):
    """
    Shown to a guide on their FIRST login.
    Admin created their user account — now they fill in their details.
    Redirects to dashboard once profile_complete = True.
    """
    guide = _get_guide_or_redirect(request)
    if guide is None:
        messages.error(request, "No guide account found for this user.")
        return redirect('home')

    # Already completed — skip straight to dashboard
    if guide.profile_complete:
        return redirect('guide_dashboard')

    if request.method == 'POST':
        form = GuideProfileForm(request.POST, instance=guide)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.profile_complete = True
            updated.save()
            form.save_m2m()  # Save specializations M2M
            messages.success(request, f"Welcome, {updated.name}! Your profile is complete.")
            return redirect('guide_dashboard')
    else:
        form = GuideProfileForm(instance=guide)

    return render(request, 'guide/guide_complete_profile.html', {
        'form': form,
        'guide': guide,
    })


@guide_required
def edit_profile(request):
    """
    Guide can update their profile at any time from the dashboard.
    """
    guide = _get_guide_or_redirect(request)
    if guide is None:
        messages.error(request, "No guide account found.")
        return redirect('home')

    if not guide.profile_complete:
        return redirect('guide_complete_profile')

    if request.method == 'POST':
        form = GuideProfileForm(request.POST, instance=guide)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('guide_dashboard')
    else:
        form = GuideProfileForm(instance=guide)

    return render(request, 'guide/guide_edit_profile.html', {
        'form': form,
        'guide': guide,
    })
