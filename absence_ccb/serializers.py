def serialize_absence(item):
    return {
        "id": item.id,
        "equipe": item.equipe,
        "shift": item.shift,
        "motif": item.motif,
        "date_absence": item.date_absence,
        "nom_absent": item.absent_nom,
        "nom_remplacant": item.remplacant_nom,
        "created_at": item.created_at,
    }

