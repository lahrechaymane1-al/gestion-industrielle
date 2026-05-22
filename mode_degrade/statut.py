"""Libellés statut mode dégradé."""

FERMER_STATUT = "Fermer"
LEGACY_CLOS_STATUT = "Clos"

STATUS_CHOICES = (
    ("Ouvert", "Ouvert"),
    ("En cours", "En cours"),
    (FERMER_STATUT, FERMER_STATUT),
)


def statut_label(value: str | None) -> str:
    if value == LEGACY_CLOS_STATUT:
        return FERMER_STATUT
    return value or ""
