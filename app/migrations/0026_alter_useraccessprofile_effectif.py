from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0025_operateureffectif_code_equipe"),
        ("effectif", "0001_operateureffectif_state"),
    ]

    operations = [
        migrations.AlterField(
            model_name="useraccessprofile",
            name="effectif",
            field=models.ForeignKey(
                blank=True,
                help_text="Pour PSP : l'operateur Effectif dont le shift fait foi.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="linked_users",
                to="effectif.operateureffectif",
            ),
        ),
    ]
