import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DownloadIcon from "@mui/icons-material/Download";
import TableChartIcon from "@mui/icons-material/TableChart";
import {
  Box,
  Button,
  Divider,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useRef, useState } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  LabelList,
  Line,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ChartGradientDefs,
  CHART_OVERFLOW_SX,
  ParetoCategoryAxisTick,
  ParetoComboTooltip,
  paretoBarValueLabel,
  paretoGradientBarShape,
  useChartTheme,
} from "../../components/charts";
import { SafeResponsiveContainer } from "../../components/SafeResponsiveContainer";
import { GiDatePicker } from "../../components/GiDatePicker";
import { api } from "../../api/client";
import type {
  AlertePanneRow,
  BerceauPosteOption,
  DashboardRoNroTrendResponse,
  Paginated,
  ProductionBerceauRow,
} from "../../api/types";
import { useLockedShift } from "../../auth/AuthContext";
import {
  addRowToParetoMinuteBuckets,
  addRowToParetoPosteMinuteBuckets,
  analyzeParetoMinuteBuckets,
  analyzeParetoPosteMinuteBuckets,
  sumAllHourlyObjectifs,
  sumAllHourlyObjectifsAcrossRows,
  sumAllHourlyProduction,
} from "../../domain/downtimeImpact";
import { formatTrendAxisDate, isoCalendarYesterday } from "../production/productionMetrics";
import { exportParetoTypesExcel } from "../../utils/exportParetoTypesExcel";
import { exportElementPng } from "./dashboardExport";
import RoNroTrendSection from "./RoNroTrendSection";

type ShiftCode = "A" | "B" | "N";

/** Valeurs acceptées par `/api/alertes-pannes/` (filtre catégorie du dashboard). */
type ArretCategoryFilter = "maintenance" | "kta" | "logistique" | "fabrication";

const CATEGORIE_OPTIONS: { value: "" | ArretCategoryFilter; label: string }[] = [
  { value: "", label: "Toutes catégories" },
  { value: "maintenance", label: "Maintenance" },
  { value: "kta", label: "KTA" },
  { value: "logistique", label: "Logistique" },
  { value: "fabrication", label: "Fabrication" },
];

const MAX_BARS_PER_CHART = 30;

/** Ligne renvoyée par le calcul Pareto types (cumul % inclus après agrégation requête). */
type DashboardParetoTypeRow = {
  typeArret: string;
  panne_type_nom: string;
  moyen_nom: string;
  poste_nom: string;
  pctA1: number;
  pctA3: number;
  minutesA1: number;
  minutesA3: number;
  totalPct: number;
  cumulePercent: number;
};

function parseIsoLocal(iso: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso ?? "").trim());
  if (!m) return null;
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), 12, 0, 0, 0);
}

