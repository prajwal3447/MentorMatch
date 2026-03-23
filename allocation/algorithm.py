"""
allocation/algorithm.py
Core allocation logic — one guide slot per group.
Uses DB-level annotation to avoid loading all guides into Python.
"""
from django.db.models import Count, F, Q
from guides.models import Guide


def find_best_guide_for_group(group):
    """
    Return the best available guide for a ProjectGroup, or None.

    Single SQL query:
      - Filters guides matching the group's project_domain specialization
      - Annotates each with their current ASSIGNED group count
      - Filters to guides where assigned_count < max_groups (DB-level capacity)
      - Orders by assigned_count ascending (least loaded first)
      - Returns the first result

    No Python-level loops. Safe for PostgreSQL at scale.
    """
    return (
        Guide.objects.filter(
            specializations=group.project_domain,
            department=group.department,        # guide must be from same dept as students
        )
        .annotate(
            assigned_count=Count(
                'assigned_groups',
                filter=Q(assigned_groups__status='ASSIGNED'),
            )
        )
        .filter(assigned_count__lt=F('max_groups'))
        .order_by('assigned_count')
        .first()
    )
