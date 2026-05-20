"""Import Berceau production volumes from production-extract-2026-05.json (May 2026 grid)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from production.models import ProductionBerceau

DEFAULT_OBJECTIFS: dict[str, dict[int, int]] = {
    "A1": {1: 40, 2: 45, 3: 45, 4: 45, 5: 25, 6: 45, 7: 45, 8: 45},
    "A3": {1: 30, 2: 33, 3: 33, 4: 33, 5: 20, 6: 33, 7: 33, 8: 33},
}


def _distribute_volume(line: str, total: int, hours: int = 8) -> list[int]:
    """Split volume across `hours` slots proportional to default objectifs."""
    weights = [DEFAULT_OBJECTIFS[line][h] for h in range(1, hours + 1)]
    weight_sum = sum(weights) or 1
    out: list[int] = []
    assigned = 0
    for i, w in enumerate(weights):
        if i == len(weights) - 1:
            out.append(max(0, total - assigned))
        else:
            part = int(round(total * w / weight_sum))
            out.append(part)
            assigned += part
    return out


def _build_shift_fields(vol_a1: int, vol_a3: int) -> dict:
    """One fiche per (date, shift): répartit A1/A3 sur H1–H8 selon le tableau."""
    lines: list[str] = []
    productions: list[int] = []
    objectifs: list[int] = []

    if vol_a1 > 0 and vol_a3 == 0:
        lines = ["A1"] * 8
        productions = _distribute_volume("A1", vol_a1)
        objectifs = [DEFAULT_OBJECTIFS["A1"][h] for h in range(1, 9)]
    elif vol_a3 > 0 and vol_a1 == 0:
        lines = ["A3"] * 8
        productions = _distribute_volume("A3", vol_a3)
        objectifs = [DEFAULT_OBJECTIFS["A3"][h] for h in range(1, 9)]
    elif vol_a1 > 0 and vol_a3 > 0:
        total = vol_a1 + vol_a3
        h_a1 = max(1, min(7, round(8 * vol_a1 / total)))
        h_a3 = 8 - h_a1
        prod_a1 = _distribute_volume("A1", vol_a1, h_a1)
        prod_a3 = _distribute_volume("A3", vol_a3, h_a3)
        for h in range(1, 9):
            if h <= h_a1:
                lines.append("A1")
                productions.append(prod_a1[h - 1])
                objectifs.append(DEFAULT_OBJECTIFS["A1"][h])
            else:
                lines.append("A3")
                productions.append(prod_a3[h - h_a1 - 1])
                objectifs.append(DEFAULT_OBJECTIFS["A3"][h])
    else:
        lines = ["A1"] * 8
        productions = [0] * 8
        objectifs = [DEFAULT_OBJECTIFS["A1"][h] for h in range(1, 9)]

    majority = "A3" if lines.count("A3") > lines.count("A1") else "A1"
    fields: dict = {
        "line": majority,
        "objectif": sum(objectifs),
        "rebut": 0,
        "retouche": 0,
        "temps_arrets": 0,
        "validated_hours_mask": (1 << 8) - 1,
    }
    for h in range(1, 9):
        fields[f"objectif_h{h}"] = objectifs[h - 1]
        fields[f"production_h{h}"] = productions[h - 1]
        fields[f"rebut_h{h}"] = 0
        fields[f"retouche_h{h}"] = 0
        fields[f"temps_arrets_h{h}"] = 0
        fields[f"line_h{h}"] = lines[h - 1]
    return fields


class Command(BaseCommand):
    help = "Import May 2026 Berceau production from production-extract-2026-05.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            type=str,
            default="production-extract-2026-05.json",
            help="Path to JSON file (relative to project root or absolute).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print plan without writing.",
        )

    def handle(self, *args, **options):
        raw_path = Path(options["json"])
        if not raw_path.is_absolute():
            raw_path = Path(__file__).resolve().parents[3] / raw_path
        if not raw_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {raw_path}"))
            return

        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        entries = payload.get("entries") or []
        if not entries:
            self.stderr.write(self.style.ERROR("No entries in JSON."))
            return

        # Regrouper A1 + A3 par (date, shift) — contrainte unique en base.
        by_shift: dict[tuple[str, str], dict[str, int]] = {}
        for row in entries:
            day_s = str(row["date"])
            shift = str(row["shift"]).strip().upper()
            line = str(row["line"]).strip().upper()
            if line not in ("A1", "A3") or shift not in ("A", "B", "N"):
                self.stderr.write(self.style.WARNING(f"Skip invalid row: {row}"))
                continue
            key = (day_s, shift)
            bucket = by_shift.setdefault(key, {"A1": 0, "A3": 0})
            bucket[line] = int(row["volume"])

        dry = bool(options["dry_run"])
        created = updated = 0

        with transaction.atomic():
            for (day_s, shift), vols in sorted(by_shift.items()):
                day = date.fromisoformat(day_s)
                defaults = _build_shift_fields(vols["A1"], vols["A3"])
                if dry:
                    self.stdout.write(
                        f"  {day} shift {shift}: A1={vols['A1']} A3={vols['A3']} "
                        f"→ volume {sum(defaults[f'production_h{h}'] for h in range(1, 9))}"
                    )
                    continue

                obj, was_created = ProductionBerceau.objects.update_or_create(
                    date=day,
                    shift=shift,
                    defaults=defaults,
                )
                obj.save()
                if was_created:
                    created += 1
                else:
                    updated += 1

            if dry:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[dry-run] ' if dry else ''}Processed {len(by_shift)} fiches (from {len(entries)} cellules) "
                f"(created={created}, updated={updated})."
            )
        )
