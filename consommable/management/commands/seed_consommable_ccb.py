from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q

from consommable.models import ConsommableItem

# (type_materiel, name, reference, unit_price_eur) — CCB catalog from provided sheet
CCB_CATALOG = [
    ("EPIs", "PROTECTION DU CORPS, VETEMENT POUR HOMME NOM TABLIER", "Z000502100", "8.54"),
    ("EPIs", "PR Gants ANSELL HYFLEX 11638 T9", "Z000510114", "6.00"),
    ("EPIs", "PR Gants ANSELL HYFLEX 11638 T8", "Z000510113", "6.00"),
    ("EPIs", "Gants soudure a chaud droit T9", "Z000527915", "6.20"),
    ("EPIs", "Gants soudure a chaud gauche T9", "Z000527916", "6.20"),
    ("EPIs", "BOUCHONS OREILLES EAR MOUSSE JAUNE ULTRAFIT SACHET DE PAIRE", "IM02181405", "1.00"),
    ("EPIs", "LUNETTES PROTECTION ENGLOBANTES INCOLORES 568,01,00,00", "Z000522887", "0.72"),
    ("EPIs", "CHAUSSURE BASKET ECO-CONCU S3S SR T37FC07BKB39A00FB6 T39", "IM02231457", "21.00"),
    ("EPIs", "CHAUSSURE BASKET ECO-CONCU S3S SR T37FC07BKB39A00FB6 T40", "IM02231458", "21.00"),
    ("EPIs", "CHAUSSURE BASKET ECO-CONCU S3S SR T37FC07BKB39A00FB6 T41", "IM02231459", "21.00"),
    ("EPIs", "CHAUSSURE BASKET ECO-CONCU S3S SR T37FC07BKB39A00FB6 T42", "IM02231460", "21.00"),
    ("EPIs", "CHAUSSURE BASKET ECO-CONCU S3S SR T37FC07BKB39A00FB6 T43", "IM02231461", "21.00"),
    ("EPIs", "CHAUSSURE BASKET ECO-CONCU S3S SR T37FC07BKB39A00FB6 T44", "IM02231462", "21.00"),
    ("EPIs", "CHAUSSURE BASKET ECO-CONCU S3S SR T37FC07BKB39A00FB6 T45", "IM02231463", "21.00"),
    ("EPIs", "CHAUSSURE BASKET ECO-CONCU S3S SR T37FC07BKB39A00FB6 T46", "IM02231464", "21.00"),
    ("EPIs", "BOUCHON ULTRAFIT UF-01-00UF-01-0016798H3M FRANCE SA", "IM02181405", "1.00"),
    (
        "EPIs",
        "PROTECTION DE LA TETE NOM MASQUE OPTOELECTRONIQ. MAT SOUDURE COUL NOIR TAIL SPEC P550 OPTREL 1007.000",
        "Z000524931",
        "145.00",
    ),
]


class Command(BaseCommand):
    help = "Seed the CCB consumable catalog (type_materiel + designation + reference + unit price)."

    def handle(self, *args, **options):
        ConsommableItem.objects.filter(equipe="CCB", type_materiel="PR TORCHE MANULLE").update(
            type_materiel="PR TORCHE MANUELLE"
        )

        created, updated = 0, 0
        catalog_keys = set()
        for type_materiel, name, reference, price in CCB_CATALOG:
            catalog_keys.add((name, reference))
            _, was_created = ConsommableItem.objects.update_or_create(
                equipe="CCB",
                reference=reference,
                name=name,
                defaults={
                    "type_materiel": type_materiel,
                    "unit_price_eur": Decimal(price),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        deactivated = 0
        keep_q = Q()
        for name, reference in catalog_keys:
            keep_q |= Q(name=name, reference=reference)
        deactivated += ConsommableItem.objects.filter(equipe="CCB", is_active=True).exclude(keep_q).update(
            is_active=False
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"CCB catalog seeded: {created} created, {updated} updated, {deactivated} legacy rows deactivated."
            )
        )
