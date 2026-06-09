import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import {
  Alert,
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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useLockedShift, useMe } from "../../auth/AuthContext";
import { GiDatePicker, GiDatePickerRhf } from "../../components/GiDatePicker";
import { api, formatApiError } from "../../api/client";
import type { AlertePanneRow, Paginated, ProductionCCBRow } from "../../api/types";
import { computeHourlyTotals } from "./productionHourlyUtils";
import ProductionShiftComparisonChart from "./ProductionShiftComparisonChart";
import { CCB_OBJECTIF_TOTAL_SHIFT } from "./ccbProductionConstants";
import {
  CCB_OBJECTIFS_SETTINGS_QUERY_KEY,
  ccbObjectifsHourlyArray,
  factoryCcbObjectifsSettings,
  objectifHourFieldsFromSettings,
  sumCcbObjectifs,
  type CcbProductionSettings,
} from "./ccbObjectifsSettings";
import {
  ccbDiversityLabel,
  ccbEffectiveObjectif,
  ccbHourVolume,
  ccbReadLhd,
  ccbReadRhd,
  ccbRoPercent,
  formatDateGroupLabel,
  formatPercentFr,
  isoCalendarToday,
  nroPercentFromRo,
} from "./productionMetrics";

type HourIndex = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
const HOURS: HourIndex[] = [1, 2, 3, 4, 5, 6, 7, 8];
const SHIFTS = ["A", "B", "N"] as const;
type ShiftCode = (typeof SHIFTS)[number];
type ShiftView = ShiftCode | "ALL";

type ObjectifHourFields = {
  [H in HourIndex as `objectif_h${H}`]: number;
};

type LhdHourFields = {
  [H in HourIndex as `production_lhd_h${H}`]: number;
};

type RhdHourFields = {
  [H in HourIndex as `production_rhd_h${H}`]: number;
};

type RebutHourFields = {
  [H in HourIndex as `rebut_h${H}`]: number;
};

type ArretHourFields = {
  [H in HourIndex as `temps_arrets_h${H}`]: number;
};

type CcbProductionFormValues = {
  date: string;
  shift: ShiftCode;
  objectif: number;
  retouche: number;
  temps_arrets: number;
} & ObjectifHourFields &
  LhdHourFields &
  RhdHourFields &
  RebutHourFields &
  ArretHourFields;

function ccbHourDefaults(): LhdHourFields & RhdHourFields & RebutHourFields & ArretHourFields {
  const o: Record<string, number> = {};
  for (const h of HOURS) {
    o[`production_lhd_h${h}`] = 0;
    o[`production_rhd_h${h}`] = 0;
    o[`rebut_h${h}`] = 0;
    o[`temps_arrets_h${h}`] = 0;
  }
  return o as LhdHourFields & RhdHourFields & RebutHourFields & ArretHourFields;
}

function ccbFormDefaults(shift: ShiftCode, settings: CcbProductionSettings): CcbProductionFormValues {
  const objectifFields = objectifHourFieldsFromSettings(settings);
  return {
    date: isoCalendarToday(),
    shift,
    objectif: sumCcbObjectifs(settings) || CCB_OBJECTIF_TOTAL_SHIFT,
    retouche: 0,
    temps_arrets: 0,
    ...objectifFields,
    ...ccbHourDefaults(),
  };
}

function applyGlobalObjectifsToForm(
  form: ReturnType<typeof useForm<CcbProductionFormValues>>,
  settings: CcbProductionSettings
) {
  const fields = objectifHourFieldsFromSettings(settings);
  HOURS.forEach((h) => form.setValue(`objectif_h${h}` as const, fields[`objectif_h${h}` as keyof typeof fields]));
  form.setValue("objectif", sumCcbObjectifs(settings));
}

