import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { Link as RouterLink } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useEffect, useMemo, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { useLockedShift, useMe } from "../../auth/AuthContext";
import { GiDatePicker, GiDatePickerRhf } from "../../components/GiDatePicker";
import { api, formatApiError } from "../../api/client";
import type { AlertePanneRow, Paginated, ProductionBerceauRow } from "../../api/types";
import { computeHourlyTotals } from "./productionHourlyUtils";
import ProductionShiftComparisonChart from "./ProductionShiftComparisonChart";
import {
  berceauEffectiveObjectif,
  berceauRoPercent,
  formatDateGroupLabel,
  formatPercentFr,
  isoCalendarToday,
  nroPercentFromRo,
} from "./productionMetrics";

function berceauHourRoPercent(production: number, objectif: number): number | null {
  if (objectif <= 0) return null;
  return Math.round((production / objectif) * 10000) / 100;
}

function BerceauProductionDetailPanel({ row }: { row: ProductionBerceauRow }) {
  const validatedSet = useMemo(() => new Set(row.validated_hours ?? []), [row.validated_hours]);
  const diversities = useMemo(
    () => Array.from(new Set(HOURS.map((h) => row[`line_h${h}` as const]).filter(Boolean))).join(" / ") || "—",
    [row]
  );
  const hourlySums = useMemo(
    () =>
      HOURS.reduce(
        (acc, h) => {
          acc.objectif += Number(row[`objectif_h${h}`] ?? 0);
          acc.production += Number(row[`production_h${h}`] ?? 0);
          acc.rebut += Number(row[`rebut_h${h}`] ?? 0);
          acc.arret += Number(row[`temps_arrets_h${h}`] ?? 0);
          return acc;
        },
        { objectif: 0, production: 0, rebut: 0, arret: 0 }
      ),
    [row]
  );
  const ro = berceauRoPercent(row);
  const nro = nroPercentFromRo(ro);

  return (
    <Stack spacing={2.5} sx={{ mt: 0.5 }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
          gap: 1.5,
        }}
      >
        <Paper variant="outlined" sx={{ p: 1.25, borderRadius: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Date · Shift
          </Typography>
          <Typography variant="body2" fontWeight={700}>
            {row.date.slice(0, 10)} · Shift {row.shift}
          </Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 1.25, borderRadius: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Diversité (H1–H8)
          </Typography>
          <Typography variant="body2" fontWeight={700}>
            {diversities}
          </Typography>
        </Paper>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(3, 1fr)", md: "repeat(6, 1fr)" },
          gap: 1,
        }}
      >
        {[
          { label: "Objectif shift", value: row.objectif },
          { label: "Volume", value: row.volume },
          { label: "Rebut", value: row.rebut },
          { label: "Arrêt total (min)", value: row.temps_arrets },
          { label: "NRO volume", value: row.nro_total },
          { label: "RO %", value: formatPercentFr(ro) },
          { label: "NRO %", value: formatPercentFr(nro) },
          { label: "Σ production H1–H8", value: hourlySums.production },
        ].map((item) => (
          <Paper key={item.label} variant="outlined" sx={{ p: 1, borderRadius: 1.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.3 }}>
              {item.label}
            </Typography>
            <Typography variant="body2" fontWeight={700} sx={{ fontVariantNumeric: "tabular-nums" }}>
              {item.value}
            </Typography>
          </Paper>
        ))}
      </Box>

      <Typography variant="subtitle2" fontWeight={800}>
        Détail horaire du shift {row.shift}
      </Typography>

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Heure</TableCell>
              <TableCell>Diversité</TableCell>
              <TableCell align="right">Objectif</TableCell>
              <TableCell align="right">Production</TableCell>
              <TableCell align="right">Rebut</TableCell>
              <TableCell align="right">Arrêt (min)</TableCell>
              <TableCell align="right">RO %</TableCell>
              <TableCell align="center">Statut</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {HOURS.map((h) => {
              const line = row[`line_h${h}` as const] || "—";
              const objectif = Number(row[`objectif_h${h}`] ?? 0);
              const production = Number(row[`production_h${h}`] ?? 0);
              const rebut = Number(row[`rebut_h${h}`] ?? 0);
              const arret = Number(row[`temps_arrets_h${h}`] ?? 0);
              const hourRo = berceauHourRoPercent(production, objectif);
              const validated = validatedSet.has(h);
              return (
                <TableRow key={h} hover>
                  <TableCell sx={{ fontWeight: 700 }}>H{h}</TableCell>
                  <TableCell>{line}</TableCell>
                  <TableCell align="right">{objectif}</TableCell>
                  <TableCell align="right">{production}</TableCell>
                  <TableCell align="right">{rebut}</TableCell>
                  <TableCell align="right">{arret}</TableCell>
                  <TableCell align="right">
                    {hourRo != null ? formatPercentFr(hourRo) : "—"}
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      size="small"
                      label={validated ? "Validé" : "Brouillon"}
                      color={validated ? "success" : "default"}
                      variant={validated ? "filled" : "outlined"}
                      sx={{ height: 22, fontSize: "0.7rem" }}
                    />
                  </TableCell>
                </TableRow>
              );
            })}
            <TableRow sx={{ bgcolor: (t) => alpha(t.palette.primary.main, 0.06) }}>
              <TableCell colSpan={2} sx={{ fontWeight: 800 }}>
                Total shift
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>
                {hourlySums.objectif}
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>
                {hourlySums.production}
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>
                {hourlySums.rebut}
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>
                {hourlySums.arret}
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>
                {formatPercentFr(ro)}
              </TableCell>
              <TableCell />
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>

      {row.validated_hours?.length ? (
        <Typography variant="caption" color="text.secondary">
          Heures validées : H{row.validated_hours.join(", H")}
        </Typography>
      ) : (
        <Typography variant="caption" color="text.secondary">
          Aucune heure validée sur cette fiche.
        </Typography>
      )}
    </Stack>
  );
}

