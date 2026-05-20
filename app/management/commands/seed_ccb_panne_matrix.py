import json
from pathlib import Path

from django.core.management.base import BaseCommand

from app.ccb_constants import CCB_MODULE_NAME
from app.models import BerceauModule, BerceauMoyen, BerceauPoste


class Command(BaseCommand):
    help = "Crée le module CCB, les postes OP10 A/B, OP20, OP30 A/B et leurs moyens (réf. seeds/ccb_matrix.json)."

    def handle(self, *args, **options):
        seeds_dir = Path(__file__).resolve().parent.parent.parent / "seeds"
        path = seeds_dir / "ccb_matrix.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        module_name = str(raw.get("module_name") or CCB_MODULE_NAME).strip()
        postes = raw.get("postes") or []
        mod, _ = BerceauModule.objects.get_or_create(name=module_name, defaults={"is_active": True})
        if not mod.is_active:
            mod.is_active = True
            mod.save(update_fields=["is_active", "updated_at"])
        created_p = updated_p = created_m = updated_m = 0
        deactivated_m = deactivated_p = 0
        seen_pairs = set()
        allowed_poste_names: set[str] = set()
        for p_def in postes:
            pn = str(p_def.get("name") or "").strip()
            if pn:
                allowed_poste_names.add(pn)
        for p_def in postes:
            pname = str(p_def.get("name") or "").strip()
            if not pname:
                continue
            poste, pc = BerceauPoste.objects.get_or_create(
                module=mod,
                name=pname,
                defaults={
                    "a1_enabled": True,
                    "a3_enabled": True,
                    "is_active": True,
                },
            )
            if pc:
                created_p += 1
            else:
                dirty = False
                if not poste.is_active:
                    poste.is_active = True
                    dirty = True
                if not poste.a1_enabled or not poste.a3_enabled:
                    poste.a1_enabled = True
                    poste.a3_enabled = True
                    dirty = True
                if dirty:
                    poste.save(update_fields=["is_active", "a1_enabled", "a3_enabled", "updated_at"])
                    updated_p += 1
            for mname in p_def.get("moyens") or []:
                label = str(mname).strip()
                if not label:
                    continue
                key = (poste.id, label)
                if key in seen_pairs:
                    self.stderr.write(self.style.WARNING(f"Doublon ignoré: {pname} / {label}"))
                    continue
                seen_pairs.add(key)
                moyen, mc = BerceauMoyen.objects.get_or_create(
                    poste=poste,
                    name=label,
                    defaults={"is_active": True},
                )
                if mc:
                    created_m += 1
                elif not moyen.is_active:
                    moyen.is_active = True
                    moyen.save(update_fields=["is_active", "updated_at"])
                    updated_m += 1

        # Désactiver postes / moyens CCB absents du référentiel (réf. historiques conservés).
        ccb_mod = BerceauModule.objects.filter(name=module_name).first()
        if ccb_mod:
            for poste in BerceauPoste.objects.filter(module=ccb_mod):
                pname = poste.name.strip()
                if pname not in allowed_poste_names:
                    if poste.is_active:
                        poste.is_active = False
                        poste.save(update_fields=["is_active", "updated_at"])
                        deactivated_p += 1
                    continue
                allowed_m: set[str] = set()
                for p_def in postes:
                    if str(p_def.get("name") or "").strip() == pname:
                        allowed_m = {str(x).strip() for x in (p_def.get("moyens") or []) if str(x).strip()}
                        break
                for moyen in BerceauMoyen.objects.filter(poste=poste):
                    if moyen.name not in allowed_m and moyen.is_active:
                        moyen.is_active = False
                        moyen.save(update_fields=["is_active", "updated_at"])
                        deactivated_m += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_ccb_panne_matrix OK module={module_name} postes_created={created_p} "
                f"postes_updated={updated_p} moyens_created={created_m} moyens_reactivated={updated_m} "
                f"postes_deactivated={deactivated_p} moyens_deactivated={deactivated_m}"
            )
        )
