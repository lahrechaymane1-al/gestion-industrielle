import Inventory2OutlinedIcon from "@mui/icons-material/Inventory2Outlined";
import {
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useMemo } from "react";
import { CartesianGrid, ComposedChart, Legend, Line, Tooltip as RechartsTooltip, XAxis, YAxis } from "recharts";
import {
  ChartGradientDefs,
  ChartLegendContent,
  ChartPlotFrame,
  CHART_OVERFLOW_SX,
  impactSeriesStyle,
  TrendAreaTooltip,
  useChartTheme,
} from "../components/charts";
import { SafeResponsiveContainer } from "../components/SafeResponsiveContainer";
import type { StockJournalResponse, StockJournalRow } from "../api/types";
import { designTokens } from "../theme/designTokens";
import { CHART_WORKING_DAYS, fmtQty, formatChartDay, isWorkingDay } from "./stock/stockJournalUtils";

type HomeStockSuiviChartProps = {
  stockA1: StockJournalResponse | undefined;
  stockA3: StockJournalResponse | undefined;
  loading: boolean;
  error?: boolean;
  today: string;
};

type StockFinPoint = {
  date: string;
  label: string;
  a1: number | null;
  a3: number | null;
};

function appendStockFinRows(rows: StockJournalRow[], key: "a1" | "a3", byDate: Map<string, StockFinPoint>) {
  for (const row of rows) {
    if (!isWorkingDay(row.date)) continue;
    const existing = byDate.get(row.date) ?? {
      date: row.date,
      label: formatChartDay(row.date),
      a1: null,
      a3: null,
    };
    existing[key] = row.stock_fin;
    byDate.set(row.date, existing);
  }
}

function buildStockFinTrendSeries(
  historyA1: StockJournalRow[],
  historyA3: StockJournalRow[]
): StockFinPoint[] {
  const byDate = new Map<string, StockFinPoint>();
  appendStockFinRows(historyA1, "a1", byDate);
  appendStockFinRows(historyA3, "a3", byDate);
  return [...byDate.values()]
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-CHART_WORKING_DAYS);
}

