import type { ProductionBerceauRow, ProductionCCBRow } from "../../api/types";

const BERCEAU_HOURS = [1, 2, 3, 4, 5, 6, 7, 8] as const;
const CCB_HOURS = [1, 2, 3, 4, 5, 6, 7, 8] as const;

export function ccbReadLhd(row: ProductionCCBRow, h: number): number {
  const lhd = Number(row[`production_lhd_h${h}` as keyof ProductionCCBRow] ?? 0);
  if (lhd > 0) return lhd;
  const legacy = Number(row[`production_h${h}` as keyof ProductionCCBRow] ?? 0);
  const rhd = Number(row[`production_rhd_h${h}` as keyof ProductionCCBRow] ?? 0);
  return rhd > 0 ? 0 : legacy;
}

export function ccbReadRhd(row: ProductionCCBRow, h: number): number {
  return Number(row[`production_rhd_h${h}` as keyof ProductionCCBRow] ?? 0);
}

export function ccbHourVolume(row: ProductionCCBRow, h: number): number {
  return ccbReadLhd(row, h) + ccbReadRhd(row, h);
}

export function ccbEffectiveObjectif(row: ProductionCCBRow): number {
  const hourly = CCB_HOURS.reduce((sum, h) => sum + Number(row[`objectif_h${h}`] ?? 0), 0);
  return hourly > 0 ? hourly : Number(row.objectif || 0);
}

export function ccbEffectiveVolume(row: ProductionCCBRow): number {
  const hourly = CCB_HOURS.reduce((sum, h) => sum + ccbHourVolume(row, h), 0);
  return hourly > 0 ? hourly : Number(row.volume || 0);
}

export function ccbRoPercent(row: ProductionCCBRow): number {
  const o = ccbEffectiveObjectif(row);
  const v = ccbEffectiveVolume(row);
  if (o <= 0) return 0;
  return Math.round((v / o) * 10000) / 100;
}

export function ccbDiversityLabel(row: ProductionCCBRow): string {
  const lines = new Set<string>();
  for (const h of CCB_HOURS) {
    if (ccbReadLhd(row, h) > 0) lines.add("LHD");
    if (ccbReadRhd(row, h) > 0) lines.add("RHD");
  }
  if (lines.size) return [...lines].join(" / ");
  return row.line ?? "—";
}

/** Jour calendaire local (YYYY-MM-DD) — évite le décalage minuit UTC de `toISOString()`. */
export function isoCalendarToday(): string {
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** J-1 calendaire local (défaut dashboard Berceau). */
export function isoCalendarYesterday(): string {
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  d.setDate(d.getDate() - 1);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Objectif / volume alignés sur H1–H8 si renseignés (même logique que l’API Berceau). */
export function berceauEffectiveObjectif(row: ProductionBerceauRow): number {
  const hourly = BERCEAU_HOURS.reduce((sum, h) => sum + Number(row[`objectif_h${h}`] ?? 0), 0);
  return hourly > 0 ? hourly : Number(row.objectif || 0);
}

export function berceauEffectiveVolume(row: ProductionBerceauRow): number {
  const hourly = BERCEAU_HOURS.reduce((sum, h) => sum + Number(row[`production_h${h}`] ?? 0), 0);
  return hourly > 0 ? hourly : Number(row.volume || 0);
}

export function berceauRoPercent(row: ProductionBerceauRow): number {
  const o = berceauEffectiveObjectif(row);
  const v = berceauEffectiveVolume(row);
  if (o <= 0) return 0;
  return Math.round((v / o) * 10000) / 100;
}

/** NRO % = complément du RO % (aligné dashboard / API trend). */
export function nroPercentFromRo(roPercent: number): number {
  const ro = Number(roPercent);
  if (!Number.isFinite(ro)) return 0;
  return Math.max(0, Math.round((100 - ro) * 100) / 100);
}

export function nroPercentFromRow(row: { ro_percent?: number | null }): number {
  return nroPercentFromRo(Number(row.ro_percent ?? 0));
}

export function formatPercentFr(value: number | null | undefined, digits = 1): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${value.toFixed(digits)} %`;
}

/** Date complète pour graphiques tendance (jour, mois, année). */
export function formatTrendAxisDate(iso: string): string {
  try {
    return new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  } catch {
    return iso.slice(0, 10);
  }
}

export function formatDateGroupLabel(iso: string): string {
  try {
    return new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString("fr-FR", {
      weekday: "short",
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  } catch {
    return iso.slice(0, 10);
  }
}
