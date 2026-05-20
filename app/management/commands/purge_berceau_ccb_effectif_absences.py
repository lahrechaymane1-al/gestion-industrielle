"""Hard-delete effectif + absence rows for Berceau and CCB (shared DB tables)."""

import argparse

from django.core.management.base import BaseCommand
from django.db import transaction

from absence.models import Absence
from app.models import OperateurEffectif

EQUIPES = ("Berceau", "CCB")


class Command(BaseCommand):
    help = (
        "Permanently delete all OperateurEffectif and Absence rows where equipe is Berceau or CCB. "
        "UserAccessProfile.effectif uses SET_NULL on delete. Run dry-run first (no flags)."
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

        absence_qs = Absence.objects.filter(equipe__in=EQUIPES)
        effectif_qs = OperateurEffectif.objects.filter(equipe__in=EQUIPES)

        abs_total = absence_qs.count()
        eff_total = effectif_qs.count()

        self.stdout.write(
            f"Rows to delete: absence={abs_total} (equipe in {list(EQUIPES)}), "
            f"operateur_effectif={eff_total}"
        )

        if not apply:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run only. Re-run with --apply --i-understand to execute."
                )
            )
            return

        with transaction.atomic():
            # Absence FKs use PROTECT toward OperateurEffectif — remove absences first.
            abs_deleted, abs_detail = absence_qs.delete()
            eff_deleted, eff_detail = effectif_qs.delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted absences: {abs_deleted} ({abs_detail})"))
        self.stdout.write(self.style.SUCCESS(f"Deleted effectifs: {eff_deleted} ({eff_detail})"))
        self.stdout.write(
            self.style.WARNING(
                "PSP users lose linked effectif until you recreate rows and re-link profiles in admin."
            )
        )
