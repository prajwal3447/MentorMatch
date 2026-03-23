import uuid
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('students', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Guide',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                # name/dept/email blank — guide fills these on first login
                ('name', models.CharField(blank=True, db_index=True, default='', max_length=100)),
                ('max_groups', models.IntegerField(
                    default=8,
                    help_text='Maximum number of project groups this guide can supervise (min 1).',
                    validators=[django.core.validators.MinValueValidator(1)],
                )),
                ('phone', models.CharField(blank=True, default='', max_length=15)),
                ('email', models.EmailField(blank=True, null=True, unique=True, default=None)),
                ('profile_complete', models.BooleanField(
                    default=False,
                    help_text='Set automatically when guide completes their profile.',
                )),
                ('user', models.OneToOneField(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='guide_profile',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('department', models.ForeignKey(
                    blank=True,
                    null=True,
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='guides',
                    to='students.department',
                )),
                ('specializations', models.ManyToManyField(
                    blank=True,
                    related_name='guides',
                    to='students.domain',
                )),
            ],
            options={'ordering': ['name'], 'verbose_name': 'Guide', 'verbose_name_plural': 'Guides'},
        ),
    ]
