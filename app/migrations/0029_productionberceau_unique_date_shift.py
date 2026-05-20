# Contrainte réelle sur la table SQL app_productionberceau (modèle hors app depuis 0027).
# Une fiche par (date, shift) ; la diversité par heure reste dans line_h1..line_h8.

from django.db import migrations


def _apply_schema(apps, schema_editor):
    from collections import defaultdict

    from production.models import ProductionBerceau

    by_key = defaultdict(list)
    for row in ProductionBerceau.objects.all().order_by("id"):
        by_key[(row.date, row.shift)].append(row.pk)
    for _key, pks in by_key.items():
        if len(pks) <= 1:
            continue
        ProductionBerceau.objects.filter(pk__in=pks[1:]).delete()

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute("DROP INDEX IF EXISTS uniq_production_berceau_line_date_shift")
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uniq_production_berceau_date_shift "
                "ON app_productionberceau (date, shift)"
            )
        elif connection.vendor == "postgresql":
            cursor.execute(
                "ALTER TABLE app_productionberceau DROP CONSTRAINT IF EXISTS uniq_production_berceau_line_date_shift"
            )
            cursor.execute(
                "ALTER TABLE app_productionberceau ADD CONSTRAINT uniq_production_berceau_date_shift "
                "UNIQUE (date, shift)"
            )
        else:
            cursor.execute("DROP INDEX IF EXISTS uniq_production_berceau_line_date_shift ON app_productionberceau")
            cursor.execute(
                "CREATE UNIQUE INDEX uniq_production_berceau_date_shift ON app_productionberceau (date, shift)"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0028_useraccessprofile_db_table"),
    ]

    operations = [
        migrations.RunPython(_apply_schema, migrations.RunPython.noop),
    ]
