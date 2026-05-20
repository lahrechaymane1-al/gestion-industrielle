def serialize_arret_summary(payload):
    return {
        "equipe": payload.get("equipe", "CCB"),
        "module": payload.get("module", "arret"),
    }

