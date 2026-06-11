"""Create the DatabaseCache table (settings.CACHES 'django_cache').

Run as a migration (not a one-off `createcachetable`) so the table exists in
every environment migrations touch — dev, prod, and the test database. DRF
throttling depends on this cache being present and shared.
"""
from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    # Idempotent: createcachetable skips the table if it already exists.
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0004_tenant_wa_phone_number_id"),
    ]

    operations = [
        migrations.RunPython(create_cache_table, migrations.RunPython.noop),
    ]
