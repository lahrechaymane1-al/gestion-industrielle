import { Box, Paper, Stack, Typography } from "@mui/material";
import { alpha, useTheme, type Theme } from "@mui/material/styles";
import { useId, useMemo, type ReactNode } from "react";
import type { CartesianTickItem } from "recharts";
import { designTokens } from "../../theme/designTokens";

export const CHART_OVERFLOW_SX = {
  "& .recharts-wrapper": { overflow: "visible" },
  "& .recharts-surface": { overflow: "visible" },
} as const;

const PARETO_X_TICK_SEP = " — ";

export type ChartTheme = ReturnType<typeof buildChartTheme>;

function buildChartTheme(theme: Theme, uid: string) {
  const primary = theme.palette.primary.main;
  const secondary = theme.palette.secondary.main;
  const warning = theme.palette.warning.main;
  const paretoLine = alpha(theme.palette.error.main, 0.92);
  const danger = theme.palette.error.main;
  /** RO / NRO : tons alignés sur le thème sombre (lisibles, non néon). */
  const seriesGreen = designTokens.accent.emerald;
  const seriesRed = theme.palette.error.main;
  const seriesGrey = alpha(designTokens.brand.text, 0.5);
  const tickFill = alpha(designTokens.brand.text, 0.7);
  const gridStroke = alpha(designTokens.brand.sky, 0.12);

  const ids = {
    barPrimary: `${uid}-grad-bar-primary`,
    barSecondary: `${uid}-grad-bar-secondary`,
    barAccent: `${uid}-grad-bar-accent`,
    barPrimaryTop: `${uid}-grad-bar-primary-top`,
    areaPrimary: `${uid}-grad-area-primary`,
    areaSecondary: `${uid}-grad-area-secondary`,
    areaWarning: `${uid}-grad-area-warning`,
    /** Même palette que Pareto impact (barres bleues dashboard Berceau). */
    areaImpact: `${uid}-grad-area-impact`,
    paretoLine: `${uid}-grad-pareto-line`,
    paretoGlow: `${uid}-pareto-glow`,
    barGreen: `${uid}-grad-bar-green`,
    barOrange: `${uid}-grad-bar-orange`,
    barRed: `${uid}-grad-bar-red`,
    areaTrendGreen: `${uid}-grad-area-trend-green`,
    areaTrendRed: `${uid}-grad-area-trend-red`,
    lineGlowGreen: `${uid}-line-glow-green`,
    lineGlowRed: `${uid}-line-glow-red`,
  };

  return {
    uid,
    ids,
    colors: {
      primary,
      secondary,
      warning,
      paretoLine,
      danger,
      tickFill,
      gridStroke,
      seriesGreen,
      seriesRed,
      seriesGrey,
    },
    grid: {
      strokeDasharray: "2 8",
      stroke: gridStroke,
      vertical: false as const,
    },
    axis: {
      tick: { fill: tickFill, fontSize: 11, fontWeight: 600 as const },
      axisLine: false as const,
      tickLine: false as const,
    },
    margins: {
      pareto: { top: 28, right: 48, left: 4, bottom: 152 },
      paretoPoste: { top: 28, right: 48, left: 4, bottom: 148 },
      sparkline: { top: 6, right: 8, left: -6, bottom: 0 },
      trendArea: { top: 36, right: 28, left: 8, bottom: 88 },
      area: { top: 12, right: 16, left: 0, bottom: 0 },
      homeTrend: { top: 14, right: 14, left: 4, bottom: 44 },
      bar: { top: 16, right: 20, left: 8, bottom: 72 },
    },
    animation: {
      barDuration: 720,
      barEasing: "ease-out" as const,
      lineDuration: 900,
    },
    reference80: {
      stroke: alpha(danger, 0.85),
      strokeDasharray: "8 5",
      labelFill: alpha(danger, 0.95),
    },
    projection: {
      stroke: alpha(paretoLine, 0.28),
      strokeDasharray: "4 6",
    },
    tooltip: {
      /** Recharts default bar cursor is light gray — unreadable on dark UI */
      barCursor: {
        fill: alpha(theme.palette.common.white, 0.06),
        stroke: alpha(theme.palette.divider, 0.35),
        strokeWidth: 1,
      },
    },
  };
}

