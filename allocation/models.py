import uuid
from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from students.models import Department, Domain
from guides.models import Guide


phone_validator = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message='Enter a valid phone number (9–15 digits, optional + prefix).',
)


class Student(models.Model):
    """
    UUID primary key — safe for distributed systems.
    Roll number unique per (department, year) only.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    name = models.CharField(max_length=100, db_index=True)
    roll_number = models.CharField(
        max_length=20, db_index=True,
        help_text='Roll number — unique within your department and admission year.',
    )
    year = models.IntegerField(db_index=True, help_text='Admission year (e.g. 2023).')
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='students', db_index=True,
    )
    phone = models.CharField(max_length=15, blank=True, default='', validators=[phone_validator])
    email = models.EmailField(blank=True, null=True, default=None)

    class Meta:
        ordering = ['name']
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        constraints = [
            models.UniqueConstraint(
                fields=['department', 'year', 'roll_number'],
                name='unique_roll_per_dept_year',
            )
        ]

    def __str__(self):
        return f"{self.name} | {self.department.code} {self.year} | {self.roll_number}"

    @property
    def active_group(self):
        """
        Return the student's current ProjectGroup with all related data
        pre-fetched in a single query. Avoids N+1 on dashboard.
        """
        membership = (
            self.memberships
            .select_related(
                'group',
                'group__department',
                'group__project_domain',
                'group__guide',
                'group__guide__department',
                'group__created_by',
            )
            .first()
        )
        return membership.group if membership else None

    @property
    def display_roll(self):
        return f"{self.department.code}/{self.year}/{self.roll_number}"


class ProjectGroup(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ASSIGNED', 'Guide Assigned'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_title = models.CharField(max_length=200, db_index=True)
    project_domain = models.ForeignKey(
        Domain, on_delete=models.PROTECT, related_name='groups', db_index=True,
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='groups', db_index=True,
    )
    guide = models.ForeignKey(
        Guide, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_groups',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True,
    )
    is_solo = models.BooleanField(default=False)
    created_by = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project Group'
        verbose_name_plural = 'Project Groups'

    def __str__(self):
        kind = 'Solo' if self.is_solo else 'Group'
        return f"[{kind}] {self.project_title}"

    @property
    def member_count(self):
        """
        Use prefetched memberships if available (avoids extra query in loops).
        Falls back to DB count if not prefetched.
        """
        if hasattr(self, '_prefetched_objects_cache') and 'memberships' in self._prefetched_objects_cache:
            return len(self._prefetched_objects_cache['memberships'])
        return self.memberships.count()

    @property
    def members(self):
        return (
            Student.objects
            .filter(memberships__group=self)
            .select_related('department')
            .order_by('name')
        )

    @property
    def leader(self):
        if hasattr(self, '_prefetched_objects_cache') and 'memberships' in self._prefetched_objects_cache:
            for m in self._prefetched_objects_cache['memberships']:
                if m.role == 'LEADER':
                    return m.student
            return None
        membership = self.memberships.filter(role='LEADER').select_related('student').first()
        return membership.student if membership else None


class GroupMembership(models.Model):
    ROLE_CHOICES = [
        ('LEADER', 'Leader'),
        ('MEMBER', 'Member'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(ProjectGroup, on_delete=models.CASCADE, related_name='memberships')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='MEMBER', db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Group Membership'
        verbose_name_plural = 'Group Memberships'
        constraints = [
            models.UniqueConstraint(fields=['student'], name='unique_student_membership')
        ]

    def __str__(self):
        return f"{self.student.name} → {self.group.project_title} ({self.role})"


class ProjectSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.OneToOneField(ProjectGroup, on_delete=models.CASCADE, related_name='submission')
    presentation = models.FileField(
        upload_to='submissions/presentations/', null=True, blank=True,
        help_text='Upload .ppt or .pptx file',
    )
    report = models.FileField(
        upload_to='submissions/reports/', null=True, blank=True,
        help_text='Upload .pdf file',
    )
    screenshot = models.ImageField(
        upload_to='submissions/screenshots/', null=True, blank=True,
        help_text='Upload project screenshot (.png, .jpg)',
    )
    uploaded_by = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, related_name='uploads')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Project Submission'
        verbose_name_plural = 'Project Submissions'

    def __str__(self):
        return f"Submission — {self.group.project_title}"


class TodoItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(ProjectGroup, on_delete=models.CASCADE, related_name='todos')
    created_by = models.ForeignKey(Guide, on_delete=models.CASCADE, related_name='todos')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    is_done = models.BooleanField(default=False, db_index=True)
    marked_done_by = models.ForeignKey(
        Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_todos',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['is_done', '-created_at']
        verbose_name = 'To-Do Item'
        verbose_name_plural = 'To-Do Items'

    def __str__(self):
        status = '✓' if self.is_done else '○'
        return f"{status} {self.title} [{self.group.project_title}]"
