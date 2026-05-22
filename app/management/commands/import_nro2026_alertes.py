"""Import arrêts from NRO2026.xlsx into AlertePanne (May 2026, day by day)."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from openpyxl import load_workbook

from app.nro_import_utils import (
    IMPORT_TAG,
    build_cause,
    category_from_excel_type,
    comment_from_imported_cause,
    distinct_days_in_rows,
    diversite_for_store_day,
    filter_rows_by_day,
    import_tag_for_day,
    normalize_moyen_name,
    normalize_panne_name,
    parse_import_date,
    resolve_moyen,
    resolve_poste,
    split_row_into_hour_fiches,
)
from arret.models import AlertePanne, BerceauModule, BerceauMoyen, BerceauPoste, PanneType


DEFAULT_XLSX = Path(r"C:\Users\ASUS\Desktop\NRO2026.xlsx")


def _parse_excel_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if " " in text:
        text = text.split(" ", 1)[0]
    return date.fromisoformat(text)


def _cell_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value).strip()


class Command(BaseCommand):
    help = (
        "Import NRO2026.xlsx alertes jour par jour (mai 2026). "
        "Utilisez --list-days puis --date 2026-05-01. Split >60 min sur H1-H8. "
        "Une ligne Excel = une fiche arrêt (durée exacte). Tag [import:NRO2026:YYYY-MM-DD]."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            default=str(DEFAULT_XLSX),
            help="Path to NRO2026.xlsx",
        )
        parser.add_argument(
            "--shift",
            type=str,
            default="A",
            choices=["A", "B", "N"],
            help="Shift for imported rows (Excel has no shift). Default: A",
        )
        parser.add_argument(
            "--date",
            type=str,
            help="Jour lu dans Excel (AAAA-MM-JJ, ex. 2026-05-16).",
        )
        parser.add_argument(
            "--store-date",
            type=str,
            help=(
                "Date enregistree en base (ex. 2026-05-17). "
                "Par defaut = --date. Utile si Excel a une date et l'app une autre."
            ),
        )
        parser.add_argument(
            "--list-days",
            action="store_true",
            help="Liste les jours presents dans le fichier Excel.",
        )
        parser.add_argument(
            "--remove-date",
            type=str,
            help="Supprime les arrêts importes pour ce jour (AAAA-MM-JJ).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse et rapport sans ecriture en base.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Supprime les arrêts de ce jour avant import.",
        )
        parser.add_argument(
            "--fix-diversite",
            action="store_true",
            help=(
                "Met a jour [diversite:A1/A3] sur les arrêts deja importes (calendrier mai 2026). "
                "Avec --date : ce jour seulement ; sans --date : tout mai 2026 importe."
            ),
        )
        parser.add_argument(
            "--move-date",
            nargs=2,
            metavar=("FROM", "TO"),
            help=(
                "Deplace les arrêts importes d'une date vers une autre "
                "(ex. 2026-05-17 2026-05-16) et met a jour le tag + diversite."
            ),
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        shift = options["shift"]
        dry_run: bool = bool(options["dry_run"])
        replace: bool = bool(options["replace"])
        list_days: bool = bool(options["list_days"])
        remove_date_raw: str | None = options.get("remove_date")
        date_raw: str | None = options.get("date")
        store_date_raw: str | None = options.get("store_date")
        fix_diversite: bool = bool(options.get("fix_diversite"))
        move_date: list[str] | None = options.get("move_date")

        if move_date:
            try:
                from_day = parse_import_date(move_date[0])
                to_day = parse_import_date(move_date[1])
            except ValueError as exc:
                self.stderr.write(self.style.ERROR(str(exc)))
                return
            self._move_imported_day(from_day, to_day, dry_run=dry_run)
            return

        if fix_diversite:
            self._fix_diversite_on_imported(
                parse_import_date(date_raw) if date_raw else None,
                dry_run=dry_run,
            )
            return

        if not path.is_file():
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        all_rows = self._load_rows(path)

        if list_days:
            self._print_day_catalog(all_rows)
            return

        if remove_date_raw:
            try:
                remove_day = parse_import_date(remove_date_raw)
            except ValueError as exc:
                self.stderr.write(self.style.ERROR(str(exc)))
                return
            self._remove_day(remove_day, dry_run=dry_run)
            return

        if not date_raw:
            self.stderr.write(
                self.style.ERROR(
                    "Precisez --date 2026-05-01 (ou --list-days / --remove-date)."
                )
            )
            return

        try:
            import_day = parse_import_date(date_raw)
        except ValueError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        if store_date_raw:
            try:
                store_day = parse_import_date(store_date_raw)
            except ValueError as exc:
                self.stderr.write(self.style.ERROR(str(exc)))
                return
        else:
            store_day = import_day

        rows = filter_rows_by_day(all_rows, import_day)
        if not rows:
            known = ", ".join(d.isoformat() for d in distinct_days_in_rows(all_rows))
            self.stderr.write(
                self.style.ERROR(
                    f"Aucune ligne Excel pour {import_day.isoformat()}. Jours dans le fichier: {known}"
                )
            )
            return

        day_tag = import_tag_for_day(store_day)

        if replace and not dry_run:
            deleted, _ = self._delete_imported_day(store_day)
            self.stdout.write(
                self.style.WARNING(f"{store_day.isoformat()} efface avant import: {deleted} fiche(s)")
            )

        modules = {m.name: m for m in BerceauModule.objects.filter(is_active=True)}
        postes_by_module: dict[tuple[int, str], BerceauPoste] = {}
        postes_by_name: dict[str, list[BerceauPoste]] = {}
        for p in BerceauPoste.objects.filter(is_active=True).select_related("module"):
            postes_by_module[(p.module_id, p.name)] = p
            postes_by_name.setdefault(p.name, []).append(p)
        moyens_by_poste: dict[tuple[int, str], BerceauMoyen] = {}
        moyens_by_module: dict[tuple[int, str], BerceauMoyen] = {}
        for m in BerceauMoyen.objects.filter(is_active=True).select_related("poste", "poste__module"):
            moyens_by_poste[(m.poste_id, m.name)] = m
            key = (m.poste.module_id, m.name)
            if key not in moyens_by_module:
                moyens_by_module[key] = m
        panne_by_name = {p.name: p for p in PanneType.objects.all()}

        created = 0
        excel_rows_imported = 0
        skipped = 0
        errors: list[str] = []
        minutes_in = 0
        minutes_out = 0

        def _run():
            nonlocal created, excel_rows_imported, skipped, minutes_in, minutes_out
            for row in rows:
                minutes_in += row["minutes"]
                try:
                    module = modules.get(row["module"])
                    if not module:
                        raise ValueError(f"Module inconnu: {row['module']}")
                    poste = resolve_poste(
                        module, row["poste"], postes_by_module, postes_by_name
                    )
                    if not poste:
                        raise ValueError(f"Poste inconnu: {row['module']} / {row['poste']}")
                    module_record = poste.module

                    moyen = resolve_moyen(
                        poste,
                        module_record,
                        row["moyen"],
                        moyens_by_poste,
                        moyens_by_module,
                    )

                    panne_name = row["panne_name"]
                    panne = panne_by_name.get(panne_name)
                    if not panne:
                        panne, _ = PanneType.objects.get_or_create(
                            name=panne_name,
                            defaults={"description": "", "is_active": True},
                        )
                        panne_by_name[panne_name] = panne

                    chunks = split_row_into_hour_fiches(row["minutes"])
                    if not chunks:
                        skipped += 1
                        continue

                    diversite = diversite_for_store_day(store_day)
                    cause = build_cause(diversite, row["probleme_raw"], day=store_day)
                    for heure, mins in chunks:
                        minutes_out += mins
                        if dry_run:
                            created += 1
                            continue
                        AlertePanne.objects.create(
                            module=module_record,
                            poste=poste,
                            moyen=moyen,
                            panne_type=panne,
                            cause=cause,
                            solution=row["probleme_raw"],
                            category=row["category"],
                            date=store_day,
                            shift=shift,
                            heure_production=heure,
                            temps_arret_min=mins,
                            equipe="Berceau",
                        )
                        created += 1
                    excel_rows_imported += 1
                except Exception as exc:
                    skipped += 1
                    errors.append(f"Ligne Excel ~{row['excel_row']}: {exc}")

        if dry_run:
            _run()
        else:
            with transaction.atomic():
                _run()

        self.stdout.write(
            self.style.SUCCESS(f"Import NRO2026 {store_day.isoformat()} termine.")
        )
        if store_day != import_day:
            self.stdout.write(
                f"  Lignes lues dans Excel: {import_day.isoformat()} -> enregistrees: {store_day.isoformat()}"
            )
        self.stdout.write(f"  Tag: {day_tag}")
        self.stdout.write(f"  Fichier: {path}")
        self.stdout.write(f"  Shift: {shift}")
        self.stdout.write(f"  Diversite (calendrier): {diversite_for_store_day(store_day)}")
        self.stdout.write(f"  Lignes Excel: {len(rows)}")
        self.stdout.write(
            f"  Fiches creees: {created} ({excel_rows_imported} lignes Excel, "
            f"decoupe H1-H8 si >60 min)"
        )
        self.stdout.write(f"  Lignes ignorees / erreur: {skipped}")
        self.stdout.write(f"  Minutes source: {minutes_in} -> minutes en base: {minutes_out}")
        if minutes_in != minutes_out:
            self.stdout.write(
                self.style.WARNING(
                    f"  Ecart minutes: {minutes_out - minutes_in} (overflow H8 ou 0 min)"
                )
            )
        if dry_run:
            self.stdout.write(self.style.WARNING("  Mode dry-run — aucune ecriture en base."))
        if errors:
            self.stdout.write(self.style.ERROR(f"  Erreurs ({len(errors)}):"))
            for err in errors[:25]:
                self.stdout.write(f"    - {err}")

    def _imported_day_queryset(self, day: date):
        tag = import_tag_for_day(day)
        return AlertePanne.objects.filter(
            equipe="Berceau",
            date=day,
        ).filter(
            Q(cause__startswith=tag)
            | Q(cause__startswith=f"{IMPORT_TAG} ")
            | Q(cause__startswith=f"{IMPORT_TAG}:w")
        )

    def _delete_imported_day(self, day: date):
        return self._imported_day_queryset(day).delete()

    def _imported_may_2026_queryset(self):
        return AlertePanne.objects.filter(
            equipe="Berceau",
            date__gte=date(2026, 5, 1),
            date__lte=date(2026, 5, 31),
        ).filter(
            Q(cause__startswith=IMPORT_TAG)
            | Q(cause__icontains=f"{IMPORT_TAG}:")
        )

    def _move_imported_day(self, from_day: date, to_day: date, *, dry_run: bool) -> None:
        qs = self._imported_day_queryset(from_day)
        count = qs.count()
        if not count:
            self.stdout.write(
                self.style.WARNING(
                    f"Aucun arrêt importe sur {from_day.isoformat()} a deplacer."
                )
            )
            return
        existing_to = self._imported_day_queryset(to_day).count()
        if existing_to and not dry_run:
            deleted, _ = self._delete_imported_day(to_day)
            self.stdout.write(
                self.style.WARNING(
                    f"{to_day.isoformat()}: {deleted} fiche(s) importee(s) effacee(s) avant deplacement."
                )
            )
        moved = 0
        for item in qs.iterator():
            div = diversite_for_store_day(to_day)
            comment = (item.solution or "").strip() or comment_from_imported_cause(item.cause)
            new_cause = build_cause(div, comment, day=to_day)
            if not dry_run:
                item.date = to_day
                item.cause = new_cause
                item.save(update_fields=["date", "cause"])
            moved += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Deplace {moved} fiche(s): {from_day.isoformat()} -> {to_day.isoformat()} "
                f"(diversite {diversite_for_store_day(to_day)})"
                + (" (dry-run)" if dry_run else "")
            )
        )

    def _fix_diversite_on_imported(self, day: date | None, *, dry_run: bool) -> None:
        qs = self._imported_may_2026_queryset()
        if day is not None:
            qs = qs.filter(date=day)
        updated = 0
        for item in qs.iterator():
            div = diversite_for_store_day(item.date)
            comment = (item.solution or "").strip() or comment_from_imported_cause(item.cause)
            new_cause = build_cause(div, comment, day=item.date)
            if new_cause == (item.cause or "").strip():
                continue
            if not dry_run:
                item.cause = new_cause
                item.save(update_fields=["cause"])
            updated += 1
        scope = day.isoformat() if day else "mai 2026 (import NRO2026)"
        self.stdout.write(
            self.style.SUCCESS(
                f"Diversite corrigee: {updated} fiche(s) pour {scope}"
                + (" (dry-run)" if dry_run else "")
            )
        )

    def _print_day_catalog(self, all_rows: list[dict]) -> None:
        self.stdout.write(self.style.SUCCESS("Jours NRO2026 dans le fichier Excel:"))
        for day in distinct_days_in_rows(all_rows):
            chunk = filter_rows_by_day(all_rows, day)
            minutes = sum(r["minutes"] for r in chunk)
            in_db = self._imported_day_queryset(day).count()
            self.stdout.write(
                f"  --date {day.isoformat()}  {len(chunk)} lignes, {minutes} min  En base: {in_db}"
            )
        self.stdout.write("")
        self.stdout.write(
            "Importer:  python manage.py import_nro2026_alertes --date 2026-05-01 [--dry-run] [--replace]"
        )
        self.stdout.write(
            "Supprimer: python manage.py import_nro2026_alertes --remove-date 2026-05-01"
        )

    def _remove_day(self, day: date, *, dry_run: bool) -> None:
        qs = self._imported_day_queryset(day)
        count = qs.count()
        if dry_run:
            self.stdout.write(
                f"Dry-run: supprimerait {count} fiche(s) pour {day.isoformat()}."
            )
            return
        deleted, _ = qs.delete()
        self.stdout.write(
            self.style.SUCCESS(f"{day.isoformat()} supprime: {deleted} fiche(s).")
        )

    def _load_rows(self, path: Path) -> list[dict]:
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        all_rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not all_rows:
            return []

        header = [_cell_str(c) for c in all_rows[0]]
        col = {h: i for i, h in enumerate(header)}
        required = ["Date", "Diversité", "Module", "Poste", "Problème", "Type", "Temps (min)"]
        missing = [h for h in required if h not in col]
        if missing:
            raise ValueError(f"Colonnes manquantes: {missing}")

        out: list[dict] = []
        for excel_row, raw in enumerate(all_rows[1:], start=2):
            if not any(raw):
                continue

            def get(name: str) -> str:
                idx = col[name]
                return _cell_str(raw[idx]) if idx < len(raw) else ""

            minutes_raw = get("Temps (min)")
            try:
                minutes = int(float(minutes_raw)) if minutes_raw else 0
            except ValueError:
                minutes = 0
            if minutes < 0:
                minutes = 0

            moyen_raw = get("Moyen")
            moyen_norm = normalize_moyen_name(moyen_raw) if moyen_raw else ""
            probleme_raw = get("Problème")
            panne_name = normalize_panne_name(probleme_raw)

            out.append(
                {
                    "excel_row": excel_row,
                    "date": _parse_excel_date(raw[col["Date"]]),
                    "diversite": get("Diversité").upper() or "A1",
                    "module": get("Module"),
                    "poste": get("Poste"),
                    "moyen": moyen_norm,
                    "probleme_raw": probleme_raw,
                    "panne_name": panne_name,
                    "category": category_from_excel_type(get("Type")),
                    "minutes": minutes,
                }
            )
        return out
