# Generated manually for squad grouping (PSP + operateurs meme shift).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0024_alter_operateureffectif_fonction"),
    ]

    operations = [
        migrations.AddField(
            model_name="operateureffectif",
            name="code_equipe",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Code court partage par le PSP et ses operateurs (meme equipe) pour synchroniser le shift.",
                max_length=24,
                verbose_name="Code equipe",
            ),
        ),
    ]
