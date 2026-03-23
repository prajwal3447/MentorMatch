import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from students.models import Department, Domain


class Guide(models.Model):
    """
    UUID primary key.
    Admin creates User + Guide record.
    Guide completes own profile on first login.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name='guide_profile',
    )
    name = models.CharField(max_length=100, db_index=True, blank=True, default='')
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='guides',
        db_index=True, null=True, blank=True,
    )
    specializations = models.ManyToManyField(Domain, related_name='guides', blank=True)
    max_groups = models.IntegerField(
        default=8,
        validators=[MinValueValidator(1)],
        help_text='Maximum number of project groups this guide can supervise (min 1).',
    )
    phone = models.CharField(max_length=15, blank=True, default='')
    email = models.EmailField(blank=True, null=True, unique=True, default=None)
    profile_complete = models.BooleanField(
        default=False,
        help_text='Set automatically when guide completes their profile.',
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Guide'
        verbose_name_plural = 'Guides'

    def __str__(self):
        if self.name and self.department:
            return f"{self.name} ({self.department.code})"
        return f"Guide (incomplete) — {self.user.username if self.user else 'no user'}"

    @property
    def current_group_count(self):
        """
        Use annotated value if available (set by views via .annotate()).
        Falls back to DB query only when not annotated.
        This avoids repeated DB hits when iterating over guides in templates.
        """
        if hasattr(self, '_current_group_count'):
            return self._current_group_count
        count = self.assigned_groups.filter(status='ASSIGNED').count()
        self._current_group_count = count
        return count

    @property
    def has_capacity(self):
        return self.current_group_count < self.max_groups

    @property
    def load_percentage(self):
        if self.max_groups == 0:
            return 0
        return round((self.current_group_count / self.max_groups) * 100)