function rowToFormValues(row: ProductionCCBRow, settings: CcbProductionSettings): CcbProductionFormValues {
  const shift = row.shift === "A" || row.shift === "B" || row.shift === "N" ? row.shift : "A";
  const fallback = ccbObjectifsHourlyArray(settings);
  const objectifs = Object.fromEntries(
    HOURS.map((h, i) => {
      const stored = row[`objectif_h${h}` as keyof ProductionCCBRow];
      const val = typeof stored === "number" && stored > 0 ? stored : fallback[i];
      return [`objectif_h${h}`, val];
    })
  );
  const hourly = Object.fromEntries(
    HOURS.flatMap((h) => [
      [`production_lhd_h${h}`, ccbReadLhd(row, h)],
      [`production_rhd_h${h}`, ccbReadRhd(row, h)],
      [`rebut_h${h}`, row[`rebut_h${h}` as keyof ProductionCCBRow] as number],
      [`temps_arrets_h${h}`, Number(row[`temps_arrets_h${h}` as keyof ProductionCCBRow] ?? 0)],
    ])
  );
  return {
    date: row.date.slice(0, 10),
    shift,
    objectif: row.objectif || CCB_OBJECTIF_TOTAL_SHIFT,
    retouche: row.retouche ?? 0,
    temps_arrets: row.temps_arrets ?? 0,
    ...objectifs,
    ...hourly,
  } as CcbProductionFormValues;
}

function sumObjectifs(values: CcbProductionFormValues): number {
  return HOURS.reduce((s, h) => s + Number(values[`objectif_h${h}`] || 0), 0);
}

function ccbHourRoPercent(row: ProductionCCBRow, h: HourIndex, fallbackObjectifs: number[]): number | null {
  const objectif = Number(row[`objectif_h${h}`] ?? 0) || fallbackObjectifs[h - 1] || 0;
  const production = ccbHourVolume(row, h);
  if (objectif <= 0) return null;
  return Math.round((production / objectif) * 10000) / 100;
}

function ccbRowHasZeroProductionHour(r: ProductionCCBRow): boolean {
  return HOURS.some((h) => ccbHourVolume(r, h) === 0);
}

function rowMatchesLineFilter(row: ProductionCCBRow, lineFilter: string): boolean {
  if (!lineFilter) return true;
  if (lineFilter === "LHD") return HOURS.some((h) => ccbReadLhd(row, h) > 0);
  if (lineFilter === "RHD") return HOURS.some((h) => ccbReadRhd(row, h) > 0);
  return true;
}