type HourIndex = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
const HOURS: HourIndex[] = [1, 2, 3, 4, 5, 6, 7, 8];
const SHIFTS = ["A", "B", "N"] as const;
type ShiftCode = (typeof SHIFTS)[number];
type ShiftView = ShiftCode | "ALL";

function majorityLineFromHours(values: Record<string, unknown>): "A1" | "A3" {
  let a1 = 0;
  let a3 = 0;
  for (const h of HOURS) {
    const v = String(values[`line_h${h}`] ?? "").trim();
    if (v === "A1") a1 += 1;
    else if (v === "A3") a3 += 1;
  }
  return a3 > a1 ? "A3" : "A1";
}

async function fetchAllBerceauProductionRows(
  baseParams: Record<string, string | number | undefined>
): Promise<ProductionBerceauRow[]> {
  const out: ProductionBerceauRow[] = [];
  let page = 1;
  const per_page = 100;
  while (true) {
    const { data: res } = await api.get<Paginated<ProductionBerceauRow>>("/api/berceau/production/", {
      params: { ...baseParams, page, per_page, sort: "-date" },
    });
    const batch = res.results ?? [];
    out.push(...batch);
    const total = res.total ?? 0;
    if (out.length >= total || batch.length === 0) break;
    page += 1;
  }
  return out;
}

const DEFAULT_OBJECTIFS: Record<"A1" | "A3", Record<HourIndex, number>> = {
  A1: { 1: 40, 2: 45, 3: 45, 4: 45, 5: 25, 6: 45, 7: 45, 8: 45 },
  A3: { 1: 30, 2: 33, 3: 33, 4: 33, 5: 20, 6: 33, 7: 33, 8: 33 },
};

function defaultObjectifForHour(line: "A1" | "A3", hour: HourIndex) {
  return DEFAULT_OBJECTIFS[line]?.[hour] ?? 0;
}

const defaultForm = () => ({
  line: "A1",
  date: isoCalendarToday(),
  shift: "A",
  objectif: 0,
  objectif_h1: 0,
  objectif_h2: 0,
  objectif_h3: 0,
  objectif_h4: 0,
  objectif_h5: 0,
  objectif_h6: 0,
  objectif_h7: 0,
  objectif_h8: 0,
  line_h1: "",
  line_h2: "",
  line_h3: "",
  line_h4: "",
  line_h5: "",
  line_h6: "",
  line_h7: "",
  line_h8: "",
  production_h1: 0,
  production_h2: 0,
  production_h3: 0,
  production_h4: 0,
  production_h5: 0,
  production_h6: 0,
  production_h7: 0,
  production_h8: 0,
  rebut_h1: 0,
  rebut_h2: 0,
  rebut_h3: 0,
  rebut_h4: 0,
  rebut_h5: 0,
  rebut_h6: 0,
  rebut_h7: 0,
  rebut_h8: 0,
  retouche_h1: 0,
  retouche_h2: 0,
  retouche_h3: 0,
  retouche_h4: 0,
  retouche_h5: 0,
  retouche_h6: 0,
  retouche_h7: 0,
  retouche_h8: 0,
  temps_arrets_h1: 0,
  temps_arrets_h2: 0,
  temps_arrets_h3: 0,
  temps_arrets_h4: 0,
  temps_arrets_h5: 0,
  temps_arrets_h6: 0,
  temps_arrets_h7: 0,
  temps_arrets_h8: 0,
  rebut: 0,
  retouche: 0,
  temps_arrets: 0,
});

/** Draft save: hours without an explicit diversité still need a valid choice for the API. */
function normalizeLineHours(values: Record<string, unknown>): Record<string, unknown> {
  const out = { ...values };
  for (const h of HOURS) {
    const k = `line_h${h}`;
    const v = String(out[k] ?? "").trim();
    if (v !== "A1" && v !== "A3") out[k] = "A1";
  }
  return out;
}

