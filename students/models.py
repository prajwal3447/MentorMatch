import uuid
from django.db import models


DOMAIN_CHOICES = [
    ('AI', 'AI / Machine Learning'),
    ('WEB', 'Web Development'),
    ('CYBER', 'Cyber Security'),
    ('DS', 'Data Science'),
    ('IOT', 'IoT'),
    ('CLOUD', 'Cloud Computing'),
    ('MOBILE', 'Mobile App Development'),
    ('OTHER', 'Other'),
]

CURRENT_YEAR = 2026


def _year_choices():
    return [(y, str(y)) for y in range(2018, CURRENT_YEAR + 1)]


class Department(models.Model):
    """
    UUID primary key — globally unique, safe for distributed systems.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Globally unique identifier (UUID v4).',
    )
    name = models.CharField(max_length=100, unique=True, db_index=True)
    code = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text='Short department code e.g. COMP, ENTC, MECH.',
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Domain(models.Model):
    """
    UUID primary key — project domain / specialisation area.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=100, unique=True, db_index=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'

    def __str__(self):
        return self.name
