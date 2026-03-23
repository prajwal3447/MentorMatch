from django import forms
from students.models import Domain
from students.forms import AddMemberByRollForm  # re-export for views
from .models import ProjectSubmission, TodoItem


class GroupCreateForm(forms.Form):
    project_title = forms.CharField(max_length=200, label='Project Title')
    project_domain = forms.ModelChoiceField(
        queryset=Domain.objects.all(),
        label='Project Domain',
    )
    is_solo = forms.BooleanField(
        required=False,
        label='Solo Project (just me)',
        help_text='Check this if you are working alone. Leave unchecked to add teammates.',
    )


class ProjectSubmissionForm(forms.ModelForm):
    class Meta:
        model = ProjectSubmission
        fields = ['presentation', 'report', 'screenshot']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['presentation'].required = False
        self.fields['report'].required = False
        self.fields['screenshot'].required = False
        self.fields['presentation'].help_text = 'Upload .ppt or .pptx (optional)'
        self.fields['report'].help_text = 'Upload .pdf report (optional)'
        self.fields['screenshot'].help_text = 'Upload project screenshot (.png, .jpg) (optional)'


class TodoItemForm(forms.ModelForm):
    class Meta:
        model = TodoItem
        fields = ['title', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
