"""
0005_fix_department_nullable.py

The guides_guide.department_id column in PostgreSQL is still NOT NULL
because migration 0004 was recorded as applied before PostgreSQL was set up,
so the ALTER COLUMN never actually executed against the DB.

This migration fixes it by directly altering the column to allow NULL,
and also ensures profile_complete column exists.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('guides', '0004_guide_profile_complete'),
        ('students', '0001_initial'),
    ]

    operations = [
        # Force the column to be nullable in PostgreSQL
        migrations.AlterField(
            model_name='guide',
            name='department',
            field=models.ForeignKey(
                blank=True,
                null=True,
                db_index=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='guides',
                to='students.department',
            ),
        ),
        # Ensure name is blank-able
        migrations.AlterField(
            model_name='guide',
            name='name',
            field=models.CharField(blank=True, db_index=True, default='', max_length=100),
        ),
        # Ensure profile_complete exists (safe to run even if already there)
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='guides_guide'
                        AND column_name='profile_complete'
                    ) THEN
                        ALTER TABLE guides_guide
                        ADD COLUMN profile_complete boolean NOT NULL DEFAULT false;
                    END IF;
                END
                $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
