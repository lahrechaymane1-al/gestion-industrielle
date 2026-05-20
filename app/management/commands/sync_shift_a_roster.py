import argparse
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from app.models import OperateurEffectif
from app.effectif_team import CANONICAL_CODE_EQUIPE_BY_SCOPE


def _norm_name(s: str) -> str:
    s = " ".join(str(s or "").strip().split())
    s = re.sub(r"\s+", " ", s)
    return s.casefold()

def _name_keys(full_name: str) -> set[str]:
    """Generate multiple normalized keys for matching."""
    full = _norm_name(full_name)
    parts = [p for p in re.split(r"\s+", full) if p]
    keys = {full}
    if len(parts) == 2:
        keys.add(_norm_name(f"{parts[1]} {parts[0]}"))
    if len(parts) > 2:
        # Also try reversing all parts (common 'prenom nom' vs 'nom prenom' issues).
        keys.add(_norm_name(" ".join(reversed(parts))))
        # Also try moving last token first: "nom nom2 prenom" -> "prenom nom nom2"
        keys.add(_norm_name(" ".join([parts[-1], *parts[:-1]])))
        # Also try moving first token last: "prenom nom nom2" -> "nom nom2 prenom"
        keys.add(_norm_name(" ".join([*parts[1:], parts[0]])))
    # Remove spaces key for robustness (e.g. 'elwahibi' vs 'el wahibi')
    keys.add(full.replace(" ", ""))
    return keys


def _slug_for_row(nom: str, prenom: str, equipe: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _norm_name(f"{nom}{prenom}{equipe}"))


SHIFT_A_ROSTER = [
            # (nom, prenom, equipe, fonction)
    ("EL MASLOUHI", "Hamza", "Berceau", "OPERATEUR"),
            ("DOUICHE", "Abdelmonim", "Berceau", "PSP"),
            ("LOUDINI", "Otmane", "Berceau", "OPERATEUR"),
            ("BRIHMI", "Amine", "Berceau", "OPERATEUR"),
            ("EARNAK", "Brahim", "Berceau", "OPERATEUR"),
            ("KHAYI", "Hamza", "Berceau", "OPERATEUR"),
            ("BRAHIMI", "Mehdi", "Berceau", "OPERATEUR"),
            ("BENMARZAK", "Bouaza", "Berceau", "OPERATEUR"),
            ("LAAFAR", "Amine", "Berceau", "OPERATEUR"),
            ("LAKHDAR", "Driss", "CCB", "OPERATEUR"),
            ("EL WAHIBI", "Yassine", "CCB", "OPERATEUR"),
            ("CHAKRI", "Fayssal", "CCB", "OPERATEUR"),
            ("RAMLI", "Amine", "CCB", "OPERATEUR"),
            ("ELHASANY", "Khalid", "CCB", "OPERATEUR"),
        ]

# Shift B — ALAMI CHENTOUFI Abdelilah + PSP TOURI Hicham (pas de rôle RU effectif).
SHIFT_B_ROSTER = [
    ("ALAMI CHENTOUFI", "Abdelilah", "Berceau", "OPERATEUR"),
    ("TOURI", "HICHAM", "Berceau", "PSP"),
    ("ISMAILI", "OUSSAMA", "Berceau", "OPERATEUR"),
    ("EZZARI", "ZOUHAIR", "Berceau", "OPERATEUR"),
    ("SAHMOUDI", "OTHMAN", "Berceau", "OPERATEUR"),
    ("CHOAYBI", "AYOUB", "Berceau", "OPERATEUR"),
    ("LKHAL", "OMAR", "Berceau", "OPERATEUR"),
    ("EL AZIZI", "ADNAN", "Berceau", "OPERATEUR"),
    ("BOUSSIF", "AYOUB", "Berceau", "OPERATEUR"),
    ("OUACHA", "Otman", "CCB", "OPERATEUR"),
    ("EL OUAAR", "Naoufal", "CCB", "OPERATEUR"),
    ("ZRAIDI", "Otman", "CCB", "OPERATEUR"),
    ("ELBOOURZGUI", "Mohamed", "CCB", "OPERATEUR"),
    ("TOUISS", "Ismail", "CCB", "OPERATEUR"),
]

