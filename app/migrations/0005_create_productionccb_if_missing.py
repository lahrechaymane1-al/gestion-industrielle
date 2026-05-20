from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0004_alter_productionberceau_line_and_more"),
    ]

    # Kept as a no-op for cross-database compatibility.
    # The ProductionCCB table is already present in normal migration history.
    operations = []
