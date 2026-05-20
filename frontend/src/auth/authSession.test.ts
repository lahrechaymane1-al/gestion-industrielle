import { describe, expect, it } from "vitest";
import { lockedShiftFromMe } from "./authSession";

describe("lockedShiftFromMe", () => {
  it("returns undefined when not PSP", () => {
    expect(lockedShiftFromMe({ role: "RU", shift: "A" })).toBeUndefined();
    expect(lockedShiftFromMe(undefined)).toBeUndefined();
  });

  it("returns shift for PSP when set", () => {
    expect(lockedShiftFromMe({ role: "PSP", shift: "B" })).toBe("B");
  });

  it("returns undefined for PSP without shift", () => {
    expect(lockedShiftFromMe({ role: "PSP", shift: null })).toBeUndefined();
  });
});
