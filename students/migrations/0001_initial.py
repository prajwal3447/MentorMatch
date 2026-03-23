import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    students app initial migration — UUID primary keys from the start.
    """
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=100, unique=True)),
                ('code', models.CharField(db_index=True, help_text='Short department code e.g. COMP, ENTC, MECH.', max_length=10, unique=True)),
            ],
            options={'ordering': ['name'], 'verbose_name': 'Department', 'verbose_name_plural': 'Departments'},
        ),
        migrations.CreateModel(
            name='Domain',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=100, unique=True)),
            ],
            options={'ordering': ['name'], 'verbose_name': 'Domain', 'verbose_name_plural': 'Domains'},
        ),
    ]
