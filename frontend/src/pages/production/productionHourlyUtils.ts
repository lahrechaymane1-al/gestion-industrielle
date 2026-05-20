import { nroPercentFromRo } from "./productionMetrics";

export type HourlyValues = {
  production: number[];
  rebut: number[];
  retouche: number[];
  arret: number[];
};

export function computeHourlyTotals(values: HourlyValues, objectifGlobal: number) {
  const volume = values.production.reduce((s, v) => s + Math.max(0, Number(v || 0)), 0);
  const rebut = values.rebut.reduce((s, v) => s + Math.max(0, Number(v || 0)), 0);
  const retouche = values.retouche.reduce((s, v) => s + Math.max(0, Number(v || 0)), 0);
  const tempsArrets = values.arret.reduce((s, v) => s + Math.max(0, Number(v || 0)), 0);
  const roPercent = objectifGlobal > 0 ? Math.round((volume / objectifGlobal) * 10000) / 100 : 0;
  const nroTotal = Math.max((objectifGlobal || 0) - volume, 0);
  const nroPercent = nroPercentFromRo(roPercent);
  return { volume, rebut, retouche, tempsArrets, roPercent, nroTotal, nroPercent };
}

export function isHourLocked(isValidated: boolean, canOverrideValidated: boolean) {
  return isValidated && !canOverrideValidated;
}