/** Courbe du stock fin (après shift N) — A1 et A3 sur le même graphique. */
export function HomeStockSuiviChart({ stockA1, stockA3, loading, error = false, today }: HomeStockSuiviChartProps) {
  const theme = useTheme();
  const chart = useChartTheme();
  const impact = impactSeriesStyle(chart);
  const curveGrey = chart.colors.seriesGrey;

  const chartData = useMemo(
    () => buildStockFinTrendSeries(stockA1?.history ?? [], stockA3?.history ?? []),
    [stockA1?.history, stockA3?.history]
  );

  const currentA1 = stockA1?.current?.stock_fin;
  const currentA3 = stockA3?.current?.stock_fin;

  return (
    <Card
      elevation={0}
      sx={{
        border: "1px solid",
        borderColor: alpha(theme.palette.divider, 0.5),
        borderRadius: 3,
        borderLeft: "4px solid",
        borderLeftColor: impact.strokeMuted,
        bgcolor: designTokens.glass.fill,
        overflow: "hidden",
        boxShadow: `0 8px 32px ${alpha(theme.palette.common.black, 0.18)}`,
        transition: `box-shadow 0.3s ease, transform 0.3s cubic-bezier(${designTokens.motion.easeOut.join(",")})`,
        "&:hover": {
          boxShadow: `0 12px 48px ${alpha(theme.palette.common.black, 0.32)}`,
        },
      }}
    >
      <CardContent sx={{ pt: 2.25, pb: 2, px: 2.25 }}>
        <Stack
          direction="row"
          alignItems="flex-start"
          spacing={1.75}
          sx={{ pb: 1.5, mb: 1, borderBottom: "1px solid", borderColor: "divider" }}
        >
          <Box
            sx={{
              p: 1,
              borderRadius: 2,
              bgcolor: alpha(impact.strokeMuted, 0.1),
              border: "1px solid",
              borderColor: alpha(impact.stroke, 0.28),
              display: "grid",
              placeItems: "center",
            }}
          >
            <Inventory2OutlinedIcon sx={{ color: impact.stroke, fontSize: 22 }} />
          </Box>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography variant="subtitle1" fontWeight={800} sx={{ letterSpacing: "-0.01em" }}>
              Suivi stock actuel · stock fin
            </Typography>
            <Typography variant="caption" sx={{ mt: 0.35, display: "block", lineHeight: 1.5, color: "text.secondary" }}>
              Stock en fin de journée (après shift N) · diversités A1 et A3 · {CHART_WORKING_DAYS} jours ouvrés
            </Typography>
            {!loading && (currentA1 != null || currentA3 != null) && (
              <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                {currentA1 != null && (
                  <Chip
                    size="small"
                    color={currentA1 < 0 ? "error" : "primary"}
                    variant="outlined"
                    label={`A1 : ${fmtQty(currentA1)}`}
                  />
                )}
                {currentA3 != null && (
                  <Chip
                    size="small"
                    color={currentA3 < 0 ? "error" : "success"}
                    variant="outlined"
                    label={`A3 : ${fmtQty(currentA3)}`}
                  />
                )}
                <Chip size="small" variant="outlined" label={`Jour ${today}`} />
              </Stack>
            )}
          </Box>
        </Stack>

        <Box sx={{ width: "100%", minHeight: 320, ...CHART_OVERFLOW_SX }}>
          {loading ? (
            <Skeleton variant="rounded" height={320} sx={{ borderRadius: 2 }} />
          ) : error ? (
            <Stack alignItems="center" justifyContent="center" sx={{ minHeight: 320, px: 2 }}>
              <Typography color="error" variant="body2" textAlign="center">
                Impossible de charger le suivi stock.
              </Typography>
            </Stack>
          ) : chartData.length === 0 ? (
            <Stack alignItems="center" justifyContent="center" sx={{ minHeight: 320 }}>
              <Typography color="text.secondary" variant="body2">
                Pas assez de données sur cette période.
              </Typography>
            </Stack>
          ) : (
            <ChartPlotFrame accent="primary" fill>
              <SafeResponsiveContainer minHeight={320} boxSx={{ height: 320, width: "100%" }}>
                <ComposedChart data={chartData} margin={chart.margins.homeTrend}>
                  <ChartGradientDefs chart={chart} />
                  <CartesianGrid {...chart.grid} />
                  <XAxis
                    dataKey="label"
                    tick={chart.axis.tick}
                    axisLine={false}
                    tickLine={false}
                    interval={0}
                    angle={-28}
                    textAnchor="end"
                    height={64}
                  />
                  <YAxis
                    allowDecimals={false}
                    width={52}
                    tick={chart.axis.tick}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => fmtQty(Number(v))}
                  />
                  <RechartsTooltip content={<TrendAreaTooltip chart={chart} />} />
                  <Legend content={<ChartLegendContent chart={chart} />} />
                  <Line
                    type="monotone"
                    dataKey="a1"
                    name="Stock fin A1"
                    stroke={impact.stroke}
                    strokeWidth={2.75}
                    connectNulls
                    style={{ filter: impact.glow }}
                    dot={{ r: 3.5, strokeWidth: 0, fill: impact.dotFill }}
                    activeDot={{ r: 6, fill: impact.stroke, stroke: "#fff", strokeWidth: 2 }}
                    isAnimationActive
                    animationDuration={chart.animation.lineDuration}
                  />
                  <Line
                    type="monotone"
                    dataKey="a3"
                    name="Stock fin A3"
                    stroke={curveGrey}
                    strokeWidth={2.75}
                    connectNulls
                    dot={{ r: 3, strokeWidth: 0, fill: curveGrey }}
                    activeDot={{ r: 6, stroke: "#fff", strokeWidth: 2 }}
                    isAnimationActive
                    animationDuration={chart.animation.lineDuration}
                  />
                </ComposedChart>
              </SafeResponsiveContainer>
            </ChartPlotFrame>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
