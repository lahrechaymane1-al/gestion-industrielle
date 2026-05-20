"""RBAC + shift restriction (PSP reads shift from Effectif dynamically).

Modèle métier visé :
- Les UEP Berceau et CCB ont chacune les shifts A / B / N.
- Un PSP est rattaché à une UEP (Berceau ou CCB) et à un seul shift ; son login ne doit
  voir/modifier que les données de ce shift (production, arrêts, effectif filtré par UEP, etc.).
- Les comptes RU/ADMIN restent transverses sur les shifts.

L'effectif lié au profil, l'identifiant de connexion = identifiant effectif PSP, ou les comptes seed
``br_psp_*`` / ``ccb_psp_*`` (login ≠ matricule) fournissent UEP + shift (champ stocké ``equipe``).
"""
from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db.models import QuerySet

from .models import UserAccessProfile

logger = logging.getLogger(__name__)

User = get_user_model()

# Actions used by legacy require_role_action and APIs
ROLE_ACTIONS = {
    "ADMIN": {"create", "read", "update", "delete"},
    "RU": {"create", "read", "update", "delete"},
    "PSP": {"create", "read", "update"},  # pas de suppression pour PSP
}


def get_profile(user) -> UserAccessProfile | None:
    if not user or not user.is_authenticated:
        return None
    try:
        return user.access_profile
    except UserAccessProfile.DoesNotExist:
        role = (
            UserAccessProfile.Role.ADMIN
            if getattr(user, "is_superuser", False)
            else UserAccessProfile.Role.RU
        )
        return UserAccessProfile.objects.create(user=user, role=role)


def get_role(user) -> str:
    if not user or not user.is_authenticated:
        return "lecture"
    prof = get_profile(user)
    if not prof:
        return "lecture"
    return prof.role


def is_admin_or_ru(user) -> bool:
    r = get_role(user)
    return r in (UserAccessProfile.Role.ADMIN, UserAccessProfile.Role.RU)


def is_psp(user) -> bool:
    return get_role(user) == UserAccessProfile.Role.PSP


def _psp_equipe_shift_from_seed_username(username: str) -> tuple[str, str] | None:
    """Map demo / legacy login names to (equipe, shift)."""
    u = (username or "").strip().lower()
    shift_map = {"a": "A", "b": "B", "n": "N"}
    if u.startswith("br_psp_"):
        suf = u.removeprefix("br_psp_")
        sh = shift_map.get(suf)
        if sh:
            return ("Berceau", sh)
    if u.startswith("ccb_psp_"):
        suf = u.removeprefix("ccb_psp_")
        sh = shift_map.get(suf)
        if sh:
            return ("CCB", sh)
    if u.startswith("psp_berceau_"):
        suf = u.removeprefix("psp_berceau_")
        sh = shift_map.get(suf)
        if sh:
            return ("Berceau", sh)
    if u.startswith("psp_ccb_"):
        suf = u.removeprefix("psp_ccb_")
        sh = shift_map.get(suf)
        if sh:
            return ("CCB", sh)
    return None


def _psp_scope_effectif(user):
    """
    Effectif row used for PSP shift / équipe / team scope.

    1) Prefer UserAccessProfile.effectif when set and not deleted.
    2) Else match Django username to OperateurEffectif.identifiant (login identifiant is usually the same),
       preferring fonction PSP so the dashboard and APIs work even if the profil link was never saved.
    3) Else, for seed-style usernames ``br_psp_{a|b|n}`` / ``ccb_psp_{a|b|n}``, resolve the unique PSP
       effectif row for that équipe + shift (username ≠ matricule effectif, e.g. ``br_psp_a`` vs ``MAT-BR-PSP-A``).
    """
    if not user or not user.is_authenticated or not is_psp(user):
        return None
    from .models import OperateurEffectif

    prof = get_profile(user)
    if prof and prof.effectif_id:
        eff = OperateurEffectif.objects.filter(pk=prof.effectif_id, is_deleted=False).first()
        if eff:
            return eff

    ident = (getattr(user, "username", None) or "").strip()
    if not ident:
        return None

    qs = OperateurEffectif.objects.filter(identifiant__iexact=ident, is_deleted=False)
    eff = qs.filter(fonction="PSP").first() or qs.first()
    if eff:
        logger.info(
            "psp_scope_by_identifiant username=%s effectif_pk=%s equipe=%s shift=%s",
            ident,
            eff.pk,
            eff.equipe,
            eff.shift,
        )
        return eff

    seed_scope = _psp_equipe_shift_from_seed_username(ident)
    if seed_scope:
        eq, sh = seed_scope
        eff = OperateurEffectif.objects.filter(
            equipe=eq, shift=sh, fonction="PSP", is_deleted=False
        ).first()
        if eff:
            logger.info(
                "psp_scope_by_seed_username username=%s effectif_pk=%s equipe=%s shift=%s",
                ident,
                eff.pk,
                eff.equipe,
                eff.shift,
            )
        return eff

    return None


