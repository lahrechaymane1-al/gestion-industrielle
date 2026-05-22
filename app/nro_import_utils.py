"""Utilities for NRO2026 Excel → AlertePanne import."""

from __future__ import annotations

from datetime import date

IMPORT_TAG = "[import:NRO2026]"

# Calendrier diversité NRO2026 (date enregistrée en base / store-date).
NRO2026_DIVERSITE_A1_RANGES: tuple[tuple[date, date], ...] = (
    (date(2026, 5, 1), date(2026, 5, 10)),
    (date(2026, 5, 13), date(2026, 5, 14)),
)


def diversite_for_store_day(day: date) -> str:
    """A1 sur les plages définies ; sinon A3 (mai 2026 import)."""
    for start, end in NRO2026_DIVERSITE_A1_RANGES:
        if start <= day <= end:
            return "A1"
    return "A3"


def parse_import_date(raw: str) -> date:
    text = (raw or "").strip()
    if not text:
        raise ValueError("Date vide (format attendu: AAAA-MM-JJ, ex. 2026-05-01).")
    return date.fromisoformat(text)


def import_tag_for_day(day: date | None) -> str:
    if day is None:
        return IMPORT_TAG
    return f"{IMPORT_TAG}:{day.isoformat()}"


def filter_rows_by_day(rows: list[dict], day: date) -> list[dict]:
    return [r for r in rows if r["date"] == day]


def distinct_days_in_rows(rows: list[dict]) -> list[date]:
    return sorted({r["date"] for r in rows})

PANNE_NAME_ALIASES: dict[str, str] = {
    "Changement des éléectrodes": "Changement des électrodes",
    "Problème élevateur": "Problème élévateur",
    "Probleme de Arrêt": "Arrêt",
    "Probleme GAZ": "Problème GAZ",
    "Probleme de capteur": "Problème de capteur",
    "Probleme de vérin": "Problème de vérin",
    "Probleme de générateur": "Problème de générateur",
}

MOYEN_NAME_ALIASES: dict[str, str] = {
    "Poinçoneuse": "Poinçonneuse",
}

TYPE_TO_CATEGORY: dict[str, str] = {
    "maintenance": "maintenance",
    "fabrication": "fabrication",
    "logistique": "logistique",
    "kta": "kta",
}


def normalize_panne_name(raw: str) -> str:
    name = (raw or "").strip()
    return PANNE_NAME_ALIASES.get(name, name)


def normalize_moyen_name(raw: str) -> str:
    name = (raw or "").strip()
    return MOYEN_NAME_ALIASES.get(name, name)


def category_from_excel_type(raw: str) -> str:
    key = (raw or "").strip().lower()
    return TYPE_TO_CATEGORY.get(key, "fabrication")


def comment_from_imported_cause(cause: str | None) -> str:
    """Texte problème sans tags import / diversité."""
    import re

    raw = (cause or "").strip()
    raw = re.sub(r"^\[import:NRO2026(?::\d{4}-\d{2}-\d{2})?\]\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\[diversite:[^\]]+\]\s*", "", raw, flags=re.IGNORECASE)
    return raw.strip()


def build_cause(diversite: str, commentaire: str, *, day: date | None = None) -> str:
    div = (diversite or "A1").strip().upper()
    if div not in {"A1", "A3"}:
        div = "A1"
    text = (commentaire or "").strip()
    tag = import_tag_for_day(day)
    return f"{tag} [diversite:{div}] {text}".strip()


def split_row_into_hour_fiches(total_minutes: int) -> list[tuple[int, int]]:
    """
    Découpe une ligne Excel en fiches par heure de production (H1–H8).
    Chaque tranche dure au plus 60 min ; le reliquat après H7 va sur H8.
    """
    remaining = int(total_minutes)
    if remaining <= 0:
        return [(1, 0)]
    out: list[tuple[int, int]] = []
    hour = 1
    while remaining > 0 and hour < 8:
        chunk = min(remaining, 60)
        out.append((hour, chunk))
        remaining -= chunk
        hour += 1
    if remaining > 0:
        out.append((8, remaining))
    return out


def resolve_poste(
    module,
    poste_name: str,
    postes_by_module: dict[tuple[int, str], object],
    postes_by_name: dict[str, list],
):
    """Poste sur le module Excel, sinon même nom sur un autre module (ex. OP90)."""
    poste = postes_by_module.get((module.id, poste_name))
    if poste:
        return poste
    candidates = postes_by_name.get(poste_name) or []
    if len(candidates) == 1:
        return candidates[0]
    for p in candidates:
        if p.module_id != module.id:
            return p
    return None


def resolve_moyen(
    poste,
    module,
    moyen_name: str,
    moyens_by_poste: dict[tuple[int, str], object],
    moyens_by_module: dict[tuple[int, str], object],
):
    """Moyen sur le poste, sinon sur le module ; vide si moyen = nom du poste (ex. M1/M1)."""
    if not moyen_name:
        return None
    if moyen_name.strip().upper() == (poste.name or "").strip().upper():
        return None
    moyen = moyens_by_poste.get((poste.id, moyen_name))
    if moyen:
        return moyen
    return moyens_by_module.get((module.id, moyen_name))
