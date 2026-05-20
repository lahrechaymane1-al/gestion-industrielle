"""Delete Berceau operational data (production, arrêts, stock, mode dégradé). Keeps effectif."""

from __future__ import annotations

import argparse

from django.core.management.base import BaseCommand
from django.db import transaction

from arret.models import AlertePanne, ArretBerceau
from mode_degrade.models import ModeDegrade
from production.models import ProductionBerceau
from stock.models import StockJournal

BERCEAU = "Berceau"


class Command(BaseCommand):
    help = (
        "Permanently delete Berceau production, arrêts (fiches + alertes panne), stock journal, "
        "and mode dégradé. OperateurEffectif (effectif) and absences are not touched. "
        "Run without flags for a dry-run count."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Perform deletes (without this, only prints counts).",
        )
        parser.add_argument(
            "--i-understand",
            action="store_true",
            help="Required with --apply (confirms destructive purge).",
        )

    def handle(self, *args, **options):
        apply: bool = bool(options["apply"])
        confirmed: bool = bool(options["i_understand"])

        if apply and not confirmed:
            self.stderr.write(
                self.style.ERROR(
                    "Refusing destructive purge: pass both --apply and --i-understand."
                )
            )
            return

        targets = [
            ("Alerte panne (Berceau)", AlertePanne.objects.filter(equipe=BERCEAU)),
            ("Arrêts Berceau", ArretBerceau.objects.all()),
            ("Production Berceau", ProductionBerceau.objects.all()),
            ("Stock journal (Berceau)", StockJournal.objects.filter(equipe=BERCEAU)),
            ("Mode dégradé (Berceau)", ModeDegrade.objects.filter(equipe=BERCEAU)),
        ]

        self.stdout.write(self.style.WARNING(f"Purge scope: {BERCEAU} operational data only."))
        self.stdout.write(self.style.SUCCESS("Kept: OperateurEffectif (effectif), absences, matrix arrêts (modules/postes/moyens/types)."))
        self.stdout.write("")

        total = 0
        for label, qs in targets:
            count = qs.count()
            total += count
            self.stdout.write(f"  {label}: {count}")

        self.stdout.write("")
        self.stdout.write(f"Total rows to delete: {total}")

        if not apply:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run only. Re-run with --apply --i-understand to execute."
                )
            )
            return

        with transaction.atomic():
            for label, qs in targets:
                deleted, detail = qs.delete()
                self.stdout.write(self.style.SUCCESS(f"Deleted {label}: {deleted} ({detail})"))

        self.stdout.write(self.style.SUCCESS("Berceau operational data cleared. Effectif unchanged."))
