from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from app.models import Absence


class Command(BaseCommand):
    help = "Ajoute des absences de demonstration."

    def handle(self, *args, **options):
        today = timezone.localdate()
        Absence.objects.get_or_create(
            equipe="Berceau",
            nom_complet="Yassine Demo",
            date_absence=today - timedelta(days=1),
            defaults={"motif": "Maladie", "remplacant": "Operateur Backup"},
        )
        Absence.objects.get_or_create(
            equipe="CCB",
            nom_complet="Sara Demo",
            date_absence=today,
            defaults={"motif": "Conge", "remplacant": ""},
        )
        self.stdout.write(self.style.SUCCESS("Seed absences termine."))