# Shift N — Berceau (UEP Berceau, responsabilité unité selon organigramme site).
SHIFT_N_ROSTER = [
    ("CHARNANE", "Mouad", "Berceau", "PSP"),
    ("MOUNANE", "Achraf", "Berceau", "OPERATEUR"),
    ("BAL", "Abdelkamal", "Berceau", "OPERATEUR"),
    ("ELMTAOUAL", "Oussama", "Berceau", "OPERATEUR"),
    ("CHALI", "Ahmed", "Berceau", "OPERATEUR"),
    ("ECH-CHELIYEH", "Mustapha", "Berceau", "OPERATEUR"),
    ("EL BAGHOURI", "Othmane", "Berceau", "OPERATEUR"),
    ("EL-HADDAD", "Omar", "Berceau", "OPERATEUR"),
    ("LGHAZY", "Said", "Berceau", "OPERATEUR"),
]

SHIFT_ROSTERS: dict[str, list[tuple[str, str, str, str]]] = {
    "A": SHIFT_A_ROSTER,
    "B": SHIFT_B_ROSTER,
    "N": SHIFT_N_ROSTER,
}


def _sparse_row_payload(slug: str) -> dict:
    """Champs à laisser vides / minimum technique (hors dates NOT NULL gérées par défaut Django)."""
    return {
        "cin": f".{slug}"[:32],
        "identifiant": f".{slug}"[:64],
        "num_tel": "",
        "ville_actuelle": "",
        "niveau_etude": "",
        "numero_casier": "",
        "parada_transport": "",
        "specialite": "",
        "ville_origine": "",
        "code_equipe": "",
        "type_contrat": "",
        "sexe": "",
        "taille_pantalon": "",
        "taille_veste": "",
        "pointure_chaussure": 1,
    }


def _build_by_name_map(qs) -> dict[str, OperateurEffectif]:
        by_name: dict[str, OperateurEffectif] = {}
    for row in qs:
            for k in _name_keys(row.nom_complet):
                by_name.setdefault(k, row)
    return by_name


def _fonction_create_order(fonction: str) -> int:
    return {"PSP": 0, "OPERATEUR": 1}.get((fonction or "").strip().upper(), 9)


def _link_berceau_operators_psp(
    roster: list[tuple[str, str, str, str]],
    by_name: dict[str, OperateurEffectif],
    psp_row: OperateurEffectif | None,
) -> int:
    """Met à jour psp_lead pour les opérateurs Berceau du roster si le PSP est connu."""
    if not psp_row:
        return 0
    linked = 0
    for nom, prenom, equipe, fonction in roster:
        if equipe != "Berceau" or fonction != "OPERATEUR":
            continue
        full_name = f"{nom} {prenom}"
        eff = None
        for k in _name_keys(full_name):
            eff = by_name.get(k)
            if eff:
                break
        if eff and eff.psp_lead_id != psp_row.id:
            OperateurEffectif.objects.filter(pk=eff.id).update(psp_lead_id=psp_row.id)
            linked += 1
    return linked


def _resolve_psp_row(
    roster: list[tuple[str, str, str, str]],
    by_name: dict[str, OperateurEffectif],
) -> OperateurEffectif | None:
    """PSP Berceau dans le roster (pour lier psp_lead aux opérateurs Berceau)."""
    for nom, prenom, equipe, fonction in roster:
        if fonction != "PSP" or equipe != "Berceau":
            continue
        full_name = f"{nom} {prenom}"
        for k in _name_keys(full_name):
            row = by_name.get(k)
            if row:
                return row
    return None


