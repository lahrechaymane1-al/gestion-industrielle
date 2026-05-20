import html2canvas from "html2canvas";

export async function exportElementPng(target: HTMLElement | null, filename: string) {
  if (!target) return;
  const canvas = await html2canvas(target, {
    backgroundColor: "#0b1325",
    scale: 2,
    useCORS: true,
  });
  const url = canvas.toDataURL("image/png");
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
}

export function downloadTextFile(filename: string, content: string, mime = "text/csv;charset=utf-8") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function csvCell(value: string) {
  if (/[",\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

export function buildRoNroTrendCsv(
  rows: { iso: string; dateLabel: string; ro: number; nroPct: number }[]
) {
  const lines = ["date_iso,date,indicateur,valeur_percent"];
  for (const row of rows) {
    const date = csvCell(row.dateLabel);
    lines.push(`${row.iso},${date},RO,${row.ro.toFixed(1)}`);
    lines.push(`${row.iso},${date},NRO,${row.nroPct.toFixed(1)}`);
  }
  return lines.join("\n");
}
