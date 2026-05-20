from django.core.management.base import BaseCommand

from app.models import PanneType
from app.panne_type_catalog import CCB_PANNE_TYPES


class Command(BaseCommand):
    help = "Crée ou réactive les types de panne réservés à la ligne CCB."

    def handle(self, *args, **options):
        created = reactivated = 0
        for name in CCB_PANNE_TYPES:
            obj, was_created = PanneType.objects.get_or_create(
                name=name,
                defaults={"description": "", "is_active": True},
            )
            if was_created:
                created += 1
            elif not obj.is_active:
                obj.is_active = True
                obj.save(update_fields=["is_active", "updated_at"])
                reactivated += 1
        self.stdout.write(
            self.style.SUCCESS(f"seed_ccb_panne_types OK created={created} reactivated={reactivated}")
        )
