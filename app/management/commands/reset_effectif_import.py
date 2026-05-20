import argparse

from django.core.management.base import BaseCommand
from django.db import transaction

from absence.models import Absence
from app.models import OperateurEffectif


class Command(BaseCommand):
    help = "Reset imported effectif data (safe by default)."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--scope",
            choices=["auto-only", "all-effectifs"],
            default="auto-only",
            help="auto-only deletes only rows with cin/identifiant starting with 'AUTO-'. all-effectifs deletes all rows.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag it's a dry-run.",
        )
        parser.add_argument(
            "--i-understand",
            action="store_true",
            help="Required for --scope=all-effectifs.",
        )

    def handle(self, *args, **options):
        scope: str = str(options["scope"])
        apply: bool = bool(options["apply"])
        understand: bool = bool(options["i_understand"])

        if scope == "all-effectifs" and not understand:
            self.stderr.write(
                self.style.ERROR(
                    "Refusing to run --scope=all-effectifs without --i-understand."
                )
            )
            return

        if scope == "auto-only":
            effectif_qs = OperateurEffectif.objects.filter(
                is_deleted=False,
            ).filter(
                cin__startswith="AUTO-"
            ) | OperateurEffectif.objects.filter(
                is_deleted=False,
                identifiant__startswith="AUTO-",
            )
        else:
            effectif_qs = OperateurEffectif.objects.filter(is_deleted=False)

        effectif_ids = list(effectif_qs.values_list("id", flat=True))

        # Absence has PROTECT on effectif FKs -> must delete absences first.
        abs_qs = Absence.objects.filter(is_deleted=False).filter(
            effectif_id__in=effectif_ids
        ) | Absence.objects.filter(is_deleted=False).filter(
            remplacant_effectif_id__in=effectif_ids
        )

        abs_ids = list(abs_qs.values_list("id", flat=True))

        self.stdout.write(
            f"Planned reset scope={scope} apply={apply}: effectifs={len(effectif_ids)} absences={len(abs_ids)}"
        )

        if not apply:
            self.stdout.write(self.style.WARNING("Dry-run only. Re-run with --apply to execute."))
            return

        with transaction.atomic():
            if abs_ids:
                Absence.objects.filter(id__in=abs_ids).delete()
            if effectif_ids:
                OperateurEffectif.objects.filter(id__in=effectif_ids).delete()

        self.stdout.write(self.style.SUCCESS("Reset complete."))

