"""Charge ``seeds/ccb_matrix.json`` (référentiel postes → moyens CCB)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


def _matrix_path() -> Path:
    return Path(__file__).resolve().parent / "seeds" / "ccb_matrix.json"


@lru_cache(maxsize=1)
def get_ccb_matrix() -> dict:
    raw = json.loads(_matrix_path().read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("ccb_matrix.json: racine objet attendu")
    return raw


def ccb_poste_names_in_order() -> list[str]:
    postes = get_ccb_matrix().get("postes") or []
    return [str(p.get("name") or "").strip() for p in postes if str(p.get("name") or "").strip()]


def ccb_moyen_order_list(poste_name: str) -> list[str]:
    """Ordre d'affichage (répétitions conservées pour index de tri)."""
    key = str(poste_name or "").strip()
    for p in get_ccb_matrix().get("postes") or []:
        if str(p.get("name") or "").strip() == key:
            return [str(x).strip() for x in (p.get("moyens") or []) if str(x).strip()]
    return []


def ccb_allowed_moyens_for_poste(poste_name: str) -> frozenset[str]:
    """Noms uniques autorisés pour un poste CCB (validation API)."""
    return frozenset(ccb_moyen_order_list(poste_name))


def ccb_moyen_sort_rank(poste_name: str) -> dict[str, int]:
    """Premier index dans la liste métier pour chaque moyen (doublons → même rang)."""
    rank: dict[str, int] = {}
    for i, name in enumerate(ccb_moyen_order_list(poste_name)):
        rank.setdefault(name, i)
    return rank
