def serialize_mode_degrade(item):
    return {
        "id": item.id,
        "equipe": item.equipe,
        "shift": item.shift,
        "action": item.action,
        "probleme": item.probleme,
        "pilote": item.pilote,
        "date": item.date,
        "statut": item.statut,
    }

