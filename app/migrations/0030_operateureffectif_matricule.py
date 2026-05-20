# Colonne SQL sur app_operateureffectif (modèle dans l'app effectif, hors état app depuis 0027).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0029_productionberceau_unique_date_shift"),
        ("effectif", "0002_operateureffectif_matricule"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE app_operateureffectif "
                "ADD COLUMN matricule varchar(64) NOT NULL DEFAULT '';"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS app_operateureffectif_matricule_idx ON app_operateureffectif (matricule);",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
