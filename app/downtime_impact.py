"""Production impact % per downtime row (Berceau Pareto).

Formula (per arrêt):
    (T_arret / diviseur) * (100 / objectif_shift)

- diviseur: A1 -> 1.3 min, A3 -> 1.8 min (diversité de l’arrêt, tag ou ligne à l’heure).
- objectif_shift: somme des ``objectif_h1``…``objectif_h8`` sur **toutes** les fiches
  production du jour (shifts A, B et N).

Diversity resolution (diviseur uniquement):
1) Explicit tag in cause: ``[diversite:A1]`` / ``[diversite:A3]``
2) Else line_h{H} on production rows (first non-null match across rows).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Literal

from django.db.models import Q

DIVISOR_A1 = 1.3
DIVISOR_A3 = 1.8


def _default_divisors() -> tuple[float, float]:
    return DIVISOR_A1, DIVISOR_A3


def get_berceau_divisors_for_date(as_of: date | None) -> tuple[float, float]:
    """Diviseurs en vigueur à la date ``as_of`` (référentiel versionné, repli sur constantes)."""
    if as_of is None:
        return _default_divisors()
    try:
        from production.models import BerceauImpactSettings

        row = BerceauImpactSettings.get_for_date(as_of)
        return float(row.divisor_a1), float(row.divisor_a3)
    except Exception:
        return _default_divisors()

Diversity = Literal["A1", "A3"]


def parse_diversite_from_cause(cause: str | None) -> Diversity | None:
    raw = (cause or "").strip()
    m = re.search(r"\[diversite:(?P<d>[^\]]+)\]", raw, flags=re.IGNORECASE)
    if not m:
        return None
    d = str(m.group("d") or "").strip().upper()
    if d in ("A1", "A3"):
        return d  # type: ignore[return-value]
    return None


def line_at_hour_from_production_row(row, hour: int) -> Diversity | None:
    if hour < 1 or hour > 8:
        return None
    val = getattr(row, f"line_h{hour}", None)
    if val in ("A1", "A3"):
        return val  # type: ignore[return-value]
    return None


def resolve_diversity_for_impact(cause: str | None, prod_rows: list | None, hour: int) -> Diversity | None:
    """User-selected diversity from cause, else production diversity at affected hour."""
    d = parse_diversite_from_cause(cause)
    if d:
        return d
    if not prod_rows:
        return None
    for r in prod_rows:
        ln = line_at_hour_from_production_row(r, hour)
        if ln:
            return ln
    return None


def hourly_objective_for_diversity(prod_rows: list | None, hour: int, diversity: Diversity | None) -> int:
    """Objective for the affected hour only (legacy / diagnostics). Impact % uses total_objectif_all_hours."""
    if not prod_rows or hour < 1 or hour > 8:
        return 0
    field_o = f"objectif_h{hour}"
    field_l = f"line_h{hour}"
    if diversity:
        for r in prod_rows:
            if getattr(r, field_l, None) == diversity:
                return int(getattr(r, field_o) or 0)
    return int(getattr(prod_rows[0], field_o) or 0)


def total_objectif_for_diversity(prod_rows: list | None, diversity: Diversity | None) -> int:
    """Sum of hourly objectives for slots running ``diversity``, across all production rows."""
    if not prod_rows or not diversity:
        return 0
    total = 0
    for r in prod_rows:
        for h in range(1, 9):
            if getattr(r, f"line_h{h}", None) == diversity:
                total += int(getattr(r, f"objectif_h{h}", 0) or 0)
    return total


def total_objectif_all_hours(prod_rows: list | None) -> int:
    """Sum of ``objectif_h1``…``objectif_h8`` across all production rows (shift / day volume)."""
    if not prod_rows:
        return 0
    total = 0
    for r in prod_rows:
        for h in range(1, 9):
            total += int(getattr(r, f"objectif_h{h}", 0) or 0)
    return total


def divisor_for_diversity(
    diversity: str | None,
    *,
    as_of: date | None = None,
    divisor_a1: float | None = None,
    divisor_a3: float | None = None,
) -> float | None:
    if divisor_a1 is None or divisor_a3 is None:
        divisor_a1, divisor_a3 = get_berceau_divisors_for_date(as_of)
    if diversity == "A1":
        return divisor_a1
    if diversity == "A3":
        return divisor_a3
    return None


def downtime_impact_percent(
    temps_arret_min: int,
    diversity: str | None,
    objectif_shift: int,
    *,
    as_of: date | None = None,
    divisor_a1: float | None = None,
    divisor_a3: float | None = None,
) -> float:
    """
    (T.arret / diviseur) * (100 / objectif_shift)
    ``objectif_shift`` = somme des objectifs horaires H1–H8 (fiches du shift).
    Returns 0 when diversity unknown, objectif <= 0, or invalid input.
    """
    div = divisor_for_diversity(
        diversity,
        as_of=as_of,
        divisor_a1=divisor_a1,
        divisor_a3=divisor_a3,
    )
    if div is None:
        return 0.0
    obj = float(objectif_shift or 0)
    if obj <= 0:
        return 0.0
    t = float(temps_arret_min or 0)
    if t <= 0:
        return 0.0
    return (t / div) * (100.0 / obj)


def berceau_alerte_impact_pct(alerte, prod_rows: list | None) -> float:
    """
    Impact % (Berceau). ``prod_rows`` = toutes les fiches production du jour (A+B+N).
    """
    hour = int(getattr(alerte, "heure_production", 0) or 0)
    cause = getattr(alerte, "cause", None)
    div = resolve_diversity_for_impact(cause, prod_rows, hour)
    if not div:
        return 0.0
    obj = total_objectif_all_hours(prod_rows)
    as_of = getattr(alerte, "date", None)
    return downtime_impact_percent(
        int(getattr(alerte, "temps_arret_min", 0) or 0),
        div,
        obj,
        as_of=as_of,
    )


def production_rows_map_for_pairs(pairs: set[tuple[date, str]]) -> dict[tuple[date, str], list]:
    """Load ProductionBerceau rows grouped by (date, shift)."""
    from production.models import ProductionBerceau

    if not pairs:
        return {}
    q = Q()
    for d, s in pairs:
        q |= Q(date=d, shift=s)
    rows = list(ProductionBerceau.objects.filter(q).order_by("date", "shift", "id"))
    out: dict[tuple[date, str], list] = {}
    for r in rows:
        key = (r.date, r.shift)
        out.setdefault(key, []).append(r)
    return out


def production_rows_map_for_berceau_alertes(alertes: list) -> dict[tuple[date, str], list]:
    pairs = {(a.date, a.shift) for a in alertes if (getattr(a, "equipe", None) or "").strip() == "Berceau"}
    return production_rows_map_for_pairs(pairs)


def production_rows_by_date_for_alertes(alertes: list) -> dict[date, list]:
    """Toutes les fiches production du jour (shifts A+B+N) pour le dénominateur impact %."""
    from production.models import ProductionBerceau

    dates = {a.date for a in alertes if (getattr(a, "equipe", None) or "").strip() == "Berceau"}
    if not dates:
        return {}
    q = Q()
    for d in dates:
        q |= Q(date=d)
    rows = list(ProductionBerceau.objects.filter(q).order_by("date", "shift", "id"))
    out: dict[date, list] = {}
    for r in rows:
        out.setdefault(r.date, []).append(r)
    return out
