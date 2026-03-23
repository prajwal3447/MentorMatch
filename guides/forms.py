from django import forms
from guides.models import Guide
from students.models import Department, Domain


class GuideProfileForm(forms.ModelForm):
    """
    Used for both first-time profile completion and subsequent edits.
    Guide fills this in after logging in for the first time.
    """
    class Meta:
        model = Guide
        fields = ['name', 'email', 'phone', 'department', 'specializations']
        widgets = {
            'specializations': forms.CheckboxSelectMultiple(),
        }
        help_texts = {
            'name': 'Your full name as it will appear to students.',
            'email': 'Official email address (must be unique).',
            'phone': 'Contact number (optional).',
            'department': 'Your department.',
            'specializations': 'Select all project domains you can supervise.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['department'].required = True
        self.fields['specializations'].required = True
        self.fields['email'].required = False
        self.fields['phone'].required = False
        # Style select fields
        self.fields['department'].widget.attrs.update({'class': 'form-select'})
