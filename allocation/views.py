"""
allocation/views.py
All views are protected with role-specific decorators from accounts.decorators.
Business logic is in services.py.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Prefetch, Q

from .models import Student, ProjectGroup, GroupMembership, TodoItem, ProjectSubmission
from guides.models import Guide
from guides.forms import GuideProfileForm
from .services import (
    create_group, add_member_to_group, remove_member_from_group,
    submit_group_for_allocation, accept_group_by_guide, unassign_group,
    save_submission, add_todo, edit_todo, delete_todo, toggle_todo_done,
)
from .forms import GroupCreateForm, ProjectSubmissionForm, TodoItemForm
from students.forms import AddMemberByRollForm
from accounts.decorators import student_required, guide_required, guide_profile_required, require_POST_mutation
from accounts.security_logger import sec_log


# ── Helpers ────────────────────────────────────────────────────────────────────

def _membership_prefetch():
    return Prefetch(
        'memberships',
        queryset=GroupMembership.objects.select_related('student', 'student__department'),
    )

def _todos_prefetch():
    return Prefetch(
        'todos',
        queryset=TodoItem.objects.select_related('marked_done_by').order_by('is_done', '-created_at'),
    )


# ── Guide: complete profile ────────────────────────────────────────────────────

@guide_profile_required
def guide_complete_profile(request):
    guide = get_object_or_404(
        Guide.objects.select_related('department').prefetch_related('specializations'),
        user=request.user,
    )
    if guide.profile_complete:
        return redirect('guide_dashboard')

    if request.method == 'POST':
        form = GuideProfileForm(request.POST, instance=guide)
        if form.is_valid():
            completed_guide = form.save(commit=False)
            completed_guide.profile_complete = True
            completed_guide.save()
            form.save_m2m()
            messages.success(request, "Profile completed! Welcome to MentorMatch.")
            return redirect('guide_dashboard')
    else:
        form = GuideProfileForm(instance=guide)

    return render(request, 'guide/guide_complete_profile.html', {'form': form})


# ── Guide: edit profile ────────────────────────────────────────────────────────

@guide_required
def guide_edit_profile(request):
    guide = get_object_or_404(
        Guide.objects.select_related('department').prefetch_related('specializations'),
        user=request.user,
    )
    if request.method == 'POST':
        form = GuideProfileForm(request.POST, instance=guide)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('guide_dashboard')
    else:
        form = GuideProfileForm(instance=guide)

    return render(request, 'guide/guide_edit_profile.html', {'form': form})


# ── Student dashboard ──────────────────────────────────────────────────────────

@student_required
def student_dashboard(request):
    student = get_object_or_404(
        Student.objects.select_related('department'),
        user=request.user,
    )
    membership = (
        GroupMembership.objects
        .filter(student=student)
        .select_related(
            'group', 'group__department', 'group__project_domain',
            'group__guide', 'group__guide__department',
        )
        .prefetch_related(
            Prefetch(
                'group__memberships',
                queryset=GroupMembership.objects.select_related('student', 'student__department'),
            ),
            Prefetch(
                'group__todos',
                queryset=TodoItem.objects.select_related('marked_done_by').order_by('is_done', '-created_at'),
            ),
            'group__submission',
        )
        .first()
    )

    group = membership.group if membership else None
    submission = None
    todos = []
    members = []
    submission_form = None

    if group:
        try:
            submission = group.submission
        except ProjectSubmission.DoesNotExist:
            submission = None
        todos = group.todos.all()
        members = [m.student for m in group.memberships.all()]
        submission_form = ProjectSubmissionForm(instance=submission)

    context = {
        'student': student,
        'group': group,
        'submission': submission,
        'todos': todos,
        'members': members,
        'submission_form': submission_form,
    }
    return render(request, 'student/student_dashboard.html', context)


# ── Guide dashboard ────────────────────────────────────────────────────────────

@guide_required
def guide_dashboard(request):
    guide = get_object_or_404(
        Guide.objects
        .select_related('department')
        .prefetch_related('specializations')
        .annotate(
            _current_group_count=Count(
                'assigned_groups',
                filter=Q(assigned_groups__status='ASSIGNED'),
            )
        ),
        user=request.user,
    )
    guide._current_group_count = guide._current_group_count

    pending_groups = (
        ProjectGroup.objects
        .filter(status='PENDING', department=guide.department)  # same dept only
        .select_related('department', 'project_domain', 'created_by')
        .prefetch_related(_membership_prefetch())
        .order_by('-created_at')
    )
    assigned_groups = (
        guide.assigned_groups
        .filter(status='ASSIGNED')
        .select_related('project_domain', 'department')
        .prefetch_related(_membership_prefetch(), _todos_prefetch(), 'submission')
        .order_by('-created_at')
    )

    context = {
        'guide': guide,
        'pending_groups': pending_groups,
        'assigned_groups': assigned_groups,
        'remaining_slots': guide.max_groups - guide._current_group_count,
        'load_percentage': guide.load_percentage,
    }
    return render(request, 'guide/guide_dashboard.html', context)


# ── Group: create ──────────────────────────────────────────────────────────────

@student_required
def create_group_view(request):
    student = get_object_or_404(Student.objects.select_related('department'), user=request.user)
    if student.active_group:
        messages.warning(request, "You are already part of a project group.")
        return redirect('student_dashboard')
    if request.method == 'POST':
        form = GroupCreateForm(request.POST)
        if form.is_valid():
            group, error = create_group(
                student=student,
                project_title=form.cleaned_data['project_title'],
                project_domain=form.cleaned_data['project_domain'],
                is_solo=form.cleaned_data['is_solo'],
            )
            if error:
                messages.error(request, error)
            else:
                sec_log.group_created(request, str(group.id), group.project_title)
                if group.is_solo:
                    submit_group_for_allocation(group, student)
                    messages.success(request, "Solo project created and submitted for guide allocation.")
                else:
                    messages.success(request, "Group project created! Add teammates then submit.")
                return redirect('manage_group', group_id=group.id)
    else:
        form = GroupCreateForm()
    return render(request, 'allocation/group_form.html', {'form': form})


# ── Group: manage ──────────────────────────────────────────────────────────────

@student_required
def manage_group(request, group_id):
    student = get_object_or_404(Student.objects.select_related('department'), user=request.user)
    group = get_object_or_404(
        ProjectGroup.objects
        .select_related('department', 'project_domain', 'guide')
        .prefetch_related(_membership_prefetch()),
        id=group_id,
    )
    is_member = False
    is_leader = False
    for m in group.memberships.all():
        if m.student_id == student.id:
            is_member = True
            is_leader = (m.role == 'LEADER')
            break

    if not is_member:
        messages.error(request, "You are not a member of this group.")
        return redirect('student_dashboard')

    context = {
        'group': group,
        'members': group.memberships.all(),
        'is_leader': is_leader,
        'add_member_form': AddMemberByRollForm(),
    }
    return render(request, 'allocation/group_manage.html', context)


# ── Group: add member ──────────────────────────────────────────────────────────

@student_required
@require_POST_mutation
def add_member(request, group_id):
    student = get_object_or_404(Student, user=request.user)
    group = get_object_or_404(ProjectGroup, id=group_id)
    form = AddMemberByRollForm(request.POST)
    if form.is_valid():
        _, error = add_member_to_group(
            group=group,
            department=form.cleaned_data['department'],
            year=form.cleaned_data['year'],
            roll_number=form.cleaned_data['roll_number'],
            requesting_student=student,
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Member added successfully.")
    return redirect('manage_group', group_id=group.id)


# ── Group: remove member ───────────────────────────────────────────────────────

@student_required
@require_POST_mutation
def remove_member(request, group_id, student_id):
    student = get_object_or_404(Student, user=request.user)
    group = get_object_or_404(ProjectGroup, id=group_id)
    success, error = remove_member_from_group(group, student_id, student)
    if error:
        messages.error(request, error)
    else:
        messages.success(request, "Member removed.")
    return redirect('manage_group', group_id=group.id)


# ── Group: submit ──────────────────────────────────────────────────────────────

@student_required
@require_POST_mutation
def submit_group(request, group_id):
    student = get_object_or_404(Student, user=request.user)
    group = get_object_or_404(ProjectGroup, id=group_id)
    success, error = submit_group_for_allocation(group, student)
    if error:
        messages.warning(request, error)
    else:
        sec_log.group_submitted(request, str(group_id))
        messages.success(request, "Guide assigned!" if group.status == 'ASSIGNED' else "On pending list.")
    return redirect('student_dashboard')


# ── Guide: accept / reject ─────────────────────────────────────────────────────

@guide_required
@require_POST_mutation
def accept_group(request, group_id):
    guide = get_object_or_404(Guide, user=request.user)
    group = get_object_or_404(ProjectGroup, id=group_id)
    success, error = accept_group_by_guide(guide, group)
    if error:
        messages.error(request, error)
    else:
        sec_log.group_assigned(request, str(group_id), guide.name)
        messages.success(request, f"Group '{group.project_title}' assigned to you.")
    return redirect('guide_dashboard')


@guide_required
@require_POST_mutation
def reject_group(request, group_id):
    guide = get_object_or_404(Guide, user=request.user)
    group = get_object_or_404(ProjectGroup, id=group_id)
    sec_log.group_rejected(request, str(group_id))
    unassign_group(group)
    messages.info(request, f"Group '{group.project_title}' returned to pending list.")
    return redirect('guide_dashboard')


# ── Uploads ────────────────────────────────────────────────────────────────────

ALLOWED_PRESENTATION_TYPES = {
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
}
ALLOWED_REPORT_TYPES = {'application/pdf'}
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


# Magic-byte signatures for server-side MIME verification.
# We read the first 8 bytes of the uploaded file and compare against known
# signatures so an attacker cannot bypass the check by renaming a .exe to .pdf.
_MAGIC_BYTES: dict[str, list[bytes]] = {
    'application/pdf':  [b'%PDF'],
    'application/vnd.ms-powerpoint': [b'\xd0\xcf\x11\xe0'],          # OLE2 (legacy .ppt)
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': [
        b'PK\x03\x04',   # ZIP/OOXML (.pptx)
    ],
    'image/jpeg': [b'\xff\xd8\xff'],
    'image/png':  [b'\x89PNG'],
    'image/webp': [b'RIFF'],   # RIFF....WEBP — checked further below
}


def _check_magic(file, allowed_types: set) -> bool:
    """Read first 12 bytes and verify against expected magic numbers."""
    file.seek(0)
    header = file.read(12)
    file.seek(0)
    for mime in allowed_types:
        for magic in _MAGIC_BYTES.get(mime, []):
            if header.startswith(magic):
                # Extra check for WebP: bytes 8-12 must be 'WEBP'
                if mime == 'image/webp' and header[8:12] != b'WEBP':
                    continue
                return True
    return False


def _validate_file(file, allowed_types, field_name):
    """Returns error string or None."""
    if file is None:
        return None
    if file.size > MAX_FILE_SIZE_BYTES:
        return f"{field_name} must be under {MAX_FILE_SIZE_MB}MB."
    # Extension check (first line of defence)
    ext = file.name.rsplit('.', 1)[-1].lower() if '.' in file.name else ''
    allowed_exts = {
        'application/pdf': {'pdf'},
        'application/vnd.ms-powerpoint': {'ppt'},
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': {'pptx'},
        'image/jpeg': {'jpg', 'jpeg'},
        'image/png': {'png'},
        'image/webp': {'webp'},
    }
    valid_exts = set()
    for t in allowed_types:
        valid_exts |= allowed_exts.get(t, set())
    if ext not in valid_exts:
        return f"{field_name}: invalid file type. Allowed: {', '.join(sorted(valid_exts))}."
    # Magic-byte check (second line of defence — catches renamed executables)
    if not _check_magic(file, set(allowed_types)):
        return f"{field_name}: file content does not match its extension. Please upload a real {ext.upper()} file."
    return None


@student_required
def upload_submission(request, group_id):
    student = get_object_or_404(Student, user=request.user)
    group = get_object_or_404(ProjectGroup, id=group_id)

    if not group.memberships.filter(student=student).exists():
        messages.error(request, "You are not a member of this group.")
        return redirect('student_dashboard')

    if request.method == 'POST':
        presentation = request.FILES.get('presentation')
        report = request.FILES.get('report')
        screenshot = request.FILES.get('screenshot')

        errors = []
        err = _validate_file(presentation, ALLOWED_PRESENTATION_TYPES, 'Presentation')
        if err:
            errors.append(err)
        err = _validate_file(report, ALLOWED_REPORT_TYPES, 'Report')
        if err:
            errors.append(err)
        err = _validate_file(screenshot, ALLOWED_IMAGE_TYPES, 'Screenshot')
        if err:
            errors.append(err)

        if errors:
            for e in errors:
                messages.error(request, e)
                sec_log.file_rejected(request, 'upload', e)
        else:
            save_submission(group=group, student=student,
                            presentation=presentation, report=report, screenshot=screenshot)
            if presentation:
                sec_log.file_uploaded(request, str(group_id), 'presentation', presentation.name)
            if report:
                sec_log.file_uploaded(request, str(group_id), 'report', report.name)
            if screenshot:
                sec_log.file_uploaded(request, str(group_id), 'screenshot', screenshot.name)
            messages.success(request, "Files uploaded successfully.")

    return redirect('student_dashboard')


# ── To-do ──────────────────────────────────────────────────────────────────────

@guide_required
@require_POST_mutation
def add_todo_view(request, group_id):
    guide = get_object_or_404(Guide, user=request.user)
    group = get_object_or_404(ProjectGroup, id=group_id)
    form = TodoItemForm(request.POST)
    if form.is_valid():
        todo, error = add_todo(guide, group, form.cleaned_data['title'],
                               form.cleaned_data.get('description', ''))
        if error:
            messages.error(request, error)
        else:
            sec_log.todo_added(request, str(todo.id), str(group_id))
    return redirect('guide_dashboard')


@guide_required
@require_POST_mutation
def edit_todo_view(request, group_id, todo_id):
    guide = get_object_or_404(Guide, user=request.user)
    todo = get_object_or_404(TodoItem, id=todo_id)
    form = TodoItemForm(request.POST, instance=todo)
    if form.is_valid():
        _, error = edit_todo(guide, todo, form.cleaned_data['title'],
                             form.cleaned_data.get('description', ''))
        if error:
            messages.error(request, error)
    return redirect('guide_dashboard')


@guide_required
@require_POST_mutation
def delete_todo_view(request, group_id, todo_id):
    guide = get_object_or_404(Guide, user=request.user)
    todo = get_object_or_404(TodoItem, id=todo_id)
    todo_id_str = str(todo.id)
    success, error = delete_todo(guide, todo)
    if error:
        messages.error(request, error)
    else:
        sec_log.todo_deleted(request, todo_id_str)
    return redirect('guide_dashboard')


@student_required
@require_POST_mutation
def toggle_todo_view(request, group_id, todo_id):
    student = get_object_or_404(Student, user=request.user)
    todo = get_object_or_404(TodoItem, id=todo_id)
    success, error = toggle_todo_done(student, todo)
    if error:
        messages.error(request, error)
    return redirect('student_dashboard')


def about(request):
    features = [
        'Domain-based matching',
        'Solo & group projects (up to 4)',
        'PPT, report & screenshot uploads',
        'Guide task management',
        'Role-based access control',
        'PostgreSQL + UUID keys',
    ]
    return render(request, 'about.html', {'features': features})
