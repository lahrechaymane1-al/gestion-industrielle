from datetime import date as date_cls, timedelta

from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from openpyxl import Workbook

from production.models import ProductionBerceau
from production_ccb.models import ProductionCCB
from stock.models import StockJournal

from .api_utils import json_body, json_forbidden
from .authz import can_do_action as auth_can_do_action
from .authz import ensure_equipe_allowed, get_psp_shift, is_admin_or_ru, is_psp


def _parse_date(value: str | None) -> date_cls:
    if not value:
        return date_cls.today()
    return date_cls.fromisoformat(value)


def _normalize_scope(equipe: str | None, line: str | None) -> tuple[str, str | None]:
    eq = (equipe or "Berceau").strip()
    ln = (line or "").strip() or None
    if eq not in {"Berceau", "CCB"}:
        eq = "Berceau"
    if eq == "Berceau":
        if ln not in {"A1", "A3"}:
            ln = "A1"
    elif ln not in {"LHD", "RHD"}:
        ln = "LHD"
    return eq, ln


def _line_filter_kwargs(line: str | None) -> dict:
    return {"line": line} if line else {"line__isnull": True}


def _berceau_entree_by_line(target_date: date_cls, line: str) -> tuple[int, dict]:
    """Entrées stock Berceau : somme production_h* dont line_h* correspond à la diversité."""
    by_shift = {"A": 0, "B": 0, "N": 0}
    for row in ProductionBerceau.objects.filter(date=target_date):
        shift = str(row.shift or "")
        if shift not in by_shift:
            continue
        for hour in range(1, 9):
            if getattr(row, f"line_h{hour}", None) != line:
                continue
            by_shift[shift] += int(getattr(row, f"production_h{hour}", 0) or 0)
    total = by_shift["A"] + by_shift["B"] + by_shift["N"]
    return total, by_shift


def _ccb_entree_by_line(target_date: date_cls, line: str) -> tuple[int, dict]:
    """Entrées stock CCB : somme production_lhd_h* ou production_rhd_h* selon la diversité."""
    by_shift = {"A": 0, "B": 0, "N": 0}
    prefix = "production_lhd_h" if line == "LHD" else "production_rhd_h"
    for row in ProductionCCB.objects.filter(date=target_date):
        shift = str(row.shift or "")
        if shift not in by_shift:
            continue
        for hour in range(1, 9):
            by_shift[shift] += int(getattr(row, f"{prefix}{hour}", 0) or 0)
    total = by_shift["A"] + by_shift["B"] + by_shift["N"]
    return total, by_shift


def _compute_entree(
    target_date: date_cls, equipe: str, line: str | None, shift_scope: str | None = None
) -> tuple[int, dict]:
    """Somme des volumes production du jour. Si shift_scope (PSP), uniquement ce shift."""
    if equipe == "Berceau":
        if line not in {"A1", "A3"}:
            line = "A1"
        total, by_shift = _berceau_entree_by_line(target_date, line)
        if shift_scope in {"A", "B", "N"}:
            return by_shift[shift_scope], by_shift
        return total, by_shift

    if line not in {"LHD", "RHD"}:
        line = "LHD"
    total, by_shift = _ccb_entree_by_line(target_date, line)
    if shift_scope in {"A", "B", "N"}:
        return by_shift[shift_scope], by_shift
    return total, by_shift


def _previous_stock_fin(target_date: date_cls, equipe: str, line: str | None) -> int:
    prev_journal = (
        StockJournal.objects.filter(equipe=equipe, date__lt=target_date, **_line_filter_kwargs(line))
        .order_by("-date")
        .first()
    )
    if prev_journal:
        anchor_date = prev_journal.date
        running = int(prev_journal.stock_fin)
    else:
        if equipe == "Berceau":
            anchor_date = (
                ProductionBerceau.objects.filter(date__lt=target_date)
                .order_by("date")
                .values_list("date", flat=True)
                .first()
            )
        else:
            anchor_date = (
                ProductionCCB.objects.filter(date__lt=target_date)
                .order_by("date")
                .values_list("date", flat=True)
                .first()
            )
        if not anchor_date:
            return 0
        running = 0

    cursor = anchor_date if not prev_journal else anchor_date + timedelta(days=1)
    while cursor < target_date:
        entree, _ = _compute_entree(cursor, equipe, line, shift_scope=None)
        rec = StockJournal.objects.filter(date=cursor, equipe=equipe, **_line_filter_kwargs(line)).first()
        sortie = int(rec.sortie_montage if rec else 0)
        running = running + entree - sortie
        cursor += timedelta(days=1)
    return running


