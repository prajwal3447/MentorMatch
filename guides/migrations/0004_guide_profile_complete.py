import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Phase 3 — Guide self-service profile:
    - name: no longer required at creation (blank=True, default='')
    - department: nullable (guide fills it in on first login)
    - profile_complete: new flag, default False
    """

    dependencies = [
        ('guides', '0003_alter_max_groups_helptext'),
        ('students', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='guide',
            name='name',
            field=models.CharField(blank=True, db_index=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='guide',
            name='department',
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='guides',
                to='students.department',
            ),
        ),
        migrations.AddField(
            model_name='guide',
            name='profile_complete',
            field=models.BooleanField(
                default=False,
                help_text='Set automatically when guide completes their profile.',
            ),
        ),
    ]
