"""Référentiels types de panne par équipe (sources uniques pour seeds + API)."""

# Types Berceau (ligne soudure / automate — inchangés fonctionnellement)
BERCEAU_PANNE_TYPES = [
    "Amorçage",
    "Arrêt programmé",
    "Basculement de A1 à A3",
    "Basculement de A3 à A1",
    "Blocage de robot de transfert",
    "Blocage de serrage",
    "Blocage manipulateur",
    "Cable de masse",
    "Changement de bobine de fil",
    "Changement de diffuseur",
    "Changement des électrodes",
    "Chute de la torche",
    "Chute de pièce",
    "Colision",
    "Défaut de robot MAG",
    "Fuite d'air",
    "Fuite d'eau",
    "Nettoyage des buses",
    "Perte d'énergie",
    "Poinçonnage",
    "Probleme automate",
    "Probleme de capteur",
    "Probleme de convoyeur",
    "Probleme de générateur",
    "Probleme de vérin",
    "Probleme GAZ",
    "Probleme pression",
    "Probleme teach",
]

# Types CCB — hors référentiel Berceau (pas de doublon avec BERCEAU_PANNE_TYPES)
CCB_PANNE_TYPES = [
    "Arrêt programme",
    "Problème qualité pièce",
    "Réglage / mise au point",
    "Maintenance corrective",
    "Manque composant",
    "Attente outillage",
    "Nettoyage ligne",
    "Perte énergie / air",
    "Autre",
]

BERCEAU_PANNE_TYPE_NAMES = frozenset(BERCEAU_PANNE_TYPES)
CCB_PANNE_TYPE_NAMES = frozenset(CCB_PANNE_TYPES)
