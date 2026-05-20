"""SQLite: ajoute production_h* / rebut_h* si absents (deploiement sans 0002)."""

from django.db import connection, migrations


def forwards(apps, schema_editor):
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cur:
        cur.execute("PRAGMA table_info(app_productionccb)")
        existing = {row[1] for row in cur.fetchall()}
    added = []
    for i in range(1, 9):
        for prefix in ("production_h", "rebut_h"):
            col = f"{prefix}{i}"
            if col not in existing:
                with connection.cursor() as cur:
                    cur.execute(
                        f"ALTER TABLE app_productionccb ADD COLUMN {col} integer NOT NULL DEFAULT 0;"
                    )
                added.append(col)
    if not added:
        return
    with connection.cursor() as cur:
        cur.execute(
            """
            UPDATE app_productionccb
            SET production_h1 = volume,
                rebut_h1 = rebut
            WHERE volume > 0
              AND IFNULL(production_h1, 0) = 0
              AND IFNULL(production_h2, 0) = 0
              AND IFNULL(production_h3, 0) = 0
              AND IFNULL(production_h4, 0) = 0
              AND IFNULL(production_h5, 0) = 0
              AND IFNULL(production_h6, 0) = 0
              AND IFNULL(production_h7, 0) = 0
              AND IFNULL(production_h8, 0) = 0
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("production_ccb", "0002_ccb_production_rebut_par_heure"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
