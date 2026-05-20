def serialize_arret(item):
    return {
        "id": item.id,
        "date": item.date,
        "shift": item.shift,
        "module": item.module.name,
        "poste": item.poste.name,
        "moyen": item.moyen.name,
        "heure_production": item.heure_production,
        "temps_arret_min": item.temps_arret_min,
        "category": item.category,
    }

