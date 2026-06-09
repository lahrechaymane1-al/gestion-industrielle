import { CCB_OBJECTIFS_HORAIRES } from "./ccbProductionConstants";

export type CcbProductionSettings = {
  objectif_h1: number;
  objectif_h2: number;
  objectif_h3: number;
  objectif_h4: number;
  objectif_h5: number;
  objectif_h6: number;
  objectif_h7: number;
  objectif_h8: number;
  objectif_total: number;
  updated_at?: string | null;
};

export const CCB_OBJECTIFS_SETTINGS_QUERY_KEY = ["ccb-production-settings"] as const;

const HOUR_KEYS = [
  "objectif_h1",
  "objectif_h2",
  "objectif_h3",
  "objectif_h4",
  "objectif_h5",
  "objectif_h6",
  "objectif_h7",
  "objectif_h8",
] as const;

export function factoryCcbObjectifsSettings(): CcbProductionSettings {
  const [h1, h2, h3, h4, h5, h6, h7, h8] = CCB_OBJECTIFS_HORAIRES;
  return {
    objectif_h1: h1,
    objectif_h2: h2,
    objectif_h3: h3,
    objectif_h4: h4,
    objectif_h5: h5,
    objectif_h6: h6,
    objectif_h7: h7,
    objectif_h8: h8,
    objectif_total: CCB_OBJECTIFS_HORAIRES.reduce((a, b) => a + b, 0),
  };
}

export function ccbObjectifsHourlyArray(settings: CcbProductionSettings): number[] {
  return HOUR_KEYS.map((k) => Number(settings[k] ?? 0));
}

export function sumCcbObjectifs(settings: Pick<CcbProductionSettings, (typeof HOUR_KEYS)[number]>): number {
  return HOUR_KEYS.reduce((s, k) => s + Number(settings[k] ?? 0), 0);
}

export function objectifHourFieldsFromSettings(
  settings: CcbProductionSettings
): Record<(typeof HOUR_KEYS)[number], number> {
  return {
    objectif_h1: settings.objectif_h1,
    objectif_h2: settings.objectif_h2,
    objectif_h3: settings.objectif_h3,
    objectif_h4: settings.objectif_h4,
    objectif_h5: settings.objectif_h5,
    objectif_h6: settings.objectif_h6,
    objectif_h7: settings.objectif_h7,
    objectif_h8: settings.objectif_h8,
  };
}
