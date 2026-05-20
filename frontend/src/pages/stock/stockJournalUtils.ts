import type { StockJournalRow } from "../../api/types";

export const HISTORY_DAYS = 10;
export const CHART_WORKING_DAYS = 14;

export function isWorkingDay(isoDate: string): boolean {
  const d = new Date(`${isoDate}T12:00:00`);
  const day = d.getDay();
  return day !== 0 && day !== 6;
}

export function formatChartDay(isoDate: string): string {
  const d = new Date(`${isoDate}T12:00:00`);
  return d.toLocaleDateString("fr-FR", { weekday: "short", day: "2-digit", month: "short" });
}

export function formatDetailDate(isoDate: string): string {
  const d = new Date(`${isoDate.slice(0, 10)}T12:00:00`);
  return d.toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function fmtQty(n: number): string {
  return Number(n).toLocaleString("fr-FR");
}

export function stockLineLabel(line: "A1" | "A3" | undefined): string {
  if (line === "A1" || line === "A3") return `stock ${line}`;
  return "stock";
}

/** Sortie aligned with entree_calculee / stock_fin (prorata shift for PSP). */
export function displaySortie(row: StockJournalRow): number {
  return row.sortie_imputee ?? row.sortie_montage;
}

export function buildChartData(history: StockJournalRow[]) {
  return [...history]
    .filter((row) => isWorkingDay(row.date))
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-CHART_WORKING_DAYS)
    .map((row) => ({
      date: row.date,
      label: formatChartDay(row.date),
      entree: row.entree_calculee,
      sortie: displaySortie(row),
    }));
}
