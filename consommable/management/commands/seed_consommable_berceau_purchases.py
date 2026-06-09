from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand

from consommable.models import ConsommableItem, ConsommablePurchase


# Source: provided Berceau sheet screenshot (Date, Référence, Désignation, Type, Shift, PU, Qté, Coût)
# NOTE:
# - All rows are imported for equipe="Berceau" only.
# - Missing items/types are auto-created.
# - Command is idempotent for purchase rows (same signature => skip).
BERCEAU_PURCHASE_ROWS = [
    ("2026-02-01", "Z000510113", "PR GANTS ANSELL HYFLEX 11638 T8", "EPIs", "N", "6.00", 2),
    ("2026-02-01", "Z000527915", "Gants soudure a chaud droit T9", "EPIs", "N", "4.10", 2),
    ("2026-02-01", "Z000527916", "Gants soudure a chaud gauche T9", "EPIs", "N", "4.10", 2),
    ("2026-02-01", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "N", "1.20", 20),
    ("2026-02-01", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "A", "1.20", 100),
    ("2026-02-01", "Z000522887", "LUNETTES PROTECTION ENGLOBANTES INCOLORES 568,01,00,00", "EPIs", "A", "0.72", 3),
    ("2026-02-02", "Z000528969", "PROTECTION DE LA TETE NOM CASQUETTE", "EPIs", "A", "7.50", 1),
    ("2026-02-02", "IM02181405", "BOUCHONS OREILLES EAR MOUSSE JAUNE ULTRAFIT SACHET DE PAIRE", "EPIs", "A", "1.00", 2),
    ("2026-02-02", "Z000510114", "PR GANTS ANSELL HYFLEX 11638 T9", "EPIs", "A", "6.00", 4),
    ("2026-02-02", "Z000527915", "Gants soudure a chaud droit T9", "EPIs", "A", "4.10", 4),
    ("2026-02-02", "Z000527916", "Gants soudure a chaud gauche T9", "EPIs", "A", "4.10", 4),
    (
        "2026-02-02",
        "N001715606",
        "BUSE A GAZI DIX 1-3-5415 A ; CN65800,131/79721C BONNEFON SAS",
        "PR BERCEAU",
        "A",
        "16.72",
        4,
    ),
    ("2026-02-02", "Z000317849", "BUSE D16 PR TORCHE MIG-MAG AUTO SCHRUB", "PR BERCEAU", "A", "14.96", 4),
    (
        "2026-02-02",
        "Z000527999",
        "PRODUIT SOUDAGE SAUF BAGUETTE & FIL PRODUIT ANTI ADHERENT SOUDURE COND SPRAY CONT 400 ML IKV-FILMSEC 1024",
        "PRODUIT CHIMIQUE",
        "A",
        "10.63",
        1,
    ),
    ("2026-02-03", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "A", "1.20", 20),
    ("2026-02-03", "Z000317914", "DIFFUSEUR PR TORCHE MIG-MAG AUTO SCHRUB", "PR BERCEAU", "N", "31.00", 2),
    ("2026-02-03", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "B", "1.20", 20),
    ("2026-02-04", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "A", "1.20", 100),
    ("2026-02-05", "Z000510114", "PR GANTS ANSELL HYFLEX 11638 T9", "EPIs", "A", "6.00", 2),
    ("2026-02-05", "Z000510113", "PR GANTS ANSELL HYFLEX 11638 T8", "EPIs", "A", "6.00", 2),
    ("2026-02-05", "Z000522887", "LUNETTES PROTECTION ENGLOBANTES INCOLORES 568,01,00,00", "EPIs", "A", "0.72", 2),
    ("2026-02-05", "Z000528969", "PROTECTION DE LA TETE NOM CASQUETTE", "EPIs", "A", "7.50", 1),
    (
        "2026-02-05",
        "Z000482496",
        "LANCE NUE 22 UTILIS, TORCHE MIG MAG DINSE METZ 542 REF CA40520,200 BONNEFON,",
        "PR BERCEAU",
        "A",
        "575.94",
        1,
    ),
    ("2026-02-05", "N000880958", "POINTE CDO POUR TORCHE DINSE CW64785.038", "PR BERCEAU", "A", "150.85", 1),
    (
        "2026-02-05",
        "Z000370419",
        "DIFFUSEUR ISOLANT UTILIS, TORCHE MIG PUSHPULL DIMENS, DINSE REF, BONNEFON : CN65800,292",
        "PR BERCEAU",
        "A",
        "24.00",
        1,
    ),
    (
        "2026-02-05",
        "N001715606",
        "BUSE A GAZI DIX 1-3-5415 A ; CN65800,131/79721C BONNEFON SAS",
        "PR BERCEAU",
        "A",
        "16.72",
        1,
    ),
]


def q2(value: str | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Command(BaseCommand):
    help = "Import Berceau consumable purchases from the provided table; creates missing items/types."

    def handle(self, *args, **options):
        created_items = 0
        updated_items = 0
        created_purchases = 0
        skipped_purchases = 0
        touched_types: set[str] = set()

        for d_iso, reference, name, type_materiel, shift, unit_price_raw, quantity in BERCEAU_PURCHASE_ROWS:
            touched_types.add(type_materiel)
            unit_price = q2(unit_price_raw)
            total_price = q2(unit_price * Decimal(quantity))
            purchase_day = date.fromisoformat(d_iso)

            item_qs = ConsommableItem.objects.filter(equipe="Berceau", reference__iexact=reference, name__iexact=name)
            item = item_qs.first()
            if item is None:
                item = ConsommableItem.objects.create(
                    equipe="Berceau",
                    type_materiel=type_materiel,
                    name=name,
                    reference=reference,
                    unit_price_eur=unit_price,
                    is_active=True,
                )
                created_items += 1
            else:
                changed = False
                if item.type_materiel != type_materiel:
                    item.type_materiel = type_materiel
                    changed = True
                if q2(item.unit_price_eur) != unit_price:
                    item.unit_price_eur = unit_price
                    changed = True
                if not item.is_active:
                    item.is_active = True
                    changed = True
                if changed:
                    item.save(update_fields=["type_materiel", "unit_price_eur", "is_active"])
                    updated_items += 1

            exists = ConsommablePurchase.objects.filter(
                equipe="Berceau",
                shift=shift,
                item=item,
                quantity=quantity,
                unit_price_eur=unit_price,
                total_price_eur=total_price,
                purchase_date=purchase_day,
            ).exists()
            if exists:
                skipped_purchases += 1
                continue

            ConsommablePurchase.objects.create(
                equipe="Berceau",
                shift=shift,
                item=item,
                quantity=quantity,
                unit_price_eur=unit_price,
                total_price_eur=total_price,
                purchase_date=purchase_day,
                note="Import Berceau 2026-02",
            )
            created_purchases += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Berceau purchases import done: "
                f"{created_items} items created, {updated_items} items updated, "
                f"{created_purchases} purchases created, {skipped_purchases} purchases skipped."
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Types touched: {', '.join(sorted(touched_types))}"))