def get_psp_shift(user) -> str | None:
    """Shift effectif courant (Effectif est la source de verite)."""
    if not is_psp(user):
        return None
    eff = _psp_scope_effectif(user)
    if not eff:
        return None
    return eff.shift or None


def get_psp_equipe(user) -> str | None:
    """Equipe Berceau/CCB depuis l'effectif lie au profil."""
    if not is_psp(user):
        return None
    eff = _psp_scope_effectif(user)
    return eff.equipe if eff else None


def get_psp_effectif_id(user) -> int | None:
    """OperateurEffectif.pk linked to this PSP user (team lead id)."""
    if not is_psp(user):
        return None
    eff = _psp_scope_effectif(user)
    return int(eff.pk) if eff else None


def restrict_psp_scope(
    user,
    queryset: QuerySet,
    *,
    shift_field: str = "shift",
    equipe_field: str | None = None,
) -> QuerySet:
    """PSP: filtre shift + optionnellement equipe (Berceau vs CCB)."""
    qs = restrict_queryset_by_shift(user, queryset, shift_field)
    if not is_psp(user):
        return qs
    if equipe_field:
        eq = get_psp_equipe(user)
        if eq:
            qs = qs.filter(**{equipe_field: eq})
    return qs


def ensure_psp_object_access(user, obj: Any, *, endpoint: str = "") -> bool:
    """PSP: enforce shift/equipe + (when applicable) team membership via psp_lead."""
    if not user or not user.is_authenticated:
        return False
    if is_admin_or_ru(user):
        return True
    if not is_psp(user):
        return True
    own_shift = get_psp_shift(user)
    own_eq = get_psp_equipe(user)
    own_effectif_id = get_psp_effectif_id(user)
    obj_shift = getattr(obj, "shift", None)
    if own_shift is None or obj_shift != own_shift:
        log_access_denied(user, requested_shift=str(obj_shift), endpoint=endpoint)
        return False
    obj_eq = getattr(obj, "equipe", None)
    if obj_eq is not None:
        if own_eq is None or obj_eq != own_eq:
            log_access_denied(user, requested_shift=f"equipe:{obj_eq}", endpoint=endpoint)
            return False

    # Team membership: for objects tied to an effectif (e.g. Absence), ensure it belongs to PSP's team.
    # Allow PSP to access their own effectif row even though psp_lead is null.
    if own_effectif_id:
        eff = getattr(obj, "effectif", None)
        eff_id = getattr(obj, "effectif_id", None)
        if eff is not None:
            eff_id = getattr(eff, "pk", None)
            lead_id = getattr(eff, "psp_lead_id", None)
        else:
            lead_id = None

        if eff_id is not None:
            if int(eff_id) == int(own_effectif_id):
                return True
            if lead_id is not None and int(lead_id) == int(own_effectif_id):
                return True
            log_access_denied(user, requested_shift=f"team_lead:{lead_id}", endpoint=endpoint)
            return False

        # Fiche OperateurEffectif (l'objet est la ligne effectif, pas une FK « effectif »).
        row_pk = getattr(obj, "pk", None)
        if row_pk is not None and eff is None and eff_id is None and hasattr(obj, "psp_lead_id"):
            row_lead_id = getattr(obj, "psp_lead_id", None)
            if int(row_pk) == int(own_effectif_id):
                return True
            if row_lead_id is not None and int(row_lead_id) == int(own_effectif_id):
                return True
            log_access_denied(user, requested_shift=f"effectif_row:{row_pk}", endpoint=endpoint)
            return False
    return True


def ensure_psp_effectif_write_allowed(
    user,
    *,
    payload: dict,
    existing_row_pk: int | None = None,
    endpoint: str = "",
) -> bool:
    """PSP : ne peut créer que des opérateurs de son équipe ; pas de nouvelle fiche PSP."""
    if not user or not user.is_authenticated:
        return False
    if is_admin_or_ru(user):
        return True
    if not is_psp(user):
        return True
    lead_id = get_psp_effectif_id(user)
    if not lead_id:
        log_access_denied(user, endpoint=endpoint)
        return False

    raw_fn = payload.get("fonction")
    if raw_fn is not None:
        fonction = str(raw_fn).strip().upper()
        if fonction == "PSP" and (existing_row_pk is None or int(existing_row_pk) != int(lead_id)):
            log_access_denied(user, requested_shift="fonction:PSP", endpoint=endpoint)
            return False

    if existing_row_pk is not None and int(existing_row_pk) == int(lead_id):
        return True

    raw_lead = payload.get("psp_lead")
    if raw_lead in (None, "", 0, "0"):
        return True
    try:
        if int(raw_lead) != int(lead_id):
            log_access_denied(user, requested_shift=f"psp_lead:{raw_lead}", endpoint=endpoint)
            return False
    except (TypeError, ValueError):
        log_access_denied(user, endpoint=endpoint)
        return False
    return True


def ensure_equipe_allowed(user, equipe_value: str | None, *, endpoint: str = "") -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_admin_or_ru(user):
        return True
    if not equipe_value:
        return False
    own = get_psp_equipe(user)
    ok = own is not None and own == equipe_value
    if not ok:
        log_access_denied(user, requested_shift=f"equipe:{equipe_value}", endpoint=endpoint)
    return ok


