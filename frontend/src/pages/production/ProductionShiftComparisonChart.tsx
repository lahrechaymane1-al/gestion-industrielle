import { Box, Paper, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
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
  TrendAreaTooltip,
  useChartTheme,
} from "../../components/charts";
import { SafeResponsiveContainer } from "../../components/SafeResponsiveContainer";
import { api } from "../../api/client";
import type { EquipeScope, StockJournalResponse } from "../../api/types";
import { formatDateGroupLabel } from "./productionMetrics";

type ProductionShiftComparisonChartProps = {
  equipe?: EquipeScope;
  date: string;
  /** When empty, Berceau defaults to A1 (stock journal is per diversité). */
  line?: string;
};

const SHIFT_BARS = [
  { key: "A", label: "Shift A", dataKey: "entree_par_shift.A" as const },
  { key: "B", label: "Shift B", dataKey: "entree_par_shift.B" as const },
  { key: "N", label: "Shift N", dataKey: "entree_par_shift.N" as const },
] as const;

/** Shift N — gris pâle, distinct du cyan (A) et de l’ambre (B). */
const SHIFT_N_PALE_GREY = "#e2e8f0";

function formatChartDate(iso: string): string {
  try {
    return new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function ProductionShiftComparisonChart({
  equipe = "Berceau",
  date,
  line,
}: ProductionShiftComparisonChartProps) {
  const chart = useChartTheme();
  const effectiveLine =
    equipe === "Berceau" ? (line === "A1" || line === "A3" ? line : "A1") : undefined;

  const stockQuery = useQuery({
    queryKey: ["stock-journal", equipe, effectiveLine, date],
    queryFn: async () =>
      (
        await api.get<StockJournalResponse>("/api/stock/journal/", {
          params: { equipe, line: effectiveLine, date, days: 10 },
        })
      ).data,
  });

  const historyChrono = useMemo(() => {
    const history = stockQuery.data?.history ?? [];
    return [...history]
      .sort((a, b) => a.date.localeCompare(b.date))
      .map((row) => ({
        ...row,
        dateLabel: formatChartDate(row.date),
      }));
  }, [stockQuery.data?.history]);

  const diversiteLabel = effectiveLine ?? "—";

  const shiftColor = {
    A: chart.colors.primary,
    B: chart.colors.secondary,
    N: SHIFT_N_PALE_GREY,
  } as const;

  const shiftFill = {
    A: `url(#${chart.ids.barPrimary})`,
    B: `url(#${chart.ids.barSecondary})`,
    N: SHIFT_N_PALE_GREY,
  } as const;

  const barLabelStyle = { fill: chart.colors.tickFill, fontSize: 10, fontWeight: 700 as const };

  return (
    <Paper sx={{ p: 2.2, borderRadius: 3, position: "relative" }}>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ position: "absolute", top: 16, right: 20, fontWeight: 600 }}
      >
        {formatDateGroupLabel(date)}
      </Typography>

      <Typography variant="h6" fontWeight={800} gutterBottom sx={{ pr: 12 }}>
        Comparaison production par shift (A / B / N)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        Entrées de stock calculées depuis la production · diversité {diversiteLabel} · 10 derniers jours.
      </Typography>

      <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
        {SHIFT_BARS.map((item) => {
          const solid = shiftColor[item.key];
          return (
            <Stack key={item.key} direction="row" spacing={1} alignItems="center">
              <Box
                sx={{
                  width: 14,
                  height: 14,
                  borderRadius: 1,
                  bgcolor: solid,
                  boxShadow: `0 0 0 1px ${alpha(solid, 0.4)}`,
                }}
              />
              <Typography variant="body2" fontWeight={700}>
                {item.label}
              </Typography>
            </Stack>
          );
        })}
      </Stack>

      <Box sx={{ width: "100%", height: 360, minHeight: 260, ...CHART_OVERFLOW_SX }}>
        <ChartPlotFrame accent="primary">
          <SafeResponsiveContainer minHeight={260} boxSx={{ height: 360 }}>
            <ComposedChart
              data={historyChrono}
              margin={chart.margins.bar}
              barCategoryGap="28%"
              barGap={6}
            >
              <ChartGradientDefs chart={chart} />
              <CartesianGrid {...chart.grid} />
              <XAxis
                dataKey="dateLabel"
                tick={chart.axis.tick}
                axisLine={false}
                tickLine={false}
                interval={0}
                angle={-32}
                textAnchor="end"
                height={56}
              />
              <YAxis allowDecimals={false} tick={chart.axis.tick} axisLine={false} tickLine={false} width={40} />
              <Tooltip content={<TrendAreaTooltip chart={chart} />} />
              <Bar
                dataKey="entree_par_shift.A"
                name="Shift A"
                fill={shiftFill.A}
                radius={[6, 6, 0, 0]}
                maxBarSize={32}
                isAnimationActive
                animationDuration={chart.animation.barDuration}
              >
                <LabelList
                  dataKey="entree_par_shift.A"
                  position="top"
                  formatter={(v) => (Number(v) > 0 ? String(v) : "")}
                  style={barLabelStyle}
                />
              </Bar>
              <Bar
                dataKey="entree_par_shift.B"
                name="Shift B"
                fill={shiftFill.B}
                radius={[6, 6, 0, 0]}
                maxBarSize={32}
                isAnimationActive
                animationDuration={chart.animation.barDuration}
              >
                <LabelList
                  dataKey="entree_par_shift.B"
                  position="top"
                  formatter={(v) => (Number(v) > 0 ? String(v) : "")}
                  style={barLabelStyle}
                />
              </Bar>
              <Bar
                dataKey="entree_par_shift.N"
                name="Shift N"
                fill={shiftFill.N}
                radius={[6, 6, 0, 0]}
                maxBarSize={32}
                isAnimationActive
                animationDuration={chart.animation.barDuration}
              >
                <LabelList
                  dataKey="entree_par_shift.N"
                  position="top"
                  formatter={(v) => (Number(v) > 0 ? String(v) : "")}
                  style={barLabelStyle}
                />
              </Bar>
            </ComposedChart>
          </SafeResponsiveContainer>
        </ChartPlotFrame>
      </Box>
    </Paper>
  );
}
