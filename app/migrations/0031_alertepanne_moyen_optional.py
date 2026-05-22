"""Allow NULL on app_alertepanne.moyen_id (optional moyen on arrêt alerts)."""

from django.db import migrations


def _sqlite_rebuild_alertepanne_nullable_moyen(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_alertepanne_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cause TEXT NOT NULL,
                solution TEXT NOT NULL,
                date date NOT NULL,
                shift varchar(1) NOT NULL,
                heure_production smallint unsigned NOT NULL
                    CHECK (heure_production >= 0),
                temps_arret_min integer unsigned NOT NULL
                    CHECK (temps_arret_min >= 0),
                equipe varchar(20) NOT NULL,
                is_deleted bool NOT NULL,
                created_at datetime NOT NULL,
                updated_at datetime NOT NULL,
                updated_by_id INTEGER NULL REFERENCES auth_user(id)
                    DEFERRABLE INITIALLY DEFERRED,
                module_id bigint NOT NULL REFERENCES app_berceaumodule(id)
                    DEFERRABLE INITIALLY DEFERRED,
                moyen_id bigint NULL REFERENCES app_berceaumoyen(id)
                    DEFERRABLE INITIALLY DEFERRED,
                poste_id bigint NOT NULL REFERENCES app_berceauposte(id)
                    DEFERRABLE INITIALLY DEFERRED,
                panne_type_id bigint NOT NULL REFERENCES app_pannetype(id)
                    DEFERRABLE INITIALLY DEFERRED,
                category varchar(20) NOT NULL
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO app_alertepanne_new (
                id, cause, solution, date, shift, heure_production, temps_arret_min,
                equipe, is_deleted, created_at, updated_at, updated_by_id,
                module_id, moyen_id, poste_id, panne_type_id, category
            )
            SELECT
                id, cause, solution, date, shift, heure_production, temps_arret_min,
                equipe, is_deleted, created_at, updated_at, updated_by_id,
                module_id, moyen_id, poste_id, panne_type_id, category
            FROM app_alertepanne
            """
        )
        cursor.execute("DROP TABLE app_alertepanne")
        cursor.execute("ALTER TABLE app_alertepanne_new RENAME TO app_alertepanne")
        cursor.execute("PRAGMA foreign_keys=ON")


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":
        _sqlite_rebuild_alertepanne_nullable_moyen(apps, schema_editor)
        return
    schema_editor.execute(
        "ALTER TABLE app_alertepanne ALTER COLUMN moyen_id DROP NOT NULL"
    )


def backwards(apps, schema_editor):
    # No safe reverse for SQLite rebuild; PostgreSQL-only reverse.
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            "UPDATE app_alertepanne SET moyen_id = ("
            "  SELECT bm.id FROM app_berceaumoyen bm "
            "  WHERE bm.poste_id = app_alertepanne.poste_id LIMIT 1"
            ") WHERE moyen_id IS NULL"
        )
        schema_editor.execute(
            "ALTER TABLE app_alertepanne ALTER COLUMN moyen_id SET NOT NULL"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0030_operateureffectif_matricule"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
