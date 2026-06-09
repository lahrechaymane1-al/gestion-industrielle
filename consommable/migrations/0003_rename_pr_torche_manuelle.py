from django.db import migrations, models


def rename_torche_type(apps, schema_editor):
    ConsommableItem = apps.get_model("consommable", "ConsommableItem")
    ConsommableItem.objects.filter(type_materiel="PR TORCHE MANULLE").update(type_materiel="PR TORCHE MANUELLE")


class Migration(migrations.Migration):

    dependencies = [
        ("consommable", "0002_remove_consommableitem_uniq_consommable_item_equipe_reference_and_more"),
    ]

    operations = [
        migrations.RunPython(rename_torche_type, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="consommableitem",
            name="type_materiel",
            field=models.CharField(
                choices=[
                    ("EPIs", "EPIs"),
                    ("AUTRE", "AUTRE"),
                    ("FOURNITURE", "FOURNITURE"),
                    ("PR BERCEAU", "PR BERCEAU"),
                    ("PR TORCHE MANUELLE", "PR TORCHE MANUELLE"),
                    ("PRODUIT CHIMIQUE", "PRODUIT CHIMIQUE"),
                ],
                default="AUTRE",
                max_length=40,
            ),
        ),
    ]
