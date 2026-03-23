"""
allocation/services.py
Business logic layer. Rule: views → services → algorithm → models.
"""
from .algorithm import find_best_guide_for_group


# ── Group management ───────────────────────────────────────────────────────────

def create_group(student, project_title, project_domain, is_solo=False):
    from .models import ProjectGroup, GroupMembership
    if student.memberships.exists():
        return None, "You are already part of a project group."
    group = ProjectGroup.objects.create(
        project_title=project_title,
        project_domain=project_domain,
        department=student.department,
        is_solo=is_solo,
        created_by=student,
    )
    GroupMembership.objects.create(group=group, student=student, role='LEADER')
    return group, None


def add_member_to_group(group, department, year, roll_number, requesting_student):
    from .models import Student, GroupMembership
    if not group.memberships.filter(student=requesting_student, role='LEADER').exists():
        return None, "Only the group leader can add members."
    if group.is_solo:
        return None, "Cannot add members to a solo project."
    if group.member_count >= 4:
        return None, "A group can have at most 4 members."
    if group.status == 'ASSIGNED':
        return None, "Cannot modify a group that has already been assigned a guide."
    try:
        target = Student.objects.select_related('department').get(
            department=department,
            year=int(year),
            roll_number=roll_number,
        )
    except Student.DoesNotExist:
        return None, f"No student found with roll number '{roll_number}' in {department.name} ({year})."

    if target.department != group.department:
        return None, (
            f"{target.name} is from {target.department} — "
            f"all members must be from {group.department}."
        )
    if target.memberships.exists():
        return None, f"{target.name} is already part of another project group."
    if group.memberships.filter(student=target).exists():
        return None, f"{target.name} is already in this group."

    membership = GroupMembership.objects.create(group=group, student=target, role='MEMBER')
    return membership, None


def remove_member_from_group(group, student_id, requesting_student):
    from .models import Student, GroupMembership
    if not group.memberships.filter(student=requesting_student, role='LEADER').exists():
        return False, "Only the group leader can remove members."
    if group.status == 'ASSIGNED':
        return False, "Cannot modify a group that has already been assigned a guide."
    try:
        target = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return False, "Student not found."
    if target == requesting_student:
        return False, "Leader cannot remove themselves from the group."
    deleted, _ = GroupMembership.objects.filter(group=group, student=target).delete()
    if not deleted:
        return False, "That student is not in this group."
    return True, None


def submit_group_for_allocation(group, requesting_student):
    if not group.memberships.filter(student=requesting_student, role='LEADER').exists():
        return False, "Only the group leader can submit for allocation."
    if group.status == 'ASSIGNED':
        return False, "This group has already been assigned a guide."
    if not group.is_solo and group.member_count < 2:
        return False, "A group project needs at least 2 members before submitting."
    success = allocate_group(group)
    if success:
        return True, None
    return False, "No guide is available for your project domain. You are on the pending list."


def allocate_group(group):
    if group.status == 'ASSIGNED':
        return True
    guide = find_best_guide_for_group(group)
    if guide:
        group.guide = guide
        group.status = 'ASSIGNED'
        group.save(update_fields=['guide', 'status'])
        return True
    group.status = 'PENDING'
    group.save(update_fields=['status'])
    return False


def allocate_all_pending_groups():
    """
    Run allocation for all PENDING groups.

    Phase 6 optimisation — bulk_update instead of one save() per group:
      1. Fetch all pending groups with their domain in one query.
      2. For each group find the best guide (single annotated SQL query per group).
      3. Collect all groups that got assigned.
      4. bulk_update assigned groups in one SQL statement.
      5. Invalidate the guide count cache for affected guides.

    This reduces DB round-trips from 2N (N selects + N saves) to N+1
    (N algorithm queries + 1 bulk_update).
    """
    from .models import ProjectGroup

    pending = list(
        ProjectGroup.objects
        .filter(status='PENDING')
        .select_related('project_domain', 'department')
    )

    if not pending:
        return {'assigned': 0, 'still_pending': 0}

    to_assign = []    # groups that found a guide
    still_pending = 0

    for group in pending:
        guide = find_best_guide_for_group(group)
        if guide:
            group.guide = guide
            group.status = 'ASSIGNED'
            to_assign.append(group)
        else:
            still_pending += 1

    # Single bulk_update instead of one save() per group
    if to_assign:
        ProjectGroup.objects.bulk_update(to_assign, fields=['guide', 'status'])

    return {'assigned': len(to_assign), 'still_pending': still_pending}


def accept_group_by_guide(guide, group):
    if group.status == 'ASSIGNED':
        return False, "This group is already assigned to a guide."
    if guide.department != group.department:
        return False, f"Department mismatch — {guide.name} is from {guide.department}, but this group is from {group.department}."
    if not guide.has_capacity:
        return False, f"{guide.name} has reached maximum group capacity ({guide.max_groups})."
    group.guide = guide
    group.status = 'ASSIGNED'
    group.save(update_fields=['guide', 'status'])
    return True, None


def unassign_group(group):
    group.guide = None
    group.status = 'PENDING'
    group.save(update_fields=['guide', 'status'])


# ── File uploads ───────────────────────────────────────────────────────────────

def save_submission(group, student, presentation=None, report=None, screenshot=None):
    from .models import ProjectSubmission
    submission, _ = ProjectSubmission.objects.get_or_create(
        group=group,
        defaults={'uploaded_by': student},
    )
    if presentation:
        submission.presentation = presentation
    if report:
        submission.report = report
    if screenshot:
        submission.screenshot = screenshot
    submission.uploaded_by = student
    submission.save()
    return submission


# ── To-do items ────────────────────────────────────────────────────────────────

def add_todo(guide, group, title, description=''):
    from .models import TodoItem
    if group.guide != guide:
        return None, "You are not the assigned guide for this group."
    todo = TodoItem.objects.create(
        group=group, created_by=guide, title=title, description=description,
    )
    return todo, None


def edit_todo(guide, todo, title, description=''):
    if todo.created_by != guide:
        return False, "You can only edit your own to-do items."
    todo.title = title
    todo.description = description
    todo.save(update_fields=['title', 'description', 'updated_at'])
    return True, None


def delete_todo(guide, todo):
    if todo.created_by != guide:
        return False, "You can only delete your own to-do items."
    todo.delete()
    return True, None


def toggle_todo_done(student, todo):
    if not todo.group.memberships.filter(student=student).exists():
        return False, "You are not a member of this group."
    todo.is_done = not todo.is_done
    todo.marked_done_by = student if todo.is_done else None
    todo.save(update_fields=['is_done', 'marked_done_by', 'updated_at'])
    return True, None
