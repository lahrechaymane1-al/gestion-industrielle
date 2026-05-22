import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import CalendarTodayOutlinedIcon from "@mui/icons-material/CalendarTodayOutlined";
import FactoryOutlinedIcon from "@mui/icons-material/FactoryOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import Inventory2OutlinedIcon from "@mui/icons-material/Inventory2Outlined";
import {
  alpha,
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  Grid,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import type { SxProps, Theme } from "@mui/material/styles";
import { useTheme } from "@mui/material/styles";
import { useQueries } from "@tanstack/react-query";
import { useMemo, type ReactNode } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ChartGradientDefs,
  ChartLegendContent,
  ChartPlotFrame,
  impactSeriesStyle,
  TrendAreaTooltip,
  useChartTheme,
} from "../components/charts";
import { SafeResponsiveContainer } from "../components/SafeResponsiveContainer";
import { api } from "../api/client";
import type {
  DashboardArretsParJourResponse,
  Paginated,
  ProductionBerceauRow,
  ProductionCCBRow,
  StockJournalResponse,
} from "../api/types";
import { useLockedShift, useMe } from "../auth/AuthContext";
import { designTokens } from "../theme/designTokens";
import { CHART_WORKING_DAYS } from "./stock/stockJournalUtils";
import { HomeStockSuiviChart } from "./HomeStockSuiviChart";

function shortDate(iso: string) {
  try {
    return new Date(iso + "T12:00:00").toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
  } catch {
    return iso;
  }
}

function sumVolumeByDate(rows: Array<{ date: string; volume: number }>) {
  const m = new Map<string, number>();
  for (const r of rows) {
    m.set(r.date, (m.get(r.date) ?? 0) + (Number(r.volume) || 0));
  }
  return m;
}

function mergeTrendSeries(
  ber: Map<string, number>,
  ccb: Map<string, number>,
  maxPoints: number
): { label: string; berceau: number; ccb: number }[] {
  const dates = new Set([...ber.keys(), ...ccb.keys()]);
  const sorted = [...dates].sort((a, b) => b.localeCompare(a));
  const slice = sorted.slice(0, maxPoints).reverse();
  return slice.map((d) => ({
    label: shortDate(d),
    berceau: ber.get(d) ?? 0,
    ccb: ccb.get(d) ?? 0,
  }));
}

