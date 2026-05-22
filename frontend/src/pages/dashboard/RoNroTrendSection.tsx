import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import ImageOutlinedIcon from "@mui/icons-material/ImageOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { useRef, type RefObject } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  LabelList,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ChartGradientDefs,
  ChartPlotFrame,
  CHART_OVERFLOW_SX,
  glassHistogramBarShape,
  SparklineTooltip,
  useChartTheme,
  type ChartTheme,
} from "../../components/charts";
import { SafeResponsiveContainer } from "../../components/SafeResponsiveContainer";
import { designTokens } from "../../theme/designTokens";
import { exportElementPng } from "./dashboardExport";

const { glass, brand } = designTokens;

const RO_BAR_GREEN = designTokens.accent.emerald;
const RO_BAR_ORANGE = "#f59e0b";
const RO_BAR_RED = "#ef4444";

const NRO_BAR_GREEN = designTokens.accent.emerald;
const NRO_BAR_ORANGE = "#f59e0b";
const NRO_BAR_RED = "#ef4444";

/** RO : > 80 % vert ; 70–80 % orange ; < 70 % rouge. */
export function roHistogramBarColor(pct: number): string {
  const v = Number(pct);
  if (!Number.isFinite(v)) return RO_BAR_RED;
  if (v > 80) return RO_BAR_GREEN;
  if (v >= 70) return RO_BAR_ORANGE;
  return RO_BAR_RED;
}

/** NRO : > 30 % rouge ; 20–30 % orange ; < 20 % vert. */
export function nroHistogramBarColor(pct: number): string {
  const v = Number(pct);
  if (!Number.isFinite(v)) return NRO_BAR_GREEN;
  if (v > 30) return NRO_BAR_RED;
  if (v >= 20) return NRO_BAR_ORANGE;
  return NRO_BAR_GREEN;
}

export type RoNroDayStatus = "good" | "medium" | "bad" | "unknown";

export function roDayStatus(pct: number | null | undefined): RoNroDayStatus {
  const v = Number(pct);
  if (!Number.isFinite(v)) return "unknown";
  if (v > 80) return "good";
  if (v >= 70) return "medium";
  return "bad";
}

export function nroDayStatus(pct: number | null | undefined): RoNroDayStatus {
  const v = Number(pct);
  if (!Number.isFinite(v)) return "unknown";
  if (v > 30) return "bad";
  if (v >= 20) return "medium";
  return "good";
}

const STATUS_UI: Record<
  RoNroDayStatus,
  { ariaLabel: string; Icon: typeof CheckCircleOutlineIcon; color: string }
> = {
  good: { ariaLabel: "Situation favorable", Icon: CheckCircleOutlineIcon, color: RO_BAR_GREEN },
  medium: { ariaLabel: "Situation moyenne", Icon: WarningAmberOutlinedIcon, color: RO_BAR_ORANGE },
  bad: { ariaLabel: "Situation défavorable", Icon: ErrorOutlineIcon, color: RO_BAR_RED },
  unknown: {
    ariaLabel: "Situation non disponible",
    Icon: WarningAmberOutlinedIcon,
    color: alpha("#fff", 0.45),
  },
};

function DayKpiStatusIcon({ status, accentColor }: { status: RoNroDayStatus; accentColor: string }) {
  const ui = STATUS_UI[status];
  const Icon = ui.Icon;
  const accent = status !== "unknown" ? accentColor : ui.color;
  return (
    <Box
      role="img"
      aria-label={ui.ariaLabel}
      sx={{
        p: 1,
        borderRadius: 2,
        bgcolor: alpha(accent, 0.14),
        border: `1px solid ${alpha(accent, 0.4)}`,
        display: "grid",
        placeItems: "center",
        flexShrink: 0,
        boxShadow: `0 0 20px ${alpha(accent, 0.25)}`,
      }}
    >
      <Icon sx={{ color: accent, fontSize: 28 }} />
    </Box>
  );
}

export type RoNroTrendPoint = {
  label: string;
  iso: string;
  ro: number;
  nroPct: number;
  isSelected: boolean;
};

