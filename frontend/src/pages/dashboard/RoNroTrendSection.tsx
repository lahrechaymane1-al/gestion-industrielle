import ImageOutlinedIcon from "@mui/icons-material/ImageOutlined";
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
import { useMemo, useRef, type RefObject } from "react";
import {
  Area,
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
  SparklineTooltip,
  trendHighlightDot,
  useChartTheme,
  type ChartTheme,
} from "../../components/charts";
import { SafeResponsiveContainer } from "../../components/SafeResponsiveContainer";
import { designTokens } from "../../theme/designTokens";
import { formatTrendAxisDate } from "../production/productionMetrics";
import { exportElementPng } from "./dashboardExport";

const { glass, brand } = designTokens;

export type RoNroTrendPoint = {
  label: string;
  iso: string;
  ro: number;
  nroPct: number;
  isSelected: boolean;
};

function trendPeriodLabel(data: RoNroTrendPoint[]) {
  if (!data.length) return "";
  if (data.length === 1) return formatTrendAxisDate(data[0].iso);
  return `${formatTrendAxisDate(data[0].iso)} → ${formatTrendAxisDate(data[data.length - 1].iso)}`;
}

type TrendChartCardProps = {
  title: string;
  value: string;
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
};

function TrendChartCard({
  title,
  value,
  indicateur,
  accent,
  dataKey,
  valueLabel,
  data,
  loading,
  error,
  chart,
  exportRef,
  onExportPng,
}: TrendChartCardProps) {
  const theme = useTheme();
  const stroke = accent === "danger" ? chart.colors.seriesRed : chart.colors.seriesGreen;
  const fillGradient =
    accent === "danger" ? `url(#${chart.ids.areaTrendRed})` : `url(#${chart.ids.areaTrendGreen})`;
  const lineGlowFilter =
    accent === "danger" ? `url(#${chart.ids.lineGlowRed})` : `url(#${chart.ids.lineGlowGreen})`;
  const period = useMemo(() => trendPeriodLabel(data), [data]);
  const headerBg = `linear-gradient(90deg, ${alpha(stroke, 0.18)} 0%, transparent 22%), ${alpha(brand.slate, 0.92)}`;
  const headerAccentBorder = `3px solid ${alpha(stroke, 0.65)}`;

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
          background: headerBg,
          borderBottom: `1px solid ${glass.border}`,
          borderLeft: headerAccentBorder,
        }}
      >
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={1}>
          <Stack spacing={0.75} sx={{ minWidth: 0 }}>
            <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
              <Chip
                label={indicateur}
                size="small"
                sx={{
                  fontWeight: 800,
                  letterSpacing: "0.06em",
                  bgcolor: alpha(stroke, 0.12),
                  color: stroke,
                  border: `1px solid ${alpha(stroke, 0.28)}`,
                }}
              />
              <Typography
                variant="overline"
                sx={{ letterSpacing: "0.12em", fontWeight: 700, fontSize: "0.65rem", color: "text.secondary" }}
              >
                {title}
              </Typography>
            </Stack>
            <Typography variant="h4" fontWeight={800} sx={{ lineHeight: 1.05, letterSpacing: "-0.03em" }}>
              {value}
            </Typography>
            {period ? (
              <Typography variant="body2" color="text.secondary" sx={{ fontVariantNumeric: "tabular-nums" }}>
                {period}
              </Typography>
            ) : null}
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
          <ChartPlotFrame accent={accent}>
            <Box sx={{ width: "100%", height: 300 }}>
              <SafeResponsiveContainer minHeight={300}>
                <ComposedChart data={data} margin={chart.margins.trendArea}>
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
                    content={
                      <SparklineTooltip chart={chart} valueLabel={valueLabel} accentColor={stroke} />
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey={dataKey}
                    name={valueLabel}
                    stroke={stroke}
                    fill={fillGradient}
                    strokeWidth={2.5}
                    style={{ filter: lineGlowFilter }}
                    dot={trendHighlightDot(stroke)}
                    activeDot={{ r: 8, fill: stroke, stroke: "#fff", strokeWidth: 2.5 }}
                    isAnimationActive
                    animationDuration={chart.animation.lineDuration}
                  >
                    <LabelList
                      dataKey={dataKey}
                      position="top"
                      offset={14}
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
                  </Area>
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
};

export default function RoNroTrendSection({
  jour,
  data,
  loading,
  error,
  roValue,
  nroValue,
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
        />
        <TrendChartCard
          title="NRO jour %"
          value={nroValue}
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
        />
      </Stack>
    </Paper>
  );
}