function KpiCard({
  title,
  value,
  subtitle,
  icon,
  accent,
  valueTypographyProps,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  accent: "primary" | "secondary";
  valueTypographyProps?: { variant?: "h4" | "h5" | "h6"; sx?: SxProps<Theme> };
}) {
  const theme = useTheme();
  const c = accent === "primary" ? "primary" : "secondary";
  const valueVariant = valueTypographyProps?.variant ?? "h4";
  return (
    <Card
      elevation={0}
      sx={{
        position: "relative",
        overflow: "hidden",
        height: "100%",
        borderRadius: 3,
        border: "1px solid",
        borderColor: alpha(theme.palette.divider, 0.55),
        borderTop: "3px solid",
        borderTopColor: `${c}.light`,
        bgcolor: designTokens.glass.fill,
        backgroundImage: (t) =>
          `linear-gradient(145deg, ${alpha(t.palette[c].light, 0.08)} 0%, transparent 52%, ${alpha(
            designTokens.brand.slateLight,
            0.85
          )} 68%)`,
        boxShadow: `0 6px 32px ${alpha(theme.palette.common.black, 0.2)}`,
        transition: `transform 0.32s cubic-bezier(${designTokens.motion.easeOut.join(",")}), box-shadow 0.32s ease`,
        "&:hover": {
          transform: "translateY(-5px)",
          boxShadow: (t) =>
            `0 18px 52px ${alpha(t.palette.common.black, 0.38)}, 0 0 0 1px ${alpha(t.palette[c].main, 0.18)}`,
        },
        "&::before": {
          content: '""',
          position: "absolute",
          top: -40,
          right: -40,
          width: 120,
          height: 120,
          borderRadius: "50%",
          background: (t) => `radial-gradient(circle, ${alpha(t.palette[c].main, 0.12)} 0%, transparent 70%)`,
          pointerEvents: "none",
        },
        "&::after": {
          content: '""',
          position: "absolute",
          inset: "auto 0 0 0",
          height: 1,
          background: (t) =>
            `linear-gradient(90deg, transparent 0%, ${alpha(t.palette[c].main, 0.35)} 50%, transparent 100%)`,
          pointerEvents: "none",
        },
      }}
    >
      <CardContent sx={{ p: 2.5, position: "relative", zIndex: 1 }}>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={1.5}>
          <Box sx={{ minWidth: 0 }}>
            <Typography
              variant="caption"
              color="text.secondary"
              fontWeight={700}
              letterSpacing="0.08em"
              textTransform="uppercase"
              sx={{ display: "block" }}
            >
              {title}
            </Typography>
            <Typography
              component="p"
              variant={valueVariant}
              fontWeight={800}
              sx={{
                mt: 0.75,
                mb: 0,
                letterSpacing: "-0.02em",
                lineHeight: 1.2,
                background: (t) =>
                  `linear-gradient(115deg, ${t.palette.text.primary} 0%, ${alpha(t.palette[c].light, 0.95)} 100%)`,
                backgroundClip: "text",
                WebkitBackgroundClip: "text",
                color: "transparent",
                WebkitTextFillColor: "transparent",
                ...valueTypographyProps?.sx,
              }}
            >
              {value}
            </Typography>
            {subtitle ? (
              <Typography
                variant="caption"
                sx={{ mt: 0.75, display: "block", color: alpha(theme.palette.text.primary, 0.62), lineHeight: 1.45 }}
              >
                {subtitle}
              </Typography>
            ) : null}
          </Box>
          <Box
            sx={(t) => ({
              flexShrink: 0,
              width: 48,
              height: 48,
              borderRadius: 2.5,
              display: "grid",
              placeItems: "center",
              bgcolor: alpha(t.palette[c].main, 0.12),
              color: `${c}.light`,
              border: "1px solid",
              borderColor: alpha(t.palette[c].main, 0.28),
              boxShadow: `0 0 28px ${alpha(t.palette[c].main, 0.15)}, inset 0 1px 0 ${alpha(t.palette.common.white, 0.06)}`,
            })}
          >
            {icon}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

/** Jour calendaire local (YYYY-MM-DD) — évite le décalage minuit UTC de `toISOString()`. */
function isoCalendarToday(): string {
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function isoDaysAgo(days: number) {
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  d.setDate(d.getDate() - days);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const TREND_DAYS = 14;

export default function HomeDashboardPage() {
  const theme = useTheme();
  const chart = useChartTheme();
  const me = useMe();
  const lockedShift = useLockedShift();
  const isPsp = me?.role === "PSP";
  const pspEquipe = (me?.equipe ?? "").trim().toUpperCase();
  const canSeeBerceau = !isPsp || pspEquipe === "BERCEAU";
  const canSeeCcb = !isPsp || pspEquipe === "CCB";
  const pspMissingScope = isPsp && !canSeeBerceau && !canSeeCcb;
  const enabled = Boolean(me?.authenticated);

  const shiftParams = lockedShift ? { shift: lockedShift } : {};
  const today = useMemo(() => isoCalendarToday(), []);
  const arretDateFrom = useMemo(() => isoDaysAgo(13), []);

  const results = useQueries({
    queries: [
      {
        queryKey: ["home-dash", "stock-ber-a1", today, lockedShift],
        enabled: enabled && canSeeBerceau,
        queryFn: async () =>
          (
            await api.get<StockJournalResponse>("/api/stock/journal/", {
              params: { equipe: "Berceau", line: "A1", date: today, days: CHART_WORKING_DAYS },
            })
          ).data,
      },
      {
        queryKey: ["home-dash", "stock-ber-a3", today, lockedShift],
        enabled: enabled && canSeeBerceau,
        queryFn: async () =>
          (
            await api.get<StockJournalResponse>("/api/stock/journal/", {
              params: { equipe: "Berceau", line: "A3", date: today, days: CHART_WORKING_DAYS },
            })
          ).data,
      },
      {
        queryKey: ["home-dash", "stock-ccb", today, lockedShift],
        enabled: enabled && canSeeCcb,
        queryFn: async () =>
          (
            await api.get<StockJournalResponse>("/api/stock/journal/", {
              params: { equipe: "CCB", date: today, days: CHART_WORKING_DAYS },
            })
          ).data,
      },
      {
        queryKey: ["home-dash", "berceau-trend", lockedShift],
        enabled: enabled && canSeeBerceau,
        queryFn: async () =>
          (
            await api.get<Paginated<ProductionBerceauRow>>("/api/berceau/production/", {
              params: { page: 1, per_page: 100, sort: "-date", ...shiftParams },
            })
          ).data,
      },
      {
        queryKey: ["home-dash", "ccb-trend", lockedShift],
        enabled: enabled && canSeeCcb,
        queryFn: async () =>
          (
            await api.get<Paginated<ProductionCCBRow>>("/api/ccb/production/", {
              params: { page: 1, per_page: 100, sort: "-date", ...shiftParams },
            })
          )
            .data,
      },
      {
        queryKey: ["home-dash", "arrets-par-jour", arretDateFrom, today, lockedShift],
        enabled: enabled && (canSeeBerceau || canSeeCcb),
        queryFn: async () =>
          (
            await api.get<DashboardArretsParJourResponse>("/api/dashboard/arrets-par-jour/", {
              params: { date_from: arretDateFrom, date_to: today, ...shiftParams },
            })
          ).data,
      },
    ],
  });

  const [stockA1, stockA3, stockCcb, berTrend, ccbTrend, arretsParJour] = results;
  const arretsChartLoading = arretsParJour.isLoading;
  const productionChartLoading =
    (canSeeBerceau && berTrend.isLoading) || (canSeeCcb && ccbTrend.isLoading);
  const stockChartLoading = stockA1.isLoading || stockA3.isLoading;

  const failedLoads = useMemo(() => {
    const items: string[] = [];
    if (canSeeBerceau && stockA1.isError) items.push("stock Berceau A1");
    if (canSeeBerceau && stockA3.isError) items.push("stock Berceau A3");
    if (canSeeCcb && stockCcb.isError) items.push("stock CCB");
    if (canSeeBerceau && berTrend.isError) items.push("production Berceau");
    if (canSeeCcb && ccbTrend.isError) items.push("production CCB");
    if ((canSeeBerceau || canSeeCcb) && arretsParJour.isError) items.push("arrêts par jour");
    return items;
  }, [
    canSeeBerceau,
    canSeeCcb,
    stockA1.isError,
    stockA3.isError,
    stockCcb.isError,
    berTrend.isError,
    ccbTrend.isError,
    arretsParJour.isError,
  ]);

  const kpiStockCount = (canSeeBerceau ? 2 : 0) + (canSeeCcb ? 1 : 0);
  const kpiGridMd = kpiStockCount === 0 ? 12 : kpiStockCount === 1 ? 6 : kpiStockCount === 2 ? 4 : 3;

  const dateLabelLong = useMemo(() => {
    try {
      const s = new Date(`${today}T12:00:00`).toLocaleDateString("fr-FR", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
      });
      return s.charAt(0).toUpperCase() + s.slice(1);
    } catch {
      return today;
    }
  }, [today]);

  const counts = useMemo(() => {
    return {
      stockA1: stockA1.data?.current?.stock_fin ?? 0,
      stockA3: stockA3.data?.current?.stock_fin ?? 0,
      stockCcb: stockCcb.data?.current?.stock_fin ?? 0,
    };
  }, [stockA1.data, stockA3.data, stockCcb.data]);

  const trendData = useMemo(() => {
    const bRows = berTrend.data?.results ?? [];
    const cRows = ccbTrend.data?.results ?? [];
    const berMap = sumVolumeByDate(bRows.map((r) => ({ date: r.date, volume: r.volume })));
    const ccbMap = sumVolumeByDate(cRows.map((r) => ({ date: r.date, volume: r.volume })));
    if (!canSeeBerceau && !canSeeCcb) return [];
    if (canSeeBerceau && !canSeeCcb) {
      const dates = [...berMap.keys()].sort((a, b) => b.localeCompare(a)).slice(0, TREND_DAYS).reverse();
      return dates.map((d) => ({ label: shortDate(d), berceau: berMap.get(d) ?? 0, ccb: 0 }));
    }
    if (!canSeeBerceau && canSeeCcb) {
      const dates = [...ccbMap.keys()].sort((a, b) => b.localeCompare(a)).slice(0, TREND_DAYS).reverse();
      return dates.map((d) => ({ label: shortDate(d), berceau: 0, ccb: ccbMap.get(d) ?? 0 }));
    }
    return mergeTrendSeries(berMap, ccbMap, TREND_DAYS);
  }, [berTrend.data, ccbTrend.data, canSeeBerceau, canSeeCcb]);

  const arretsTrendData = useMemo(() => {
    const d = arretsParJour.data;
    if (!d?.labels?.length) return [];
    const max = 14;
    const start = Math.max(0, d.labels.length - max);
    return d.labels.slice(start).map((iso, idx) => {
      const i = start + idx;
      return {
        label: shortDate(iso),
        berceau: d.series.berceau_minutes[i] ?? 0,
        ccb: d.series.ccb_minutes[i] ?? 0,
      };
    });
  }, [arretsParJour.data]);

  const impact = impactSeriesStyle(chart);
  const curveGrey = chart.colors.seriesGrey;
  const captionMuted = alpha(theme.palette.text.primary, 0.58);

  return (
    <Stack spacing={3.5}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1.5}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "center" }}
      >
        <Box>
          <Typography component="h1" variant="h5" fontWeight={800} sx={{ letterSpacing: "-0.02em" }}>
            Tableau de bord
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Indicateurs du jour, tendances production / arrêts et suivi des stocks Berceau A1 · A3.
          </Typography>
        </Box>
        <Button
          component={RouterLink}
          to="/berceau/dashboard"
          variant="contained"
          size="medium"
          startIcon={<InsightsOutlinedIcon />}
          disabled={!canSeeBerceau}
          sx={{ alignSelf: { xs: "stretch", sm: "center" }, fontWeight: 700, whiteSpace: "nowrap" }}
        >
          Analyse Berceau
        </Button>
      </Stack>

      {pspMissingScope && (
        <Alert severity="warning">
          Compte PSP sans périmètre UEP : le tableau ne charge aucune donnée Berceau/CCB tant que votre utilisateur
          n’est pas relié à une fiche <strong>Effectif</strong> (profil d’accès : champ effectif / UEP Berceau ou CCB).
          Demandez à un administrateur de lier votre compte à votre ligne PSP dans l’effectif.
        </Alert>
      )}

      {failedLoads.length > 0 && (
        <Alert severity="error">
          Impossible de charger : {failedLoads.join(", ")}. Vérifiez la session ou réessayez plus tard.
        </Alert>
      )}

      <Stack direction="row" alignItems="center" spacing={2} sx={{ pt: 0.25 }}>
        <Box
          sx={{
            width: 4,
            height: 24,
            borderRadius: 1,
            bgcolor: "primary.main",
            boxShadow: (t) => `0 0 16px ${alpha(t.palette.primary.main, 0.45)}`,
          }}
        />
        <Typography variant="overline" fontWeight={800} letterSpacing="0.18em" color="text.secondary">
          Indicateurs clés
        </Typography>
        <Divider sx={{ flex: 1, borderColor: alpha(theme.palette.divider, 0.9) }} />
      </Stack>

      <Grid container spacing={2.25}>
        <Grid item xs={12} sm={6} md={kpiGridMd}>
          {!enabled ? (
            <Skeleton variant="rounded" height={128} sx={{ borderRadius: 3 }} />
          ) : (
            <KpiCard
              title="Date du jour"
              value={dateLabelLong}
              subtitle={`Jour calendaire · ${today}`}
              icon={<CalendarTodayOutlinedIcon />}
              accent="primary"
              valueTypographyProps={{
                variant: "h5",
                sx: {
                  fontSize: { xs: "1.05rem", sm: "1.15rem", md: "1.3rem" },
                  lineHeight: 1.28,
                },
              }}
            />
          )}
        </Grid>
        {canSeeBerceau && (
          <>
            <Grid item xs={12} sm={6} md={kpiGridMd}>
              {stockA1.isLoading ? (
                <Skeleton variant="rounded" height={128} sx={{ borderRadius: 3 }} />
              ) : (
                <KpiCard
                  title="Stock A1 actuel"
                  value={counts.stockA1.toLocaleString("fr-FR")}
                  subtitle={
                    isPsp && lockedShift
                      ? `Entrée shift ${lockedShift} ${(stockA1.data?.current?.entree_calculee ?? 0).toLocaleString("fr-FR")} · sortie imputée au prorata`
                      : `Entrée ${(stockA1.data?.current?.entree_calculee ?? 0).toLocaleString("fr-FR")} · Jour ${today}`
                  }
                  icon={<Inventory2OutlinedIcon />}
                  accent="primary"
                />
              )}
            </Grid>
            <Grid item xs={12} sm={6} md={kpiGridMd}>
              {stockA3.isLoading ? (
                <Skeleton variant="rounded" height={128} sx={{ borderRadius: 3 }} />
              ) : (
                <KpiCard
                  title="Stock A3 actuel"
                  value={counts.stockA3.toLocaleString("fr-FR")}
                  subtitle={
                    isPsp && lockedShift
                      ? `Entrée shift ${lockedShift} ${(stockA3.data?.current?.entree_calculee ?? 0).toLocaleString("fr-FR")} · sortie imputée au prorata`
                      : `Entrée ${(stockA3.data?.current?.entree_calculee ?? 0).toLocaleString("fr-FR")} · Jour ${today}`
                  }
                  icon={<Inventory2OutlinedIcon />}
                  accent="secondary"
                />
              )}
            </Grid>
          </>
        )}
        {canSeeCcb && (
          <Grid item xs={12} sm={6} md={kpiGridMd}>
            {stockCcb.isLoading ? (
              <Skeleton variant="rounded" height={128} sx={{ borderRadius: 3 }} />
            ) : (
              <KpiCard
                title="Stock CCB actuel"
                value={counts.stockCcb.toLocaleString("fr-FR")}
                subtitle={
                  isPsp && lockedShift
                    ? `Entrée shift ${lockedShift} ${(stockCcb.data?.current?.entree_calculee ?? 0).toLocaleString("fr-FR")} · sortie imputée au prorata`
                    : `Entrée ${(stockCcb.data?.current?.entree_calculee ?? 0).toLocaleString("fr-FR")} · Jour ${today}`
                }
                icon={<Inventory2OutlinedIcon />}
                accent="secondary"
              />
            )}
          </Grid>
        )}
      </Grid>

      <Stack direction="row" alignItems="center" spacing={2} sx={{ mt: 1 }}>
        <Box
          sx={{
            width: 4,
            height: 24,
            borderRadius: 1,
            bgcolor: "secondary.main",
            boxShadow: (t) => `0 0 16px ${alpha(t.palette.secondary.main, 0.4)}`,
          }}
        />
        <Typography variant="overline" fontWeight={800} letterSpacing="0.18em" color="text.secondary">
          Analyses &amp; tendances
        </Typography>
        <Divider sx={{ flex: 1, borderColor: alpha(theme.palette.divider, 0.9) }} />
      </Stack>

      <Grid container spacing={2.25}>
        <Grid item xs={12} lg={6}>
          <Card
            elevation={0}
            sx={{
              minHeight: 400,
              height: { xs: 380, md: 420 },
              border: "1px solid",
              borderColor: alpha(theme.palette.divider, 0.5),
              borderRadius: 3,
              borderLeft: "4px solid",
              borderLeftColor: impact.strokeMuted,
              bgcolor: designTokens.glass.fill,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              boxShadow: `0 8px 32px ${alpha(theme.palette.common.black, 0.18)}`,
              backgroundImage: (t) =>
                `linear-gradient(180deg, ${alpha(t.palette.primary.light, 0.05)} 0%, transparent 36%)`,
              transition: `box-shadow 0.3s ease, transform 0.3s cubic-bezier(${designTokens.motion.easeOut.join(",")})`,
              "&:hover": {
                boxShadow: `0 12px 48px ${alpha(theme.palette.common.black, 0.32)}`,
              },
            }}
          >
            <CardContent sx={{ flex: 1, display: "flex", flexDirection: "column", pt: 2.25, pb: 2, px: 2.25, minHeight: 0 }}>
              <Stack
                direction="row"
                alignItems="flex-start"
                spacing={1.75}
                sx={{
                  pb: 1.5,
                  mb: 1,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Box
                  sx={{
                    p: 1,
                    borderRadius: 2,
                    bgcolor: alpha(impact.strokeMuted, 0.12),
                    border: "1px solid",
                    borderColor: alpha(impact.stroke, 0.32),
                    display: "grid",
                    placeItems: "center",
                  }}
                >
                  <AssessmentOutlinedIcon sx={{ color: impact.stroke, fontSize: 22 }} />
                </Box>
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="subtitle1" fontWeight={800} sx={{ letterSpacing: "-0.01em" }}>
                    Arrêts Berceau vs CCB
                  </Typography>
                  <Typography variant="caption" sx={{ mt: 0.35, display: "block", lineHeight: 1.5, color: captionMuted }}>
                    Minutes par jour · 14 derniers jours
                  </Typography>
                </Box>
              </Stack>
              <Box sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
                {arretsChartLoading ? (
                  <Skeleton variant="rounded" sx={{ flex: 1, minHeight: 260, borderRadius: 2 }} />
                ) : arretsParJour.isError ? (
                  <Stack alignItems="center" justifyContent="center" sx={{ flex: 1, minHeight: 260, px: 2 }}>
                    <Typography color="error" variant="body2" textAlign="center">
                      Impossible de charger les arrêts.
                    </Typography>
                  </Stack>
                ) : arretsTrendData.length === 0 ? (
                  <Stack alignItems="center" justifyContent="center" sx={{ flex: 1, minHeight: 260 }}>
                    <Typography color="text.secondary" variant="body2">
                      Pas assez de donnees pour tracer la courbe.
                    </Typography>
                  </Stack>
                ) : (
                  <ChartPlotFrame accent="primary" fill>
                    <SafeResponsiveContainer
                      minHeight={260}
                      boxSx={{ flex: 1, height: "100%", width: "100%", minHeight: 260 }}
                    >
                      <ComposedChart data={arretsTrendData} margin={chart.margins.homeTrend}>
                        <ChartGradientDefs chart={chart} />
                        <CartesianGrid {...chart.grid} />
                        <XAxis dataKey="label" tick={chart.axis.tick} axisLine={false} tickLine={false} />
                        <YAxis tick={chart.axis.tick} axisLine={false} tickLine={false} width={40} />
                        <Tooltip content={<TrendAreaTooltip chart={chart} />} />
                        <Legend content={<ChartLegendContent chart={chart} />} />
                        {canSeeBerceau && (
                          <Area
                            type="monotone"
                            dataKey="berceau"
                            name="Arrets Berceau"
                            stroke={impact.stroke}
                            strokeWidth={2.75}
                            fill={impact.areaFill}
                            style={{ filter: impact.glow }}
                            dot={{ r: 3.5, strokeWidth: 0, fill: impact.dotFill }}
                            activeDot={{ r: 6, fill: impact.stroke, stroke: "#fff", strokeWidth: 2 }}
                            isAnimationActive
                            animationDuration={chart.animation.lineDuration}
                          />
                        )}
                        {canSeeCcb && (
                          <Area
                            type="monotone"
                            dataKey="ccb"
                            name="Arrets CCB"
                            stroke={curveGrey}
                            strokeWidth={2.5}
                            fill={alpha(curveGrey, 0.14)}
                            dot={{ r: 3, strokeWidth: 0, fill: curveGrey }}
                            activeDot={{ r: 6, stroke: "#fff", strokeWidth: 2 }}
                            isAnimationActive
                            animationDuration={chart.animation.lineDuration}
                          />
                        )}
                      </ComposedChart>
                    </SafeResponsiveContainer>
                  </ChartPlotFrame>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={6}>
          <Card
            elevation={0}
            sx={{
              minHeight: 400,
              height: { xs: 380, md: 420 },
              border: "1px solid",
              borderColor: alpha(theme.palette.divider, 0.5),
              borderRadius: 3,
              borderLeft: "4px solid",
              borderLeftColor: curveGrey,
              bgcolor: designTokens.glass.fill,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              boxShadow: `0 8px 32px ${alpha(theme.palette.common.black, 0.18)}`,
              backgroundImage: (t) =>
                `linear-gradient(180deg, ${alpha(t.palette.secondary.light, 0.06)} 0%, transparent 36%)`,
              transition: `box-shadow 0.3s ease, transform 0.3s cubic-bezier(${designTokens.motion.easeOut.join(",")})`,
              "&:hover": {
                boxShadow: `0 12px 48px ${alpha(theme.palette.common.black, 0.32)}`,
              },
            }}
          >
            <CardContent sx={{ flex: 1, display: "flex", flexDirection: "column", pt: 2.25, pb: 2, px: 2.25, minHeight: 0 }}>
              <Stack
                direction="row"
                alignItems="flex-start"
                spacing={1.75}
                sx={{
                  pb: 1.5,
                  mb: 1,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Box
                  sx={{
                    p: 1,
                    borderRadius: 2,
                    bgcolor: alpha(curveGrey, 0.1),
                    border: "1px solid",
                    borderColor: alpha(curveGrey, 0.28),
                    display: "flex",
                    alignItems: "center",
                    gap: 0.5,
                  }}
                >
                  <FactoryOutlinedIcon sx={{ color: impact.stroke, fontSize: 20 }} />
                  <AssessmentOutlinedIcon sx={{ color: curveGrey, fontSize: 20 }} />
                </Box>
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="subtitle1" fontWeight={800} sx={{ letterSpacing: "-0.01em" }}>
                    Volume production
                  </Typography>
                  <Typography variant="caption" sx={{ mt: 0.35, display: "block", lineHeight: 1.5, color: captionMuted }}>
                    Berceau et CCB · 14 derniers jours
                  </Typography>
                </Box>
              </Stack>
              <Box sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
                {productionChartLoading ? (
                  <Skeleton variant="rounded" sx={{ flex: 1, minHeight: 260, borderRadius: 2 }} />
                ) : (canSeeBerceau && berTrend.isError) || (canSeeCcb && ccbTrend.isError) ? (
                  <Stack alignItems="center" justifyContent="center" sx={{ flex: 1, minHeight: 260, px: 2 }}>
                    <Typography color="error" variant="body2" textAlign="center">
                      Impossible de charger la production.
                    </Typography>
                  </Stack>
                ) : trendData.length === 0 ? (
                  <Stack alignItems="center" justifyContent="center" sx={{ flex: 1, minHeight: 260 }}>
                    <Typography color="text.secondary" variant="body2">
                      Pas assez de donnees pour tracer la courbe.
                    </Typography>
                  </Stack>
                ) : (
                  <ChartPlotFrame accent="secondary" fill>
                    <SafeResponsiveContainer
                      minHeight={260}
                      boxSx={{ flex: 1, height: "100%", width: "100%", minHeight: 260 }}
                    >
                      <ComposedChart data={trendData} margin={chart.margins.homeTrend}>
                        <ChartGradientDefs chart={chart} />
                        <CartesianGrid {...chart.grid} />
                        <XAxis dataKey="label" tick={chart.axis.tick} axisLine={false} tickLine={false} />
                        <YAxis tick={chart.axis.tick} axisLine={false} tickLine={false} width={36} />
                        <Tooltip content={<TrendAreaTooltip chart={chart} />} />
                        <Legend content={<ChartLegendContent chart={chart} />} />
                        {canSeeBerceau && (
                          <Area
                            type="monotone"
                            dataKey="berceau"
                            name="Berceau"
                            stroke={impact.stroke}
                            strokeWidth={2.75}
                            fill={impact.areaFill}
                            style={{ filter: impact.glow }}
                            dot={{ r: 3.5, strokeWidth: 0, fill: impact.dotFill }}
                            activeDot={{ r: 6, fill: impact.stroke, stroke: "#fff", strokeWidth: 2 }}
                            isAnimationActive
                            animationDuration={chart.animation.lineDuration}
                          />
                        )}
                        {canSeeCcb && (
                          <Area
                            type="monotone"
                            dataKey="ccb"
                            name="CCB"
                            stroke={curveGrey}
                            strokeWidth={2.5}
                            fill={alpha(curveGrey, 0.14)}
                            dot={{ r: 3, strokeWidth: 0, fill: curveGrey }}
                            activeDot={{ r: 6, stroke: "#fff", strokeWidth: 2 }}
                            isAnimationActive
                            animationDuration={chart.animation.lineDuration}
                          />
                        )}
                      </ComposedChart>
                    </SafeResponsiveContainer>
                  </ChartPlotFrame>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {canSeeBerceau && (
        <>
          <Stack direction="row" alignItems="center" spacing={2} sx={{ mt: 1 }}>
            <Box
              sx={{
                width: 4,
                height: 24,
                borderRadius: 1,
                bgcolor: designTokens.brand.sky,
                boxShadow: `0 0 16px ${alpha(designTokens.brand.skyGlow, 0.55)}`,
              }}
            />
            <Typography variant="overline" fontWeight={800} letterSpacing="0.18em" color="text.secondary">
              Stock actuelle · suivi
            </Typography>
            <Divider sx={{ flex: 1, borderColor: alpha(theme.palette.divider, 0.9) }} />
          </Stack>

          <HomeStockSuiviChart
            stockA1={stockA1.data}
            stockA3={stockA3.data}
            loading={stockChartLoading}
            error={stockA1.isError || stockA3.isError}
            today={today}
          />
        </>
      )}
    </Stack>
  );
}
