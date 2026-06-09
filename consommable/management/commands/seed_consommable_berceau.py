from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q

from consommable.models import ConsommableItem

# (type_materiel, name, reference, unit_price_eur) — aligned with Réf_Mabec catalog
BERCEAU_CATALOG = [
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
    ("EPIs", "PROTECTION DE LA TETE NOM CASQUETTE", "Z000528969", "7.50"),
    ("TUBE CONTACT", "TUBE CONTACT BERCEAU", "Z000366717", "1.20"),
    ("AUTRE", "SAC DE 10 KG DE CHIFFON BLANC COTON SANS COUTURE POUR ESSUYAGES DELICATS", "P935852408", "13.64"),
    ("FOURNITURE", "POCHETTE DE 4 MARQUEURS EFFACABLES 961242 54211Z STE DACTYL BUREAU", "IM02094838", "3.15"),
    ("PR BERCEAU", "JOINT THORIQUE UTILIS, TORCHE DINSE DIMENS, DIAM 22*2 1023052,08", "Z000472423", "0.98"),
    ("PR BERCEAU", "INTERMEDIAIRE TARAUDE M6 UTILIS LANCE TORCHE DINSE", "Z000458741", "13.08"),
    (
        "PR BERCEAU",
        "DIFFUSEUR ISOLANT UTILIS, TORCHE MIG PUSHPULL DIMENS, DINSE REF, BONNEFON : CN65800,292",
        "Z000370419",
        "24.00",
    ),
    (
        "PR BERCEAU",
        "LANCE NUE 22 UTILIS, TORCHE MIG MAG DINSE METZ 542 REF CA40520,200 BONNEFON,",
        "Z000482496",
        "566.93",
    ),
    ("PR BERCEAU", "TORCHE INDEXEE ISOLEE 30 SCHRUB", "Z000373801", "572.00"),
    ("PR BERCEAU", "JOINT THORIQUE D,INT 12 TORE 2,5 VITON 80SH", "X045157501", "0.44"),
    ("PR BERCEAU", "GUIDE FIL PR TORCHE P915271407 SCHRUB", "P915282761", "12.30"),
    ("PR BERCEAU", "BAGUE DETANCHEITE PR TORCHE MIG-MAG AUTO SCHRUB BAGUE D ETANCHEITE", "Z000317912", "32.40"),
    ("PR BERCEAU", "BUSE D16 PR TORCHE MIG-MAG AUTO SCHRUB", "Z000317849", "23.60"),
    ("PR BERCEAU", "DIFFUSEUR PR TORCHE MIG-MAG AUTO SCHRUB", "Z000317914", "54.60"),
    ("PR BERCEAU", "BAGUE ANTI-RETOUR PR TORCHE MIG-MAG AUTO SCHRUB", "Z000317911", "51.25"),
    ("PR BERCEAU", "BROSSE A LATTE DIMENS. 150*35*20 LONGUEUR FIBRE 40MM", "Z000494562", "17.30"),
    ("PR BERCEAU", "BUSE A GAZ DIX 1-3-5415 A : CN65800.131 79721C BONNEFON SAS", "N001715606", "16.72"),
    ("PR TORCHE MANUELLE", "TORCHES 70025220 05639D ESAB AUTOMATION, S.A.", "IM02169938", "244.00"),
    (
        "PR TORCHE MANUELLE",
        "BUSE DE GAZ STANDARD POUR TORCHE PSF250 ESAB 0458464881 37774H ESAB FRANCE SA",
        "N001513969",
        "26.54",
    ),
    (
        "PR TORCHE MANUELLE",
        "PROTECTION ANTI PROJECTION PSF 250 ESAB 0458471002 37774H ESAB FRANCE SA",
        "N001513970",
        "5.00",
    ),
    (
        "PR TORCHE MANUELLE",
        "SUPPORT TC M6 POUR TORCHE PSF 250 ESAB 0366314001 37774H ESAB FRANCE SA",
        "N001513971",
        "11.60",
    ),
    ("PRODUIT CHIMIQUE", "ACEITE ANTIADHERENTE, REF. 4204118042-10LT FRONIUS INTERNATIONA", "Z000505392", "171.86"),
    (
        "PRODUIT CHIMIQUE",
        "PRODUIT SOUDAGE SAUF BAGUETTE & FIL PRODUIT ANTI ADHERENT SOUDURE COND SPRAY CONT 400 ML IKV-FILMSEC 1024",
        "Z000527999",
        "10.50",
    ),
]

# Legacy wrong rows from first seed (reference typos) — deactivate after catalog refresh
LEGACY_BAD_KEYS = {
    ("Gants soudure a chaud droit T9", "Z000527916"),
    ("LANCE NUE 22 UTILIS, TORCHE MIG MAG DINSE METZ 542 REF CA40520,200 BONNEFON", "Z000452496"),
    ("JOINT TORIQUE D,INT 12 TORE 2,5 VITON 80SH", "X043157501"),
    ("GUIDE FIL PR TORCHE SCHRUB", "P915287140"),
}


class Command(BaseCommand):
    help = "Seed the Berceau consumable catalog (type_materiel + designation + reference + unit price)."

    def handle(self, *args, **options):
        ConsommableItem.objects.filter(equipe="Berceau", type_materiel="PR TORCHE MANULLE").update(
            type_materiel="PR TORCHE MANUELLE"
        )

        created, updated = 0, 0
        catalog_keys = set()
        for type_materiel, name, reference, price in BERCEAU_CATALOG:
            catalog_keys.add((name, reference))
            obj, was_created = ConsommableItem.objects.update_or_create(
                equipe="Berceau",
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
        for name, reference in LEGACY_BAD_KEYS:
            deactivated += ConsommableItem.objects.filter(
                equipe="Berceau", name=name, reference=reference, is_active=True
            ).update(is_active=False)

        keep_q = Q()
        for name, reference in catalog_keys:
            keep_q |= Q(name=name, reference=reference)
        deactivated += ConsommableItem.objects.filter(equipe="Berceau", is_active=True).exclude(keep_q).update(
            is_active=False
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Berceau catalog seeded: {created} created, {updated} updated, {deactivated} legacy rows deactivated."
            )
        )
