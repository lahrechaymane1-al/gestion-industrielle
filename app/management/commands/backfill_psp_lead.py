import argparse

from django.core.management.base import BaseCommand

from app.models import OperateurEffectif, UserAccessProfile


class Command(BaseCommand):
    help = "Backfill OperateurEffectif.psp_lead for operators using code_equipe -> PSP mapping."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without updating rows.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Optional limit of operators to process (0 = no limit).",
        )

    def handle(self, *args, **options):
        dry_run: bool = bool(options["dry_run"])
        limit: int = int(options["limit"] or 0)

        psp_ids = set(
            UserAccessProfile.objects.filter(
                role=UserAccessProfile.Role.PSP,
                effectif_id__isnull=False,
            ).values_list("effectif_id", flat=True)
        )

        # Build lookup: (equipe, shift, code_equipe) -> psp_effectif_id
        psp_by_key: dict[tuple[str, str, str], int] = {}
        psp_qs = (
            OperateurEffectif.objects.filter(is_deleted=False, pk__in=psp_ids)
            .only("id", "equipe", "shift", "code_equipe")
        )
        for psp in psp_qs:
            code = (psp.code_equipe or "").strip()
            if not code:
                continue
            key = (psp.equipe, psp.shift, code)
            # If multiple PSP share the same key, keep the first to avoid thrashing.
            psp_by_key.setdefault(key, int(psp.id))

        ops_qs = (
            OperateurEffectif.objects.filter(is_deleted=False, fonction="OPERATEUR", psp_lead_id__isnull=True)
            .exclude(code_equipe="")
            .only("id", "equipe", "shift", "code_equipe")
            .order_by("id")
        )
        if limit > 0:
            ops_qs = ops_qs[:limit]

        checked = 0
        updated = 0
        would_update = 0
        missing = 0
        for op in ops_qs:
            checked += 1
            code = (op.code_equipe or "").strip()
            key = (op.equipe, op.shift, code)
            lead_id = psp_by_key.get(key)
            if not lead_id:
                missing += 1
                continue
            if dry_run:
                self.stdout.write(f"Would set operator {op.id} psp_lead_id={lead_id} (key={key})")
                would_update += 1
            else:
                OperateurEffectif.objects.filter(pk=op.id).update(psp_lead_id=lead_id)
                updated += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backfill complete (dry-run). checked={checked} would_update={would_update} missing_mapping={missing}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backfill complete. checked={checked} updated={updated} missing_mapping={missing}"
                )
            )

