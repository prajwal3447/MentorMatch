"""
0006_force_nullable_columns.py

Django's AlterField did not physically alter the NOT NULL constraints
in PostgreSQL because the migration state was out of sync.
This migration uses raw SQL to force the actual column changes.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('guides', '0005_fix_department_nullable'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Allow department_id to be NULL (guide fills on first login)
                ALTER TABLE guides_guide
                    ALTER COLUMN department_id DROP NOT NULL;

                -- Allow name to be NULL/empty (guide fills on first login)
                ALTER TABLE guides_guide
                    ALTER COLUMN name DROP NOT NULL,
                    ALTER COLUMN name SET DEFAULT '';

                -- Allow phone to be NULL/empty
                ALTER TABLE guides_guide
                    ALTER COLUMN phone DROP NOT NULL,
                    ALTER COLUMN phone SET DEFAULT '';
            """,
            reverse_sql="""
                ALTER TABLE guides_guide
                    ALTER COLUMN department_id SET NOT NULL;
                ALTER TABLE guides_guide
                    ALTER COLUMN name SET NOT NULL;
                ALTER TABLE guides_guide
                    ALTER COLUMN phone SET NOT NULL;
            """,
        ),
    ]