type TrendChartCardProps = {
  title: string;
  value: string;
  dayPct: number | null;
  dayStatus: RoNroDayStatus;
  indicateur: "RO" | "NRO";
  accent: "success" | "danger";
  dataKey: "ro" | "nroPct";
  valueLabel: string;
  data: RoNroTrendPoint[];
  loading: boolean;
  error: boolean;
  chart: ChartTheme;
  exportRef: RefObject<HTMLDivElement | null>;
  onExportPng: () => void;
  barColorForValue: (pct: number) => string;
};

function TrendChartCard({
  title,
  value,
  dayPct,
  dayStatus,
  indicateur,
  accent: _accent,
  dataKey,
  valueLabel,
  data,
  loading,
  error,
  chart,
  exportRef,
  onExportPng,
  barColorForValue,
}: TrendChartCardProps) {
  const theme = useTheme();
  const headerNeutral = alpha(brand.slate, 0.92);
  const dayAccent =
    dayPct != null && Number.isFinite(dayPct) ? barColorForValue(dayPct) : STATUS_UI[dayStatus].color;

  return (
    <Box ref={exportRef} sx={{ flex: 1, minWidth: 0 }}>
      <Paper
        elevation={0}
        sx={{
          borderRadius: 3,
          overflow: "hidden",
          border: `1px solid ${glass.border}`,
          boxShadow: designTokens.shadow.card,
          bgcolor: alpha(brand.slate, 0.65),
          backgroundImage: "none",
        }}
      >
        <Stack
          spacing={1.25}
          sx={{
            px: 2.5,
            py: 2,
            background: headerNeutral,
            borderBottom: `1px solid ${glass.border}`,
          }}
        >
          <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={1}>
            <Stack spacing={0.75} sx={{ minWidth: 0, flex: 1 }}>
              <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
                <Chip
                  label={indicateur}
                  size="small"
                  sx={{
                    fontWeight: 800,
                    letterSpacing: "0.06em",
                    bgcolor: alpha(theme.palette.common.white, 0.06),
                    color: "text.secondary",
                    border: `1px solid ${glass.border}`,
                  }}
                />
                <Typography
                  variant="overline"
                  sx={{
                    letterSpacing: "0.12em",
                    fontWeight: 700,
                    fontSize: "0.65rem",
                    color: "text.secondary",
                  }}
                >
                  {title}
                </Typography>
              </Stack>
              <Stack direction="row" alignItems="center" spacing={1.5} flexWrap="wrap" useFlexGap>
                <Typography variant="h4" fontWeight={800} sx={{ lineHeight: 1.05, letterSpacing: "-0.03em" }}>
                  {value}
                </Typography>
                {dayPct != null && Number.isFinite(dayPct) && (
                  <DayKpiStatusIcon status={dayStatus} accentColor={dayAccent} />
                )}
              </Stack>
            </Stack>
            <Button
              size="small"
              variant="outlined"
              startIcon={<ImageOutlinedIcon />}
              onClick={onExportPng}
              disabled={loading || error || data.length === 0}
              sx={{ flexShrink: 0 }}
            >
              PNG
            </Button>
          </Stack>
        </Stack>

        <Box
          sx={{
            px: { xs: 0.5, sm: 1.25 },
            pb: 2,
            pt: 1,
            minHeight: 320,
            bgcolor: alpha(brand.ink, 0.35),
            ...CHART_OVERFLOW_SX,
          }}
        >
          {loading ? (
            <Stack alignItems="center" justifyContent="center" sx={{ minHeight: 300 }}>
              <CircularProgress size={32} thickness={4} />
            </Stack>
          ) : error || data.length === 0 ? (
            <Stack alignItems="center" justifyContent="center" sx={{ minHeight: 300 }}>
              <Typography variant="body2" color="text.secondary">
                Aucune donnée sur la période.
              </Typography>
            </Stack>
          ) : (
            <ChartPlotFrame accent="primary">
              <Box sx={{ width: "100%", height: 300 }}>
                <SafeResponsiveContainer minHeight={300}>
                  <ComposedChart data={data} margin={chart.margins.bar}>
                    <ChartGradientDefs chart={chart} />
                    <CartesianGrid {...chart.grid} vertical={false} />
                    <XAxis
                      dataKey="label"
                      tick={{ ...chart.axis.tick, fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                      interval={0}
                      angle={-32}
                      textAnchor="end"
                      height={76}
                      minTickGap={2}
                    />
                    <YAxis
                      width={48}
                      domain={[0, 100]}
                      tickFormatter={(v) => `${v}%`}
                      tick={chart.axis.tick}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      content={({ active, payload, label }) => {
                        if (!active || !payload?.length) return null;
                        const raw = payload[0]?.value;
                        const pct = Number(raw);
                        const color = Number.isFinite(pct) ? barColorForValue(pct) : chart.colors.primary;
                        return (
                          <SparklineTooltip
                            active={active}
                            payload={payload}
                            label={label}
                            chart={chart}
                            valueLabel={valueLabel}
                            accentColor={color}
                          />
                        );
                      }}
                    />
                    <Bar
                      dataKey={dataKey}
                      name={valueLabel}
                      maxBarSize={40}
                      shape={glassHistogramBarShape(chart, 4, 28, dataKey, barColorForValue)}
                      isAnimationActive
                      animationDuration={chart.animation.barDuration}
                      animationEasing={chart.animation.barEasing}
                    >
                      <LabelList
                        dataKey={dataKey}
                        position="top"
                        offset={10}
                        formatter={(value: unknown) => {
                          const v = Number(value);
                          return Number.isFinite(v) ? `${v.toFixed(1)} %` : "";
                        }}
                        style={{
                          fill: alpha(theme.palette.text.primary, 0.88),
                          fontSize: 10,
                          fontWeight: 600,
                        }}
                      />
                    </Bar>
                  </ComposedChart>
                </SafeResponsiveContainer>
              </Box>
            </ChartPlotFrame>
          )}
        </Box>
      </Paper>
    </Box>
  );
}

type RoNroTrendSectionProps = {
  jour: string;
  data: RoNroTrendPoint[];
  loading: boolean;
  error: boolean;
  roValue: string;
  nroValue: string;
  roDayPct: number | null;
  nroDayPct: number | null;
};

export default function RoNroTrendSection({
  jour,
  data,
  loading,
  error,
  roValue,
  nroValue,
  roDayPct,
  nroDayPct,
}: RoNroTrendSectionProps) {
  const chart = useChartTheme();
  const roChartRef = useRef<HTMLDivElement | null>(null);
  const nroChartRef = useRef<HTMLDivElement | null>(null);

  const exportRoPng = () => void exportElementPng(roChartRef.current, `RO_${jour}.png`);
  const exportNroPng = () => void exportElementPng(nroChartRef.current, `NRO_${jour}.png`);

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        borderRadius: 3,
        border: `1px solid ${glass.border}`,
        bgcolor: alpha(brand.slate, 0.5),
        backgroundImage: "none",
        boxShadow: designTokens.shadow.card,
      }}
    >
      <Stack direction={{ xs: "column", lg: "row" }} spacing={2}>
        <TrendChartCard
          title="RO % jour"
          value={roValue}
          dayPct={roDayPct}
          dayStatus={roDayStatus(roDayPct)}
          indicateur="RO"
          accent="success"
          dataKey="ro"
          valueLabel="RO %"
          data={data}
          loading={loading}
          error={error}
          chart={chart}
          exportRef={roChartRef}
          onExportPng={exportRoPng}
          barColorForValue={roHistogramBarColor}
        />
        <TrendChartCard
          title="NRO jour %"
          value={nroValue}
          dayPct={nroDayPct}
          dayStatus={nroDayStatus(nroDayPct)}
          indicateur="NRO"
          accent="danger"
          dataKey="nroPct"
          valueLabel="NRO %"
          data={data}
          loading={loading}
          error={error}
          chart={chart}
          exportRef={nroChartRef}
          onExportPng={exportNroPng}
          barColorForValue={nroHistogramBarColor}
        />
      </Stack>
    </Paper>
  );
}
