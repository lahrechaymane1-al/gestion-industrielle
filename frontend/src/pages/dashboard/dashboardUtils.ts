export function buildDashboardCsv(
  labels: string[],
  ro: number[],
  nro: number[],
  arrets: number[]
) {
  const rows = ["date,ro_percent,nro_percent,arrets_minutes"];
  labels.forEach((d, i) => rows.push(`${d},${ro[i] ?? 0},${nro[i] ?? 0},${arrets[i] ?? 0}`));
  return rows.join("\n");
}
