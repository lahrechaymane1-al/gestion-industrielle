import { api } from "../../api/client";

export type BerceauImpactDivisors = {
  divisor_a1: number;
  divisor_a3: number;
  effective_from: string;
  id?: number;
};

export type BerceauImpactSettingsResponse = {
  versions: BerceauImpactDivisors[];
  for_date?: BerceauImpactDivisors & { date: string };
};

export const BERCEAU_IMPACT_SETTINGS_QUERY_KEY = ["berceau-impact-settings"] as const;

export const DEFAULT_BERCEAU_DIVISOR_A1 = 1.3;
export const DEFAULT_BERCEAU_DIVISOR_A3 = 1.8;

export function factoryBerceauImpactDivisors(): BerceauImpactDivisors {
  return {
    effective_from: "2000-01-01",
    divisor_a1: DEFAULT_BERCEAU_DIVISOR_A1,
    divisor_a3: DEFAULT_BERCEAU_DIVISOR_A3,
  };
}

/** Diviseurs en vigueur à la date ISO (dernière version avec effective_from <= date). */
export function resolveBerceauDivisorsForDate(
  versions: BerceauImpactDivisors[],
  isoDate: string
): BerceauImpactDivisors {
  const sorted = [...versions].sort((a, b) => b.effective_from.localeCompare(a.effective_from));
  const match = sorted.find((v) => v.effective_from <= isoDate);
  return match ?? factoryBerceauImpactDivisors();
}

export async function fetchBerceauImpactSettings(date?: string): Promise<BerceauImpactSettingsResponse> {
  const params = date ? { date } : undefined;
  const { data } = await api.get<BerceauImpactSettingsResponse>("/api/berceau/impact-settings/", { params });
  return data;
}
