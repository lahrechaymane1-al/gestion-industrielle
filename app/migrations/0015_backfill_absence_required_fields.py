from django.db import migrations


def backfill_absence_fields(apps, schema_editor):
    Absence = apps.get_model("app", "Absence")
    for item in Absence.objects.select_related("effectif", "remplacant_effectif").all():
        changed = False
        if item.effectif_id and not (item.nom_complet or "").strip():
            item.nom_complet = (item.effectif.nom_complet or "").strip()
            changed = True
        if item.remplacant_effectif_id and not (item.remplacant or "").strip():
            item.remplacant = (item.remplacant_effectif.nom_complet or "").strip()
            changed = True
        if changed:
            item.save(update_fields=["nom_complet", "remplacant", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0014_alter_absence_options_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_absence_fields, migrations.RunPython.noop),
    ]
