import * as XLSX from "xlsx";

export type ParetoTypeExcelRow = {
  /** Libellé combiné (graphique / référence), inchangé pour compatibilité. */
  typeArret: string;
  panne_type_nom: string;
  moyen_nom: string;
  pctA1: number;
  pctA3: number;
  minutesA1?: number;
  minutesA3?: number;
  cumulePercent: number;
};

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

/**
 * Exporte le tableau Pareto types en .xlsx : feuille « Contexte » (5 lignes de filtrage) + « Pareto types » (données).
 */
export function exportParetoTypesExcel(params: {
  rows: ParetoTypeExcelRow[];
  jourIso: string;
  shiftLabel: string;
  categoryLabel: string | null;
  /** Libellé court catégorie pour le nom de fichier (sans caractères interdits). */
  categorySlug?: string;
  /** Filtre poste appliqué au Pareto types uniquement (libellé lisible). */
  posteFilterLabel?: string | null;
}): void {
  const { rows, jourIso, shiftLabel, categoryLabel, categorySlug, posteFilterLabel } = params;
  if (!rows.length) return;

  const wb = XLSX.utils.book_new();

  const contextAoa: (string | number)[][] = [
    ["Document", "Pareto types d'arrêt — impact production"],
    ["Date (jour)", jourIso],
    ["Shift(s)", shiftLabel],
    ["Catégorie d'arrêts (filtre)", categoryLabel ?? "Toutes catégories"],
    ["Poste (filtre graphique types)", posteFilterLabel?.trim() ? posteFilterLabel : "Tous les postes"],
    ["UEP", "Berceau"],
    ["Dénominateur % impact", "Σ objectifs H1–H8 (fiches production du périmètre)"],
  ];

  const wsCtx = XLSX.utils.aoa_to_sheet(contextAoa);
  wsCtx["!cols"] = [{ wch: 28 }, { wch: 72 }];
  XLSX.utils.book_append_sheet(wb, wsCtx, "Contexte");

  const headers = [
    "#",
    "Type d'arrêt",
    "Moyen",
    "% total (A1+A3)",
    "% A1",
    "% A3",
    "Minutes A1",
    "Minutes A3",
    "Cumulé %",
  ];
  const body = rows.map((r, i) => {
    const total = round2(Number(r.pctA1 || 0) + Number(r.pctA3 || 0));
    return [
      i + 1,
      r.panne_type_nom || r.typeArret,
      r.moyen_nom?.trim() ? r.moyen_nom : "—",
      total,
      round2(Number(r.pctA1 || 0)),
      round2(Number(r.pctA3 || 0)),
      round2(Number(r.minutesA1 ?? 0)),
      round2(Number(r.minutesA3 ?? 0)),
      round2(Number(r.cumulePercent || 0)),
    ];
  });
  const wsData = XLSX.utils.aoa_to_sheet([headers, ...body]);
  wsData["!cols"] = [
    { wch: 4 },
    { wch: 28 },
    { wch: 24 },
    { wch: 18 },
    { wch: 10 },
    { wch: 10 },
    { wch: 14 },
    { wch: 14 },
    { wch: 12 },
  ];
  XLSX.utils.book_append_sheet(wb, wsData, "Pareto types");

  const slug = (categorySlug ?? "toutes")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "")
    .slice(0, 24);
  const fname = `pareto_types_arrets_${jourIso}_${slug}.xlsx`;
  XLSX.writeFile(wb, fname);
}
