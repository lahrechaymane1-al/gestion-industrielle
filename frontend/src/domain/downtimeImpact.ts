import type { ProductionBerceauRow } from "../api/types";

/** Minutes divisor per diversity (aligned with `app.downtime_impact`). */
export const DIVISOR_A1 = 1.3;
export const DIVISOR_A3 = 1.8;

export type Diversity = "A1" | "A3";

/** Normalize API shape: une fiche ou plusieurs (même date/shift, lignes A1/A3 distinctes). */
export type ProductionRowsForImpact = ProductionBerceauRow | readonly ProductionBerceauRow[] | null | undefined;

export function parseDiversiteFromCause(cause: string | undefined | null): Diversity | null {
  const raw = (cause ?? "").trim();
  const m = raw.match(/\[diversite:(?<d>[^\]]+)\]/i);
  const d = String(m?.groups?.d ?? "").trim().toUpperCase();
  if (d === "A1" || d === "A3") return d;
  return null;
}

function asProductionRowList(prod: ProductionRowsForImpact): ProductionBerceauRow[] {
  if (prod == null) return [];
  return Array.isArray(prod) ? [...prod] : [prod];
}

export function lineFromProductionHour(row: ProductionBerceauRow | null | undefined, hour: number): Diversity | null {
  if (!row) return null;
  const h = Number(hour || 0);
  if (h === 1) return row.line_h1 ?? null;
  if (h === 2) return row.line_h2 ?? null;
  if (h === 3) return row.line_h3 ?? null;
  if (h === 4) return row.line_h4 ?? null;
  if (h === 5) return row.line_h5 ?? null;
  if (h === 6) return row.line_h6 ?? null;
  if (h === 7) return row.line_h7 ?? null;
  if (h === 8) return row.line_h8 ?? null;
  return null;
}

/** Diversity from `[diversite:…]` in cause, else première ligne horaire non nulle (aligné sur `app.downtime_impact`). */
export function resolveDiversityForImpact(
  cause: string | undefined | null,
  prodRows: ProductionRowsForImpact,
  hour: number
): Diversity | null {
  const fromCause = parseDiversiteFromCause(cause);
  if (fromCause) return fromCause;
  for (const r of asProductionRowList(prodRows)) {
    const ln = lineFromProductionHour(r, hour);
    if (ln) return ln;
  }
  return null;
}

function divisorForDiversity(d: Diversity | null): number | null {
  if (d === "A1") return DIVISOR_A1;
  if (d === "A3") return DIVISOR_A3;
  return null;
}

/**
 * Sum of `objectif_h1`…`objectif_h8` for hours where `line_h*` equals the given diversity.
 */
export function summedObjectifsFromProductionRow(row: ProductionBerceauRow | undefined | null): { A1: number; A3: number } {
  if (!row) return { A1: 0, A3: 0 };
  let a1 = 0;
  let a3 = 0;
  (
    [
      [1, row.line_h1, row.objectif_h1],
      [2, row.line_h2, row.objectif_h2],
      [3, row.line_h3, row.objectif_h3],
      [4, row.line_h4, row.objectif_h4],
      [5, row.line_h5, row.objectif_h5],
      [6, row.line_h6, row.objectif_h6],
      [7, row.line_h7, row.objectif_h7],
      [8, row.line_h8, row.objectif_h8],
    ] as const
  ).forEach(([, line, obj]) => {
    if (line === "A1") a1 += Number(obj || 0);
    if (line === "A3") a3 += Number(obj || 0);
  });
  return { A1: a1, A3: a3 };
}

/** Total objectif for one diversity on a single production row (sum over H1–H8 where line matches). */
export function totalObjectifForDiversity(row: ProductionBerceauRow | null | undefined, diversity: Diversity | null): number {
  if (!diversity) return 0;
  const sums = summedObjectifsFromProductionRow(row);
  return diversity === "A1" ? sums.A1 : sums.A3;
}

/** Somme des objectifs H1–H8 (toutes lignes) — volume shift pour repli dénominateur impact. */
export function sumAllHourlyObjectifs(row: ProductionBerceauRow | null | undefined): number {
  if (!row) return 0;
  let s = 0;
  for (let h = 1; h <= 8; h++) {
    const k = `objectif_h${h}` as keyof ProductionBerceauRow;
    s += Number(row[k] ?? 0);
  }
  return s;
}

