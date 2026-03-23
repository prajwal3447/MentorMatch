from django import forms
from django.core.validators import RegexValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from allocation.models import Student
from students.models import Department

import datetime

phone_validator = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message='Enter a valid phone number.',
)

CURRENT_YEAR = datetime.date.today().year
YEAR_CHOICES = [(y, str(y)) for y in range(2018, CURRENT_YEAR + 1)]

# Shared widget attrs for the SaaS design system
_input  = {'class': 'input'}
_select = {'class': 'select'}


class StudentRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, help_text='Choose a unique login username.',
                               widget=forms.TextInput(attrs=_input))
    password = forms.CharField(widget=forms.PasswordInput(attrs=_input),
                               help_text='At least 8 characters. Cannot be entirely numeric or a common password.')
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={**_input, 'placeholder': 'Re-enter password'}),
                                       label='Confirm Password')

    class Meta:
        model = Student
        fields = ['name', 'department', 'year', 'roll_number', 'phone', 'email']
        widgets = {
            'name':        forms.TextInput(attrs=_input),
            'department':  forms.Select(attrs=_select),
            'year':        forms.Select(choices=YEAR_CHOICES, attrs=_select),
            'roll_number': forms.TextInput(attrs=_input),
            'phone':       forms.TextInput(attrs=_input),
            'email':       forms.EmailInput(attrs=_input),
        }
        help_texts = {
            'roll_number': 'Unique within your department and year.',
            'year': 'Your admission year.',
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm = cleaned.get('confirm_password')
        if password and confirm and password != confirm:
            raise forms.ValidationError('Passwords do not match.')
        dept = cleaned.get('department')
        year = cleaned.get('year')
        roll = cleaned.get('roll_number')
        if dept and year and roll:
            if Student.objects.filter(department=dept, year=year, roll_number=roll).exists():
                raise forms.ValidationError(
                    f"Roll number '{roll}' already exists in {dept.name} ({year})."
                )
        return cleaned


class AddMemberByRollForm(forms.Form):
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        label="Teammate's Department",
        widget=forms.Select(attrs=_select),
    )
    year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        label="Admission Year",
        widget=forms.Select(attrs=_select),
    )
    roll_number = forms.CharField(
        max_length=20,
        label="Roll Number",
        widget=forms.TextInput(attrs={**_input, 'placeholder': 'e.g. 101'}),
    )