function berceauRowToFormValues(row: ProductionBerceauRow) {
  return {
    line: row.line,
    date: row.date.slice(0, 10),
    shift: row.shift,
    objectif: row.objectif,
    objectif_h1: row.objectif_h1,
    objectif_h2: row.objectif_h2,
    objectif_h3: row.objectif_h3,
    objectif_h4: row.objectif_h4,
    objectif_h5: row.objectif_h5,
    objectif_h6: row.objectif_h6,
    objectif_h7: row.objectif_h7,
    objectif_h8: row.objectif_h8,
    line_h1: row.line_h1 ?? "A1",
    line_h2: row.line_h2 ?? "A1",
    line_h3: row.line_h3 ?? "A1",
    line_h4: row.line_h4 ?? "A1",
    line_h5: row.line_h5 ?? "A1",
    line_h6: row.line_h6 ?? "A1",
    line_h7: row.line_h7 ?? "A1",
    line_h8: row.line_h8 ?? "A1",
    production_h1: row.production_h1,
    production_h2: row.production_h2,
    production_h3: row.production_h3,
    production_h4: row.production_h4,
    production_h5: row.production_h5,
    production_h6: row.production_h6,
    production_h7: row.production_h7,
    production_h8: row.production_h8,
    rebut_h1: row.rebut_h1 ?? 0,
    rebut_h2: row.rebut_h2 ?? 0,
    rebut_h3: row.rebut_h3 ?? 0,
    rebut_h4: row.rebut_h4 ?? 0,
    rebut_h5: row.rebut_h5 ?? 0,
    rebut_h6: row.rebut_h6 ?? 0,
    rebut_h7: row.rebut_h7 ?? 0,
    rebut_h8: row.rebut_h8 ?? 0,
    retouche_h1: row.retouche_h1 ?? 0,
    retouche_h2: row.retouche_h2 ?? 0,
    retouche_h3: row.retouche_h3 ?? 0,
    retouche_h4: row.retouche_h4 ?? 0,
    retouche_h5: row.retouche_h5 ?? 0,
    retouche_h6: row.retouche_h6 ?? 0,
    retouche_h7: row.retouche_h7 ?? 0,
    retouche_h8: row.retouche_h8 ?? 0,
    temps_arrets_h1: row.temps_arrets_h1 ?? 0,
    temps_arrets_h2: row.temps_arrets_h2 ?? 0,
    temps_arrets_h3: row.temps_arrets_h3 ?? 0,
    temps_arrets_h4: row.temps_arrets_h4 ?? 0,
    temps_arrets_h5: row.temps_arrets_h5 ?? 0,
    temps_arrets_h6: row.temps_arrets_h6 ?? 0,
    temps_arrets_h7: row.temps_arrets_h7 ?? 0,
    temps_arrets_h8: row.temps_arrets_h8 ?? 0,
    rebut: row.rebut,
    retouche: row.retouche,
    temps_arrets: row.temps_arrets,
  };
}

function parseDiversiteFromCause(cause: string | null | undefined) {
  const raw = (cause ?? "").trim();
  const m = raw.match(/^\[diversite:(?<d>[^\]]+)\]/i);
  const d = String(m?.groups?.d ?? "").trim().toUpperCase();
  if (d === "A1" || d === "A3") return d as "A1" | "A3";
  return null;
}

/** Draft-style row: at least one hour still has zero production volume. */
function berceauRowHasZeroProductionHour(r: ProductionBerceauRow): boolean {
  return HOURS.some((h) => {
    const v = r[`production_h${h}` as keyof ProductionBerceauRow];
    return Number(v ?? 0) === 0;
  });
}

