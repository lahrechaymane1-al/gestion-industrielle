import { describe, expect, it } from "vitest";
import { autoTimeLabel, onModuleChange, onPosteChange } from "./alertePanneUtils";

describe("alertePanneUtils cascades", () => {
  it("resets poste and moyen when module changes", () => {
    const out = onModuleChange({ moduleId: 1, posteId: 10, moyenId: 100 }, 2);
    expect(out).toEqual({ moduleId: 2, posteId: undefined, moyenId: undefined });
  });

  it("resets moyen when poste changes", () => {
    const out = onPosteChange({ moduleId: 1, posteId: 10, moyenId: 100 }, 12);
    expect(out).toEqual({ moduleId: 1, posteId: 12, moyenId: undefined });
  });
});

describe("alertePanneUtils auto time label", () => {
  it("returns fallback label when data not found", () => {
    expect(autoTimeLabel(false, 0)).toContain("0");
  });

  it("returns populated label when data exists", () => {
    expect(autoTimeLabel(true, 15)).toContain("15");
  });
});
