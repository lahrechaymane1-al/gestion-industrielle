import { api } from "../../api/client";
import type { ImpactDivisors } from "../../domain/downtimeImpact";

const HOUR_KEYS = [1, 2, 3, 4, 5, 6, 7, 8] as const;
export type BerceauHourKey = (typeof HOUR_KEYS)[number];

export type BerceauLineCode = "A1" | "A3";

export type BerceauProductionSettings = {
  objectif_a1_h1: number;
  objectif_a1_h2: number;
  objectif_a1_h3: number;
  objectif_a1_h4: number;
  objectif_a1_h5: number;
  objectif_a1_h6: number;
  objectif_a1_h7: number;
  objectif_a1_h8: number;
  objectif_a3_h1: number;
  objectif_a3_h2: number;
  objectif_a3_h3: number;
  objectif_a3_h4: number;
  objectif_a3_h5: number;
  objectif_a3_h6: number;
  objectif_a3_h7: number;
  objectif_a3_h8: number;
  objectif_total_a1?: number;
  objectif_total_a3?: number;
  divisor_a1: number;
  divisor_a3: number;
  divisor_effective_from: string;
  divisor_version_id?: number;
  divisor_resolved_for?: string;
  objectif_effective_from?: string;
  objectif_version_id?: number;
  objectif_resolved_for?: string;
  updated_at?: string | null;
  impact_versions?: Array<{
    id?: number;
    effective_from: string;
    divisor_a1: number;
    divisor_a3: number;
  }>;
  objectif_versions?: BerceauObjectifVersion[];
};

export type BerceauObjectifVersion = {
  id?: number;
  effective_from: string;
  objectif_a1_h1: number;
  objectif_a1_h2: number;
  objectif_a1_h3: number;
  objectif_a1_h4: number;
  objectif_a1_h5: number;
  objectif_a1_h6: number;
  objectif_a1_h7: number;
  objectif_a1_h8: number;
  objectif_a3_h1: number;
  objectif_a3_h2: number;
  objectif_a3_h3: number;
  objectif_a3_h4: number;
  objectif_a3_h5: number;
  objectif_a3_h6: number;
  objectif_a3_h7: number;
  objectif_a3_h8: number;
  objectif_total_a1?: number;
  objectif_total_a3?: number;
};

export const BERCEAU_PRODUCTION_SETTINGS_QUERY_KEY = ["berceau-production-settings"] as const;

export function factoryBerceauProductionSettings(): BerceauProductionSettings {
  return {
    objectif_a1_h1: 40,
    objectif_a1_h2: 45,
    objectif_a1_h3: 45,
    objectif_a1_h4: 45,
    objectif_a1_h5: 25,
    objectif_a1_h6: 45,
    objectif_a1_h7: 45,
    objectif_a1_h8: 45,
    objectif_a3_h1: 30,
    objectif_a3_h2: 33,
    objectif_a3_h3: 33,
    objectif_a3_h4: 33,
    objectif_a3_h5: 20,
    objectif_a3_h6: 33,
    objectif_a3_h7: 33,
    objectif_a3_h8: 33,
    divisor_a1: 1.3,
    divisor_a3: 1.8,
    divisor_effective_from: "2000-01-01",
  };
}

export function berceauObjectifKey(line: BerceauLineCode, hour: BerceauHourKey): keyof BerceauProductionSettings {
  const prefix = line === "A1" ? "objectif_a1" : "objectif_a3";
  return `${prefix}_h${hour}` as keyof BerceauProductionSettings;
}

export function objectifForHourFromSettings(
  settings: BerceauProductionSettings,
  line: BerceauLineCode,
  hour: BerceauHourKey
): number {
  return Number(settings[berceauObjectifKey(line, hour)] ?? 0);
}