function formatIsoLocal(d: Date): string {
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${mo}-${day}`;
}

/** Liste de jours calendaires locaux entre deux ISO (inclus). */
function listIsoDates(from: string, to: string) {
  const start = parseIsoLocal(from);
  const end = parseIsoLocal(to);
  if (!start || !end) return [];
  const res: string[] = [];
  const cur = new Date(start.getTime());
  while (cur <= end) {
    res.push(formatIsoLocal(cur));
    cur.setDate(cur.getDate() + 1);
  }
  return res;
}

/** ISO YYYY-MM-DD minus N calendar days (calendrier local). */
function isoDateMinusDays(iso: string, days: number): string {
  const d = parseIsoLocal(iso);
  if (!d || days < 0) return iso;
  d.setDate(d.getDate() - days);
  return formatIsoLocal(d);
}

/** Date du jour affichée sur les graphiques Pareto (jj/mm/aaaa). */
function shortDate(iso: string) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso ?? "").trim());
  if (m) return `${m[3]}/${m[2]}/${m[1]}`;
  try {
    return new Date(`${iso}T12:00:00`).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export type DashboardProductionKpis = {
  roPercent: number | null;
  nroPercent: number | null;
  volume: number;
  objectif: number;
};

function computeProductionKpis(
  prodRowsByDay: Map<string, ProductionBerceauRow[]>,
  dates: string[],
  shiftFilter: ShiftCode | ""
): DashboardProductionKpis | null {
  const rows: ProductionBerceauRow[] = [];
  for (const d of dates) {
    for (const r of prodRowsByDay.get(d) ?? []) {
      if (!shiftFilter || r.shift === shiftFilter) rows.push(r);
    }
  }
  if (!rows.length) return null;
  /** Align KPIs with Pareto / fiche horaire : sommes H1–H8 si renseignées, sinon champs agrégés. */
  const effectiveVolumeObjectif = (r: ProductionBerceauRow) => {
    const objH = sumAllHourlyObjectifs(r);
    const volH = sumAllHourlyProduction(r);
    const objectif = objH > 0 ? objH : Number(r.objectif ?? 0);
    const volume = volH > 0 ? volH : Number(r.volume ?? 0);
    return { objectif, volume };
  };
  const volume = rows.reduce((s, r) => s + effectiveVolumeObjectif(r).volume, 0);
  const objectif = rows.reduce((s, r) => s + effectiveVolumeObjectif(r).objectif, 0);
  const roPercent = objectif > 0 ? Math.round((volume / objectif) * 10000) / 100 : null;
  const nroPercent = roPercent != null ? Math.max(0, Math.round((100 - roPercent) * 100) / 100) : null;
  return { roPercent, nroPercent, volume, objectif };
}

/**
 * Fiches production pour dénominateurs Pareto / KPI : alignées sur les shifts des alertes du jour.
 * Sans cela, « Tous shifts » additionne A+B+N alors que les alertes peuvent n'être que sur A → % impact faux.
 */
function productionRowsForImpactDenominators(
  prodRowsDay: ProductionBerceauRow[],
  shiftsInAlertes: Set<string>,
  shiftLocked: ShiftCode | ""
): ProductionBerceauRow[] {
  if (shiftLocked) {
    return prodRowsDay.filter((p) => p.shift === shiftLocked);
  }
  if (!shiftsInAlertes.size) {
    return prodRowsDay;
  }
  return prodRowsDay.filter((p) => shiftsInAlertes.has(p.shift));
}

async function fetchAllBerceauProductionForDate(date: string): Promise<ProductionBerceauRow[]> {
  const out: ProductionBerceauRow[] = [];
  let page = 1;
  const perPage = 100;
  while (true) {
    const { data: res } = await api.get<Paginated<ProductionBerceauRow>>("/api/berceau/production/", {
      params: { page, per_page: perPage, date, sort: "-date" },
    });
    const batch = res.results ?? [];
    out.push(...batch);
    const total = res.total ?? 0;
    if (out.length >= total || batch.length === 0) break;
    page += 1;
  }
  return out;
}

async function fetchAllAlertesPannes(params: Record<string, unknown>) {
  const results: AlertePanneRow[] = [];
  const perPage = 100; // backend caps per_page at 100
  for (let page = 1; page <= 60; page++) {
    const res = await api.get<Paginated<AlertePanneRow>>("/api/alertes-pannes/", {
      params: { ...params, page, per_page: perPage },
    });
    const rows = res.data.results ?? [];
    results.push(...rows);
    if (rows.length < perPage) break;
  }
  return results;
}

export default function ProductionDashboardPage() {
  const theme = useTheme();
  const chart = useChartTheme();
  /** Hauteurs graphiques : moins haut sur mobile pour limiter le scroll « tout blanc ». */
  const typeChartBoxSx = { height: { xs: 400, sm: 520, md: 600 } } as const;
  const posteChartBoxSx = { height: { xs: 340, sm: 420, md: 500 } } as const;
  const paretoGraphRef = useRef<HTMLDivElement | null>(null);
  const paretoPosteGraphRef = useRef<HTMLDivElement | null>(null);
  const [searchParams] = useSearchParams();
  const lockedShift = useLockedShift();
  const [jour, setJour] = useState(() => {
    const raw = (searchParams.get("jour") || searchParams.get("date") || "").trim();
    return /^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : isoCalendarYesterday();
  });
  /** Toujours « tous shifts » sauf si le profil impose un shift (PSP). */
  const effectiveShift = (lockedShift as ShiftCode | undefined) ?? ("" as const);
  const [categorie, setCategorie] = useState<"" | ArretCategoryFilter>("");
  /** Filtre poste pour le Pareto « types × moyen » uniquement (tableau + graphique du haut). */
  const [paretoPosteId, setParetoPosteId] = useState("");
  const categorieLabelActive = useMemo(
    () => (categorie ? CATEGORIE_OPTIONS.find((o) => o.value === categorie)?.label ?? categorie : null),
    [categorie]
  );

  const { data: paretoPostesList = [] } = useQuery({
    queryKey: ["berceau-postes-dashboard-pareto"],
    queryFn: async () =>
      (await api.get<{ results: BerceauPosteOption[] }>("/api/berceau/postes/", { params: { equipe: "Berceau" } })).data
        .results,
  });

  const paretoPosteLabel = useMemo(() => {
    if (!paretoPosteId) return null;
    const p = paretoPostesList.find((x) => String(x.id) === paretoPosteId);
    return p?.name?.trim() || null;
  }, [paretoPosteId, paretoPostesList]);

  const percentParetoQuery = useQuery({
    queryKey: [
      "dashboard-pareto-types-percent",
      jour,
      effectiveShift || "__all__",
      categorie || "__all_cat__",
      paretoPosteId || "__all_postes__",
    ],
    enabled: !!jour,
    staleTime: 0,
    queryFn: async () => {
      const dates = listIsoDates(jour, jour);
      if (!dates.length) return null;

      const shiftFilter = (effectiveShift || "").trim() as ShiftCode | "";
      const categoryParam = categorie.trim() ? categorie.trim().toLowerCase() : "";

      const prodRowsByDay = new Map<string, ProductionBerceauRow[]>();
      await Promise.all(
        dates.map(async (d) => {
          const rows = await fetchAllBerceauProductionForDate(d);
          prodRowsByDay.set(
            d,
            shiftFilter ? rows.filter((p) => p.shift === shiftFilter) : rows
          );
        })
      );

      const alertesByDay = await Promise.all(
        dates.map(async (d) => {
          const rows = await fetchAllAlertesPannes({
            date: d,
            equipe: "Berceau",
            ...(shiftFilter ? { shift: shiftFilter } : {}),
            ...(categoryParam ? { category: categoryParam } : {}),
          });
          return { day: d, rows };
        })
      );

      const shiftsByDay = new Map<string, Set<string>>();
      for (const { day, rows } of alertesByDay) {
        const set = shiftsByDay.get(day) ?? new Set<string>();
        for (const r of rows) {
          set.add(r.shift);
        }
        shiftsByDay.set(day, set);
      }

      const prodRowsForImpactByDay = new Map<string, ProductionBerceauRow[]>();
      for (const d of dates) {
        const prodAll = prodRowsByDay.get(d) ?? [];
        const want = shiftsByDay.get(d) ?? new Set<string>();
        prodRowsForImpactByDay.set(d, productionRowsForImpactDenominators(prodAll, want, shiftFilter));
      }

      // Par jour : minutes par (type × moyen × heure H1–8 × diversité), formule par seau, somme des % par ligne type+moyen.
      // (Σ min / diviseur) × (100 / objectif_jour).
      // « Tous shifts » : objectif_jour = Σ (objectif_h1…h8) sur chaque fiche production des shifts A+B+N
      // (chaque heure compte l’objectif de la ligne A1 ou A3 de ce shift) ; toutes les minutes d’arrêt du jour
      // partagent ce même dénominateur.
      const byType = new Map<
        string,
        {
          type: string;
          panne_type_nom: string;
          moyen_nom: string;
          poste_nom: string;
          pctA1: number;
          pctA3: number;
          minutesA1: number;
          minutesA3: number;
        }
      >();
      const byPoste = new Map<
        string,
        { poste: string; pctA1: number; pctA3: number; minutesA1: number; minutesA3: number }
      >();
      for (const { day, rows } of alertesByDay) {
        const prodRowsDay = prodRowsByDay.get(day) ?? [];
        const prodRowsForDenoms = prodRowsForImpactByDay.get(day) ?? [];
        const objectifShift = sumAllHourlyObjectifsAcrossRows(prodRowsForDenoms);
        const prodByShift = new Map<string, ProductionBerceauRow[]>();
        for (const pr of prodRowsDay) {
          const k = `${pr.date.slice(0, 10)}|${pr.shift}`;
          const arr = prodByShift.get(k) ?? [];
          arr.push(pr);
          prodByShift.set(k, arr);
        }
        const buckets = new Map<string, number>();
        const posteBuckets = new Map<string, number>();
        const posteIdFilter = Number(paretoPosteId);
        const filterByPoste = Number.isFinite(posteIdFilter) && posteIdFilter > 0;
        for (const row of rows) {
          const rowDay = row.date.slice(0, 10);
          const prodRowsForAlert = prodByShift.get(`${rowDay}|${row.shift}`) ?? [];
          if (!filterByPoste || Number(row.poste_id) === posteIdFilter) {
            addRowToParetoMinuteBuckets(buckets, row, prodRowsForAlert);
          }
          addRowToParetoPosteMinuteBuckets(posteBuckets, row, prodRowsForAlert);
        }
        const { byType: dayByType } = analyzeParetoMinuteBuckets(buckets, objectifShift);
        for (const [label, v] of dayByType) {
          if (!byType.has(label)) {
            byType.set(label, {
              type: v.type,
              panne_type_nom: v.panne_type_nom,
              moyen_nom: v.moyen_nom,
              poste_nom: v.poste_nom,
              pctA1: 0,
              pctA3: 0,
              minutesA1: 0,
              minutesA3: 0,
            });
          }
          const entry = byType.get(label)!;
          entry.pctA1 += v.pctA1;
          entry.pctA3 += v.pctA3;
          entry.minutesA1 += v.minutesA1;
          entry.minutesA3 += v.minutesA3;
        }
        const { byPoste: dayByPoste } = analyzeParetoPosteMinuteBuckets(posteBuckets, objectifShift);
        for (const [posteName, v] of dayByPoste) {
          if (!byPoste.has(posteName)) {
            byPoste.set(posteName, { poste: posteName, pctA1: 0, pctA3: 0, minutesA1: 0, minutesA3: 0 });
          }
          const pe = byPoste.get(posteName)!;
          pe.pctA1 += v.pctA1;
          pe.pctA3 += v.pctA3;
          pe.minutesA1 += v.minutesA1;
          pe.minutesA3 += v.minutesA3;
        }
      }

      const rowsOut = Array.from(byType.values()).map((r) => ({
        typeArret: r.type,
        panne_type_nom: r.panne_type_nom,
        moyen_nom: r.moyen_nom,
        poste_nom: r.poste_nom,
        pctA1: r.pctA1,
        pctA3: r.pctA3,
        minutesA1: r.minutesA1,
        minutesA3: r.minutesA3,
      }));

      rowsOut.sort((a, b) => b.pctA1 + b.pctA3 - (a.pctA1 + a.pctA3));
      const limited = rowsOut.slice(0, MAX_BARS_PER_CHART);
      const totalPct = limited.reduce((s, r) => s + r.pctA1 + r.pctA3, 0);
      let cum = 0;
      const withCum = limited.map((r) => {
        const totalRowPct = r.pctA1 + r.pctA3;
        cum += totalPct > 0 ? (totalRowPct / totalPct) * 100 : 0;
        return { ...r, totalPct: totalRowPct, cumulePercent: cum };
      });

      const posteRowsOut = Array.from(byPoste.values()).map((r) => ({
        poste: r.poste,
        pctA1: r.pctA1,
        pctA3: r.pctA3,
        minutesA1: r.minutesA1,
        minutesA3: r.minutesA3,
      }));
      posteRowsOut.sort((a, b) => b.pctA1 + b.pctA3 - (a.pctA1 + a.pctA3));
      const posteLimited = posteRowsOut.slice(0, MAX_BARS_PER_CHART);
      const posteTotalPct = posteLimited.reduce((s, r) => s + r.pctA1 + r.pctA3, 0);
      let posteCum = 0;
      const posteWithCum = posteLimited.map((r) => {
        const totalRowPct = r.pctA1 + r.pctA3;
        posteCum += posteTotalPct > 0 ? (totalRowPct / posteTotalPct) * 100 : 0;
        const tempsArretMin = r.minutesA1 + r.minutesA3;
        return { ...r, totalPct: totalRowPct, cumulePercent: posteCum, tempsArretMin };
      });

      const productionKpis = computeProductionKpis(prodRowsForImpactByDay, dates, shiftFilter);
      return { rows: withCum, posteImpactRows: posteWithCum, productionKpis };
    },
  });

  const roNroTrendQuery = useQuery({
    queryKey: ["dashboard-ro-nro-trend", jour, effectiveShift || "__all__"],
    enabled: Boolean(jour),
    queryFn: async () => {
      const date_to = jour;
      const date_from = isoDateMinusDays(jour, 13);
      const params: Record<string, string> = { date_from, date_to };
      if (effectiveShift) params.shift = effectiveShift;
      const { data } = await api.get<DashboardRoNroTrendResponse>("/api/dashboard/ro-nro-trend/", { params });
      return data;
    },
  });

  const posteImpactRows = percentParetoQuery.data?.posteImpactRows ?? [];
  const posteChartData = posteImpactRows;
  const posteChartDataLimited = posteChartData.slice(0, 20);
  const hasPostePareto = posteImpactRows.length > 0;
  const seuilPosteIdx = posteImpactRows.findIndex((v) => Number(v.cumulePercent ?? 0) >= 80);
  const seuilPoste = seuilPosteIdx >= 0 ? String(posteImpactRows[seuilPosteIdx].poste) : undefined;
  const percentRows = (percentParetoQuery.data?.rows ?? []) as DashboardParetoTypeRow[];
  const hasTypePareto = percentRows.length > 0;
  const productionKpis = percentParetoQuery.data?.productionKpis ?? null;
  const typeChartDataLimited = percentRows;
  const typeTableData = percentRows.map((row) => ({
    typeArret: row.typeArret,
    panne_type_nom: row.panne_type_nom,
    moyen_nom: row.moyen_nom,
    totalPct: Number(row.pctA1 || 0) + Number(row.pctA3 || 0),
    pctA1: Number(row.pctA1 || 0),
    pctA3: Number(row.pctA3 || 0),
    cumulePercent: Number(row.cumulePercent || 0),
  }));
  const seuilTypeIdx = percentRows.findIndex((v) => Number(v.cumulePercent ?? 0) >= 80);
  const seuilType = seuilTypeIdx >= 0 ? String(percentRows[seuilTypeIdx].typeArret) : undefined;
  const topType =
    percentRows.length > 0
      ? {
          label: String(percentRows[0].typeArret),
          minutes: Number(percentRows[0].minutesA1 ?? 0) + Number(percentRows[0].minutesA3 ?? 0),
          impactPct: Number(percentRows[0].pctA1 || 0) + Number(percentRows[0].pctA3 || 0),
        }
      : null;

  const roNroMiniChartData = useMemo(() => {
    const d = roNroTrendQuery.data;
    if (!d?.labels?.length) return [];
    return d.labels.map((iso, i) => ({
      label: formatTrendAxisDate(iso),
      iso,
      ro: d.series.ro_percent[i] ?? 0,
      nroPct: d.series.nro_percent[i] ?? 0,
      isSelected: iso === jour,
    }));
  }, [roNroTrendQuery.data, jour]);

  const selectedDayTrend = useMemo(() => {
    const d = roNroTrendQuery.data;
    if (!d?.labels?.length || !jour) return null;
    const i = d.labels.indexOf(jour);
    if (i < 0) return null;
    return {
      ro: d.series.ro_percent[i] ?? null,
      nro: d.series.nro_percent[i] ?? null,
    };
  }, [roNroTrendQuery.data, jour]);

  const displayRoValue =
    selectedDayTrend?.ro != null
      ? `${Number(selectedDayTrend.ro).toFixed(1)} %`
      : productionKpis?.roPercent != null
        ? `${productionKpis.roPercent.toFixed(1)} %`
        : "—";
  const displayNroValue =
    selectedDayTrend?.nro != null
      ? `${Number(selectedDayTrend.nro).toFixed(1)} %`
      : productionKpis?.nroPercent != null
        ? `${productionKpis.nroPercent.toFixed(1)} %`
        : "—";

  const handleExportParetoTypesExcel = useCallback(() => {
    if (!percentRows.length) return;
    exportParetoTypesExcel({
      rows: percentRows.map((r) => ({
        typeArret: String(r.typeArret),
        panne_type_nom: r.panne_type_nom,
        moyen_nom: r.moyen_nom,
        pctA1: Number(r.pctA1 || 0),
        pctA3: Number(r.pctA3 || 0),
        minutesA1: Number(r.minutesA1 ?? 0),
        minutesA3: Number(r.minutesA3 ?? 0),
        cumulePercent: Number(r.cumulePercent || 0),
      })),
      jourIso: jour,
      shiftLabel: effectiveShift ? `Shift ${effectiveShift}` : "Tous shifts (A, B, N)",
      categoryLabel: categorieLabelActive,
      categorySlug: categorie || undefined,
      posteFilterLabel: paretoPosteLabel,
    });
  }, [percentRows, jour, effectiveShift, categorieLabelActive, categorie, paretoPosteLabel]);

  return (
    <Stack spacing={2.5}>
      <Paper
        elevation={0}
        sx={{
          py: { xs: 1, sm: 1.25 },
          px: { xs: 1, sm: 1.5 },
          mb: 1.5,
          borderRadius: 2,
        }}
      >
        <Stack spacing={{ xs: 1.25, sm: 1 }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems={{ xs: "stretch", sm: "center" }}
            justifyContent="space-between"
            spacing={1.25}
            flexWrap="wrap"
            useFlexGap
          >
            <Typography variant="subtitle1" fontWeight={800} sx={{ lineHeight: 1.25 }}>
              Dashboard Production
              <Typography component="span" variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.25 }}>
                Pareto
              </Typography>
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ flexShrink: 0 }}>
              <Button
                component={RouterLink}
                to="/berceau/production"
                startIcon={<ArrowBackIcon />}
                variant="outlined"
                size="small"
              >
                Retour Production
              </Button>
              <Button
                variant="contained"
                size="small"
                startIcon={<DownloadIcon />}
                onClick={() => void exportElementPng(paretoGraphRef.current, "pareto_types_arrets.png")}
                disabled={!hasTypePareto}
              >
                Exporter screenshot
              </Button>
            </Stack>
          </Stack>

          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1.25}
            alignItems={{ xs: "stretch", sm: "center" }}
            flexWrap="wrap"
            useFlexGap
          >
            <GiDatePicker
              label="Jour"
              value={jour}
              onChange={(v) => {
                const next = (v || "").trim();
                setJour(/^\d{4}-\d{2}-\d{2}$/.test(next) ? next : isoCalendarYesterday());
              }}
              sx={{ maxWidth: 220 }}
              size="small"
            />
            <TextField
              select
              size="small"
              label="Catégorie"
              value={categorie}
              onChange={(e) => setCategorie((e.target.value || "") as "" | ArretCategoryFilter)}
              sx={{ minWidth: 180, maxWidth: 280 }}
              placeholder="Types et postes"
            >
              {CATEGORIE_OPTIONS.map((opt) => (
                <MenuItem key={opt.value || "all"} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              size="small"
              label="Poste (Pareto types)"
              value={paretoPosteId}
              onChange={(e) => setParetoPosteId(e.target.value)}
              sx={{ minWidth: 220, maxWidth: 320 }}
              helperText="Filtre uniquement le tableau et le graphique « types × moyen » ci‑dessous."
              FormHelperTextProps={{ sx: { maxWidth: 320 } }}
            >
              <MenuItem value="">
                <em>Tous les postes</em>
              </MenuItem>
              {paretoPostesList.map((p) => (
                <MenuItem key={p.id} value={String(p.id)}>
                  {p.name}
                </MenuItem>
              ))}
            </TextField>
            {lockedShift && (
              <Typography variant="caption" color="text.secondary" sx={{ alignSelf: { sm: "center" } }}>
                Shift imposé : {lockedShift}
              </Typography>
            )}
          </Stack>
        </Stack>
      </Paper>

      {percentParetoQuery.isLoading && (
        <Paper sx={{ p: 2, borderRadius: 2 }}>
          <Typography color="text.secondary">Chargement du Pareto...</Typography>
        </Paper>
      )}

      {!percentParetoQuery.isLoading &&
        percentParetoQuery.isSuccess &&
        !hasTypePareto &&
        !productionKpis && (
        <Paper sx={{ p: 2, borderRadius: 2 }}>
          <Typography color="text.secondary">
            Aucune donnée pour ce périmètre (arrêts UEP Berceau + fiche production avec objectifs H1–H8 renseignés
            {effectiveShift ? ` · shift ${effectiveShift}` : " · tous shifts"}
            {categorie ? ` · catégorie « ${categorieLabelActive} »` : ""}
            {paretoPosteLabel ? ` · poste « ${paretoPosteLabel} »` : ""}). Réessaie avec un autre jour, « Tous les postes », ou une autre catégorie.
          </Typography>
        </Paper>
      )}

      {!percentParetoQuery.isLoading &&
        percentParetoQuery.isSuccess &&
        !hasTypePareto &&
        productionKpis && (
        <Paper sx={{ p: 2, borderRadius: 2 }}>
          <Typography color="text.secondary">
            Aucun arrêt enregistré pour ces filtres sur la journée sélectionnée. Les indicateurs RO / NRO jour
            (Berceau) et les tendances % ci‑dessous restent disponibles.
            {effectiveShift ? ` · shift ${effectiveShift}` : ""}
            {categorie ? ` · catégorie « ${categorieLabelActive} »` : ""}
            {paretoPosteLabel ? ` · poste « ${paretoPosteLabel} »` : ""}
          </Typography>
        </Paper>
      )}

      {percentParetoQuery.isError && (
        <Paper sx={{ p: 2, borderRadius: 2 }}>
          <Typography color="error.main">
            Erreur chargement Pareto %. Vérifie les données ou réessaie.
          </Typography>
        </Paper>
      )}

      {!jour && (
        <Paper sx={{ p: 2, borderRadius: 2 }}>
          <Typography color="text.secondary">Sélectionne un jour pour calculer le %.</Typography>
        </Paper>
      )}

      {jour && (
        <RoNroTrendSection
          jour={jour}
          data={roNroMiniChartData}
          loading={roNroTrendQuery.isLoading}
          error={roNroTrendQuery.isError}
          roValue={displayRoValue}
          nroValue={displayNroValue}
        />
      )}

      {hasTypePareto && (
        <Stack spacing={2}>
          <Paper
            elevation={0}
            sx={{
              width: "100%",
              maxWidth: { md: 720 },
              borderRadius: 3,
              overflow: "hidden",
              border: `1px solid ${alpha(theme.palette.divider, 0.45)}`,
              boxShadow: `0 10px 40px ${alpha("#000", 0.28)}, 0 0 0 1px ${alpha(theme.palette.common.white, 0.04)}`,
            }}
          >
            <Stack
              sx={{
                p: 2.5,
                background: `linear-gradient(165deg, ${alpha(theme.palette.secondary.main, 0.14)} 0%, ${alpha(theme.palette.secondary.main, 0.04)} 55%, transparent 100%)`,
              }}
              spacing={1}
            >
              <Typography
                variant="overline"
                sx={{
                  letterSpacing: "0.12em",
                  fontWeight: 700,
                  fontSize: "0.65rem",
                  color: alpha(theme.palette.text.secondary, 0.95),
                }}
              >
                Arrêt long
              </Typography>
              <Typography variant="h6" fontWeight={800} sx={{ lineHeight: 1.35, wordBreak: "break-word" }}>
                {topType ? topType.label : "—"}
              </Typography>
              {topType && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Temps d&apos;arrêt : {topType.minutes.toLocaleString("fr-FR")} min · Impact :{" "}
                  {topType.impactPct.toFixed(1)} %
                </Typography>
              )}
            </Stack>
          </Paper>

          <Paper sx={{ p: 2.5, borderRadius: 3, position: "relative" }} ref={paretoGraphRef}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ position: "absolute", top: 20, right: 20, fontWeight: 600 }}
            >
              {shortDate(jour)}
            </Typography>
            <Typography variant="h6" fontWeight={800} gutterBottom sx={{ pr: 10 }}>
              Pareto des types d&apos;arrêt
              {effectiveShift ? ` (jour · shift ${effectiveShift})` : " (jour · tous shifts)"}
              {categorieLabelActive ? ` · ${categorieLabelActive}` : ""}
              {paretoPosteLabel ? ` · poste ${paretoPosteLabel}` : ""}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              {seuilType ? `Seuil 80 % atteint à : ${seuilType}` : ""}
            </Typography>
            <Box sx={{ width: "100%", ...typeChartBoxSx, minHeight: { xs: 260, md: 300 }, ...CHART_OVERFLOW_SX }}>
              <SafeResponsiveContainer minHeight={260} boxSx={typeChartBoxSx}>
                <ComposedChart data={typeChartDataLimited} margin={chart.margins.pareto}>
                  <ChartGradientDefs chart={chart} />
                  <CartesianGrid {...chart.grid} />
                  <XAxis
                    dataKey="typeArret"
                    height={132}
                    tickMargin={8}
                    interval={0}
                    padding={{ left: 8, right: 8 }}
                    tick={(p) => <ParetoCategoryAxisTick {...p} fill={chart.colors.tickFill} />}
                  />
                  <YAxis
                    yAxisId="left"
                    width={48}
                    tickFormatter={(v) => `${Number(v).toFixed(1)}%`}
                    tick={chart.axis.tick}
                    axisLine={chart.axis.axisLine}
                    tickLine={chart.axis.tickLine}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    domain={[0, 100]}
                    tickFormatter={(v) => `${Number(v).toFixed(0)}%`}
                    tick={chart.axis.tick}
                    axisLine={chart.axis.axisLine}
                    tickLine={chart.axis.tickLine}
                  />
                  <Tooltip content={<ParetoComboTooltip chart={chart} />} />
                  <ReferenceLine
                    yAxisId="right"
                    y={80}
                    stroke={chart.reference80.stroke}
                    strokeDasharray={chart.reference80.strokeDasharray}
                    label={{
                      value: "Seuil 80%",
                      position: "insideTopRight",
                      fill: chart.reference80.labelFill,
                      fontWeight: 700,
                    }}
                  />
                  {seuilType && (
                    <ReferenceLine
                      x={seuilType}
                      stroke={chart.reference80.stroke}
                      strokeDasharray={chart.reference80.strokeDasharray}
                    />
                  )}
                  {typeChartDataLimited.map((row) => (
                    <ReferenceLine
                      key={`projection-${row.typeArret}`}
                      yAxisId="right"
                      segment={[
                        { x: row.typeArret, y: 0 },
                        { x: row.typeArret, y: row.cumulePercent },
                      ]}
                      stroke={chart.projection.stroke}
                      strokeDasharray={chart.projection.strokeDasharray}
                    />
                  ))}
                  <Bar
                    yAxisId="left"
                    dataKey="totalPct"
                    name="Impact"
                    fill={`url(#${chart.ids.barGreen})`}
                    maxBarSize={44}
                    shape={paretoGradientBarShape(chart, 3, 4, "green")}
                    isAnimationActive
                    animationDuration={chart.animation.barDuration}
                    animationEasing={chart.animation.barEasing}
                  >
                    <LabelList dataKey="totalPct" position="top" content={paretoBarValueLabel()} />
                  </Bar>
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="cumulePercent"
                    name="Cumulé"
                    stroke={`url(#${chart.ids.paretoLine})`}
                    strokeWidth={3}
                    style={{ filter: `url(#${chart.ids.lineGlowRed})` }}
                    dot={{ r: 4.5, fill: chart.colors.seriesRed, stroke: alpha("#fff", 0.35), strokeWidth: 1 }}
                    activeDot={{ r: 7, fill: chart.colors.seriesRed, stroke: "#fff", strokeWidth: 2 }}
                    isAnimationActive
                    animationDuration={chart.animation.lineDuration}
                  >
                    <LabelList
                      dataKey="cumulePercent"
                      content={({ x, y, value }) => {
                        if (x == null || y == null || value == null) return null;
                        return (
                          <text
                            x={Number(x)}
                            y={Number(y) - 10}
                            fill={chart.colors.seriesRed}
                            fontSize={10}
                            fontWeight={700}
                            textAnchor="middle"
                          >
                            {`${Number(value).toFixed(1)}%`}
                          </text>
                        );
                      }}
                    />
                  </Line>
                </ComposedChart>
              </SafeResponsiveContainer>
            </Box>
          </Paper>
        </Stack>
      )}

      <Divider sx={{ my: 0.5 }} />

      <Stack spacing={1.5}>
        {percentParetoQuery.isLoading && (
          <Paper sx={{ p: 2, borderRadius: 2 }}>
            <Typography color="text.secondary">Chargement du Pareto postes…</Typography>
          </Paper>
        )}
        {percentParetoQuery.isError && (
          <Paper sx={{ p: 2, borderRadius: 2 }}>
            <Typography color="error.main">Erreur chargement Pareto (types et postes).</Typography>
          </Paper>
        )}
        {!percentParetoQuery.isLoading && !hasPostePareto && jour && (
          <Paper sx={{ p: 2, borderRadius: 2 }}>
            <Typography color="text.secondary">
              Aucune donnée poste pour ce jour
              {categorieLabelActive ? ` (catégorie « ${categorieLabelActive} »)` : ""}.
            </Typography>
          </Paper>
        )}
        {hasPostePareto && (
          <Paper sx={{ p: 2.5, borderRadius: 3, position: "relative" }} ref={paretoPosteGraphRef}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 0.5 }}>
              <Typography variant="h6" fontWeight={800} sx={{ pr: 2 }}>
                Pareto des postes (impact production + courbe cumulée)
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center" flexShrink={0}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                  {shortDate(jour)}
                </Typography>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<DownloadIcon />}
                  onClick={() => void exportElementPng(paretoPosteGraphRef.current, "pareto_postes_arrets.png")}
                >
                  PNG
                </Button>
              </Stack>
            </Stack>
            <Box sx={{ width: "100%", ...posteChartBoxSx, minHeight: { xs: 240, md: 260 }, ...CHART_OVERFLOW_SX }}>
              <SafeResponsiveContainer minHeight={240} boxSx={posteChartBoxSx}>
                <ComposedChart data={posteChartDataLimited} margin={chart.margins.paretoPoste}>
                  <ChartGradientDefs chart={chart} />
                  <CartesianGrid {...chart.grid} />
                  <XAxis
                    dataKey="poste"
                    height={128}
                    tickMargin={8}
                    interval={0}
                    padding={{ left: 8, right: 8 }}
                    tick={(p) => <ParetoCategoryAxisTick {...p} fill={chart.colors.tickFill} />}
                  />
                  <YAxis
                    yAxisId="left"
                    width={48}
                    tickFormatter={(v) => `${Number(v).toFixed(1)}%`}
                    tick={chart.axis.tick}
                    axisLine={chart.axis.axisLine}
                    tickLine={chart.axis.tickLine}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    domain={[0, 100]}
                    tickFormatter={(v) => `${Number(v).toFixed(0)}%`}
                    tick={chart.axis.tick}
                    axisLine={chart.axis.axisLine}
                    tickLine={chart.axis.tickLine}
                  />
                  <Tooltip content={<ParetoComboTooltip chart={chart} />} />
                  <ReferenceLine
                    yAxisId="right"
                    y={80}
                    stroke={chart.reference80.stroke}
                    strokeDasharray={chart.reference80.strokeDasharray}
                    label={{
                      value: "Seuil 80%",
                      position: "insideTopRight",
                      fill: chart.reference80.labelFill,
                      fontWeight: 700,
                    }}
                  />
                  {seuilPoste && (
                    <ReferenceLine
                      x={seuilPoste}
                      stroke={chart.reference80.stroke}
                      strokeDasharray={chart.reference80.strokeDasharray}
                    />
                  )}
                  {posteChartDataLimited.map((row) => (
                    <ReferenceLine
                      key={`poste-proj-${row.poste}`}
                      yAxisId="right"
                      segment={[
                        { x: row.poste, y: 0 },
                        { x: row.poste, y: row.cumulePercent },
                      ]}
                      stroke={chart.projection.stroke}
                      strokeDasharray={chart.projection.strokeDasharray}
                    />
                  ))}
                  <Bar
                    yAxisId="left"
                    dataKey="totalPct"
                    name="Impact"
                    fill={`url(#${chart.ids.barGreen})`}
                    maxBarSize={42}
                    shape={paretoGradientBarShape(chart, 3, 4, "green")}
                    isAnimationActive
                    animationDuration={chart.animation.barDuration}
                    animationEasing={chart.animation.barEasing}
                  >
                    <LabelList dataKey="totalPct" position="top" content={paretoBarValueLabel()} />
                  </Bar>
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="cumulePercent"
                    name="Cumulé"
                    stroke={`url(#${chart.ids.paretoLine})`}
                    strokeWidth={3}
                    style={{ filter: `url(#${chart.ids.lineGlowRed})` }}
                    dot={{ r: 4.5, fill: chart.colors.seriesRed, stroke: alpha("#fff", 0.35), strokeWidth: 1 }}
                    activeDot={{ r: 7, fill: chart.colors.seriesRed, stroke: "#fff", strokeWidth: 2 }}
                    isAnimationActive
                    animationDuration={chart.animation.lineDuration}
                  >
                    <LabelList
                      dataKey="cumulePercent"
                      content={({ x, y, value }) => {
                        if (x == null || y == null || value == null) return null;
                        return (
                          <text
                            x={Number(x)}
                            y={Number(y) - 10}
                            fill={chart.colors.seriesRed}
                            fontSize={10}
                            fontWeight={700}
                            textAnchor="middle"
                          >
                            {`${Number(value).toFixed(1)}%`}
                          </text>
                        );
                      }}
                    />
                  </Line>
                </ComposedChart>
              </SafeResponsiveContainer>
            </Box>
          </Paper>
        )}
      </Stack>

      {hasTypePareto && (
        <Stack spacing={1.5} sx={{ mt: 1 }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1} sx={{ px: 0.25 }}>
            <Typography variant="subtitle2" color="text.secondary" fontWeight={600}>
              Tableau Pareto (types n°1 à {typeTableData.length})
            </Typography>
            <Button
              size="small"
              variant="outlined"
              startIcon={<TableChartIcon />}
              onClick={handleExportParetoTypesExcel}
              disabled={!typeTableData.length}
            >
              Exporter Excel
            </Button>
          </Stack>

          <TableContainer
            component={Paper}
            sx={{ borderRadius: 3, maxHeight: { xs: 260, sm: 320, md: 480 }, overflow: "auto" }}
          >
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  <TableCell>Type d&apos;arrêt</TableCell>
                  <TableCell>Moyen</TableCell>
                  <TableCell align="right">% total</TableCell>
                  <TableCell align="right">% A1</TableCell>
                  <TableCell align="right">% A3</TableCell>
                  <TableCell align="right">Cumulé %</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {typeTableData.map((row, idx) => (
                  <TableRow key={`pareto-row-${idx}-${row.typeArret}`}>
                    <TableCell>{idx + 1}</TableCell>
                    <TableCell>{row.panne_type_nom}</TableCell>
                    <TableCell>{row.moyen_nom?.trim() ? row.moyen_nom : "—"}</TableCell>
                    <TableCell align="right">{row.totalPct.toFixed(2)}%</TableCell>
                    <TableCell align="right">{row.pctA1.toFixed(2)}%</TableCell>
                    <TableCell align="right">{row.pctA3.toFixed(2)}%</TableCell>
                    <TableCell align="right">{row.cumulePercent.toFixed(2)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Stack>
      )}
    </Stack>
  );
}