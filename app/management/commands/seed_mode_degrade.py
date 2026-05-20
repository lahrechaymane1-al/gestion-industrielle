from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from app.models import ModeDegrade


class Command(BaseCommand):
    help = "Ajoute des elements mode degrade de demonstration."

    def handle(self, *args, **options):
        today = timezone.localdate()
        ModeDegrade.objects.get_or_create(
            equipe="Berceau",
            shift="A",
            probleme="Arret convoyeur",
            date=today,
            defaults={
                "action": "Maintenance corrective",
                "pilote": "Chef Berceau",
                "delai": today + timedelta(days=2),
                "cause": "Usure composant",
                "statut": "Ouvert",
            },
        )
        ModeDegrade.objects.get_or_create(
            equipe="CCB",
            shift="B",
            probleme="Defaut qualite",
            date=today,
            defaults={
                "action": "Controle renforce",
                "pilote": "Chef CCB",
                "delai": today + timedelta(days=1),
                "cause": "Derive reglage",
                "statut": "En cours",
            },
        )
        self.stdout.write(self.style.SUCCESS("Seed mode degrade termine."))
