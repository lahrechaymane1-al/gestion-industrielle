from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand

from consommable.models import ConsommableItem, ConsommablePurchase


# Source: second provided Berceau sheet screenshot.
# All rows are imported for equipe="Berceau" only.
# The row number is kept in note so repeated identical-looking rows from the sheet are preserved,
# while the command remains idempotent when re-run.
BERCEAU_PURCHASE_ROWS = [
    ("2026-02-06", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "N", "1.20", 20),
    ("2026-02-06", "Z000502100", "PROTECTION DU CORPS, VETEMENT POUR HOMME NOM TABLIER", "EPIs", "B", "8.54", 1),
    ("2026-02-06", "Z000510113", "PR GANTS ANSELL HYFLEX 11638 T8", "EPIs", "B", "6.00", 3),
    ("2026-02-06", "Z000527915", "Gants soudure a chaud droit T9", "EPIs", "B", "4.10", 5),
    ("2026-02-06", "Z000527916", "Gants soudure a chaud gauche T9", "EPIs", "B", "4.10", 5),
    ("2026-02-06", "IM02181405", "BOUCHONS OREILLES EAR MOUSSE JAUNE ULTRAFIT SACHET DE PAIRE", "EPIs", "B", "1.00", 4),
    ("2026-02-06", "Z000522887", "LUNETTES PROTECTION ENGLOBANTES INCOLORES 568,01,00,00", "EPIs", "B", "0.72", 6),
    ("2026-02-06", "Z000528969", "PROTECTION DE LA TETE NOM CASQUETTE", "EPIs", "B", "7.50", 1),
    (
        "2026-02-06",
        "Z000527999",
        "PRODUIT SOUDAGE SAUF BAGUETTE & FIL PRODUIT ANTI ADHERENT SOUDURE COND SPRAY CONT 400 ML IKV-FILMSEC 1024",
        "PRODUIT CHIMIQUE",
        "B",
        "10.63",
        1,
    ),
    ("2026-02-06", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "B", "1.20", 30),
    ("2026-02-06", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "A", "1.20", 100),
    ("2026-02-06", "Z000317849", "BUSE D16 PR TORCHE MIG-MAG AUTO SCHRUB", "PR BERCEAU", "A", "14.90", 4),
    ("2026-02-06", "Z000317914", "DIFFUSEUR PR TORCHE MIG-MAG AUTO SCHRUB", "PR BERCEAU", "A", "31.00", 4),
    (
        "2026-02-06",
        "Z000370419",
        "DIFFUSEUR ISOLANT UTILIS, TORCHE MIG PUSHPULL DIMENS, DINSE REF, BONNEFON : CN65800,292",
        "PR BERCEAU",
        "A",
        "24.00",
        4,
    ),
    ("2026-02-06", "Z000317911", "BAGUE ANTI-RETOUR PR TORCHE MIG-MAG AUTO SCHRUB", "PR BERCEAU", "A", "30.45", 4),
    (
        "2026-02-06",
        "N001715606",
        "BUSE A GAZI DIX 1-3-5415 A ; CN65800,131/79721C BONNEFON SAS",
        "PR BERCEAU",
        "A",
        "16.72",
        4,
    ),
    (
        "2026-02-06",
        "Z000527999",
        "PRODUIT SOUDAGE SAUF BAGUETTE & FIL PRODUIT ANTI ADHERENT SOUDURE COND SPRAY CONT 400 ML IKV-FILMSEC 1024",
        "PRODUIT CHIMIQUE",
        "A",
        "10.63",
        2,
    ),
    ("2026-02-07", "Z000527915", "Gants soudure a chaud droit T9", "EPIs", "N", "4.10", 2),
    ("2026-02-07", "Z000527916", "Gants soudure a chaud gauche T9", "EPIs", "N", "4.10", 2),
    ("2026-02-07", "Z000510113", "PR GANTS ANSELL HYFLEX 11638 T8", "EPIs", "N", "6.00", 2),
    ("2026-02-07", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "N", "1.20", 20),
    ("2026-02-07", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "N", "1.20", 100),
    ("2026-02-07", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "N", "1.20", 20),
    ("2026-02-09", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "A", "1.20", 100),
    ("2026-02-10", "Z000366717", "TUBE CONTACT BERCEAU", "TUBE CONTACT", "N", "1.20", 20),
    ("2026-02-10", "Z000527915", "Gants soudure a chaud droit T9", "EPIs", "N", "4.10", 1),
    ("2026-02-10", "Z000527916", "Gants soudure a chaud gauche T9", "EPIs", "N", "4.10", 1),
    (
        "2026-02-10",
        "P935852408",
        "SAC DE 10 KG DE CHIFFON BLANC COTON SANS COUTURES POUR ESSUYAGES DELICATS",
        "AUTRE",
        "A",
        "30.84",
        1,
    ),
]


def q2(value: str | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Command(BaseCommand):
    help = "Import Berceau consumable purchases lot 2 from the provided table; creates missing items/types."

    def handle(self, *args, **options):
        created_items = 0
        updated_items = 0
        created_purchases = 0
        skipped_purchases = 0
        touched_types: set[str] = set()

        for idx, (d_iso, reference, name, type_materiel, shift, unit_price_raw, quantity) in enumerate(
            BERCEAU_PURCHASE_ROWS, start=1
        ):
            touched_types.add(type_materiel)
            unit_price = q2(unit_price_raw)
            total_price = q2(unit_price * Decimal(quantity))
            purchase_day = date.fromisoformat(d_iso)
            note = f"Import Berceau 2026-02 lot 2 row {idx:02d}"

            item = ConsommableItem.objects.filter(
                equipe="Berceau", reference__iexact=reference, name__iexact=name
            ).first()
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
                note=note,
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
                note=note,
            )
            created_purchases += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Berceau purchases lot 2 import done: "
                f"{created_items} items created, {updated_items} items updated, "
                f"{created_purchases} purchases created, {skipped_purchases} purchases skipped."
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Types touched: {', '.join(sorted(touched_types))}"))
