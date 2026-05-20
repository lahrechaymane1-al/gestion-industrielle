def serialize_dashboard_metrics(payload):
    return {
        "equipe": payload.get("equipe", "CCB"),
        "module": payload.get("module", "dashboard"),
    }

