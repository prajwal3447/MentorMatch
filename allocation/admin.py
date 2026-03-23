from django.contrib import admin
from django.utils.html import format_html
from students.models import Department, Domain
from guides.models import Guide
from allocation.models import Student, ProjectGroup, GroupMembership, ProjectSubmission, TodoItem
from allocation.services import allocate_all_pending_groups


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    """
    Admin workflow:
      1. Auth > Users > Add User — create username + password
      2. Guides > Add Guide — select that user, set max_groups, save
      3. Share credentials with the guide
      4. Guide logs in and fills their own profile
    """
    list_display = (
        'display_name', 'user', 'department', 'email',
        'max_groups', 'profile_status', 'current_group_count', 'load_pct'
    )
    list_filter = ('department', 'profile_complete')
    search_fields = ('name', 'email', 'user__username')
    filter_horizontal = ('specializations',)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            # Creating a new guide — admin only needs user + max_groups
            return (
                (
                    'Admin Setup — guide will complete profile on first login',
                    {'fields': ('user', 'max_groups')},
                ),
            )
        # Editing existing guide
        return (
            ('Account', {
                'fields': ('user', 'profile_complete'),
            }),
            ('Profile (completed by guide on first login)', {
                'fields': ('name', 'email', 'phone', 'department', 'specializations'),
                'classes': ('collapse',),
                'description': 'These fields are filled by the guide. Expand to view or override.',
            }),
            ('Capacity', {
                'fields': ('max_groups',),
            }),
        )

    def display_name(self, obj):
        if obj.name:
            return obj.name
        username = obj.user.username if obj.user else '—'
        # format_html requires at least one {} argument — use it correctly
        return format_html(
            '<span style="color:#999">(awaiting profile) {}</span>',
            username,
        )
    display_name.short_description = 'Name'

    def profile_status(self, obj):
        if obj.profile_complete:
            # Must pass the string as an argument, not inline
            return format_html(
                '<span style="color:green">{}</span>',
                '✓ Complete',
            )
        return format_html(
            '<span style="color:orange">{}</span>',
            '⏳ Pending',
        )
    profile_status.short_description = 'Profile'

    def current_group_count(self, obj):
        return obj.current_group_count
    current_group_count.short_description = 'Groups'

    def load_pct(self, obj):
        return f"{obj.load_percentage}%"
    load_pct.short_description = 'Load'


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'year', 'roll_number', 'display_roll_col', 'active_group_display')
    list_filter = ('department', 'year')
    search_fields = ('name', 'roll_number')

    def active_group_display(self, obj):
        g = obj.active_group
        return g.project_title if g else '—'
    active_group_display.short_description = 'Active Group'

    def display_roll_col(self, obj):
        return obj.display_roll
    display_roll_col.short_description = 'Full ID'


@admin.action(description="Run allocation for all pending groups")
def run_allocation_action(modeladmin, request, queryset):
    result = allocate_all_pending_groups()
    modeladmin.message_user(
        request,
        f"Allocation complete — Assigned: {result['assigned']}, Still pending: {result['still_pending']}"
    )


@admin.register(ProjectGroup)
class ProjectGroupAdmin(admin.ModelAdmin):
    list_display = ('project_title', 'department', 'project_domain', 'is_solo', 'member_count', 'guide', 'status')
    list_filter = ('status', 'is_solo', 'department', 'project_domain')
    search_fields = ('project_title',)
    actions = [run_allocation_action]

    def member_count(self, obj):
        return obj.member_count
    member_count.short_description = 'Members'


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('student', 'group', 'role', 'joined_at')
    list_filter = ('role',)


@admin.register(ProjectSubmission)
class ProjectSubmissionAdmin(admin.ModelAdmin):
    list_display = ('group', 'uploaded_by', 'updated_at')


@admin.register(TodoItem)
class TodoItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'created_by', 'is_done', 'marked_done_by')
    list_filter = ('is_done',)
