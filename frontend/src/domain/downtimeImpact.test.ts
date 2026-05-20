import { describe, expect, it } from "vitest";
import type { ProductionBerceauRow } from "../api/types";
import {
  addRowToParetoMinuteBuckets,
  analyzeParetoMinuteBuckets,
  downtimeImpactPercent,
  hourlyObjectiveForDiversity,
  parseDiversiteFromCause,
  resolveDiversityForImpact,
  sumAllHourlyObjectifs,
  sumAllHourlyObjectifsAcrossRows,
  totalObjectifForDiversity,
} from "./downtimeImpact";

describe("downtimeImpact", () => {
  it("parses diversity prefix from cause", () => {
    expect(parseDiversiteFromCause("[diversite:A3] libellé")).toBe("A3");
    expect(parseDiversiteFromCause("pas de tag")).toBeNull();
  });

  it("computes impact per formula for A1 and A3", () => {
    expect(downtimeImpactPercent(13, "A1", 100)).toBeCloseTo(10, 5);
    expect(downtimeImpactPercent(18, "A3", 100)).toBeCloseTo(10, 5);
  });

  it("returns 0 for invalid inputs", () => {
    expect(downtimeImpactPercent(10, null, 100)).toBe(0);
    expect(downtimeImpactPercent(10, "A1", 0)).toBe(0);
    expect(downtimeImpactPercent(0, "A1", 50)).toBe(0);
  });

  it("resolves diversity from production row when cause has no tag", () => {
    const row = { line_h4: "A3" } as ProductionBerceauRow;
    expect(resolveDiversityForImpact("cause", row, 4)).toBe("A3");
  });

  it("scans all production rows for line at hour (same shift, plusieurs fiches)", () => {
    const sansLigneH4 = { line_h1: "A1" } as ProductionBerceauRow;
    const avecA3h4 = { line_h4: "A3" } as ProductionBerceauRow;
    expect(resolveDiversityForImpact("sans tag", [sansLigneH4, avecA3h4], 4)).toBe("A3");
  });

  it("totalObjectifForDiversity sums objectives for matching line hours", () => {
    const row = {
      line_h1: "A1",
      objectif_h1: 30,
      line_h2: "A1",
      objectif_h2: 70,
      line_h3: "A3",
      objectif_h3: 99,
    } as ProductionBerceauRow;
    expect(totalObjectifForDiversity(row, "A1")).toBe(100);
    expect(totalObjectifForDiversity(row, "A3")).toBe(99);
  });

  it("hourlyObjectiveForDiversity returns objective for the affected hour", () => {
    const row = {
      line_h2: "A1",
      objectif_h2: 120,
    } as ProductionBerceauRow;
    expect(hourlyObjectiveForDiversity(row, 2, "A1")).toBe(120);
    expect(hourlyObjectiveForDiversity(row, 2, "A3")).toBe(120);
    expect(hourlyObjectiveForDiversity(row, 0, "A1")).toBe(0);
  });

  it("pareto minute buckets merge same hour/type/diversity then one formula (linear)", () => {
    const prod = {
      line_h2: "A1",
      objectif_h2: 50,
      line_h3: "A3",
      objectif_h3: 40,
    } as ProductionBerceauRow;
    const objectifShift = sumAllHourlyObjectifs(prod);
    expect(objectifShift).toBe(90);
    const buckets = new Map<string, number>();
    addRowToParetoMinuteBuckets(buckets, { cause: "x", heure_production: 2, temps_arret_min: 13, panne_type_nom: "T" }, prod);
    addRowToParetoMinuteBuckets(buckets, { cause: "x", heure_production: 2, temps_arret_min: 13, panne_type_nom: "T" }, prod);
    const { byType } = analyzeParetoMinuteBuckets(buckets, objectifShift);
    const merged = downtimeImpactPercent(26, "A1", objectifShift);
    const sumTwo = downtimeImpactPercent(13, "A1", objectifShift) + downtimeImpactPercent(13, "A1", objectifShift);
    expect(byType.get("T")?.pctA1).toBeCloseTo(merged, 5);
    expect(byType.get("T")?.pctA1).toBeCloseTo(sumTwo, 5);
  });

  it("pareto uses objectif shift sum H1–H8 as denominator (tag A3, fiche lignes A1)", () => {
    const prod = {
      line_h1: "A1",
      objectif_h1: 50,
      line_h2: "A1",
      objectif_h2: 50,
    } as ProductionBerceauRow;
    const objA3 = totalObjectifForDiversity(prod, "A3");
    expect(objA3).toBe(0);
    const shiftTotal = sumAllHourlyObjectifs(prod);
    const buckets = new Map<string, number>();
    addRowToParetoMinuteBuckets(
      buckets,
      { cause: "[diversite:A3] x", heure_production: 2, temps_arret_min: 18, panne_type_nom: "T" },
      prod
    );
    const { byType } = analyzeParetoMinuteBuckets(buckets, shiftTotal);
    expect(byType.get("T")?.pctA3).toBeCloseTo(10, 5);
  });

  it("jour tous shifts : un seul objectif_jour = Σ objectifs H1–H8 de chaque fiche shift", () => {
    const ficheA = {
      objectif_h1: 100,
      line_h1: "A1",
      objectif_h2: 100,
      line_h2: "A1",
      objectif_h3: 100,
      line_h3: "A1",
      objectif_h4: 100,
      line_h4: "A1",
      objectif_h5: 100,
      line_h5: "A1",
      objectif_h6: 100,
      line_h6: "A1",
      objectif_h7: 100,
      line_h7: "A3",
      objectif_h8: 100,
      line_h8: "A3",
    } as ProductionBerceauRow;
    const ficheB = { ...ficheA, objectif_h1: 50, objectif_h7: 50 } as ProductionBerceauRow;
    const objectifJour = sumAllHourlyObjectifsAcrossRows([ficheA, ficheB]);
    expect(objectifJour).toBe(1500);

    const buckets = new Map<string, number>();
    addRowToParetoMinuteBuckets(
      buckets,
      { cause: "[diversite:A1] a", heure_production: 1, temps_arret_min: 13, panne_type_nom: "T" },
      [ficheA]
    );
    addRowToParetoMinuteBuckets(
      buckets,
      { cause: "[diversite:A3] b", heure_production: 7, temps_arret_min: 18, panne_type_nom: "T" },
      [ficheB]
    );
    const { byType } = analyzeParetoMinuteBuckets(buckets, objectifJour);
    const pctA1 = (13 / 1.3) * (100 / objectifJour);
    const pctA3 = (18 / 1.8) * (100 / objectifJour);
    expect(byType.get("T")?.pctA1).toBeCloseTo(pctA1, 5);
    expect(byType.get("T")?.pctA3).toBeCloseTo(pctA3, 5);
  });
});
