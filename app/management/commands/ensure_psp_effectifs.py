"""Crée les fiches PSP Berceau/CCB manquantes et relie les comptes PSP (dont psp_ccb_*)."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from app.effectif_team import CANONICAL_CODE_EQUIPE_BY_SCOPE
from app.management.commands.seed_demo_data import EFFECTIF_PSP_ROWS
from app.models import OperateurEffectif, UserAccessProfile

LEGACY_USER_LINKS = {
    "psp_berceau_a": ("Berceau", "A"),
    "psp_berceau_b": ("Berceau", "B"),
    "psp_berceau_n": ("Berceau", "N"),
    "psp_ccb_a": ("CCB", "A"),
    "psp_ccb_b": ("CCB", "B"),
    "psp_ccb_n": ("CCB", "N"),
    "br_psp_a": ("Berceau", "A"),
    "br_psp_b": ("Berceau", "B"),
    "br_psp_n": ("Berceau", "N"),
    "ccb_psp_a": ("CCB", "A"),
    "ccb_psp_b": ("CCB", "B"),
    "ccb_psp_n": ("CCB", "N"),
}


class Command(BaseCommand):
    help = "Assure les fiches effectif PSP (6) et lie les comptes PSP connus."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        psp_by_scope: dict[tuple[str, str], OperateurEffectif] = {}
        base_common = {
            "type_contrat": "CDI",
            "niveau_etude": "Bac professionnel",
            "pointure_chaussure": 42,
            "taille_pantalon": "M",
            "taille_veste": "L",
            "ville_origine": "Kenitra",
            "ville_actuelle": "Kenitra",
        }

        for row in EFFECTIF_PSP_ROWS:
            (
                cin,
                equipe,
                shift,
                nom_complet,
                identifiant,
                num_tel,
                date_naissance,
                date_entree,
                casier,
                parada,
            ) = row
            squad_code = CANONICAL_CODE_EQUIPE_BY_SCOPE[(equipe, shift)]
            eff, created = OperateurEffectif.objects.update_or_create(
                cin=cin,
                defaults={
                    **base_common,
                    "equipe": equipe,
                    "shift": shift,
                    "nom_complet": nom_complet,
                    "identifiant": identifiant,
                    "num_tel": num_tel,
                    "date_naissance": date_naissance,
                    "date_entree": date_entree,
                    "sexe": "Homme",
                    "fonction": "PSP",
                    "psp_lead": None,
                    "code_equipe": squad_code,
                    "is_deleted": False,
                    "numero_casier": casier,
                    "parada_transport": parada,
                    "specialite": "Pilotage equipe et coordination shift",
                },
            )
            psp_by_scope[(equipe, shift)] = eff
            self.stdout.write(
                f"{'Created' if created else 'Updated'} PSP effectif {equipe} shift {shift} ({identifiant})"
            )

        linked = 0
        for username, scope in LEGACY_USER_LINKS.items():
            user = User.objects.filter(username=username).first()
            if not user:
                continue
            eff = psp_by_scope[scope]
            UserAccessProfile.objects.update_or_create(
                user=user,
                defaults={"role": UserAccessProfile.Role.PSP, "effectif": eff},
            )
            linked += 1
            self.stdout.write(f"Linked user {username} -> PSP {scope[0]} shift {scope[1]}")

        team_linked = self._sync_operator_psp_leads()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {len(psp_by_scope)} PSP fiches, {linked} comptes lies, {team_linked} operateurs rattaches."
            )
        )

    def _primary_psp_for_scope(self, equipe: str, shift: str) -> OperateurEffectif | None:
        """Un PSP par (equipe, shift) ; en cas de doublon, privilegie la fiche liee a un compte login."""
        psps = list(
            OperateurEffectif.objects.filter(
                equipe=equipe, shift=shift, fonction="PSP", is_deleted=False
            ).order_by("id")
        )
        if not psps:
            return None
        if len(psps) == 1:
            return psps[0]
        linked_ids = set(
            UserAccessProfile.objects.filter(
                role=UserAccessProfile.Role.PSP,
                effectif_id__in=[p.pk for p in psps],
            ).values_list("effectif_id", flat=True)
        )
        for psp in psps:
            if psp.pk in linked_ids:
                return psp
        return psps[0]

    def _sync_operator_psp_leads(self) -> int:
        """Rattache au PSP (psp_lead) les operateurs sans lead, meme equipe + shift."""
        total = 0
        seen: set[tuple[str, str]] = set()
        for psp in OperateurEffectif.objects.filter(fonction="PSP", is_deleted=False):
            scope = (psp.equipe, psp.shift)
            if scope in seen:
                continue
            seen.add(scope)
            primary = self._primary_psp_for_scope(psp.equipe, psp.shift)
            if not primary:
                continue
            peer_count = OperateurEffectif.objects.filter(
                equipe=psp.equipe, shift=psp.shift, fonction="PSP", is_deleted=False
            ).count()
            if peer_count > 1:
                self.stdout.write(
                    self.style.WARNING(
                        f"{psp.equipe} shift {psp.shift}: {peer_count} PSP — rattachement via {primary.identifiant}."
                    )
                )

            sibling_psp_ids = list(
                OperateurEffectif.objects.filter(
                    equipe=psp.equipe,
                    shift=psp.shift,
                    fonction="PSP",
                    is_deleted=False,
                )
                .exclude(pk=primary.pk)
                .values_list("pk", flat=True)
            )

            base_op_qs = OperateurEffectif.objects.filter(
                equipe=psp.equipe,
                shift=psp.shift,
                is_deleted=False,
            ).exclude(fonction="PSP")

            qs_null = base_op_qs.filter(psp_lead_id__isnull=True)
            n_null = qs_null.update(psp_lead=primary)

            n_wrong = 0
            if sibling_psp_ids:
                qs_wrong = base_op_qs.filter(psp_lead_id__in=sibling_psp_ids)
                n_wrong = qs_wrong.update(psp_lead=primary)

            deleted_lead_ids = list(
                OperateurEffectif.objects.filter(is_deleted=True).values_list("pk", flat=True)
            )
            n_stale = 0
            if deleted_lead_ids:
                qs_stale = base_op_qs.filter(psp_lead_id__in=deleted_lead_ids)
                n_stale = qs_stale.update(psp_lead=primary)

            n = n_null + n_wrong + n_stale
            total += n
            if n:
                extra = []
                if n_wrong:
                    extra.append(f"{n_wrong} depuis autre PSP doublon")
                if n_stale:
                    extra.append(f"{n_stale} depuis PSP supprime")
                self.stdout.write(
                    f"Team {psp.equipe} shift {psp.shift}: {n} operateur(s) -> PSP {primary.identifiant}"
                    + (f" ({', '.join(extra)})" if extra else "")
                )
        return total