export function useChartTheme() {
  const theme = useTheme();
  const uid = useId().replace(/:/g, "");
  return useMemo(() => buildChartTheme(theme, uid), [theme, uid]);
}

/** Courbes / zones Berceau alignées sur le bleu Pareto impact (ciel + teal). */
export function impactSeriesStyle(chart: ChartTheme) {
  const stroke = designTokens.brand.skySoft;
  const strokeMuted = designTokens.brand.sky;
  return {
    stroke,
    strokeMuted,
    areaFill: `url(#${chart.ids.areaImpact})`,
    barFill: `url(#${chart.ids.barPrimary})`,
    dotFill: strokeMuted,
    glow: `drop-shadow(0 3px 10px ${alpha(designTokens.brand.sky, 0.42)})`,
    cardAccent: strokeMuted,
    chipColor: "primary" as const,
  };
}

export function ChartGradientDefs({ chart }: { chart: ChartTheme }) {
  const { ids, colors } = chart;
  return (
    <defs>
      <linearGradient id={ids.barPrimary} x1="0" y1="1" x2="0" y2="0">
        <stop offset="0%" stopColor={alpha(designTokens.brand.sky, 0.35)} />
        <stop offset="55%" stopColor={alpha(designTokens.accent.teal, 0.65)} />
        <stop offset="100%" stopColor={alpha(designTokens.brand.skySoft, 0.95)} />
      </linearGradient>
      <linearGradient id={ids.barSecondary} x1="0" y1="1" x2="0" y2="0">
        <stop offset="0%" stopColor={alpha(colors.secondary, 0.32)} />
        <stop offset="100%" stopColor={alpha(colors.secondary, 0.88)} />
      </linearGradient>
      <linearGradient id={ids.barAccent} x1="0" y1="1" x2="0" y2="0">
        <stop offset="0%" stopColor={alpha(colors.warning, 0.28)} />
        <stop offset="100%" stopColor={alpha(colors.warning, 0.85)} />
      </linearGradient>
      <linearGradient id={ids.areaPrimary} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={alpha(colors.primary, 0.42)} />
        <stop offset="88%" stopColor={alpha(colors.primary, 0.02)} />
      </linearGradient>
      <linearGradient id={ids.areaSecondary} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={alpha(colors.secondary, 0.38)} />
        <stop offset="88%" stopColor={alpha(colors.secondary, 0.02)} />
      </linearGradient>
      <linearGradient id={ids.areaWarning} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={alpha(colors.warning, 0.4)} />
        <stop offset="88%" stopColor={alpha(colors.warning, 0.02)} />
      </linearGradient>
      <linearGradient id={ids.areaImpact} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={alpha(designTokens.brand.skySoft, 0.5)} />
        <stop offset="48%" stopColor={alpha(designTokens.accent.teal, 0.24)} />
        <stop offset="100%" stopColor={alpha(designTokens.brand.sky, 0.04)} />
      </linearGradient>
      <linearGradient id={ids.paretoLine} x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stopColor={alpha(colors.seriesRed, 0.55)} />
        <stop offset="100%" stopColor={colors.seriesRed} />
      </linearGradient>
      <linearGradient id={ids.barGreen} x1="0" y1="1" x2="0" y2="0">
        <stop offset="0%" stopColor={alpha(colors.seriesGreen, 0.35)} />
        <stop offset="55%" stopColor={alpha(colors.seriesGreen, 0.78)} />
        <stop offset="100%" stopColor={alpha(colors.seriesGreen, 0.98)} />
      </linearGradient>
      <linearGradient id={ids.barOrange} x1="0" y1="1" x2="0" y2="0">
        <stop offset="0%" stopColor={alpha("#f59e0b", 0.32)} />
        <stop offset="55%" stopColor={alpha("#f59e0b", 0.75)} />
        <stop offset="100%" stopColor={alpha("#fbbf24", 0.95)} />
      </linearGradient>
      <linearGradient id={ids.barRed} x1="0" y1="1" x2="0" y2="0">
        <stop offset="0%" stopColor={alpha(colors.seriesRed, 0.32)} />
        <stop offset="55%" stopColor={alpha(colors.seriesRed, 0.72)} />
        <stop offset="100%" stopColor={alpha(colors.seriesRed, 0.95)} />
      </linearGradient>
      <linearGradient id={ids.areaTrendGreen} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={alpha(colors.seriesGreen, 0.32)} />
        <stop offset="72%" stopColor={alpha(colors.seriesGreen, 0.08)} />
        <stop offset="100%" stopColor={alpha(colors.seriesGreen, 0)} />
      </linearGradient>
      <linearGradient id={ids.areaTrendRed} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={alpha(colors.seriesRed, 0.28)} />
        <stop offset="72%" stopColor={alpha(colors.seriesRed, 0.07)} />
        <stop offset="100%" stopColor={alpha(colors.seriesRed, 0)} />
      </linearGradient>
      <filter id={ids.paretoGlow} x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="2" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <filter id={ids.lineGlowGreen} x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="1.2" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <filter id={ids.lineGlowRed} x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="1.2" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>
  );
}

