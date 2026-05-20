import { describe, expect, it } from "vitest";
import { buildDashboardCsv } from "./dashboardUtils";

describe("buildDashboardCsv", () => {
  it("builds csv rows aligned with labels", () => {
    const csv = buildDashboardCsv(["2026-04-27", "2026-04-28"], [82.5, 91], [17.5, 9], [44, 12]);
    const lines = csv.split("\n");
    expect(lines[0]).toBe("date,ro_percent,nro_percent,arrets_minutes");
    expect(lines[1]).toBe("2026-04-27,82.5,17.5,44");
    expect(lines[2]).toBe("2026-04-28,91,9,12");
  });
});