class Command(BaseCommand):
    help = (
        "Sync effectif from embedded roster sheets for shift A, B ou N (PSP Berceau, opérateurs Berceau/CCB). "
        "Use --shift A|B|N. Creates/updates nom, UEP, shift, rôle. "
        "CIN/identifiant minimal stubs ('.'+slug); autres champs vides sauf NOT NULL (ex. pointure=1)."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--shift",
            choices=("A", "B", "N"),
            default="A",
            help="Roster / shift cible (default: A).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply updates (default is dry-run).",
        )
        parser.add_argument(
            "--create-missing",
            action="store_true",
            help="Create missing rows. Only roster fields + minimal DB keys; unknown info left blank (see command docstring).",
        )

    def handle(self, *args, **options):
        apply: bool = bool(options["apply"])
        create_missing: bool = bool(options["create_missing"])
        desired_shift: str = options["shift"]
        roster = SHIFT_ROSTERS[desired_shift]

        existing_qs = OperateurEffectif.objects.filter(is_deleted=False).only(
            "id",
            "nom_complet",
            "equipe",
            "shift",
            "fonction",
            "psp_lead_id",
            "cin",
            "identifiant",
            "code_equipe",
        )
        by_name = _build_by_name_map(existing_qs)

        psp_row = _resolve_psp_row(roster, by_name)

        missing = 0
        updated = 0
        created = 0
        to_update: list[tuple[int, dict]] = []
        to_create: list[dict] = []

        for nom, prenom, equipe, fonction in roster:
            full_name = f"{nom} {prenom}"
            eff = None
            for k in _name_keys(full_name):
                eff = by_name.get(k)
                if eff:
                    break
            if not eff:
                if not create_missing:
                    missing += 1
                    self.stdout.write(self.style.WARNING(f"Missing effectif row for '{full_name}' (equipe={equipe})"))
                    continue

                nom_complet = f"{prenom} {nom}"
                slug = _slug_for_row(nom, prenom, equipe)
                sparse = _sparse_row_payload(slug)
                canon_code = CANONICAL_CODE_EQUIPE_BY_SCOPE.get((equipe, desired_shift), "") or ""
                new_row = {
                    "nom_complet": nom_complet,
                    "equipe": equipe,
                    "shift": desired_shift,
                    "fonction": fonction,
                    **sparse,
                }
                if canon_code:
                    new_row["code_equipe"] = canon_code
                to_create.append(new_row)
                continue

            changes: dict = {}
            if eff.equipe != equipe:
                changes["equipe"] = equipe
            if (eff.shift or "").strip() != desired_shift:
                changes["shift"] = desired_shift
            if (eff.fonction or "").strip().upper() != fonction:
                changes["fonction"] = fonction

            canon_code = CANONICAL_CODE_EQUIPE_BY_SCOPE.get((equipe, desired_shift), "") or ""
            if canon_code and (eff.code_equipe or "").strip() != canon_code:
                changes["code_equipe"] = canon_code

            # Auto-assign PSP lead for Berceau operators in this roster when PSP exists.
            if equipe == "Berceau" and fonction == "OPERATEUR" and psp_row:
                if eff.psp_lead_id != psp_row.id:
                    changes["psp_lead_id"] = psp_row.id

            # Ancien import AUTO-* : aligner sur fiche légère (champs vides + stubs '.').
            slug_u = _slug_for_row(nom, prenom, equipe)
            if str(eff.cin or "").startswith("AUTO-") or str(eff.identifiant or "").startswith(
                "AUTO-"
            ):
                changes.update(_sparse_row_payload(slug_u))

            if changes:
                to_update.append((eff.id, changes))

        if not to_update:
            if not to_create:
                if missing:
                    self.stdout.write(
                        self.style.WARNING(
                            f"No rows to update or create; missing={missing} roster names without effectif "
                            f"(add rows or re-run with --create-missing).\n"
                            f"  Exemple: python manage.py sync_shift_a_roster --shift {desired_shift} "
                            f"--create-missing --apply"
                        )
                    )
                else:
                    self.stdout.write(self.style.SUCCESS("No changes needed."))
                return

        if to_update:
            self.stdout.write(f"Planned updates (count={len(to_update)}) apply={apply}")
            for eff_id, changes in to_update:
                self.stdout.write(f"- effectif_id={eff_id} changes={changes}")

        if to_create:
            self.stdout.write(f"Planned creates (count={len(to_create)}) apply={apply}")
            for row in to_create:
                self.stdout.write(f"- create nom_complet={row['nom_complet']} equipe={row['equipe']} shift={row['shift']} fonction={row['fonction']}")

        if not apply:
            self.stdout.write(self.style.WARNING("Dry-run only. Re-run with --apply to write changes."))
            return

        with transaction.atomic():
            if to_create:
                to_create_sorted = sorted(
                    to_create,
                    key=lambda r: (_fonction_create_order(r["fonction"]), r["nom_complet"]),
                )
                for row in to_create_sorted:
                    OperateurEffectif.objects.create(**row)
                    created += 1
            for eff_id, changes in to_update:
                OperateurEffectif.objects.filter(pk=eff_id).update(**changes)
                updated += 1

            # Après création du PSP, résoudre à nouveau et lier les opérateurs Berceau (première importation).
            by_after = _build_by_name_map(
                OperateurEffectif.objects.filter(is_deleted=False).only(
                    "id",
                    "nom_complet",
                    "equipe",
                    "shift",
                    "fonction",
                    "psp_lead_id",
                    "cin",
                    "identifiant",
                    "code_equipe",
                )
            )
            psp_after = _resolve_psp_row(roster, by_after)
            linked_psp = _link_berceau_operators_psp(roster, by_after, psp_after)

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete. shift={desired_shift} created={created} updated={updated} "
                f"psp_links_applied={linked_psp} missing_in_db={missing}"
            )
        )