def ensure_psp_absence_effectifs_allowed(
    user,
    *,
    effectif_id: int | str | None,
    remplacant_effectif_id: int | str | None,
    equipe: str | None,
    shift: str | None,
    endpoint: str = "",
) -> bool:
    """PSP: l'absent et le remplaçant effectif doivent appartenir à l'équipe du PSP."""
    if not user or not user.is_authenticated:
        return False
    if is_admin_or_ru(user):
        return True
    if not is_psp(user):
        return True
    if not ensure_equipe_allowed(user, equipe, endpoint=endpoint):
        return False
    if shift and not ensure_shift_allowed(user, shift, endpoint=endpoint):
        return False
    lead_id = get_psp_effectif_id(user)
    if not lead_id:
        log_access_denied(user, endpoint=endpoint)
        return False

    from effectif.models import OperateurEffectif

    def _effectif_in_team(eid: int) -> bool:
        eff = (
            OperateurEffectif.objects.filter(pk=eid, is_deleted=False)
            .only("pk", "shift", "equipe", "psp_lead_id")
            .first()
        )
        if not eff:
            return False
        own_shift = get_psp_shift(user)
        own_eq = get_psp_equipe(user)
        if own_shift and eff.shift != own_shift:
            return False
        if own_eq and eff.equipe != own_eq:
            return False
        if int(eff.pk) == int(lead_id):
            return True
        if eff.psp_lead_id is not None and int(eff.psp_lead_id) == int(lead_id):
            return True
        return False

    for raw_id, label in ((effectif_id, "effectif"), (remplacant_effectif_id, "remplacant_effectif")):
        if raw_id is None or raw_id == "":
            continue
        try:
            pk = int(raw_id)
        except (TypeError, ValueError):
            log_access_denied(user, endpoint=endpoint)
            return False
        if not _effectif_in_team(pk):
            log_access_denied(user, requested_shift=f"{label}:{pk}", endpoint=endpoint)
            return False
    return True


def allowed_actions(user) -> set[str]:
    if not user or not user.is_authenticated:
        return set()
    role = get_role(user)
    return set(ROLE_ACTIONS.get(role, set()))


def can_do_action(user, action: str) -> bool:
    return action in allowed_actions(user)


def can_access_shift(user, shift: str | None) -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_admin_or_ru(user):
        return True
    if not shift:
        return False
    own = get_psp_shift(user)
    return own is not None and own == shift


def restrict_queryset_by_shift(user, queryset: QuerySet, shift_field: str = "shift") -> QuerySet:
    if not user or not user.is_authenticated:
        return queryset.none()
    if is_admin_or_ru(user):
        return queryset
    own = get_psp_shift(user)
    if not own:
        return queryset.none()
    return queryset.filter(**{shift_field: own})


def ensure_shift_allowed(user, shift_value: str | None, *, endpoint: str = "") -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_admin_or_ru(user):
        return True
    if shift_value not in {"A", "B", "N"}:
        return False
    ok = can_access_shift(user, shift_value)
    if not ok:
        log_access_denied(user, requested_shift=shift_value, endpoint=endpoint)
    return ok


def ensure_object_shift_allowed(user, obj: Any, shift_attr: str = "shift", *, endpoint: str = "") -> bool:
    shift_val = getattr(obj, shift_attr, None)
    return ensure_shift_allowed(user, shift_val, endpoint=endpoint)


def log_access_denied(user, *, requested_shift: str | None, endpoint: str) -> None:
    role = get_role(user) if user and user.is_authenticated else "anonymous"
    own = get_psp_shift(user) if user and user.is_authenticated else None
    uid = getattr(user, "pk", None) if user and user.is_authenticated else None
    logger.warning(
        "access_denied user_id=%s role=%s shift_own=%s shift_requested=%s endpoint=%s",
        uid,
        role,
        own,
        requested_shift,
        endpoint,
    )


def resolve_permissions_dict(user) -> dict[str, bool]:
    acts = allowed_actions(user)
    return {
        "create": "create" in acts,
        "read": "read" in acts,
        "update": "update" in acts,
        "delete": "delete" in acts,
    }


def serialize_me(user) -> dict[str, Any]:
    if not user or not user.is_authenticated or isinstance(user, AnonymousUser):
        return {}
    prof = get_profile(user)
    shift = get_psp_shift(user) if is_psp(user) else None
    equipe = get_psp_equipe(user) if is_psp(user) else None
    effectif_id = get_psp_effectif_id(user) if is_psp(user) else (prof.effectif_id if prof else None)
    return {
        "id": user.pk,
        "identifiant": user.username,
        "role": prof.role if prof else get_role(user),
        "shift": shift,
        "equipe": equipe,
        "effectif_id": effectif_id,
        "permissions": resolve_permissions_dict(user),
    }


# Legacy bridge: map old group-based logic to new roles (unused once migrated)
def legacy_resolve_role(user) -> str:
    """Return internal role code for decorators."""
    return get_role(user)