def _snapshot(target_date: date_cls, equipe: str, line: str | None, shift_scope: str | None = None) -> dict:
    entree_all, by_shift = _compute_entree(target_date, equipe, line, shift_scope=None)
    stock_debut = _previous_stock_fin(target_date, equipe, line)
    rec = StockJournal.objects.filter(date=target_date, equipe=equipe, **_line_filter_kwargs(line)).first()
    sortie = int(rec.sortie_montage if rec else 0)

    if shift_scope in {"A", "B", "N"}:
        entree_total, _ = _compute_entree(target_date, equipe, line, shift_scope)
        total_day = by_shift["A"] + by_shift["B"] + by_shift["N"]
        sortie_imputee = int(sortie * entree_total / total_day) if total_day > 0 else 0
        stock_fin = stock_debut + entree_total - sortie_imputee
    else:
        entree_total = entree_all
        sortie_imputee = sortie
        stock_fin = stock_debut + entree_total - sortie

    return {
        "id": rec.id if rec else None,
        "date": target_date.isoformat(),
        "equipe": equipe,
        "line": line,
        "stock_debut": stock_debut,
        "entree_calculee": entree_total,
        "entree_par_shift": by_shift,
        "sortie_montage": sortie,
        "sortie_imputee": sortie_imputee,
        "stock_fin": stock_fin,
        "is_closed": bool(rec.is_closed) if rec else False,
        "note": rec.note if rec else "",
        "updated_at": rec.updated_at.isoformat() if rec and rec.updated_at else None,
    }


def api_stock_journal(request):
    if not auth_can_do_action(request.user, "read"):
        return json_forbidden()
    equipe, line = _normalize_scope(request.GET.get("equipe"), request.GET.get("line"))
    if not ensure_equipe_allowed(request.user, equipe, endpoint="api_stock_journal GET"):
        return json_forbidden()
    target_date = _parse_date(request.GET.get("date"))
    days = max(1, min(int(request.GET.get("days") or 7), 31))

    shift_scope: str | None = None
    if is_psp(request.user):
        own = get_psp_shift(request.user)
        if own in {"A", "B", "N"}:
            shift_scope = own

    history = []
    for i in range(days):
        d = target_date - timedelta(days=i)
        history.append(_snapshot(d, equipe, line, shift_scope))
    history.sort(key=lambda row: row["date"], reverse=True)

    export_format = (request.GET.get("export") or "").lower().strip()
    if export_format == "excel":
        sortie_header = f"Sortie montage (stock {line})" if line else "Sortie montage"
        headers = [
            "Date",
            "Diversite",
            "Entree shift A",
            "Entree shift B",
            "Entree shift N",
            "Stock debut",
            "Entree totale",
            sortie_header,
            "Stock fin",
            "Note",
        ]
        rows = [
            [
                row["date"],
                row["line"] or "",
                row["entree_par_shift"]["A"],
                row["entree_par_shift"]["B"],
                row["entree_par_shift"]["N"],
                row["stock_debut"],
                row["entree_calculee"],
                row["sortie_montage"],
                row["stock_fin"],
                row["note"] or "",
            ]
            for row in history
        ]
        workbook = Workbook()
        sheet = workbook.active
        title = f"Stock {equipe}"
        if line:
            title += f" {line}"
        sheet.title = title[:31]
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        scope = equipe.lower()
        if line:
            scope += f"_{line.lower()}"
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="stock_{scope}_{target_date.isoformat()}.xlsx"'
        )
        workbook.save(response)
        return response

    return JsonResponse({"current": history[0], "history": history})


def api_stock_journal_update(request):
    if request.method not in {"POST", "PATCH"}:
        return HttpResponse(status=405)
    if not is_admin_or_ru(request.user):
        return json_forbidden("Seuls RU/ADMIN peuvent saisir la sortie montage.")

    payload = json_body(request)
    equipe, line = _normalize_scope(payload.get("equipe"), payload.get("line"))
    if not ensure_equipe_allowed(request.user, equipe, endpoint="api_stock_journal_update"):
        return json_forbidden()
    target_date = _parse_date(payload.get("date"))
    sortie = int(payload.get("sortie_montage") or 0)
    if sortie < 0:
        return JsonResponse({"errors": {"sortie_montage": ["La sortie doit etre >= 0."]}}, status=400)
    is_closed = bool(payload.get("is_closed", False))
    note = str(payload.get("note") or "").strip()

    entree_total, _ = _compute_entree(target_date, equipe, line, shift_scope=None)
    stock_debut = _previous_stock_fin(target_date, equipe, line)
    stock_fin = stock_debut + entree_total - sortie
    rec, _ = StockJournal.objects.get_or_create(
        date=target_date,
        equipe=equipe,
        defaults={"line": line},
        **_line_filter_kwargs(line),
    )
    rec.line = line
    rec.stock_debut = stock_debut
    rec.entree_calculee = entree_total
    rec.sortie_montage = sortie
    rec.stock_fin = stock_fin
    rec.is_closed = is_closed
    rec.note = note
    rec.updated_by = request.user if request.user.is_authenticated else None
    rec.save()
    return JsonResponse(_snapshot(target_date, equipe, line, shift_scope=None))