/** Somme production_h1…h8 (alignée sur le modèle Django : volume = Σ créneaux). */
export function sumAllHourlyProduction(row: ProductionBerceauRow | null | undefined): number {
  if (!row) return 0;
  let s = 0;
  for (let h = 1; h <= 8; h++) {
    const k = `production_h${h}` as keyof ProductionBerceauRow;
    s += Number(row[k] ?? 0);
  }
  return s;
}

export function sumAllHourlyObjectifsAcrossRows(rows: ProductionBerceauRow[] | null | undefined): number {
  if (!rows?.length) return 0;
  return rows.reduce((acc, r) => acc + sumAllHourlyObjectifs(r), 0);
}

/** Sum of `totalObjectifForDiversity` across many production rows (e.g. all shifts for one day). */
export function totalObjectifForDiversityAcrossRows(
  rows: ProductionBerceauRow[] | null | undefined,
  diversity: Diversity | null
): number {
  if (!rows?.length || !diversity) return 0;
  return rows.reduce((sum, r) => sum + totalObjectifForDiversity(r, diversity), 0);
}

/**
 * Hourly objective for the affected slot (legacy / diagnostics).
 * L’impact % Berceau utilise la somme objectif du shift (H1–H8), voir {@link downtimeImpactPercent}.
 */
export function hourlyObjectiveForDiversity(
  prodRow: ProductionBerceauRow | null | undefined,
  hour: number,
  diversity: Diversity | null
): number {
  if (!prodRow || hour < 1 || hour > 8) return 0;
  const lineKey = `line_h${hour}` as keyof ProductionBerceauRow;
  const objKey = `objectif_h${hour}` as keyof ProductionBerceauRow;
  if (diversity && prodRow[lineKey] === diversity) {
    return Number(prodRow[objKey] ?? 0);
  }
  return Number(prodRow[objKey] ?? 0);
}

/**
 * (T.arret / diviseur) × (100 / objectif_shift)
 *
 * ``objectif_shift`` : somme des objectifs H1–H8 sur toutes les fiches production du jour (A+B+N).
 */
export function downtimeImpactPercent(
  tempsArretMin: number,
  diversity: Diversity | null,
  objectifShift: number
): number {
  const div = divisorForDiversity(diversity);
  if (div == null) return 0;
  const obj = Number(objectifShift || 0);
  if (obj <= 0) return 0;
  const t = Number(tempsArretMin || 0);
  if (t <= 0) return 0;
  return (t / div) * (100 / obj);
}

const PARETO_BUCKET_SEP = "\u0000";

export type ParetoTypeImpactRow = {
  cause: string;
  heure_production: number | string;
  temps_arret_min: number | string;
  panne_type_nom?: string | null;
  /** Moyen concerné (machine / outil) — différencie le même type d’arrêt sur plusieurs moyens. */
  moyen_nom?: string | null;
  /** Poste de travail — affiché avec le type et le moyen sur le Pareto types. */
  poste_nom?: string | null;
};

/**
 * Agrège les minutes d’arrêt par (type de panne × moyen × heure production 1–8 × diversité résolue),
 * puis applique une fois par seau : (Σ minutes / diviseur) × (100 / objectif_shift),
 * et somme les % par combinaison type + moyen (libellé « Type — Moyen » si le moyen est renseigné).
 */
export function addRowToParetoMinuteBuckets(
  buckets: Map<string, number>,
  row: ParetoTypeImpactRow,
  prodRows: ProductionRowsForImpact
): void {
  const hour = Number(row.heure_production ?? 0);
  if (hour < 1 || hour > 8) return;
  const div = resolveDiversityForImpact(row.cause, prodRows, hour);
  if (!div) return;
  const min = Number(row.temps_arret_min ?? 0);
  if (min <= 0) return;
  const typeName = String(row.panne_type_nom ?? "Type").trim() || "Type";
  const moyenSeg = String(row.moyen_nom ?? "").trim() || "__none__";
  const posteSeg = String(row.poste_nom ?? "").trim() || "__none__";
  const key = `${typeName}${PARETO_BUCKET_SEP}${moyenSeg}${PARETO_BUCKET_SEP}${posteSeg}${PARETO_BUCKET_SEP}${hour}${PARETO_BUCKET_SEP}${div}`;
  buckets.set(key, (buckets.get(key) ?? 0) + min);
}

export type ParetoTypeAggregate = {
  /** Libellé affiché : « Type — Moyen — Poste » (segments absents omis). */
  type: string;
  panne_type_nom: string;
  moyen_nom: string;
  poste_nom: string;
  pctA1: number;
  pctA3: number;
  minutesA1: number;
  minutesA3: number;
};

