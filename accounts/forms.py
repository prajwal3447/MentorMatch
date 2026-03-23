"""
accounts/forms.py — Auth-related forms.
"""
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class GuidePasswordChangeForm(forms.Form):
    """
    Allows a guide to change their password after first login.
    Shown as a banner/prompt on the guide dashboard if they haven't changed it.
    """
    current_password = forms.CharField(
        widget=forms.PasswordInput,
        label='Current Password',
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput,
        label='New Password',
        help_text='Min 8 characters. Cannot be entirely numeric.',
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        label='Confirm New Password',
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current = self.cleaned_data.get('current_password')
        if not self.user.check_password(current):
            raise ValidationError("Current password is incorrect.")
        return current

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get('new_password')
        confirm = cleaned.get('confirm_password')
        if new and confirm and new != confirm:
            raise ValidationError("New passwords do not match.")
        if new:
            try:
                validate_password(new, self.user)
            except ValidationError as e:
                raise ValidationError(e.messages)
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save(update_fields=['password'])


class StudentPasswordChangeForm(forms.Form):
    """Password change form for students."""
    current_password = forms.CharField(widget=forms.PasswordInput, label='Current Password')
    new_password = forms.CharField(
        widget=forms.PasswordInput,
        label='New Password',
        help_text='Min 8 characters.',
    )
    confirm_password = forms.CharField(widget=forms.PasswordInput, label='Confirm New Password')

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current = self.cleaned_data.get('current_password')
        if not self.user.check_password(current):
            raise ValidationError("Current password is incorrect.")
        return current

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get('new_password')
        confirm = cleaned.get('confirm_password')
        if new and confirm and new != confirm:
            raise ValidationError("New passwords do not match.")
        if new:
            try:
                validate_password(new, self.user)
            except ValidationError as e:
                raise ValidationError(e.messages)
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save(update_fields=['password'])
