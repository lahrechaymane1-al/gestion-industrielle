"""Constantes métier CCB (ligne CCB, filtres API)."""

CCB_MODULE_NAME = "CCB"

# Objectifs de production CCB par heure H1–H8 (identiques pour chaque shift / chaque jour).
CCB_OBJECTIFS_HORAIRES: tuple[int, ...] = (20, 20, 20, 20, 11, 20, 20, 20)
CCB_OBJECTIF_TOTAL_SHIFT: int = sum(CCB_OBJECTIFS_HORAIRES)
