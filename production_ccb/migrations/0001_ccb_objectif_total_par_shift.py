"""Aligne objectif CCB sur la somme des objectifs horaires fixes (H1–H8)."""

from django.db import connection, migrations


def forwards(apps, schema_editor):
    with connection.cursor() as cur:
        cur.execute("UPDATE app_productionccb SET objectif = 151")


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("app", "0025_operateureffectif_code_equipe"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
