def serialize_stock_summary(payload):
    return {
        "equipe": payload.get("equipe", "CCB"),
        "module": payload.get("module", "stock"),
    }

