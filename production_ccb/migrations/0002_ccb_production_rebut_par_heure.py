"""Colonnes production_h1..h8 et rebut_h1..h8 sur app_productionccb (saisie horaire CCB)."""

from django.db import connection, migrations


def _add_int_column(name: str):
    return migrations.RunSQL(
        sql=f'ALTER TABLE app_productionccb ADD COLUMN {name} integer NOT NULL DEFAULT 0;',
        reverse_sql=migrations.RunSQL.noop,
    )


def backfill_from_totals(apps, schema_editor):
    with connection.cursor() as cur:
        cur.execute(
            """
            UPDATE app_productionccb
            SET production_h1 = COALESCE(volume, 0),
                rebut_h1 = COALESCE(rebut, 0)
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("production_ccb", "0001_ccb_objectif_total_par_shift"),
    ]

    operations = [
        *[_add_int_column(f"production_h{i}") for i in range(1, 9)],
        *[_add_int_column(f"rebut_h{i}") for i in range(1, 9)],
        migrations.RunPython(backfill_from_totals, migrations.RunPython.noop),
    ]
