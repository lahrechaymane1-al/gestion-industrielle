def serialize_production(item):
    return {
        "id": item.id,
        "line": item.line,
        "date": item.date,
        "shift": item.shift,
        "objectif": item.objectif,
        "volume": item.volume,
        "rebut": item.rebut,
        "retouche": item.retouche,
        "temps_arrets": item.temps_arrets,
        "ro_percent": item.ro_percent,
    }

