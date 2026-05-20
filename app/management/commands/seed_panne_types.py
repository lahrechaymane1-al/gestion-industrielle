from django.core.management.base import BaseCommand

from app.models import PanneType
from app.panne_type_catalog import BERCEAU_PANNE_TYPES

PANNE_TYPES = BERCEAU_PANNE_TYPES


class Command(BaseCommand):
    help = "Injecte le référentiel initial de types de pannes."

    def handle(self, *args, **options):
        created = 0
        reactivated = 0
        deactivated = 0
        target = set(PANNE_TYPES)
        stale_qs = PanneType.objects.exclude(name__in=target)
        deactivated = stale_qs.update(is_active=False)
        for name in PANNE_TYPES:
            obj, was_created = PanneType.objects.get_or_create(
                name=name,
                defaults={"description": "", "is_active": True},
            )
            if was_created:
                created += 1
                continue
            if not obj.is_active:
                obj.is_active = True
                obj.save(update_fields=["is_active", "updated_at"])
                reactivated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed panne types terminé. deactivated={deactivated}, created={created}, reactivated={reactivated}, total_target={len(PANNE_TYPES)}"
            )
        )
