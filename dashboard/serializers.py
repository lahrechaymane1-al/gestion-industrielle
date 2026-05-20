def serialize_dashboard_metrics(payload):
    return {
        "equipe": payload.get("equipe", "Berceau"),
        "module": payload.get("module", "dashboard"),
    }

