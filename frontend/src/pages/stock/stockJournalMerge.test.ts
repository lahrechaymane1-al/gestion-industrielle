import { describe, expect, it } from "vitest";
import { mergeStockJournalResponses } from "./stockJournalMerge";
import type { StockJournalResponse } from "../../api/types";

function row(
  date: string,
  line: "A1" | "A3",
  shifts: { A: number; B: number; N: number }
): StockJournalResponse {
  const entree = shifts.A + shifts.B + shifts.N;
  const r = {
    id: 1,
    date,
    equipe: "Berceau" as const,
    line,
    stock_debut: 0,
    entree_calculee: entree,
    entree_par_shift: shifts,
    sortie_montage: 0,
    stock_fin: entree,
    is_closed: false,
    note: "",
    updated_at: null,
  };
  return { current: r, history: [r] };
}

describe("mergeStockJournalResponses", () => {
  it("adds entree_par_shift for the same date across A1 and A3", () => {
    const a1 = row("2026-05-17", "A1", { A: 10, B: 0, N: 0 });
    const a3 = row("2026-05-17", "A3", { A: 0, B: 0, N: 197 });
    const merged = mergeStockJournalResponses(a1, a3, "2026-05-17");
    const day = merged.history.find((h) => h.date.startsWith("2026-05-17"));
    expect(day?.entree_par_shift).toEqual({ A: 10, B: 0, N: 197 });
  });
});