function splitParetoCategoryLabel(raw: string): string[] {
  const s = String(raw ?? "").trim();
  if (!s) return [""];
  if (!s.includes(PARETO_X_TICK_SEP)) return [s];
  const parts = s.split(PARETO_X_TICK_SEP).map((p) => p.trim()).filter(Boolean);
  return parts.length ? parts.slice(0, 3) : [s];
}

export function ParetoCategoryAxisTick(props: {
  x?: number | string;
  y?: number | string;
  payload?: CartesianTickItem;
  fill?: string;
}) {
  const xi = Number(props.x ?? 0);
  const yi = Number(props.y ?? 0);
  const { payload, fill = alpha(designTokens.brand.text, 0.62) } = props;
  const raw = typeof payload?.value === "string" ? payload.value : String(payload?.value ?? "");
  const lines = splitParetoCategoryLabel(raw);
  return (
    <g transform={`translate(${xi},${yi})`}>
      <text textAnchor="end" fill={fill} fontSize={10} fontWeight={600} transform="rotate(-36)">
        {lines.map((line, idx) => (
          <tspan key={idx} x={0} dy={idx === 0 ? 0 : 11} opacity={idx === 0 ? 1 : 0.82}>
            {line}
          </tspan>
        ))}
      </text>
    </g>
  );
}

type TooltipRow = { label: string; value: string; accent?: string };

function GlassTooltipShell({
  title,
  rows,
}: {
  title?: string;
  rows: TooltipRow[];
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        px: 1.75,
        py: 1.25,
        borderRadius: 2,
        minWidth: 168,
        bgcolor: alpha(designTokens.brand.slate, 0.94),
        border: `1px solid ${designTokens.glass.borderStrong}`,
        boxShadow: `${designTokens.shadow.card}, 0 0 40px ${alpha(designTokens.brand.sky, 0.18)}`,
        backdropFilter: designTokens.glass.blur,
      }}
    >
      {title ? (
        <Typography variant="subtitle2" fontWeight={800} sx={{ mb: 0.75, lineHeight: 1.35, pr: 0.5 }}>
          {title}
        </Typography>
      ) : null}
      <Stack spacing={0.35}>
        {rows.map((row) => (
          <Stack key={row.label} direction="row" justifyContent="space-between" spacing={2} alignItems="baseline">
            <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.4 }}>
              {row.label}
            </Typography>
            <Typography
              variant="body2"
              fontWeight={700}
              sx={{ color: row.accent ?? "text.primary", fontVariantNumeric: "tabular-nums" }}
            >
              {row.value}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Paper>
  );
}

