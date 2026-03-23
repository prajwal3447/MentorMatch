import uuid
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('students', '0001_initial'),
        ('guides', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── Student ────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=100)),
                ('roll_number', models.CharField(
                    db_index=True,
                    help_text='Roll number — unique within your department and admission year.',
                    max_length=20,
                )),
                ('year', models.IntegerField(db_index=True, help_text='Admission year (e.g. 2023).')),
                ('phone', models.CharField(
                    blank=True, default='', max_length=15,
                    validators=[django.core.validators.RegexValidator(
                        message='Enter a valid phone number (9–15 digits, optional + prefix).',
                        regex='^\\+?1?\\d{9,15}$',
                    )],
                )),
                # null=True for PostgreSQL — blank optional fields should be NULL not ''
                ('email', models.EmailField(blank=True, null=True, default=None)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='student_profile',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('department', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='students',
                    to='students.department',
                )),
            ],
            options={'ordering': ['name'], 'verbose_name': 'Student', 'verbose_name_plural': 'Students'},
        ),
        migrations.AddConstraint(
            model_name='student',
            constraint=models.UniqueConstraint(
                fields=['department', 'year', 'roll_number'],
                name='unique_roll_per_dept_year',
            ),
        ),

        # ── ProjectGroup ───────────────────────────────────────────────────────
        migrations.CreateModel(
            name='ProjectGroup',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('project_title', models.CharField(db_index=True, max_length=200)),
                ('status', models.CharField(
                    choices=[('PENDING', 'Pending'), ('ASSIGNED', 'Guide Assigned')],
                    db_index=True, default='PENDING', max_length=20,
                )),
                ('is_solo', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project_domain', models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='groups', to='students.domain',
                )),
                ('department', models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='groups', to='students.department',
                )),
                ('guide', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assigned_groups', to='guides.guide',
                )),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='created_groups', to='allocation.student',
                )),
            ],
            options={'ordering': ['-created_at'], 'verbose_name': 'Project Group', 'verbose_name_plural': 'Project Groups'},
        ),

        # ── GroupMembership ────────────────────────────────────────────────────
        migrations.CreateModel(
            name='GroupMembership',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(
                    choices=[('LEADER', 'Leader'), ('MEMBER', 'Member')],
                    db_index=True, default='MEMBER', max_length=10,
                )),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='memberships', to='allocation.projectgroup',
                )),
                ('student', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='memberships', to='allocation.student',
                )),
            ],
            options={'verbose_name': 'Group Membership', 'verbose_name_plural': 'Group Memberships'},
        ),
        migrations.AddConstraint(
            model_name='groupmembership',
            constraint=models.UniqueConstraint(
                fields=['student'], name='unique_student_membership',
            ),
        ),

        # ── ProjectSubmission ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='ProjectSubmission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('presentation', models.FileField(
                    blank=True, null=True, help_text='Upload .ppt or .pptx file',
                    upload_to='submissions/presentations/',
                )),
                ('report', models.FileField(
                    blank=True, null=True, help_text='Upload .pdf file',
                    upload_to='submissions/reports/',
                )),
                ('screenshot', models.ImageField(
                    blank=True, null=True, help_text='Upload project screenshot (.png, .jpg)',
                    upload_to='submissions/screenshots/',
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='submission', to='allocation.projectgroup',
                )),
                ('uploaded_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='uploads', to='allocation.student',
                )),
            ],
            options={'verbose_name': 'Project Submission', 'verbose_name_plural': 'Project Submissions'},
        ),

        # ── TodoItem ───────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='TodoItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, default='')),
                ('is_done', models.BooleanField(db_index=True, default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='todos', to='allocation.projectgroup',
                )),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='todos', to='guides.guide',
                )),
                ('marked_done_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='completed_todos', to='allocation.student',
                )),
            ],
            options={'ordering': ['is_done', '-created_at'], 'verbose_name': 'To-Do Item', 'verbose_name_plural': 'To-Do Items'},
        ),
    ]
