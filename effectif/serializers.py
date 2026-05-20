def serialize_effectif(item):
    return {
        "id": item.id,
        "nom_complet": item.nom_complet,
        "shift": item.shift,
        "identifiant": item.identifiant,
        "cin": item.cin,
        "fonction": item.fonction,
        "equipe": item.equipe,
    }