export function ParetoComboTooltip({
  active,
  payload,
  label,
  chart,
}: {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number | string; dataKey?: string; payload?: { tempsArretMin?: number } }>;
  label?: string;
  chart: ChartTheme;
}) {
  if (!active || !payload?.length) return null;
  const total = Number(
    payload.find((p) => p.dataKey === "totalPct")?.value ??
      payload.find((p) => String(p.name ?? "").includes("perte"))?.value ??
      0
  );
  const cumul = Number(payload.find((p) => p.dataKey === "cumulePercent")?.value ?? 0);
  const mins = Number(payload[0]?.payload?.tempsArretMin ?? 0);
  const rows: TooltipRow[] = [
    { label: "Impact", value: `${total.toFixed(2)} %`, accent: chart.colors.primary },
    { label: "Cumulé Pareto", value: `${cumul.toFixed(1)} %`, accent: "#ffffff" },
  ];
  if (mins > 0) rows.push({ label: "Minutes", value: `${mins.toFixed(0)} min` });
  return <GlassTooltipShell title={label} rows={rows} />;
}

/** Compatible with Recharts `TooltipPayload` entries. */
export type SparklineTooltipPayloadItem = Readonly<{
  name?: string | number;
  value?: number | string | readonly (string | number)[];
}>;

export function SparklineTooltip({
  active,
  payload,
  label,
  chart,
  valueLabel = "Valeur",
  accentColor,
}: {
  active?: boolean;
  payload?: readonly SparklineTooltipPayloadItem[];
  label?: string | number;
  chart: ChartTheme;
  valueLabel?: string;
  accentColor?: string;
}) {
  if (!active || !payload?.length) return null;
  const raw = payload[0]?.value;
  const scalar = Array.isArray(raw) ? raw[0] : raw;
  const v = Number(scalar ?? 0);
  const title = label != null && label !== "" ? String(label) : undefined;
  return (
    <GlassTooltipShell
      title={title}
      rows={[
        {
          label: valueLabel,
          value: Number.isFinite(v) ? `${v.toFixed(1)} %` : "—",
          accent: accentColor ?? chart.colors.primary,
        },
      ]}
    />
  );
}

export function StackedA1A3Tooltip({
  active,
  payload,
  label,
  chart,
}: {
  active?: boolean;
  payload?: Array<{ dataKey?: string; value?: number | string; payload?: { minutesA1?: number; minutesA3?: number } }>;
  label?: string;
  chart: ChartTheme;
}) {
  if (!active || !payload?.length) return null;
  const a1 = Number(payload.find((p) => p.dataKey === "pctA1")?.value ?? 0);
  const a3 = Number(payload.find((p) => p.dataKey === "pctA3")?.value ?? 0);
  const row = payload[0]?.payload;
  const mA1 = Number(row?.minutesA1 ?? 0);
  const mA3 = Number(row?.minutesA3 ?? 0);
  return (
    <GlassTooltipShell
      title={label}
      rows={[
        { label: "A1", value: `${a1.toFixed(2)} % · ${mA1} min`, accent: chart.colors.primary },
        { label: "A3", value: `${a3.toFixed(2)} % · ${mA3} min`, accent: chart.colors.secondary },
      ]}
    />
  );
}

