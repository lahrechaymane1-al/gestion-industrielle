import { describe, expect, it } from "vitest";
import { computeHourlyTotals, isHourLocked } from "./productionHourlyUtils";

describe("computeHourlyTotals", () => {
  it("calculates volume/rebut/retouche/arret/RO/NRO", () => {
    const out = computeHourlyTotals(
      {
        production: [10, 20, 0, 0, 0, 0, 0, 0],
        rebut: [1, 2, 0, 0, 0, 0, 0, 0],
        retouche: [3, 0, 0, 0, 0, 0, 0, 0],
        arret: [5, 5, 0, 0, 0, 0, 0, 0],
      },
      100
    );
    expect(out.volume).toBe(30);
    expect(out.rebut).toBe(3);
    expect(out.retouche).toBe(3);
    expect(out.tempsArrets).toBe(10);
    expect(out.roPercent).toBe(30);
    expect(out.nroTotal).toBe(70);
    expect(out.nroPercent).toBe(70);
  });
});

describe("isHourLocked", () => {
  it("locks validated hour for PSP", () => {
    expect(isHourLocked(true, false)).toBe(true);
  });
  it("allows override for RU/ADMIN", () => {
    expect(isHourLocked(true, true)).toBe(false);
  });
});

