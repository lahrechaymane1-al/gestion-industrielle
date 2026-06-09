"""Colonne line (diversité dominante LHD/RHD) sur app_productionccb."""

from django.db import connection, migrations


def forwards(apps, schema_editor):
    if connection.vendor != "sqlite":
        return
    table = "app_productionccb"
    with connection.cursor() as cur:
        cur.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cur.fetchall()}

    if "line" not in existing:
        with connection.cursor() as cur:
            cur.execute(
                f"ALTER TABLE {table} ADD COLUMN line varchar(3) NOT NULL DEFAULT 'LHD';"
            )

    # Déduire la diversité dominante à partir des volumes LHD/RHD horaires.
    with connection.cursor() as cur:
        cur.execute(
            f"""
            UPDATE {table}
            SET line = CASE
                WHEN (
                    IFNULL(production_rhd_h1, 0) + IFNULL(production_rhd_h2, 0) +
                    IFNULL(production_rhd_h3, 0) + IFNULL(production_rhd_h4, 0) +
                    IFNULL(production_rhd_h5, 0) + IFNULL(production_rhd_h6, 0) +
                    IFNULL(production_rhd_h7, 0) + IFNULL(production_rhd_h8, 0)
                ) > (
                    IFNULL(production_lhd_h1, 0) + IFNULL(production_lhd_h2, 0) +
                    IFNULL(production_lhd_h3, 0) + IFNULL(production_lhd_h4, 0) +
                    IFNULL(production_lhd_h5, 0) + IFNULL(production_lhd_h6, 0) +
                    IFNULL(production_lhd_h7, 0) + IFNULL(production_lhd_h8, 0)
                ) THEN 'RHD'
                ELSE 'LHD'
            END
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("production_ccb", "0006_ccb_production_settings"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
