from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from app.models import OperateurEffectif


class Command(BaseCommand):
    help = "Ajoute des effectifs de demonstration."

    def handle(self, *args, **options):
        for group_name in ("admin", "superviseur", "lecture"):
            Group.objects.get_or_create(name=group_name)

        user_model = get_user_model()
        admin_user, _ = user_model.objects.get_or_create(
            username="effectif_admin",
            defaults={"is_staff": True, "is_superuser": True},
        )
        admin_user.set_password("admin12345")
        admin_user.save()

        today = timezone.localdate()
        OperateurEffectif.objects.get_or_create(
            cin="AB123456",
            defaults={
                "nom_complet": "Yassine Demo",
                "shift": "A",
                "type_contrat": "CDI",
                "date_naissance": today - timedelta(days=30 * 365),
                "sexe": "Homme",
                "date_entree": today - timedelta(days=2 * 365),
                "identifiant": "EMP-1001",
                "num_tel": "+212612345678",
                "fonction": "Operateur",
                "ville_actuelle": "Kenitra",
                "niveau_etude": "Bac",
                "numero_casier": "C12",
                "parada_transport": "Parada Nord",
                "pointure_chaussure": 42,
                "specialite": "Assemblage",
                "taille_pantalon": "M",
                "taille_veste": "L",
                "ville_origine": "Rabat",
                "equipe": "Berceau",
                "updated_by": admin_user,
            },
        )
        self.stdout.write(self.style.SUCCESS("Seed effectifs termine."))