export function TrendAreaTooltip({
  active,
  payload,
  label,
  chart,
}: {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number | string; color?: string }>;
  label?: string;
  chart?: ChartTheme;
}) {
  if (!active || !payload?.length) return null;
  const rows: TooltipRow[] = payload
    .filter((p) => p.value != null && p.name)
    .map((p) => {
      const raw = String(p.color ?? "");
      const accent =
        chart && raw.includes("url(")
          ? resolveChartSwatchColor({ value: p.name, color: p.color }, chart)
          : raw && !raw.includes("url(")
            ? raw
            : undefined;
      return {
        label: String(p.name),
        value: typeof p.value === "number" ? p.value.toLocaleString("fr-FR") : String(p.value),
        accent,
      };
    });
  return <GlassTooltipShell title={label} rows={rows} />;
}

type LegendEntry = { value?: string; color?: string };

/** Recharts may pass `url(#gradientId)` as color — MUI `alpha()` only accepts real colors. */
export function resolveChartSwatchColor(
  entry: LegendEntry,
  chart: ChartTheme
): string {
  const raw = String(entry.color ?? "");
  if (raw && !raw.includes("url(")) return raw;
  const label = String(entry.value ?? "").toLowerCase();
  if (label.includes("sortie")) return chart.colors.secondary;
  if (label.includes("entree") || label.includes("entrée")) return chart.colors.primary;
  if (label.includes("cumul")) return chart.colors.paretoLine;
  if (label.includes("stock fin a3") || (label.includes("a3") && label.includes("stock"))) {
    return chart.colors.seriesGrey;
  }
  if (label.includes("stock fin a1") || (label.includes("a1") && label.includes("stock"))) {
    return designTokens.brand.skySoft;
  }
  if (label.includes("% a3") || label.endsWith("a3")) return chart.colors.seriesGrey;
  if (label.includes("nro") || label.includes("cumul")) return chart.colors.seriesRed;
  if (label.includes("ccb")) return chart.colors.seriesGrey;
  if (label.includes("arret") && label.includes("berceau")) {
    return designTokens.brand.skySoft;
  }
  if (label.includes("berceau") || label.includes("ro") || label.includes("impact")) {
    return designTokens.brand.skySoft;
  }
  if (label.includes("arret")) return chart.colors.seriesRed;
  return chart.colors.seriesGreen;
}

export function StockEntreeSortieTooltip({
  active,
  payload,
  label,
  chart,
  stockLine,
}: {
  active?: boolean;
  payload?: Array<{
    name?: string;
    value?: number | string;
    dataKey?: string;
    payload?: { date?: string };
  }>;
  label?: string;
  chart: ChartTheme;
  /** A1 or A3 — labels entree/sortie for that diversity stock */
  stockLine?: "A1" | "A3" | "LHD" | "RHD";
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  const title = point?.date
    ? new Date(`${point.date}T12:00:00`).toLocaleDateString("fr-FR", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : label;
  const entreeLabel = stockLine ? `Entree stock ${stockLine}` : "Entree stock";
  const sortieLabel = stockLine ? `Sortie montage (stock ${stockLine})` : "Sortie montage";
  const rows: TooltipRow[] = payload.map((p) => {
    const key = String(p.dataKey ?? "");
    const isEntree = key === "entree";
    const seriesName = String(p.name ?? "");
    return {
      label: seriesName || (isEntree ? entreeLabel : sortieLabel),
      value: Number(p.value ?? 0).toLocaleString("fr-FR"),
      accent: isEntree ? chart.colors.primary : chart.colors.secondary,
    };
  });
  return <GlassTooltipShell title={title} rows={rows} />;
}

export function ChartLegendContent({
  payload,
  chart,
}: {
  payload?: LegendEntry[];
  chart: ChartTheme;
}) {
  if (!payload?.length) return null;
  return (
    <Box
      component="ul"
      sx={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        gap: 1,
        listStyle: "none",
        m: 0,
        p: 0,
        mt: 1,
      }}
    >
      {payload.map((entry) => {
        const swatch = resolveChartSwatchColor(entry, chart);
        return (
        <Box
          component="li"
          key={String(entry.value)}
          sx={{
            display: "inline-flex",
            alignItems: "center",
            gap: 0.75,
            px: 1.25,
            py: 0.35,
            borderRadius: 99,
            bgcolor: alpha(swatch, 0.08),
            border: `1px solid ${alpha(swatch, 0.22)}`,
          }}
        >
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              bgcolor: swatch,
              boxShadow: `0 0 10px ${alpha(swatch, 0.45)}`,
            }}
          />
          <Typography variant="caption" fontWeight={700} color="text.secondary">
            {entry.value}
          </Typography>
        </Box>
        );
      })}
    </Box>
  );
}

