"""Effectif squad metadata (canonical ``code_equipe`` par équipe × shift, aligné sur le seed démo)."""

# Même logique que ``seed_demo_data.EFFECTIF_CODE_EQUIPE`` — garder synchro si vous changez les codes métier.
CANONICAL_CODE_EQUIPE_BY_SCOPE: dict[tuple[str, str], str] = {
    ("Berceau", "A"): "BER-EQ-A",
    ("Berceau", "B"): "BER-EQ-B",
    ("Berceau", "N"): "BER-EQ-N",
    ("CCB", "A"): "CCB-EQ-A",
    ("CCB", "B"): "CCB-EQ-B",
    ("CCB", "N"): "CCB-EQ-N",
}
