import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models import BerceauModule, BerceauMoyen, BerceauPoste


class Command(BaseCommand):
    help = "Seed initial Berceau Module/Poste/Moyen matrix."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="",
            help="Optional JSON file path. Defaults to app/seeds/berceau_matrix.json",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Deactivate modules/postes/moyens not present in source matrix.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = options["file"] or str(Path("app") / "seeds" / "berceau_matrix.json")
        p = Path(file_path)
        if not p.exists():
            raise CommandError(f"Matrix file not found: {p}")
        data = json.loads(p.read_text(encoding="utf-8"))
        modules = data.get("modules") or []
        if not modules:
            raise CommandError("No modules found in matrix JSON.")

        created_modules = created_postes = created_moyens = dedup_skipped = 0
        active_modules: set[str] = set()
        active_postes: set[tuple[str, str]] = set()
        active_moyens: set[tuple[str, str, str]] = set()
        for module_data in modules:
            module_name = (module_data.get("name") or "").strip()
            if not module_name:
                continue
            active_modules.add(module_name)
            module, m_created = BerceauModule.objects.get_or_create(name=module_name)
            if m_created:
                created_modules += 1
            if not module.is_active:
                module.is_active = True
                module.save(update_fields=["is_active", "updated_at"])
            for poste_data in module_data.get("postes") or []:
                poste_name = (poste_data.get("name") or "").strip()
                if not poste_name:
                    continue
                active_postes.add((module_name, poste_name))
                poste, p_created = BerceauPoste.objects.get_or_create(
                    module=module,
                    name=poste_name,
                    defaults={
                        "a1_enabled": bool(poste_data.get("a1_enabled", True)),
                        "a3_enabled": bool(poste_data.get("a3_enabled", True)),
                    },
                )
                if not p_created:
                    poste.a1_enabled = bool(poste_data.get("a1_enabled", True))
                    poste.a3_enabled = bool(poste_data.get("a3_enabled", True))
                    poste.is_active = True
                    poste.save(update_fields=["a1_enabled", "a3_enabled", "is_active", "updated_at"])
                if p_created:
                    created_postes += 1
                seen_names = set()
                for moyen_name in poste_data.get("moyens") or []:
                    cleaned = (moyen_name or "").strip()
                    if not cleaned:
                        continue
                    # Rule: duplicates from source matrix are deduplicated per poste.
                    if cleaned.lower() in seen_names:
                        dedup_skipped += 1
                        continue
                    seen_names.add(cleaned.lower())
                    active_moyens.add((module_name, poste_name, cleaned))
                    _, mo_created = BerceauMoyen.objects.get_or_create(
                        poste=poste,
                        name=cleaned,
                    )
                    if mo_created:
                        created_moyens += 1

        deactivated_modules = deactivated_postes = deactivated_moyens = 0
        if options["sync"]:
            for module in BerceauModule.objects.all():
                should_be_active = module.name in active_modules
                if module.is_active != should_be_active:
                    module.is_active = should_be_active
                    module.save(update_fields=["is_active", "updated_at"])
                    if not should_be_active:
                        deactivated_modules += 1

            for poste in BerceauPoste.objects.select_related("module"):
                key = (poste.module.name, poste.name)
                should_be_active = key in active_postes
                if poste.is_active != should_be_active:
                    poste.is_active = should_be_active
                    poste.save(update_fields=["is_active", "updated_at"])
                    if not should_be_active:
                        deactivated_postes += 1

            for moyen in BerceauMoyen.objects.select_related("poste__module"):
                key = (moyen.poste.module.name, moyen.poste.name, moyen.name)
                should_be_active = key in active_moyens
                if moyen.is_active != should_be_active:
                    moyen.is_active = should_be_active
                    moyen.save(update_fields=["is_active", "updated_at"])
                    if not should_be_active:
                        deactivated_moyens += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Matrix seeded. modules+={created_modules}, postes+={created_postes}, "
                f"moyens+={created_moyens}, moyens_duplicated_skipped={dedup_skipped}, "
                f"deactivated_modules={deactivated_modules}, deactivated_postes={deactivated_postes}, "
                f"deactivated_moyens={deactivated_moyens}"
            )
        )