type ParetoBarShapeProps = {
  fill?: string;
  x?: number | string;
  y?: number | string;
  width?: number | string;
  height?: number | string;
};

const HISTO_ORANGE = "#f59e0b";

/** Dégradé verre pour barres RO/NRO selon la couleur seuil. */
export function histogramGradientId(chart: ChartTheme, solidColor: string): string {
  if (solidColor === chart.colors.seriesGreen || solidColor === designTokens.accent.emerald) {
    return chart.ids.barGreen;
  }
  if (solidColor === HISTO_ORANGE) return chart.ids.barOrange;
  return chart.ids.barRed;
}

export function paretoGradientBarShape(
  chart: ChartTheme,
  minHeightPx: number,
  minWidthPx: number,
  variant: "primary" | "green" = "primary"
) {
  const fillUrl = `url(#${variant === "green" ? chart.ids.barGreen : chart.ids.barPrimary})`;
  const glowColor = variant === "green" ? chart.colors.seriesGreen : chart.colors.primary;
  return glassBarRectShape({ fillUrl, glowColor, minHeightPx, minWidthPx });
}

/** Barres histogramme / Pareto — dégradé + ombre (effet verre). */
export function glassHistogramBarShape(
  chart: ChartTheme,
  minHeightPx: number,
  minWidthPx: number,
  dataKey: string,
  colorForValue: (pct: number) => string
) {
  return (props: ParetoBarShapeProps & { payload?: Record<string, unknown> }) => {
    const payload = props.payload ?? {};
    const pct = Number(payload[dataKey]);
    const glow = colorForValue(pct);
    const fillUrl = `url(#${histogramGradientId(chart, glow)})`;
    const selected = Boolean(payload.isSelected);
    return glassBarRectShape({
      fillUrl,
      glowColor: glow,
      minHeightPx,
      minWidthPx,
      stroke: selected ? alpha("#fff", 0.9) : undefined,
      strokeWidth: selected ? 2 : 0,
    })(props);
  };
}

function glassBarRectShape({
  fillUrl,
  glowColor,
  minHeightPx,
  minWidthPx,
  stroke,
  strokeWidth = 0,
}: {
  fillUrl: string;
  glowColor: string;
  minHeightPx: number;
  minWidthPx: number;
  stroke?: string;
  strokeWidth?: number;
}) {
  return (props: ParetoBarShapeProps) => {
    const x = Number(props.x ?? 0);
    const y = Number(props.y ?? 0);
    const width = Number(props.width ?? 0);
    const height = Number(props.height ?? 0);
    const w = Math.max(width, minWidthPx);
    const h = Math.max(height, minHeightPx);
    const xAdj = x + (width - w) / 2;
    const yAdj = y + height - h;
    return (
      <g>
        <rect
          x={xAdj}
          y={yAdj}
          width={w}
          height={h}
          fill={fillUrl}
          rx={6}
          ry={6}
          stroke={stroke}
          strokeWidth={strokeWidth}
          style={{ filter: `drop-shadow(0 4px 14px ${alpha(glowColor, 0.45)})` }}
        />
      </g>
    );
  };
}

