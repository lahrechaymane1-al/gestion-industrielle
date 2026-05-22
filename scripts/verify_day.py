"""Verify one day from NRO2026.xlsx."""
import sys
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

path = Path(r"C:\Users\ASUS\Desktop\NRO2026.xlsx")
target = date.fromisoformat(sys.argv[1] if len(sys.argv) > 1 else "2026-05-01")

wb = load_workbook(path, read_only=True, data_only=True)
ws = wb[wb.sheetnames[0]]
rows = list(ws.iter_rows(values_only=True))
wb.close()
header = [str(c).strip() if c else "" for c in rows[0]]
col = {h: i for i, h in enumerate(header)}
print("Headers:", header)

day_rows = []
for i, raw in enumerate(rows[1:], 2):
    if not any(raw):
        continue
    d = raw[col["Date"]]
    if isinstance(d, datetime):
        dv = d.date()
    elif isinstance(d, date):
        dv = d
    else:
        dv = date.fromisoformat(str(d).split()[0])
    if dv != target:
        continue

    def g(name):
        idx = col.get(name)
        return raw[idx] if idx is not None and idx < len(raw) else None

    mins = g("Temps (min)")
    day_rows.append((i, g("Module"), g("Poste"), g("Moyen"), g("Problème"), g("Type"), mins, g("Diversité")))

print("Count:", len(day_rows))
print("Sum min:", sum(int(float(m)) for *_, m, _, _ in day_rows if m is not None))
for r in day_rows:
    row, mod, poste, moyen, prob, typ, mins, div = r
    moyen_s = moyen if moyen else ""
    print(f"{row:3} | {mod} | {poste} | {moyen_s} | {prob} | {typ} | {mins} | div={div}")
