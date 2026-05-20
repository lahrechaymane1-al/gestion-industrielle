"""
Import lignes d'arrêt (tableau utilisateur) en AlertePanne pour 2026-05-13, poste OP60, shifts A / B / N.

Sans fiche **Production Berceau** par shift, le dashboard calcule des % d'impact à 0
(graphes « vides ») et les KPI RO/NRO sont absents : ce script crée une fiche minimale si elle
n'existe pas encore (objectifs H1–H6 en A1, H7–H8 en A3), puis resynchronise les temps d'arrêt
horaires depuis les alertes.

Idempotence : supprime les alertes dont la cause contient VERIFY_TAG pour le(s) shift(s) ciblé(s).

Usage:
  python manage.py import_verify_arrets_2026_05_13_op60 --shift B
  python manage.py import_verify_arrets_2026_05_13_op60 --shift N
  python manage.py import_verify_arrets_2026_05_13_op60 --shift all
  python manage.py import_verify_arrets_2026_05_13_op60 --dry-run --shift B
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from arret.models import AlertePanne, ArretCategory, BerceauMoyen, BerceauPoste, PanneType
from production.models import ProductionBerceau

VERIFY_TAG = "[VERIFY-ARRETS-2026-05-13]"
TARGET_DATE = date(2026, 5, 13)
POSTE_HINT = "OP60"

# (diversite, heure 1..8, moyen Excel, libellé panne pour matching, minutes)
RowSpec = tuple[str, int, str, str, int]

ROWS_SHIFT_A: list[RowSpec] = [
    ("A1", 1, "R2", "Amorçage", 5),
    ("A1", 1, "R1", "Amorçage", 5),
    ("A1", 2, "Maquette", "Chute de pièce", 3),
    ("A1", 2, "Maquette", "Chute de pièce", 6),
    ("A1", 3, "Maquette", "Problème pression", 8),
    ("A1", 3, "Maquette", "Fuite d'eau", 4),
    ("A1", 4, "Maquette", "Blocage de serrage", 6),
    ("A1", 4, "Maquette", "Problème de capteur", 3),
    ("A1", 5, "R2", "Défaut de robot MAG", 10),
    ("A1", 5, "R1", "Collision", 8),
    ("A1", 6, "R1", "Fuite d'air", 4),
    ("A1", 6, "R21", "Blocage de robot de transfert", 10),
    ("A3", 7, "R1", "Fuite d'air", 10),
    ("A3", 7, "R2", "Nettoyage des buses", 2),
    ("A3", 8, "R2", "Chute de la torche", 9),
]

ROWS_SHIFT_B: list[RowSpec] = [
    ("A1", 1, "R2", "Amorçage", 5),
    ("A1", 1, "R1", "Amorçage", 7),
    ("A1", 2, "Maquette", "Chute de pièce", 4),
    ("A1", 2, "Maquette", "Chute de pièce", 3),
    ("A1", 3, "Maquette", "Problème pression", 8),
    ("A1", 3, "Maquette", "Fuite d'eau", 4),
    ("A1", 4, "Maquette", "Blocage de serrage", 6),
    ("A1", 4, "Maquette", "Problème de capteur", 3),
    ("A1", 5, "R2", "Défaut de robot MAG", 10),
    ("A1", 5, "R1", "Collision", 8),
    ("A1", 6, "R1", "Fuite d'air", 4),
    ("A1", 6, "R21", "Blocage de robot de transfert", 10),
    ("A3", 7, "R1", "Fuite d'air", 10),
    ("A3", 7, "R2", "Nettoyage des buses", 2),
    ("A3", 8, "R2", "Chute de la torche", 5),
]

ROWS_SHIFT_N: list[RowSpec] = [
    ("A1", 1, "R2", "Amorçage", 6),
    ("A1", 1, "R1", "Amorçage", 3),
    ("A1", 2, "Maquette", "Chute de pièce", 4),
    ("A1", 2, "Maquette", "Chute de pièce", 7),
    ("A1", 3, "Maquette", "Problème pression", 3),
    ("A1", 3, "Maquette", "Fuite d'eau", 2),
    ("A1", 4, "Maquette", "Blocage de serrage", 5),
    ("A1", 4, "Maquette", "Problème de capteur", 8),
    ("A1", 5, "R2", "Défaut de robot MAG", 9),
    ("A1", 5, "R1", "Collision", 9),
    ("A1", 6, "R1", "Fuite d'air", 5),
    ("A1", 6, "R21", "Blocage de robot de transfert", 2),
    ("A3", 7, "R1", "Fuite d'air", 10),
    ("A3", 7, "R2", "Nettoyage des buses", 2),
    ("A3", 8, "R2", "Chute de la torche", 9),
]

ROWS_BY_SHIFT: dict[str, list[RowSpec]] = {
    "A": ROWS_SHIFT_A,
    "B": ROWS_SHIFT_B,
    "N": ROWS_SHIFT_N,
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _find_panne_type(label: str) -> PanneType | None:
    """Map libellé tableau / Excel vers PanneType (référentiel local)."""
    n = _norm(label)
    if "fuite" in n:
        if "eau" in n:
            pt = PanneType.objects.filter(
                Q(name__icontains="Fuite") & Q(name__icontains="eau"), is_active=True
            ).order_by("id").first()
            if pt:
                return pt
        if "air" in n:
            pt = PanneType.objects.filter(
                Q(name__icontains="Fuite") & Q(name__icontains="air"), is_active=True
            ).order_by("id").first()
            if pt:
                return pt
    rules: list[tuple[str, Q]] = [
        ("amorcage", Q(name__icontains="Amor")),
        ("chute de piece", Q(name__icontains="Chute") & Q(name__icontains="pi")),
        ("chute de la torche", Q(name__icontains="torche")),
        ("probleme pression", Q(name__icontains="pression")),
        ("blocage de serrage", Q(name__icontains="serrage")),
        ("probleme de capteur", Q(name__icontains="capteur") & ~Q(name__iexact="Panne capteur")),
        ("defaut de robot mag", Q(name__icontains="robot") & Q(name__icontains="MAG")),
        ("collision", Q(name__icontains="Col") & Q(name__icontains="ision")),
        ("blocage de robot de transfert", Q(name__icontains="transfert")),
        ("nettoyage des buses", Q(name__icontains="Nettoyage")),
    ]
    for key, q in rules:
        if key in n or n in key:
            pt = PanneType.objects.filter(q, is_active=True).order_by("id").first()
            if pt:
                return pt
    first = re.split(r"[\s\-]+", label.strip(), maxsplit=1)[0]
    if len(first) >= 4:
        return PanneType.objects.filter(name__icontains=first[:12], is_active=True).order_by("id").first()
    return None


def _find_poste() -> BerceauPoste | None:
    q = Q(name__iexact="OP60") | Q(name__icontains="OP60")
    return (
        BerceauPoste.objects.filter(q, is_active=True)
        .select_related("module")
        .order_by("id")
        .first()
    )


def _find_moyen(poste: BerceauPoste, name: str) -> BerceauMoyen | None:
    n = name.strip()
    return (
        BerceauMoyen.objects.filter(poste=poste, name__iexact=n, is_active=True).first()
        or BerceauMoyen.objects.filter(poste=poste, name__icontains=n, is_active=True).order_by("id").first()
    )


def _ensure_minimal_production_berceau(cmd: BaseCommand, shift: str) -> None:
    """Une fiche (date, shift) avec objectifs > 0 : dénominateur shift + jour (Σ shifts)."""
    if ProductionBerceau.objects.filter(date=TARGET_DATE, shift=shift).exists():
        return
    hour_fields: dict = {}
    for h in range(1, 7):
        hour_fields[f"objectif_h{h}"] = 100
        hour_fields[f"production_h{h}"] = 95
        hour_fields[f"line_h{h}"] = "A1"
    for h in range(7, 9):
        hour_fields[f"objectif_h{h}"] = 100
        hour_fields[f"production_h{h}"] = 95
        hour_fields[f"line_h{h}"] = "A3"
    ProductionBerceau.objects.create(
        line="A1",
        date=TARGET_DATE,
        shift=shift,
        objectif=800,
        volume=0,
        rebut=0,
        retouche=0,
        temps_arrets=0,
        **hour_fields,
    )
    cmd.stdout.write(
        cmd.style.SUCCESS(
            f"Fiche Production Berceau créée pour {TARGET_DATE.isoformat()} shift {shift} "
            "(H1–H6 A1, H7–H8 A3, objectif shift = 800)."
        )
    )


def _resolve_rows(
    poste: BerceauPoste, rows: list[RowSpec]
) -> tuple[list[tuple[str, int, BerceauMoyen, PanneType, str, int]], list[str]]:
    resolved: list[tuple[str, int, BerceauMoyen, PanneType, str, int]] = []
    errors: list[str] = []
    for div, heure, moyen_name, panne_label, mins in rows:
        pt = _find_panne_type(panne_label)
        moyen = _find_moyen(poste, moyen_name)
        if not pt:
            errors.append(f"PanneType introuvable pour {panne_label!r}")
        if not moyen:
            errors.append(f"Moyen introuvable {moyen_name!r} sur {poste.name}")
        if pt and moyen:
            cause = f"[diversite:{div}] {VERIFY_TAG} {panne_label} — {moyen_name}"
            resolved.append((div, heure, moyen, pt, cause, mins))
    return resolved, errors


class Command(BaseCommand):
    help = "Insère les alertes panne OP60 (2026-05-13) pour shifts A, B et/ou N (tableau de vérification)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Affiche le plan sans écrire en base.")
        parser.add_argument(
            "--skip-production",
            action="store_true",
            help="Ne crée pas les fiches Production Berceau manquantes.",
        )
        parser.add_argument(
            "--shift",
            choices=["A", "B", "N", "all"],
            default="all",
            help="Shift à importer (défaut: all). Shift A déjà saisi → utiliser B ou N.",
        )

    def handle(self, *args, **options):
        dry: bool = options["dry_run"]
        skip_production: bool = options["skip_production"]
        shift_arg: str = options["shift"]
        shifts = list(ROWS_BY_SHIFT.keys()) if shift_arg == "all" else [shift_arg]

        poste = _find_poste()
        if not poste:
            self.stderr.write(self.style.ERROR(f"Aucun poste actif trouvé pour {POSTE_HINT!r}."))
            return

        mod = poste.module
        any_error = False

        for shift in shifts:
            rows = ROWS_BY_SHIFT[shift]
            resolved, errors = _resolve_rows(poste, rows)
            if errors:
                any_error = True
                self.stderr.write(self.style.ERROR(f"Shift {shift}:"))
                for e in errors:
                    self.stderr.write(self.style.ERROR(f"  {e}"))
                continue

            total_min = sum(t[5] for t in resolved)
            self.stdout.write(
                f"Shift {shift}: {poste.name} (module {mod.name}), {len(resolved)} lignes, {total_min} min."
            )

            if dry:
                for div, heure, moyen, pt, cause, mins in resolved:
                    self.stdout.write(f"  H{heure} {div} {moyen.name} | {pt.name} | {mins} min")
                if not skip_production and not ProductionBerceau.objects.filter(
                    date=TARGET_DATE, shift=shift
                ).exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"Dry-run shift {shift}: fiche Production Berceau à créer (objectifs H1–H8)."
                        )
                    )
                continue

            with transaction.atomic():
                deleted, _ = AlertePanne.objects.filter(
                    date=TARGET_DATE, shift=shift, cause__contains=VERIFY_TAG
                ).delete()
                if deleted:
                    self.stdout.write(
                        f"Shift {shift}: supprimé {deleted} alerte(s) avec le tag de vérification."
                    )

                if not skip_production:
                    _ensure_minimal_production_berceau(self, shift)

                for div, heure, moyen, pt, cause, mins in resolved:
                    AlertePanne.objects.create(
                        module=mod,
                        poste=poste,
                        moyen=moyen,
                        panne_type=pt,
                        cause=cause,
                        solution=f"Import vérification calculs (OP60, {TARGET_DATE.isoformat()}, shift {shift}).",
                        category=ArretCategory.FABRICATION,
                        date=TARGET_DATE,
                        shift=shift,
                        heure_production=heure,
                        temps_arret_min=mins,
                        equipe="Berceau",
                    )

            if not skip_production:
                for prod in ProductionBerceau.objects.filter(date=TARGET_DATE, shift=shift):
                    prod.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Shift {shift}: créé {len(resolved)} AlertePanne pour {TARGET_DATE.isoformat()}."
                )
            )

        if dry:
            self.stdout.write(self.style.WARNING("Dry-run : aucune écriture."))
        elif any_error:
            self.stderr.write(self.style.ERROR("Import partiel : corriger les erreurs ci-dessus."))
