"""Colonnes objectif_h*, production_lhd_h*, production_rhd_h* sur app_productionccb."""

from django.db import connection, migrations

from app.ccb_constants import CCB_OBJECTIFS_HORAIRES


def _add_int_column(cur, table: str, col: str, default: int = 0) -> None:
    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} integer NOT NULL DEFAULT {default};")


def forwards(apps, schema_editor):
    if connection.vendor != "sqlite":
        return
    table = "app_productionccb"
    with connection.cursor() as cur:
        cur.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cur.fetchall()}

    for h in range(1, 9):
        col_o = f"objectif_h{h}"
        if col_o not in existing:
            default_o = int(CCB_OBJECTIFS_HORAIRES[h - 1])
            with connection.cursor() as cur:
                _add_int_column(cur, table, col_o, default_o)

    for h in range(1, 9):
        for prefix in ("production_lhd_h", "production_rhd_h"):
            col = f"{prefix}{h}"
            if col not in existing:
                with connection.cursor() as cur:
                    _add_int_column(cur, table, col, 0)

    # Anciennes saisies : tout le volume horaire part en LHD.
    with connection.cursor() as cur:
        for h in range(1, 9):
            cur.execute(
                f"""
                UPDATE {table}
                SET production_lhd_h{h} = production_h{h}
                WHERE IFNULL(production_lhd_h{h}, 0) = 0
                  AND IFNULL(production_rhd_h{h}, 0) = 0
                  AND IFNULL(production_h{h}, 0) > 0
                """
            )


class Migration(migrations.Migration):
    dependencies = [
        ("production_ccb", "0004_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