/** Diversité horaire saisie ; ligne vide → A1 pour le pré-remplissage des objectifs. */
export function berceauLineCodeForHour(raw: string | undefined | null): BerceauLineCode {
  const v = String(raw ?? "").trim();
  return v === "A3" ? "A3" : "A1";
}

/** Applique les objectifs horaires du référentiel selon la diversité de chaque heure. */
export function buildHourlyObjectifsFromReferential(
  settings: BerceauProductionSettings,
  lineByHour: readonly (BerceauLineCode | string)[]
): Record<`objectif_h${BerceauHourKey}`, number> & { objectif: number } {
  const out = {} as Record<`objectif_h${BerceauHourKey}`, number>;
  let sum = 0;
  HOUR_KEYS.forEach((h, idx) => {
    const line = berceauLineCodeForHour(lineByHour[idx]);
    const key = `objectif_h${h}` as const;
    const val = objectifForHourFromSettings(settings, line, h);
    out[key] = val;
    sum += val;
  });
  return { ...out, objectif: sum };
}

export function sumBerceauObjectifsA1(settings: BerceauProductionSettings): number {
  return HOUR_KEYS.reduce((sum, h) => sum + objectifForHourFromSettings(settings, "A1", h), 0);
}

export function sumBerceauObjectifsA3(settings: BerceauProductionSettings): number {
  return HOUR_KEYS.reduce((sum, h) => sum + objectifForHourFromSettings(settings, "A3", h), 0);
}

export function divisorsFromBerceauSettings(
  settings: Pick<BerceauProductionSettings, "divisor_a1" | "divisor_a3">
): ImpactDivisors {
  return { divisor_a1: settings.divisor_a1, divisor_a3: settings.divisor_a3 };
}

/** Objectifs horaires en vigueur à la date ISO (versions enregistrées via la fiche production). */
export function resolveBerceauObjectifsForDate(
  settings: BerceauProductionSettings,
  isoDate: string
): BerceauProductionSettings {
  const versions = settings.objectif_versions ?? [];
  if (!versions.length) {
    return settings;
  }
  const sorted = [...versions].sort((a, b) => b.effective_from.localeCompare(a.effective_from));
  const match = sorted.find((v) => v.effective_from <= isoDate);
  if (!match) return factoryBerceauProductionSettings();
  return { ...settings, ...match };
}

/** Temps de cycle en vigueur à la date ISO (versions enregistrées via la fiche production). */
export function resolveBerceauCycleTimeForDate(
  settings: BerceauProductionSettings,
  isoDate: string
): ImpactDivisors {
  const versions = settings.impact_versions ?? [];
  if (!versions.length) {
    return divisorsFromBerceauSettings(settings);
  }
  const sorted = [...versions].sort((a, b) => b.effective_from.localeCompare(a.effective_from));
  const match = sorted.find((v) => v.effective_from <= isoDate);
  return match
    ? { divisor_a1: match.divisor_a1, divisor_a3: match.divisor_a3 }
    : divisorsFromBerceauSettings(factoryBerceauProductionSettings());
}

export async function fetchBerceauProductionSettings(date?: string): Promise<BerceauProductionSettings> {
  const params = date ? { date } : undefined;
  const { data } = await api.get<BerceauProductionSettings>("/api/berceau/production-settings/", { params });
  return data;
}

export async function saveBerceauProductionSettings(
  payload: BerceauProductionSettings
): Promise<BerceauProductionSettings> {
  const {
    divisor_effective_from: _eff,
    divisor_version_id: _vid,
    divisor_resolved_for: _res,
    impact_versions: _ivers,
    objectif_effective_from: _oeff,
    objectif_version_id: _ovid,
    objectif_resolved_for: _ores,
    objectif_versions: _overs,
    objectif_total_a1: _t1,
    objectif_total_a3: _t3,
    updated_at: _upd,
    ...body
  } = payload;
  const { data } = await api.patch<BerceauProductionSettings>("/api/berceau/production-settings/", body);
  return data;
}