export function analyzeParetoMinuteBuckets(
  buckets: Map<string, number>,
  objectifShift: number
): { byType: Map<string, ParetoTypeAggregate>; totalPctA1: number; totalPctA3: number } {
  const denom = Number(objectifShift || 0);
  const byType = new Map<string, ParetoTypeAggregate>();
  let totalPctA1 = 0;
  let totalPctA3 = 0;
  for (const [key, minutes] of buckets) {
    const parts = key.split(PARETO_BUCKET_SEP);
    if (parts.length !== 5) continue;
    const [typeName, moyenSeg, posteSeg, , divStr] = parts;
    const div = divStr as Diversity;
    if (div !== "A1" && div !== "A3") continue;
    const pct = downtimeImpactPercent(minutes, div, denom);
    if (div === "A1") totalPctA1 += pct;
    else totalPctA3 += pct;
    const moyenNom = moyenSeg === "__none__" ? "" : moyenSeg;
    const posteNom = posteSeg === "__none__" ? "" : posteSeg;
    const displayType = [typeName, moyenNom, posteNom].filter(Boolean).join(" — ");
    if (!byType.has(displayType)) {
      byType.set(displayType, {
        type: displayType,
        panne_type_nom: typeName,
        moyen_nom: moyenNom,
        poste_nom: posteNom,
        pctA1: 0,
        pctA3: 0,
        minutesA1: 0,
        minutesA3: 0,
      });
    }
    const e = byType.get(displayType)!;
    if (div === "A1") {
      e.pctA1 += pct;
      e.minutesA1 += minutes;
    } else {
      e.pctA3 += pct;
      e.minutesA3 += minutes;
    }
  }
  return { byType, totalPctA1, totalPctA3 };
}

/** Row shape for poste buckets (poste name + champs alignés sur {@link ParetoTypeImpactRow}). */
export type ParetoPosteImpactRow = ParetoTypeImpactRow & { poste_nom?: string | null };

/**
 * Agrège les minutes par (poste × heure H1–8 × diversité), puis même formule que les types :
 * (Σ minutes / diviseur) × (100 / objectif_shift), somme des % par poste.
 */
export function addRowToParetoPosteMinuteBuckets(
  buckets: Map<string, number>,
  row: ParetoPosteImpactRow,
  prodRows: ProductionRowsForImpact
): void {
  const hour = Number(row.heure_production ?? 0);
  if (hour < 1 || hour > 8) return;
  const div = resolveDiversityForImpact(row.cause, prodRows, hour);
  if (!div) return;
  const min = Number(row.temps_arret_min ?? 0);
  if (min <= 0) return;
  const poste = String(row.poste_nom ?? "Poste").trim() || "Poste";
  const key = `${poste}${PARETO_BUCKET_SEP}${hour}${PARETO_BUCKET_SEP}${div}`;
  buckets.set(key, (buckets.get(key) ?? 0) + min);
}

export type ParetoPosteAggregate = {
  poste: string;
  pctA1: number;
  pctA3: number;
  minutesA1: number;
  minutesA3: number;
};

export function analyzeParetoPosteMinuteBuckets(
  buckets: Map<string, number>,
  objectifShift: number
): { byPoste: Map<string, ParetoPosteAggregate>; totalPctA1: number; totalPctA3: number } {
  const denom = Number(objectifShift || 0);
  const byPoste = new Map<string, ParetoPosteAggregate>();
  let totalPctA1 = 0;
  let totalPctA3 = 0;
  for (const [key, minutes] of buckets) {
    const parts = key.split(PARETO_BUCKET_SEP);
    if (parts.length !== 3) continue;
    const [posteName, , divStr] = parts;
    const div = divStr as Diversity;
    if (div !== "A1" && div !== "A3") continue;
    const pct = downtimeImpactPercent(minutes, div, denom);
    if (div === "A1") totalPctA1 += pct;
    else totalPctA3 += pct;
    if (!byPoste.has(posteName)) {
      byPoste.set(posteName, { poste: posteName, pctA1: 0, pctA3: 0, minutesA1: 0, minutesA3: 0 });
    }
    const e = byPoste.get(posteName)!;
    if (div === "A1") {
      e.pctA1 += pct;
      e.minutesA1 += minutes;
    } else {
      e.pctA3 += pct;
      e.minutesA3 += minutes;
    }
  }
  return { byPoste, totalPctA1, totalPctA3 };
}
