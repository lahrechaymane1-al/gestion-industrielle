def serialize_stock_summary(payload):
    return {
        "equipe": payload.get("equipe", "Berceau"),
        "module": payload.get("module", "stock"),
    }