/** Integer labels above bars — dark pill keeps values readable on screen and PNG export. */
export function barIntegerValueLabel(fill: string) {
  return (props: {
    x?: number | string;
    y?: number | string;
    width?: number | string;
    value?: unknown;
  }) => {
    const { x, y, width, value } = props;
    if (x == null || y == null || width == null || value == null) return null;
    const num = Number(value);
    if (!Number.isFinite(num) || num <= 0) return null;
    const cx = Number(x) + Number(width) / 2;
    const cy = Number(y) - 8;
    const text = num.toLocaleString("fr-FR");
    const pad = 4;
    const w = Math.max(text.length * 6.5 + pad * 2, 22);
    return (
      <g>
        <rect
          x={cx - w / 2}
          y={cy - 12}
          width={w}
          height={16}
          rx={4}
          fill="rgba(8, 12, 18, 0.78)"
        />
        <text x={cx} y={cy} fill={fill} fontSize={10} fontWeight={700} textAnchor="middle">
          {text}
        </text>
      </g>
    );
  };
}

export function paretoBarValueLabel(fill = "#d1fae5") {
  return (props: {
    x?: number | string;
    y?: number | string;
    width?: number | string;
    value?: unknown;
  }) => {
    const { x, y, width, value } = props;
    if (x == null || y == null || width == null || value == null) return null;
    const num = Number(value);
    if (!Number.isFinite(num)) return null;
    const cx = Number(x) + Number(width) / 2;
    const cy = Number(y) - 10;
    const text = `${num.toFixed(1)}%`;
    const pad = 4;
    const w = text.length * 6.2 + pad * 2;
    return (
      <g>
        <rect
          x={cx - w / 2}
          y={cy - 12}
          width={w}
          height={16}
          rx={4}
          fill="rgba(8, 12, 18, 0.72)"
        />
        <text x={cx} y={cy} fill={fill} fontSize={10} fontWeight={700} textAnchor="middle">
          {text}
        </text>
      </g>
    );
  };
}

export function trendHighlightDot(stroke: string) {
  return (props: { cx?: number; cy?: number; payload?: { isSelected?: boolean } }) => {
    const { cx = 0, cy = 0, payload } = props;
    if (cx == null || cy == null) return null;
    const selected = Boolean(payload?.isSelected);
    const r = selected ? 5.5 : 3;
    return (
      <g>
        {selected ? (
          <circle cx={cx} cy={cy} r={10} fill={alpha(stroke, 0.2)} stroke="none" />
        ) : null}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill={stroke}
          stroke={selected ? "#fff" : alpha(stroke, 0.35)}
          strokeWidth={selected ? 2.5 : 1}
        />
      </g>
    );
  };
}

export function ChartPlotFrame({
  children,
  accent = "primary",
  fill = false,
}: {
  children: ReactNode;
  accent?: "primary" | "secondary" | "warning" | "success" | "danger";
  /** When true, expands to fill a flex parent (dashboard trend cards). */
  fill?: boolean;
}) {
  const theme = useTheme();
  const chart = useChartTheme();
  const glow =
    accent === "success"
      ? chart.colors.seriesGreen
      : accent === "danger"
        ? chart.colors.seriesRed
        : accent === "secondary"
          ? theme.palette.secondary.main
          : accent === "warning"
            ? theme.palette.warning.main
            : theme.palette.primary.main;
  return (
    <Box
      sx={{
        position: "relative",
        borderRadius: 2.5,
        overflow: "hidden",
        bgcolor: alpha(designTokens.brand.ink, 0.72),
        backgroundImage: `radial-gradient(ellipse 80% 55% at 50% 0%, ${alpha(glow, 0.08)} 0%, transparent 62%)`,
        border: `1px solid ${designTokens.glass.border}`,
        ...(fill
          ? { flex: 1, minHeight: 0, display: "flex", flexDirection: "column", width: "100%" }
          : {}),
        ...CHART_OVERFLOW_SX,
      }}
    >
      {fill ? (
        <Box sx={{ flex: 1, minHeight: 0, width: "100%", display: "flex", flexDirection: "column" }}>
          {children}
        </Box>
      ) : (
        children
      )}
    </Box>
  );
}