async function fetchAllCcbProductionRows(
  baseParams: Record<string, string | number | undefined>
): Promise<ProductionCCBRow[]> {
  const out: ProductionCCBRow[] = [];
  let page = 1;
  const per_page = 100;
  while (true) {
    const { data: res } = await api.get<Paginated<ProductionCCBRow>>("/api/ccb/production/", {
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

function CcbProductionDetailPanel({
  row,
  fallbackObjectifs,
}: {
  row: ProductionCCBRow;
  fallbackObjectifs: number[];
}) {
  const hourlySums = useMemo(
    () =>
      HOURS.reduce(
        (acc, h) => {
          acc.objectif += Number(row[`objectif_h${h}`] ?? 0) || fallbackObjectifs[h - 1] || 0;
          acc.production += ccbHourVolume(row, h);
          acc.lhd += ccbReadLhd(row, h);
          acc.rhd += ccbReadRhd(row, h);
          acc.rebut += Number(row[`rebut_h${h}`] ?? 0);
          acc.arret += Number(row[`temps_arrets_h${h}`] ?? 0);
          return acc;
        },
        { objectif: 0, production: 0, lhd: 0, rhd: 0, rebut: 0, arret: 0 }
      ),
    [row, fallbackObjectifs]
  );
  const ro = ccbRoPercent(row);
  const nro = nroPercentFromRo(ro);

  return (
    <Stack spacing={2.5} sx={{ mt: 0.5 }}>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1.5 }}>
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
            Diversités (H1–H8)
          </Typography>
          <Typography variant="body2" fontWeight={700}>
            {ccbDiversityLabel(row)}
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
          { label: "LHD Σ", value: hourlySums.lhd },
          { label: "RHD Σ", value: hourlySums.rhd },
          { label: "Rebut", value: row.rebut },
          { label: "Arrêt total (min)", value: row.temps_arrets },
          { label: "RO %", value: formatPercentFr(ro) },
          { label: "NRO %", value: formatPercentFr(nro) },
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
              <TableCell align="right">Objectif</TableCell>
              <TableCell align="right">LHD</TableCell>
              <TableCell align="right">RHD</TableCell>
              <TableCell align="right">Σ</TableCell>
              <TableCell align="right">Rebut</TableCell>
              <TableCell align="right">Arrêt (min)</TableCell>
              <TableCell align="right">RO %</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {HOURS.map((h) => {
              const objectif = Number(row[`objectif_h${h}`] ?? 0) || fallbackObjectifs[h - 1] || 0;
              const lhd = ccbReadLhd(row, h);
              const rhd = ccbReadRhd(row, h);
              const production = lhd + rhd;
              const rebut = Number(row[`rebut_h${h}`] ?? 0);
              const arret = Number(row[`temps_arrets_h${h}`] ?? 0);
              const hourRo = ccbHourRoPercent(row, h, fallbackObjectifs);
              return (
                <TableRow key={h} hover>
                  <TableCell sx={{ fontWeight: 700 }}>H{h}</TableCell>
                  <TableCell align="right">{objectif}</TableCell>
                  <TableCell align="right">{lhd || "—"}</TableCell>
                  <TableCell align="right">{rhd || "—"}</TableCell>
                  <TableCell align="right">{production}</TableCell>
                  <TableCell align="right">{rebut}</TableCell>
                  <TableCell align="right">{arret}</TableCell>
                  <TableCell align="right">{hourRo != null ? formatPercentFr(hourRo) : "—"}</TableCell>
                </TableRow>
              );
            })}
            <TableRow sx={{ bgcolor: (t) => alpha(t.palette.primary.main, 0.06) }}>
              <TableCell sx={{ fontWeight: 800 }}>Total shift</TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>
                {hourlySums.objectif}
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>
                {hourlySums.lhd}
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>
                {hourlySums.rhd}
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
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    </Stack>
  );
}

export default function CcbProductionPage() {
  const qc = useQueryClient();
  const me = useMe();
  const lockedShift = useLockedShift();
  const canDelete = me?.permissions?.delete === true;
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(15);
  const [open, setOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsDraft, setSettingsDraft] = useState<CcbProductionSettings>(() => factoryCcbObjectifsSettings());
  const [editing, setEditing] = useState<ProductionCCBRow | null>(null);
  const [detailRow, setDetailRow] = useState<ProductionCCBRow | null>(null);
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
    queryKey: ["prod-ccb-day", dateFilter, lineFilter],
    enabled: Boolean(dateFilter),
    queryFn: async () => {
      const rows = await fetchAllCcbProductionRows({
        ...(dateFilter ? { date: dateFilter } : {}),
      });
      return rows.filter((r) => rowMatchesLineFilter(r, lineFilter));
    },
  });

  const tableFetchAll = completionFilter === "incomplete";

  const { data: tableAllRows = [], isLoading: tableAllLoading } = useQuery({
    queryKey: ["prod-ccb-all", lineFilter, lockedShift, dateFilter, tableShiftParam, tableFetchAll],
    enabled: tableFetchAll,
    queryFn: async () => {
      const rows = await fetchAllCcbProductionRows({
        ...(dateFilter ? { date: dateFilter } : {}),
        ...(tableShiftParam ? { shift: tableShiftParam } : {}),
      });
      return rows.filter((r) => rowMatchesLineFilter(r, lineFilter));
    },
  });

  const { data, isLoading: tablePageLoading, isError, error } = useQuery({
    queryKey: ["prod-ccb", page, rowsPerPage, lineFilter, lockedShift, shiftFocus, dateFilter, tableShiftParam],
    enabled: !tableFetchAll,
    queryFn: async () => {
      const { data: res } = await api.get<Paginated<ProductionCCBRow>>("/api/ccb/production/", {
        params: {
          page: page + 1,
          per_page: rowsPerPage,
          sort: "-date",
          ...(dateFilter ? { date: dateFilter } : {}),
          ...(tableShiftParam ? { shift: tableShiftParam } : {}),
        },
      });
      return res;
    },
  });

  const isLoading = tableFetchAll ? tableAllLoading : tablePageLoading;

  const { data: globalObjectifs = factoryCcbObjectifsSettings() } = useQuery({
    queryKey: CCB_OBJECTIFS_SETTINGS_QUERY_KEY,
    queryFn: async () => (await api.get<CcbProductionSettings>("/api/ccb/production-settings/")).data,
  });

  const globalObjectifsHourly = useMemo(
    () => ccbObjectifsHourlyArray(globalObjectifs),
    [globalObjectifs]
  );

  const form = useForm<CcbProductionFormValues>({
    defaultValues: ccbFormDefaults("A", factoryCcbObjectifsSettings()),
  });

  const settingsSaveMutation = useMutation({
    mutationFn: async (payload: CcbProductionSettings) =>
      (await api.patch<CcbProductionSettings>("/api/ccb/production-settings/", payload)).data,
    onSuccess: async (saved) => {
      await qc.invalidateQueries({ queryKey: CCB_OBJECTIFS_SETTINGS_QUERY_KEY });
      setSettingsDraft(saved);
      setSettingsOpen(false);
      if (open && !editing) {
        applyGlobalObjectifsToForm(form, saved);
      }
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const saveMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      if (editing) {
        const { data } = await api.patch<ProductionCCBRow>(`/api/ccb/production/${editing.id}/`, payload);
        return data;
      }
      const date = String(payload.date ?? "");
      const shift = String(payload.shift ?? "");
      const existing = await api.get<Paginated<ProductionCCBRow>>("/api/ccb/production/", {
        params: { page: 1, per_page: 50, date, shift },
      });
      const existingRow = (existing.data.results ?? []).find(
        (r) => r.shift === shift && r.date.slice(0, 10) === date
      );
      if (existingRow) {
        const { data } = await api.patch<ProductionCCBRow>(`/api/ccb/production/${existingRow.id}/`, payload);
        return data;
      }
      const { data } = await api.post<ProductionCCBRow>("/api/ccb/production/", payload);
      return data;
    },
    onSuccess: async (saved) => {
      await qc.invalidateQueries({ queryKey: ["prod-ccb"] });
      await qc.invalidateQueries({ queryKey: ["prod-ccb-day"] });
      await qc.invalidateQueries({ queryKey: ["prod-ccb-all"] });
      await qc.invalidateQueries({ queryKey: ["stock-journal"] });
      setEditing(saved);
      form.reset(rowToFormValues(saved, globalObjectifs));
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/api/ccb/production/${id}/`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["prod-ccb"] });
      await qc.invalidateQueries({ queryKey: ["prod-ccb-day"] });
      await qc.invalidateQueries({ queryKey: ["prod-ccb-all"] });
    },
  });

  const dialogDate = form.watch("date");
  const dialogShift = (lockedShift as ShiftCode | undefined) ?? (form.watch("shift") as ShiftCode);

  const arretsHourQuery = useQuery({
    queryKey: ["ccb-arrets-hourly", dialogDate, dialogShift],
    enabled: open && !!dialogDate && !!dialogShift,
    queryFn: async () =>
      (
        await api.get<Paginated<AlertePanneRow>>("/api/alertes-pannes/", {
          params: {
            page: 1,
            per_page: 5000,
            equipe: "CCB",
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
    const minutesByHour = new Map<number, number>();
    for (const row of rows) {
      const h = Number(row.heure_production ?? 0);
      if (h < 1 || h > 8) continue;
      const min = Number(row.temps_arret_min ?? 0);
      minutesByHour.set(h, (minutesByHour.get(h) ?? 0) + min);
    }
    HOURS.forEach((h) => {
      form.setValue(`temps_arrets_h${h}` as const, Math.max(0, Math.round(minutesByHour.get(h) ?? 0)));
    });
  }, [open, arretsHourQuery.data, form]);

  const openEdit = (row: ProductionCCBRow) => {
    setEditing(row);
    setShiftFocus(row.shift as ShiftCode);
    form.reset(rowToFormValues(row, globalObjectifs));
    setOpen(true);
  };

  const watchedObjectifsHourly = HOURS.map((h) => form.watch(`objectif_h${h}` as const));
  const objectifLive = useMemo(
    () => watchedObjectifsHourly.reduce((sum, v) => sum + Number(v || 0), 0),
    [watchedObjectifsHourly]
  );

  const watchedLhd = HOURS.map((h) => form.watch(`production_lhd_h${h}` as const));
  const watchedRhd = HOURS.map((h) => form.watch(`production_rhd_h${h}` as const));
  const watchedRebut = HOURS.map((h) => form.watch(`rebut_h${h}` as const));
  const watchedArret = HOURS.map((h) => form.watch(`temps_arrets_h${h}` as const));

  const totalsLive = useMemo(() => {
    const production = HOURS.map((_, idx) => Number(watchedLhd[idx] || 0) + Number(watchedRhd[idx] || 0));
    return computeHourlyTotals(
      {
        production,
        rebut: watchedRebut.map((v) => Number(v || 0)),
        retouche: HOURS.map(() => 0),
        arret: watchedArret.map((v) => Number(v || 0)),
      },
      objectifLive
    );
  }, [watchedLhd, watchedRhd, watchedRebut, watchedArret, objectifLive]);

  const onSubmit = form.handleSubmit((values) => {
    const objectif = sumObjectifs(values);
    saveMutation.mutate({
      ...(values as Record<string, unknown>),
      objectif: objectif > 0 ? objectif : CCB_OBJECTIF_TOTAL_SHIFT,
      retouche: 0,
      ...(lockedShift ? { shift: lockedShift } : {}),
    });
  });

  const exportExcelHref = useMemo(() => {
    const p = new URLSearchParams({ format: "excel" });
    if (lineFilter === "LHD" || lineFilter === "RHD") p.set("line", lineFilter);
    if (dateFilter) p.set("date", dateFilter);
    if (tableShiftParam) p.set("shift", tableShiftParam);
    return `/ccb/production/export/?${p.toString()}`;
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
    if (completionFilter === "incomplete") rows = rows.filter(ccbRowHasZeroProductionHour);
    return rows;
  }, [dayRows, lockedShift, shiftFocus, completionFilter]);

  const kpiMetrics = useMemo(() => {
    const vol = kpiRows.reduce((s, r) => s + (r.volume || 0), 0);
    const obj = kpiRows.reduce((s, r) => s + ccbEffectiveObjectif(r), 0);
    const arret = kpiRows.reduce((s, r) => s + (r.temps_arrets || 0), 0);
    const ro = obj > 0 ? (vol / obj) * 100 : null;
    return { vol, obj, arret, ro };
  }, [kpiRows]);

  const kpiReady = Boolean(dateFilter) && !dayLoading;

  const filteredTableRows = useMemo(() => {
    const base = tableFetchAll ? tableAllRows : (data?.results ?? []);
    const lineFiltered = base.filter((r) => rowMatchesLineFilter(r, lineFilter));
    if (completionFilter === "incomplete") return lineFiltered.filter(ccbRowHasZeroProductionHour);
    return lineFiltered;
  }, [tableFetchAll, tableAllRows, data?.results, completionFilter, lineFilter]);

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
    const groups: { date: string; rows: ProductionCCBRow[] }[] = [];
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
      const { data: res } = await api.get<Paginated<ProductionCCBRow>>("/api/ccb/production/", {
        params: { page: 1, per_page: 50, date, shift },
      });
      const rows = res.results ?? [];
      const same = rows.filter((r) => r.date.slice(0, 10) === date && r.shift === shift);
      const existing = same.find((r) => ccbRowHasZeroProductionHour(r)) ?? same[0];
      if (existing) {
        openEdit(existing);
        return;
      }
    } catch {
      /* blank form */
    }
    setEditing(null);
    form.reset({ ...ccbFormDefaults(shift, globalObjectifs), date, shift });
    setOpen(true);
  };

  const openObjectifsSettings = () => {
    setSettingsDraft(globalObjectifs);
    setSettingsOpen(true);
  };

  const settingsDraftTotal = sumCcbObjectifs(settingsDraft);

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={2} justifyContent="space-between" alignItems={{ md: "center" }}>
        <Typography variant="h5" fontWeight={800}>
          Production · UEP CCB
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <TextField
            select
            size="small"
            label="Diversité"
            id="prod-ccb-filter-diversite"
            value={lineFilter}
            onChange={(e) => {
              setLineFilter(e.target.value);
              setPage(0);
            }}
            sx={{ minWidth: 120 }}
          >
            <MenuItem value="">Toutes</MenuItem>
            <MenuItem value="LHD">LHD</MenuItem>
            <MenuItem value="RHD">RHD</MenuItem>
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
          <Button variant="outlined" size="small" startIcon={<TuneOutlinedIcon />} onClick={openObjectifsSettings}>
            Objectifs horaires
          </Button>
          <TextField
            select
            size="small"
            label="État"
            id="prod-ccb-filter-etat"
            value={completionFilter}
            onChange={(e) => setCompletionFilter(e.target.value as "all" | "incomplete")}
            sx={{ minWidth: 170 }}
          >
            <MenuItem value="all">Toutes les fiches</MenuItem>
            <MenuItem value="incomplete">Fiches incomplètes</MenuItem>
          </TextField>
          <Button startIcon={<AddIcon />} variant="contained" onClick={() => void openNewProductionDialog()}>
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
            Temps d&apos;arrêt (min)
          </Typography>
          <Typography variant="h4" fontWeight={800}>
            {kpiReady ? kpiMetrics.arret : "—"}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Somme des arrêts sur les fiches filtrées
          </Typography>
        </Paper>
      </Stack>

      <ProductionShiftComparisonChart equipe="CCB" date={dateFilter} line={lineFilter} />

      {errorMsg && (
        <Paper sx={{ p: 2, borderRadius: 2, bgcolor: "error.light", color: "error.contrastText" }}>
          {errorMsg}
        </Paper>
      )}

      {isError && <Alert severity="error">{formatApiError(error)}</Alert>}

      <TableContainer component={Paper} elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: "action.hover" }}>
              <TableCell>Diversité</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Shift</TableCell>
              <TableCell align="right">Volume</TableCell>
              <TableCell align="right">Objectif</TableCell>
              <TableCell align="right">RO %</TableCell>
              <TableCell align="right">NRO %</TableCell>
              <TableCell align="right">Rebut</TableCell>
              <TableCell align="right">Arrêt</TableCell>
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
                        <Chip label={ccbDiversityLabel(row)} size="small" />
                      </TableCell>
                      <TableCell>{row.date.slice(0, 10)}</TableCell>
                      <TableCell>
                        <Chip label={`Shift ${row.shift}`} size="small" color="primary" variant="outlined" />
                      </TableCell>
                      <TableCell align="right">{row.volume}</TableCell>
                      <TableCell align="right">{row.objectif}</TableCell>
                      <TableCell align="right">{formatPercentFr(ccbRoPercent(row))}</TableCell>
                      <TableCell align="right">{formatPercentFr(nroPercentFromRo(ccbRoPercent(row)))}</TableCell>
                      <TableCell align="right">{row.rebut}</TableCell>
                      <TableCell align="right">{row.temps_arrets}</TableCell>
                      <TableCell align="right">
                        <IconButton size="small" onClick={() => setDetailRow(row)} aria-label="detail">
                          <VisibilityOutlinedIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" onClick={() => openEdit(row)} aria-label="modifier">
                          <EditOutlinedIcon fontSize="small" />
                        </IconButton>
                        {canDelete && (
                          <IconButton
                            size="small"
                            color="error"
                            aria-label="supprimer"
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

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="lg">
        <DialogTitle>{editing ? "Modifier production CCB" : "Nouvelle production CCB"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} flexWrap="wrap" useFlexGap>
              <GiDatePickerRhf control={form.control} name="date" label="Date" sx={{ minWidth: 180 }} />
              <TextField
                select
                label="Shift"
                id="prod-ccb-dialog-shift"
                sx={{ minWidth: 120 }}
                disabled={!!lockedShift}
                helperText={lockedShift ? "Shift imposé (profil PSP)" : undefined}
                {...form.register("shift")}
              >
                {(lockedShift ? ([lockedShift] as const) : SHIFTS).map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                type="number"
                label="Volume total"
                sx={{ minWidth: 130 }}
                value={totalsLive.volume}
                InputProps={{ readOnly: true }}
              />
              <TextField
                type="number"
                label="Rebut total"
                sx={{ minWidth: 120 }}
                value={totalsLive.rebut}
                InputProps={{ readOnly: true }}
              />
              <TextField
                type="number"
                label="Arrêt total (H1–H8)"
                sx={{ minWidth: 180 }}
                value={totalsLive.tempsArrets}
                InputProps={{ readOnly: true }}
              />
              <TextField label="RO %" sx={{ minWidth: 100 }} value={formatPercentFr(totalsLive.roPercent)} InputProps={{ readOnly: true }} />
              <TextField label="NRO %" sx={{ minWidth: 100 }} value={formatPercentFr(totalsLive.nroPercent)} InputProps={{ readOnly: true }} />
            </Stack>
            <Typography variant="subtitle2" fontWeight={700}>
              Détail horaire du shift {form.watch("shift") as string}
            </Typography>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(4, 1fr)" },
                gap: 1,
              }}
            >
              {HOURS.map((h) => (
                <Paper key={h} variant="outlined" sx={{ p: 1.5, borderRadius: 2 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                    H{h} — objectif {Number(form.watch(`objectif_h${h}` as const)) || globalObjectifsHourly[h - 1]}
                  </Typography>
                  <TextField
                    size="small"
                    fullWidth
                    label="Production LHD"
                    type="number"
                    inputProps={{ min: 0 }}
                    {...form.register(`production_lhd_h${h}` as const, { valueAsNumber: true })}
                  />
                  <TextField
                    size="small"
                    fullWidth
                    label="Production RHD"
                    type="number"
                    sx={{ mt: 1 }}
                    inputProps={{ min: 0 }}
                    {...form.register(`production_rhd_h${h}` as const, { valueAsNumber: true })}
                  />
                  <TextField
                    size="small"
                    fullWidth
                    label="Rebut"
                    type="number"
                    sx={{ mt: 1 }}
                    inputProps={{ min: 0 }}
                    {...form.register(`rebut_h${h}` as const, { valueAsNumber: true })}
                  />
                  <TextField
                    size="small"
                    fullWidth
                    label="Arrêt"
                    type="number"
                    disabled
                    helperText="Auto depuis module Arrêts"
                    sx={{ mt: 1 }}
                    {...form.register(`temps_arrets_h${h}` as const, { valueAsNumber: true })}
                  />
                </Paper>
              ))}
            </Box>
            <input type="hidden" {...form.register("objectif", { valueAsNumber: true })} />
            <input type="hidden" {...form.register("retouche", { valueAsNumber: true })} />
            <input type="hidden" {...form.register("temps_arrets", { valueAsNumber: true })} />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setOpen(false)}>Annuler</Button>
          <Button variant="contained" onClick={onSubmit} disabled={saveMutation.isPending}>
            Enregistrer brouillon
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={settingsOpen} onClose={() => setSettingsOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Objectifs horaires CCB (référentiel)</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Ces objectifs s&apos;appliquent à toutes les nouvelles fiches de production (toutes dates, tous shifts)
            jusqu&apos;à la prochaine modification. Les fiches déjà enregistrées conservent leurs objectifs.
          </Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(4, 1fr)" }, gap: 1.5 }}>
            {HOURS.map((h) => (
              <TextField
                key={h}
                size="small"
                type="number"
                label={`Objectif H${h}`}
                inputProps={{ min: 0 }}
                value={settingsDraft[`objectif_h${h}` as keyof CcbProductionSettings] ?? 0}
                onChange={(e) => {
                  const val = Math.max(0, Number(e.target.value) || 0);
                  setSettingsDraft((prev) => ({ ...prev, [`objectif_h${h}`]: val }));
                }}
              />
            ))}
          </Box>
          <Typography variant="body2" sx={{ mt: 2, fontWeight: 600 }}>
            Total shift : {settingsDraftTotal}
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setSettingsDraft(factoryCcbObjectifsSettings())}>Réinitialiser usine</Button>
          <Button onClick={() => setSettingsOpen(false)}>Annuler</Button>
          <Button
            variant="contained"
            disabled={settingsSaveMutation.isPending}
            onClick={() => settingsSaveMutation.mutate(settingsDraft)}
          >
            Enregistrer le référentiel
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!detailRow} onClose={() => setDetailRow(null)} fullWidth maxWidth="lg">
        <DialogTitle>
          Détail production CCB
          {detailRow ? (
            <Typography component="span" variant="body2" color="text.secondary" sx={{ display: "block", mt: 0.5, fontWeight: 500 }}>
              {detailRow.date.slice(0, 10)} · Shift {detailRow.shift}
            </Typography>
          ) : null}
        </DialogTitle>
        <DialogContent dividers>
          {detailRow ? (
            <CcbProductionDetailPanel row={detailRow} fallbackObjectifs={globalObjectifsHourly} />
          ) : null}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDetailRow(null)}>Fermer</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