export default function BerceauProductionPage() {
  const qc = useQueryClient();
  const me = useMe();
  const lockedShift = useLockedShift();
  const canDelete = me?.permissions?.delete === true;
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(15);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ProductionBerceauRow | null>(null);
  const [detailRow, setDetailRow] = useState<ProductionBerceauRow | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [lineFilter, setLineFilter] = useState<string>("");
  const [shiftFocus, setShiftFocus] = useState<ShiftView>(lockedShift ? (lockedShift as ShiftCode) : "ALL");
  const [completionFilter, setCompletionFilter] = useState<"all" | "incomplete">("all");
  const [dateFilter, setDateFilter] = useState<string>(() => isoCalendarToday());

  useEffect(() => {
    if (lockedShift) setShiftFocus(lockedShift as ShiftCode);
  }, [lockedShift]);

  const tableShiftParam = lockedShift ?? (shiftFocus !== "ALL" ? shiftFocus : undefined);

  useEffect(() => {
    setPage(0);
  }, [completionFilter, dateFilter, lineFilter, tableShiftParam]);

  const { data: dayRows = [], isLoading: dayLoading } = useQuery({
    queryKey: ["prod-berceau-day", dateFilter, lineFilter],
    enabled: Boolean(dateFilter),
    queryFn: () =>
      fetchAllBerceauProductionRows({
        ...(dateFilter ? { date: dateFilter } : {}),
        ...(lineFilter && lineFilter !== "all" ? { line: lineFilter } : {}),
      }),
  });

  const tableFetchAll = completionFilter === "incomplete";

  const { data: tableAllRows = [], isLoading: tableAllLoading } = useQuery({
    queryKey: ["prod-berceau-all", lineFilter, lockedShift, dateFilter, tableShiftParam, tableFetchAll],
    enabled: tableFetchAll,
    queryFn: () =>
      fetchAllBerceauProductionRows({
        ...(dateFilter ? { date: dateFilter } : {}),
        ...(lineFilter && lineFilter !== "all" ? { line: lineFilter } : {}),
        ...(tableShiftParam ? { shift: tableShiftParam } : {}),
      }),
  });

  const { data, isLoading: tablePageLoading } = useQuery({
    queryKey: ["prod-berceau", page, rowsPerPage, lineFilter, lockedShift, shiftFocus, dateFilter, tableShiftParam],
    enabled: !tableFetchAll,
    queryFn: async () => {
      const { data: res } = await api.get<Paginated<ProductionBerceauRow>>("/api/berceau/production/", {
        params: {
          page: page + 1,
          per_page: rowsPerPage,
          sort: "-date",
          ...(dateFilter ? { date: dateFilter } : {}),
          ...(lineFilter && lineFilter !== "all" ? { line: lineFilter } : {}),
          ...(tableShiftParam ? { shift: tableShiftParam } : {}),
        },
      });
      return res;
    },
  });

  const isLoading = tableFetchAll ? tableAllLoading : tablePageLoading;

  const form = useForm({ defaultValues: defaultForm() });

  // Auto-fill hourly objectif based on the hour's diversité (A1/A3), but don't overwrite manual edits.
  const lineByHour = HOURS.map((h) => form.watch(`line_h${h}` as const));
  useEffect(() => {
    if (!open) return;
    const dirty: any = (form.formState as any)?.dirtyFields ?? {};
    let sum = 0;
    HOURS.forEach((h, idx) => {
      const raw = lineByHour[idx];
      const objectifKey = `objectif_h${h}`;
      const isDirty = !!dirty?.[objectifKey];
      if (raw !== "A1" && raw !== "A3") {
        if (!isDirty) form.setValue(objectifKey as any, 0);
        return;
      }
      const line = raw as "A1" | "A3";
      const next = defaultObjectifForHour(line, h);
      if (!isDirty) form.setValue(objectifKey as any, next);
      const cur = Number(form.getValues(objectifKey as any) || 0);
      sum += cur;
    });
    if (!dirty?.objectif) form.setValue("objectif" as any, sum);
  }, [open, form, lineByHour]);

  const buildPayload = (values: Record<string, unknown>) => {
    const rec = normalizeLineHours(values);
    const objectifByHours = HOURS.reduce(
      (sum, h) => sum + Number(rec[`objectif_h${h}` as keyof typeof rec] || 0),
      0
    );
    return {
      ...rec,
      line: majorityLineFromHours(rec),
      objectif: objectifByHours > 0 ? objectifByHours : Number(rec.objectif || 0),
      rebut: HOURS.reduce((sum, h) => sum + Number(rec[`rebut_h${h}` as keyof typeof rec] || 0), 0),
      retouche: HOURS.reduce((sum, h) => sum + Number(rec[`retouche_h${h}` as keyof typeof rec] || 0), 0),
      ...(lockedShift ? { shift: lockedShift } : {}),
    };
  };

  const saveMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      if (editing) {
        const { data } = await api.patch<ProductionBerceauRow>(`/api/berceau/production/${editing.id}/`, payload);
        return data;
      }
      const date = String(payload.date ?? "");
      const shift = String(payload.shift ?? "");
      const existing = await api.get<Paginated<ProductionBerceauRow>>("/api/berceau/production/", {
        params: {
          page: 1,
          per_page: 50,
          date,
          shift,
        },
      });
      const existingRow = (existing.data.results ?? []).find(
        (r) => r.shift === shift && r.date.slice(0, 10) === date
      );
      if (existingRow) {
        const { data } = await api.patch<ProductionBerceauRow>(`/api/berceau/production/${existingRow.id}/`, payload);
        return data;
      }
      const { data } = await api.post<ProductionBerceauRow>("/api/berceau/production/", payload);
      return data;
    },
    onSuccess: async (saved) => {
      await qc.invalidateQueries({ queryKey: ["prod-berceau"] });
      await qc.invalidateQueries({ queryKey: ["prod-berceau-day"] });
      await qc.invalidateQueries({ queryKey: ["stock-journal"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-pareto-types-percent"] });
      await qc.invalidateQueries({ queryKey: ["alertes-pannes-graph"] });
      setEditing(saved);
      form.reset(berceauRowToFormValues(saved));
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/api/berceau/production/${id}/`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["prod-berceau"] });
      await qc.invalidateQueries({ queryKey: ["prod-berceau-day"] });
      await qc.invalidateQueries({ queryKey: ["stock-journal"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-pareto-types-percent"] });
      await qc.invalidateQueries({ queryKey: ["alertes-pannes-graph"] });
    },
  });

  const dialogDate = form.watch("date");
  const dialogShift = (lockedShift as ShiftCode | undefined) ?? (form.watch("shift") as ShiftCode);

  const arretsHourQuery = useQuery({
    queryKey: ["berceau-arrets-hourly", dialogDate, dialogShift],
    enabled: open && !!dialogDate && !!dialogShift,
    queryFn: async () =>
      (
        await api.get<Paginated<AlertePanneRow>>("/api/alertes-pannes/", {
          params: {
            page: 1,
            per_page: 5000,
            equipe: "Berceau",
            date: dialogDate,
            shift: dialogShift,
          },
        })
      ).data.results ?? [],
  });

  useEffect(() => {
    if (!open) return;
    const rows = arretsHourQuery.data ?? [];
    if (!rows.length) {
      HOURS.forEach((h) => form.setValue(`temps_arrets_h${h}` as const, 0));
      return;
    }

    const minutesByHour = new Map<number, { a1: number; a3: number; total: number }>();
    for (const row of rows) {
      const h = Number(row.heure_production ?? 0);
      if (h < 1 || h > 8) continue;
      const div = parseDiversiteFromCause(row.cause);
      const min = Number(row.temps_arret_min ?? 0);
      if (!minutesByHour.has(h)) minutesByHour.set(h, { a1: 0, a3: 0, total: 0 });
      const agg = minutesByHour.get(h)!;
      agg.total += min;
      if (div === "A1") agg.a1 += min;
      if (div === "A3") agg.a3 += min;
    }

    HOURS.forEach((h) => {
      const agg = minutesByHour.get(h) ?? { a1: 0, a3: 0, total: 0 };
      form.setValue(`temps_arrets_h${h}` as const, Math.max(0, Math.round(agg.total)));
      if (editing) return;
      const curLine = String(form.getValues(`line_h${h}` as const) ?? "").trim();
      if (agg.total > 0 && curLine !== "A1" && curLine !== "A3") {
        const chosen = agg.a3 > agg.a1 ? "A3" : "A1";
        form.setValue(`line_h${h}` as const, chosen);
      }
    });
  }, [open, arretsHourQuery.data, form, editing]);

  const openEdit = (row: ProductionBerceauRow) => {
    setEditing(row);
    setShiftFocus(row.shift as ShiftCode);
    form.reset(berceauRowToFormValues(row));
    setOpen(true);
  };

  const watchedObjectifGlobal = form.watch("objectif");
  const watchedObjectifsHourly = HOURS.map((h) => form.watch(`objectif_h${h}` as const));
  const objectifLive = useMemo(() => {
    const hourly = watchedObjectifsHourly.reduce((sum, v) => sum + Number(v || 0), 0);
    const global = Number(watchedObjectifGlobal || 0);
    return hourly > 0 ? hourly : global;
  }, [watchedObjectifsHourly, watchedObjectifGlobal]);

  const totalsLive = computeHourlyTotals(
    {
      production: HOURS.map((h) => Number(form.watch(`production_h${h}` as const) || 0)),
      rebut: HOURS.map((h) => Number(form.watch(`rebut_h${h}` as const) || 0)),
      retouche: HOURS.map((h) => Number(form.watch(`retouche_h${h}` as const) || 0)),
      arret: HOURS.map((h) => Number(form.watch(`temps_arrets_h${h}` as const) || 0)),
    },
    objectifLive
  );
  const totalArret = totalsLive.tempsArrets;
  const totalRebut = totalsLive.rebut;
  const totalVolume = totalsLive.volume;
  const roLive = totalsLive.roPercent;
  const nroLive = totalsLive.nroPercent;

  const onSubmit = form.handleSubmit((values) => {
    saveMutation.mutate(buildPayload(values as Record<string, unknown>));
  });

  const exportExcelHref = useMemo(() => {
    const p = new URLSearchParams({ format: "excel" });
    if (lineFilter === "A1" || lineFilter === "A3") p.set("line", lineFilter);
    if (dateFilter) p.set("date", dateFilter);
    if (tableShiftParam) p.set("shift", tableShiftParam);
    return `/berceau/production/export/?${p.toString()}`;
  }, [lineFilter, dateFilter, tableShiftParam]);

  const shiftSummaries = useMemo(
    () =>
      SHIFTS.map((shift) => {
        const rows = dayRows.filter((r) => r.shift === shift);
        return {
          shift,
          count: rows.length,
          volume: rows.reduce((sum, r) => sum + (r.volume || 0), 0),
          rebut: rows.reduce((sum, r) => sum + (r.rebut || 0), 0),
        };
      }),
    [dayRows]
  );

  const kpiRows = useMemo(() => {
    let rows = [...dayRows];
    const effShift = lockedShift ?? (shiftFocus !== "ALL" ? shiftFocus : null);
    if (effShift) rows = rows.filter((r) => r.shift === effShift);
    if (completionFilter === "incomplete") rows = rows.filter(berceauRowHasZeroProductionHour);
    return rows;
  }, [dayRows, lockedShift, shiftFocus, completionFilter]);

  const kpiMetrics = useMemo(() => {
    const vol = kpiRows.reduce((s, r) => s + (r.volume || 0), 0);
    const obj = kpiRows.reduce((s, r) => s + berceauEffectiveObjectif(r), 0);
    const arret = kpiRows.reduce((s, r) => s + (r.temps_arrets || 0), 0);
    const ro = obj > 0 ? (vol / obj) * 100 : null;
    return { vol, obj, arret, ro };
  }, [kpiRows]);

  const kpiReady = Boolean(dateFilter) && !dayLoading;

  const filteredTableRows = useMemo(() => {
    const base = tableFetchAll ? tableAllRows : (data?.results ?? []);
    if (completionFilter === "incomplete") return base.filter(berceauRowHasZeroProductionHour);
    return base;
  }, [tableFetchAll, tableAllRows, data?.results, completionFilter]);

  const tableTotal = tableFetchAll ? filteredTableRows.length : (data?.total ?? 0);

  const shiftRows = useMemo(() => {
    if (!tableFetchAll) return filteredTableRows;
    const start = page * rowsPerPage;
    return filteredTableRows.slice(start, start + rowsPerPage);
  }, [tableFetchAll, filteredTableRows, page, rowsPerPage]);

  const productionRowsByDate = useMemo(() => {
    const shiftOrder: Record<string, number> = { A: 0, B: 1, N: 2 };
    const sorted = [...shiftRows].sort((a, b) => {
      const d = a.date.slice(0, 10).localeCompare(b.date.slice(0, 10));
      if (d !== 0) return d;
      return (shiftOrder[a.shift] ?? 9) - (shiftOrder[b.shift] ?? 9);
    });
    const groups: { date: string; rows: ProductionBerceauRow[] }[] = [];
    for (const row of sorted) {
      const d = row.date.slice(0, 10);
      const last = groups[groups.length - 1];
      if (last?.date === d) last.rows.push(row);
      else groups.push({ date: d, rows: [row] });
    }
    return groups;
  }, [shiftRows]);

  const openNewProductionDialog = async () => {
    const shift = (lockedShift ?? (shiftFocus === "ALL" ? "A" : shiftFocus)) as ShiftCode;
    const date = dateFilter || isoCalendarToday();
    setErrorMsg(null);
    try {
      const { data: res } = await api.get<Paginated<ProductionBerceauRow>>("/api/berceau/production/", {
        params: { page: 1, per_page: 50, date, shift },
      });
      const rows = res.results ?? [];
      const same = rows.filter((r) => r.date.slice(0, 10) === date && r.shift === shift);
      const existing =
        same.find((r) => berceauRowHasZeroProductionHour(r)) ?? same[0];
      if (existing) {
        openEdit(existing);
        return;
      }
    } catch {
      /* fall through to blank form */
    }
    setEditing(null);
    form.reset({
      ...defaultForm(),
      date,
      shift,
    });
    setOpen(true);
  };

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={2} justifyContent="space-between" alignItems={{ md: "center" }}>
        <Typography variant="h5" fontWeight={800}>
          Production · UEP Berceau
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <TextField
            select
            size="small"
            label="Diversite"
            id="prod-berceau-filter-diversite"
            name="prod-berceau-filter-diversite"
            SelectProps={{ inputProps: { id: "prod-berceau-filter-diversite" } }}
            value={lineFilter}
            onChange={(e) => {
              setLineFilter(e.target.value);
              setPage(0);
            }}
            sx={{ minWidth: 120 }}
          >
            <MenuItem value="">Toutes</MenuItem>
            <MenuItem value="A1">A1</MenuItem>
            <MenuItem value="A3">A3</MenuItem>
          </TextField>
          <GiDatePicker
            label="Date"
            value={dateFilter}
            onChange={(v) => {
              setDateFilter(v || isoCalendarToday());
              setPage(0);
            }}
            size="small"
            sx={{ minWidth: 168 }}
          />
          <Button component="a" href={exportExcelHref} variant="outlined" size="small">
            Export Excel
          </Button>
          <Button component={RouterLink} to="/berceau/dashboard" variant="outlined" size="small">
            Ouvrir Dashboard
          </Button>
          <TextField
            select
            size="small"
            label="Etat"
            id="prod-berceau-filter-etat"
            name="prod-berceau-filter-etat"
            SelectProps={{ inputProps: { id: "prod-berceau-filter-etat" } }}
            value={completionFilter}
            onChange={(e) => setCompletionFilter(e.target.value as "all" | "incomplete")}
            sx={{ minWidth: 170 }}
          >
            <MenuItem value="all">Toutes les fiches</MenuItem>
            <MenuItem value="incomplete">Fiches incompletes</MenuItem>
          </TextField>
          <Button
            startIcon={<AddIcon />}
            variant="contained"
            onClick={() => void openNewProductionDialog()}
          >
            Nouvelle saisie {shiftFocus === "ALL" ? "" : `shift ${shiftFocus}`}
          </Button>
        </Stack>
      </Stack>

      {!lockedShift && (
        <Stack direction="row" spacing={1}>
          <Button
            size="small"
            variant={shiftFocus === "ALL" ? "contained" : "outlined"}
            onClick={() => setShiftFocus("ALL")}
          >
            Tous les shifts
          </Button>
        </Stack>
      )}

      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
        {(lockedShift ? shiftSummaries.filter((s) => s.shift === lockedShift) : shiftSummaries).map((item) => (
          <Paper
            key={item.shift}
            onClick={() => {
              if (!lockedShift) setShiftFocus(item.shift);
            }}
            sx={(t) => ({
              p: 1.5,
              borderRadius: 2.5,
              flex: 1,
              cursor: lockedShift ? "default" : "pointer",
              border: "1px solid",
              borderColor: shiftFocus === item.shift ? "primary.main" : "divider",
              boxShadow:
                shiftFocus === item.shift ? `0 10px 28px ${alpha(t.palette.primary.main, 0.35)}` : undefined,
              bgcolor: shiftFocus === item.shift ? alpha(t.palette.primary.main, 0.14) : "background.paper",
              transition: "border-color 0.2s ease, box-shadow 0.25s ease, background 0.2s ease, transform 0.2s ease",
              "&:hover":
                lockedShift || shiftFocus === item.shift
                  ? undefined
                  : { transform: "translateY(-2px)", borderColor: alpha(t.palette.primary.main, 0.35) },
            })}
          >
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="h6" fontWeight={800}>
                Shift {item.shift}
              </Typography>
              <Chip
                size="small"
                label={shiftFocus === item.shift ? "Actif" : "Filtrer"}
                color={shiftFocus === item.shift ? "primary" : "default"}
              />
            </Stack>
          </Paper>
        ))}
      </Stack>

      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
        <Paper sx={{ p: 2, borderRadius: 3, flex: 1 }}>
          <Typography variant="overline" color="text.secondary">
            Production (volume)
          </Typography>
          <Typography variant="h4" fontWeight={800}>
            {kpiReady ? kpiMetrics.vol : "—"}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {dateFilter} · {shiftFocus === "ALL" && !lockedShift ? "Tous les shifts" : `Shift ${lockedShift ?? shiftFocus}`}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, borderRadius: 3, flex: 1 }}>
          <Typography variant="overline" color="text.secondary">
            RO (%)
          </Typography>
          <Typography variant="h4" fontWeight={800}>
            {kpiReady && kpiMetrics.ro != null ? `${kpiMetrics.ro.toFixed(1)} %` : "—"}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Volume / objectif (filtres date, shift, diversité, état)
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, borderRadius: 3, flex: 1 }}>
          <Typography variant="overline" color="text.secondary">
            Temps d'arrêt (min)
          </Typography>
          <Typography variant="h4" fontWeight={800}>
            {kpiReady ? kpiMetrics.arret : "—"}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Somme des arrêts sur les fiches filtrées
          </Typography>
        </Paper>
      </Stack>

      <ProductionShiftComparisonChart date={dateFilter} line={lineFilter} />

      {errorMsg && (
        <Paper sx={{ p: 2, borderRadius: 2, bgcolor: "error.light", color: "error.contrastText" }}>
          {errorMsg}
        </Paper>
      )}

      <TableContainer component={Paper} elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: "action.hover" }}>
              <TableCell>Diversite</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Shift</TableCell>
              <TableCell align="right">Volume</TableCell>
              <TableCell align="right">Objectif</TableCell>
              <TableCell align="right">RO %</TableCell>
              <TableCell align="right">NRO %</TableCell>
              <TableCell align="right">Rebut</TableCell>
              <TableCell align="right">Arret</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={10}>
                  <Typography color="text.secondary">Chargement...</Typography>
                </TableCell>
              </TableRow>
            )}
            {!isLoading &&
              productionRowsByDate.map((group, groupIdx) => (
                <Fragment key={group.date}>
                  <TableRow
                    sx={(t) => ({
                      bgcolor: alpha(t.palette.primary.main, 0.1),
                      "& td": { borderBottom: `2px solid ${alpha(t.palette.primary.main, 0.35)}` },
                    })}
                  >
                    <TableCell colSpan={10}>
                      <Typography variant="subtitle2" fontWeight={800}>
                        {formatDateGroupLabel(group.date)}
                      </Typography>
                    </TableCell>
                  </TableRow>
                  {group.rows.map((row) => (
                    <TableRow key={row.id} hover>
                      <TableCell>
                        <Chip
                          label={Array.from(new Set(HOURS.map((h) => row[`line_h${h}` as const]))).join(" / ")}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{row.date.slice(0, 10)}</TableCell>
                      <TableCell>
                        <Chip label={`Shift ${row.shift}`} size="small" color="primary" variant="outlined" />
                      </TableCell>
                      <TableCell align="right">{row.volume}</TableCell>
                      <TableCell align="right">{row.objectif}</TableCell>
                      <TableCell align="right">{formatPercentFr(berceauRoPercent(row))}</TableCell>
                      <TableCell align="right">{formatPercentFr(nroPercentFromRo(berceauRoPercent(row)))}</TableCell>
                      <TableCell align="right">{row.rebut}</TableCell>
                      <TableCell align="right">{row.temps_arrets}</TableCell>
                      <TableCell align="right">
                        <IconButton size="small" onClick={() => setDetailRow(row)} aria-label="detail">
                          <VisibilityOutlinedIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" onClick={() => openEdit(row)}>
                          <EditOutlinedIcon fontSize="small" />
                        </IconButton>
                        {canDelete && (
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => {
                              if (window.confirm("Supprimer cette ligne ?")) deleteMutation.mutate(row.id);
                            }}
                          >
                            <DeleteOutlineIcon fontSize="small" />
                          </IconButton>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                  {groupIdx < productionRowsByDate.length - 1 && (
                    <TableRow>
                      <TableCell colSpan={10} sx={{ height: 10, p: 0, border: 0, bgcolor: "transparent" }} />
                    </TableRow>
                  )}
                </Fragment>
              ))}
            {!isLoading && shiftRows.length === 0 && (
              <TableRow>
                <TableCell colSpan={10}>
                  <Typography color="text.secondary">
                    {shiftFocus === "ALL"
                      ? "Aucun enregistrement sur cette page."
                      : `Aucun enregistrement pour le shift ${shiftFocus} sur cette page.`}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={tableTotal}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          labelRowsPerPage="Lignes"
        />
      </TableContainer>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{editing ? "Modifier production" : "Nouvelle production"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} flexWrap="wrap" useFlexGap>
              <GiDatePickerRhf control={form.control} name="date" label="Date" sx={{ minWidth: 180 }} />
              <TextField
                select
                label="Shift"
                id="prod-berceau-dialog-shift"
                sx={{ minWidth: 120 }}
                disabled={!!lockedShift}
                helperText={lockedShift ? "Shift impose (profil PSP)" : undefined}
                {...form.register("shift")}
              >
                {(lockedShift ? ([lockedShift] as const) : SHIFTS).map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>
              {editing && (
                <TextField type="number" label="Objectif global" sx={{ minWidth: 140 }} {...form.register("objectif", { valueAsNumber: true })} />
              )}
              <TextField type="number" label="Volume total" sx={{ minWidth: 130 }} value={totalVolume} InputProps={{ readOnly: true }} />
              <TextField type="number" label="Rebut total" sx={{ minWidth: 120 }} value={totalRebut} InputProps={{ readOnly: true }} />
              <TextField type="number" label="Arret total (H1-H8)" sx={{ minWidth: 180 }} value={totalArret} InputProps={{ readOnly: true }} />
              <TextField
                label="RO %"
                sx={{ minWidth: 100 }}
                value={formatPercentFr(roLive)}
                InputProps={{ readOnly: true }}
              />
              <TextField
                label="NRO %"
                sx={{ minWidth: 100 }}
                value={formatPercentFr(nroLive)}
                InputProps={{ readOnly: true }}
              />
            </Stack>
            <Typography variant="subtitle2" fontWeight={700}>
              Detail horaire du shift {form.watch("shift") as string}
            </Typography>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(4, 1fr)" },
                gap: 1,
              }}
            >
              {HOURS.map((h, idx) => {
                const lineVal = lineByHour[idx];
                const showObjectif = lineVal === "A1" || lineVal === "A3";
                return (
                <Paper key={h} variant="outlined" sx={{ p: 1.5, borderRadius: 2 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                    H{h}
                  </Typography>
                  <Controller
                    name={`line_h${h}`}
                    control={form.control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        size="small"
                        fullWidth
                        select
                        label="Diversite"
                        id={`prod-berceau-hour-${h}-diversite`}
                        value={field.value === "A1" || field.value === "A3" ? field.value : ""}
                        onChange={(e) => field.onChange(e.target.value)}
                        SelectProps={{
                          displayEmpty: true,
                          renderValue: (v) =>
                            v === "A1" || v === "A3" ? (
                              String(v)
                            ) : (
                              <Box component="span" sx={{ color: "text.disabled" }}>
                                —
                              </Box>
                            ),
                        }}
                        sx={{ mt: 1 }}
                      >
                        <MenuItem value="A1">A1</MenuItem>
                        <MenuItem value="A3">A3</MenuItem>
                      </TextField>
                    )}
                  />
                  <TextField
                    size="small"
                    fullWidth
                    label="Volume"
                    type="number"
                    {...form.register(`production_h${h}` as const, { valueAsNumber: true })}
                  />
                  <TextField
                    size="small"
                    fullWidth
                    label="Rebut"
                    type="number"
                    sx={{ mt: 1 }}
                    {...form.register(`rebut_h${h}` as const, { valueAsNumber: true })}
                  />
                  <input type="hidden" {...form.register(`retouche_h${h}` as const, { valueAsNumber: true })} />
                  <TextField
                    size="small"
                    fullWidth
                    label="Arret"
                    type="number"
                    disabled
                    helperText="Auto depuis module Arrets"
                    sx={{ mt: 1 }}
                    {...form.register(`temps_arrets_h${h}` as const, { valueAsNumber: true })}
                  />
                  {showObjectif && (
                    <TextField
                      size="small"
                      fullWidth
                      label={`Objectif H${h}`}
                      type="number"
                      sx={{ mt: 1 }}
                      {...form.register(`objectif_h${h}` as const, { valueAsNumber: true })}
                    />
                  )}
                </Paper>
                );
              })}
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setOpen(false)}>Annuler</Button>
          <Button variant="contained" onClick={onSubmit} disabled={saveMutation.isPending}>
            Enregistrer brouillon
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!detailRow} onClose={() => setDetailRow(null)} fullWidth maxWidth="lg">
        <DialogTitle>
          Détail production Berceau
          {detailRow ? (
            <Typography component="span" variant="body2" color="text.secondary" sx={{ display: "block", mt: 0.5, fontWeight: 500 }}>
              {detailRow.date.slice(0, 10)} · Shift {detailRow.shift}
            </Typography>
          ) : null}
        </DialogTitle>
        <DialogContent dividers>
          {detailRow ? <BerceauProductionDetailPanel row={detailRow} /> : null}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDetailRow(null)}>Fermer</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
