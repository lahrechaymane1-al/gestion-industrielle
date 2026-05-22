import type { StockJournalResponse, StockJournalRow } from "../../api/types";

function mergeShiftEntrees(
  a: StockJournalRow["entree_par_shift"],
  b: StockJournalRow["entree_par_shift"]
): StockJournalRow["entree_par_shift"] {
  return {
    A: Number(a.A || 0) + Number(b.A || 0),
    B: Number(a.B || 0) + Number(b.B || 0),
    N: Number(a.N || 0) + Number(b.N || 0),
  };
}

/** Fusionne les historiques A1 et A3 (entrées par shift additionnées par jour). */
export function mergeStockJournalResponses(
  a1: StockJournalResponse,
  a3: StockJournalResponse,
  anchorDate?: string
): StockJournalResponse {
  const byDate = new Map<string, StockJournalRow>();

  const ingest = (row: StockJournalRow) => {
    const d = row.date.slice(0, 10);
    const prev = byDate.get(d);
    if (!prev) {
      byDate.set(d, {
        ...row,
        line: null,
        entree_par_shift: { ...row.entree_par_shift },
      });
      return;
    }
    byDate.set(d, {
      ...prev,
      entree_calculee: Number(prev.entree_calculee || 0) + Number(row.entree_calculee || 0),
      entree_par_shift: mergeShiftEntrees(prev.entree_par_shift, row.entree_par_shift),
    });
  };

  for (const row of a1.history ?? []) ingest(row);
  for (const row of a3.history ?? []) ingest(row);

  const history = [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
  const anchor = (anchorDate ?? a1.current?.date ?? a3.current?.date ?? "").slice(0, 10);
  const current =
    history.find((h) => h.date.slice(0, 10) === anchor) ??
    history[history.length - 1] ??
    a1.current;

  return { current, history };
}
