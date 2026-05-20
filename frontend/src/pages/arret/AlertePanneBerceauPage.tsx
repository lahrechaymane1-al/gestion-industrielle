import { zodResolver } from "@hookform/resolvers/zod";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import FilterAltOutlinedIcon from "@mui/icons-material/FilterAltOutlined";
import RestartAltRoundedIcon from "@mui/icons-material/RestartAltRounded";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  InputAdornment,
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
  Tooltip,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import {
  Bar,
  CartesianGrid,
  Legend,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
  BarChart,
} from "recharts";
import {
  ChartGradientDefs,
  ChartLegendContent,
  CHART_OVERFLOW_SX,
  StackedA1A3Tooltip,
  useChartTheme,
} from "../../components/charts";
import { SafeResponsiveContainer } from "../../components/SafeResponsiveContainer";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useLockedShift, useMe } from "../../auth/AuthContext";
import { GiDatePicker, GiDatePickerRhf } from "../../components/GiDatePicker";
import { api, formatApiError } from "../../api/client";
import type {
  AlertePanneRow,
  BerceauModuleOption,
  BerceauMoyenOption,
  BerceauPosteOption,
  Paginated,
  PanneTypeOption,
  ProductionBerceauRow,
} from "../../api/types";
import { autoTimeLabel, onModuleChange, onPosteChange } from "./alertePanneUtils";
import { PanneTypesManagerDialog } from "./PanneTypesManagerDialog";
import {
  addRowToParetoMinuteBuckets,
  analyzeParetoMinuteBuckets,
  sumAllHourlyObjectifs,
  summedObjectifsFromProductionRow,
} from "../../domain/downtimeImpact";

const alerteBaseSchema = z.object({
  module_id: z.coerce.number().int().positive(),
  poste_id: z.coerce.number().int().positive(),
  moyen_id: z.coerce.number().int().positive(),
  panne_type_id: z.coerce.number().int().positive(),
  category: z.enum(["maintenance", "kta", "logistique", "fabrication"]),
  commentaire: z.string().min(1),
  date: z.string().min(1),
  shift: z.enum(["A", "B", "N"]),
  heure_production: z.coerce.number().int().min(1).max(8),
  temps_arret_min: z.preprocess(
    (v) => (v === "" || v === null || v === undefined ? undefined : v),
    z.coerce.number().int().positive("Le temps d'arret est obligatoire.")
  ),
});

const berceauAlerteSchema = alerteBaseSchema.extend({
  diversite: z.enum(["A1", "A3"]),
});

const ccbAlerteSchema = alerteBaseSchema;

type BerceauFormValues = z.infer<typeof berceauAlerteSchema>;
type CcbFormValues = z.infer<typeof ccbAlerteSchema>;
type FormData = BerceauFormValues | CcbFormValues;

const ARRET_CATEGORIES = [
  { value: "maintenance", label: "Maintenance" },
  { value: "kta", label: "KTA" },
  { value: "logistique", label: "Logistique" },
  { value: "fabrication", label: "Fabrication" },
] as const;

const DIVERSITES = [
  { value: "A1", label: "A1" },
  { value: "A3", label: "A3" },
] as const;

type DiversiteValue = (typeof DIVERSITES)[number]["value"];

function normalizeShift(value: unknown): "A" | "B" | "N" {
  const s = String(value ?? "").trim().toUpperCase();
  if (s === "A" || s === "B" || s === "N") return s;
  return "A";
}

function normalizeCategory(value: unknown) {
  const s = String(value ?? "").trim().toLowerCase();
  if (s === "maintenance" || s === "kta" || s === "logistique" || s === "fabrication") return s;
  return "fabrication";
}

function splitCauseIntoDiversiteAndCommentaire(cause: string | undefined | null) {
  const raw = (cause ?? "").trim();
  const m = raw.match(/^\[diversite:(?<d>[^\]]+)\]\s*(?<c>[\s\S]*)$/i);
  if (!m?.groups) return { diversite: "A1" as DiversiteValue, commentaire: raw };
  const d = String(m.groups.d ?? "").trim().toUpperCase();
  const allowed = new Set(DIVERSITES.map((x) => x.value));
  const diversite = (allowed.has(d as DiversiteValue) ? (d as DiversiteValue) : "A1") as DiversiteValue;
  return { diversite, commentaire: String(m.groups.c ?? "").trim() };
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

type AlertePannePageProps = {
  equipe?: "Berceau" | "CCB";
};

export default function AlertePanneBerceauPage({ equipe = "Berceau" }: AlertePannePageProps) {
  const chart = useChartTheme();
  const qc = useQueryClient();
  const me = useMe();
  const lockedShift = useLockedShift();
  const isCcb = equipe === "CCB";
  const alerteResolver = useMemo(
    () => zodResolver(isCcb ? ccbAlerteSchema : berceauAlerteSchema),
    [isCcb]
  );
  const canDelete = me?.permissions?.delete === true;
  const canCreate = me?.permissions?.create === true;
  const canUpdate = me?.permissions?.update === true;
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<AlertePanneRow | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [filterDate, setFilterDate] = useState("");
  const [filterShift, setFilterShift] = useState("");
  const [filterPosteId, setFilterPosteId] = useState("");
  const [filterCategory, setFilterCategory] = useState("");

  useEffect(() => {
    if (lockedShift) setFilterShift(lockedShift);
  }, [lockedShift]);

  const effectiveFilterShift = lockedShift ?? filterShift;
  const graphEnabled = equipe === "Berceau" && !!filterDate && !!effectiveFilterShift;
  const exportQuery = useMemo(() => {
    const params = new URLSearchParams();
    params.set("format", "excel");
    params.set("equipe", equipe);
    if (filterCategory) params.set("category", filterCategory);
    if (filterDate) params.set("date", filterDate);
    if (effectiveFilterShift) params.set("shift", effectiveFilterShift);
    if (filterPosteId) params.set("poste_id", filterPosteId);
    return params.toString();
  }, [equipe, filterCategory, filterDate, effectiveFilterShift, filterPosteId]);

  const objectifA1Query = useQuery({
    queryKey: ["arrets-objectif-hourly", equipe, filterDate, effectiveFilterShift],
    enabled: graphEnabled,
    queryFn: async () =>
      (
        await api.get<Paginated<ProductionBerceauRow>>("/api/berceau/production/", {
          params: { page: 1, per_page: 50, date: filterDate, shift: effectiveFilterShift },
        })
      ).data.results?.[0] ?? null,
  });

  const objectifs = useMemo(() => summedObjectifsFromProductionRow(objectifA1Query.data ?? null), [objectifA1Query.data]);

  const arretsGraphQuery = useQuery({
    queryKey: ["alertes-pannes-graph", equipe, filterDate, effectiveFilterShift, filterPosteId, filterCategory],
    enabled: graphEnabled,
    queryFn: async () =>
      await fetchAllAlertesPannes({
        date: filterDate || undefined,
        shift: effectiveFilterShift || undefined,
        poste_id: filterPosteId || undefined,
        category: filterCategory || undefined,
        equipe,
      }),
  });

  const { data: modulesData } = useQuery({
    queryKey: ["berceau-modules"],
    enabled: !isCcb,
    queryFn: async () => (await api.get<{ results: BerceauModuleOption[] }>("/api/berceau/modules/")).data.results,
  });
  const modules = modulesData ?? [];
  const { data: equipePostesData } = useQuery({
    queryKey: ["berceau-postes-by-equipe", equipe],
    queryFn: async () =>
      (
        await api.get<{ results: BerceauPosteOption[] }>("/api/berceau/postes/", {
          params: { equipe },
        })
      ).data.results,
  });
  const equipePostes = useMemo(() => equipePostesData ?? [], [equipePostesData]);

  const form = useForm<FormData>({
    resolver: alerteResolver,
    defaultValues: {
      date: new Date().toISOString().slice(0, 10),
      shift: (lockedShift ?? "A") as "A" | "B" | "N",
      heure_production: 1,
      category: "fabrication",
      commentaire: "",
      temps_arret_min: undefined,
      ...(isCcb ? {} : { diversite: "A1" as const }),
    },
  });

  const resetAlerteFormForCreate = () => {
    setEditing(null);
    form.reset({
      date: new Date().toISOString().slice(0, 10),
      shift: (lockedShift ?? "A") as "A" | "B" | "N",
      heure_production: 1,
      category: "fabrication",
      commentaire: "",
      temps_arret_min: undefined,
      ...(isCcb ? {} : { diversite: "A1" as const }),
    });
    setErrorMsg(null);
  };

  const moduleId = form.watch("module_id");
  const posteId = form.watch("poste_id");
  const moyenId = form.watch("moyen_id");
  const shift = form.watch("shift");
  const date = form.watch("date");
  const heure = form.watch("heure_production");
  const tempsArret = form.watch("temps_arret_min");

  const { data: postesData } = useQuery({
    queryKey: ["berceau-postes", moduleId],
    enabled: !!moduleId && !isCcb,
    queryFn: async () =>
      (await api.get<{ results: BerceauPosteOption[] }>(`/api/berceau/modules/${moduleId}/postes/`)).data.results,
  });
  const postesByModule = postesData ?? [];
  const formPostes = isCcb ? equipePostes : postesByModule;
  const selectedPoste = formPostes.find((p) => p.id === posteId);

  useEffect(() => {
    if (isCcb || !selectedPoste) return;
    const vals = form.getValues() as Record<string, unknown>;
    const current = vals.diversite as DiversiteValue | undefined;
    const allowed: DiversiteValue[] = [
      ...(selectedPoste.a1_enabled ? (["A1"] as const) : []),
      ...(selectedPoste.a3_enabled ? (["A3"] as const) : []),
    ];
    const setDiv = (v: DiversiteValue) => form.setValue("diversite", v as never);
    if (allowed.length === 1 && current !== allowed[0]) setDiv(allowed[0]);
    if (allowed.length > 0 && (current === undefined || !allowed.includes(current))) setDiv(allowed[0]);
  }, [isCcb, selectedPoste, form]);

  useEffect(() => {
    if (!isCcb || !posteId) return;
    const p = equipePostes.find((x) => x.id === posteId);
    if (p) form.setValue("module_id", p.module_id as never);
  }, [isCcb, posteId, equipePostes, form]);

  const { data: moyensData } = useQuery({
    queryKey: ["berceau-moyens", posteId, isCcb ? editing?.moyen_id ?? null : null],
    enabled: !!posteId,
    queryFn: async () =>
      (
        await api.get<{ results: BerceauMoyenOption[] }>(`/api/berceau/postes/${posteId}/moyens/`, {
          params:
            isCcb && editing?.moyen_id != null && editing.moyen_id > 0
              ? { include_moyen_id: editing.moyen_id }
              : undefined,
        })
      ).data.results,
  });
  const moyens = moyensData ?? [];

  const { data: panneTypesData } = useQuery({
    queryKey: ["panne-types", equipe],
    queryFn: async () =>
      (await api.get<{ results: PanneTypeOption[] }>("/api/panne-types/", { params: { equipe } })).data.results,
  });
  const panneTypes = panneTypesData ?? [];

  const autoTimeEnabled = useMemo(
    () => !!(date && shift && moduleId && posteId && moyenId && heure),
    [date, shift, moduleId, posteId, moyenId, heure]
  );
  const { data: autoTime } = useQuery({
    queryKey: ["arret-temps-auto", date, shift, moduleId, posteId, moyenId, heure],
    enabled: autoTimeEnabled,
    queryFn: async () =>
      (
        await api.get<{ temps_arret_min: number; found: boolean }>("/api/arrets/temps-auto/", {
          params: { date, shift, module_id: moduleId, poste_id: posteId, moyen_id: moyenId, heure },
        })
      ).data,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["alertes-pannes", equipe, page, rowsPerPage, filterDate, effectiveFilterShift, filterPosteId, filterCategory],
    queryFn: async () =>
      (
        await api.get<Paginated<AlertePanneRow>>("/api/alertes-pannes/", {
          params: {
            page: page + 1,
            per_page: rowsPerPage,
            date: filterDate || undefined,
            shift: effectiveFilterShift || undefined,
            poste_id: filterPosteId || undefined,
            category: filterCategory || undefined,
            equipe,
          },
        })
      ).data,
  });

  const saveMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      if (editing) await api.patch(`/api/alertes-pannes/${editing.id}/`, payload);
      else await api.post("/api/alertes-pannes/", payload);
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["alertes-pannes"] });
      await qc.invalidateQueries({ queryKey: ["alertes-pannes-graph"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-pareto-types-percent"] });
      if (!isCcb) await qc.invalidateQueries({ queryKey: ["arrets-objectif-hourly"] });
      if (isCcb) await qc.invalidateQueries({ queryKey: ["prod-ccb"] });
      setOpen(false);
      setEditing(null);
      setErrorMsg(null);
    },
    onError: (err) => setErrorMsg(formatApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/api/alertes-pannes/${id}/`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["alertes-pannes"] });
      await qc.invalidateQueries({ queryKey: ["alertes-pannes-graph"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-pareto-types-percent"] });
      if (!isCcb) await qc.invalidateQueries({ queryKey: ["arrets-objectif-hourly"] });
      if (isCcb) await qc.invalidateQueries({ queryKey: ["prod-ccb"] });
      setErrorMsg(null);
    },
    onError: (err) => setErrorMsg(formatApiError(err)),
  });

  const openEdit = (row: AlertePanneRow) => {
    setEditing(row);
    setOpen(true);
    const parsed = splitCauseIntoDiversiteAndCommentaire(row.cause);
    const commentaire = isCcb
      ? String(row.cause ?? "").trim() || row.solution || ""
      : parsed.commentaire || row.solution || "";
    form.reset({
      module_id: row.module_id,
      poste_id: row.poste_id,
      moyen_id: row.moyen_id,
      panne_type_id: Number(row.panne_type_id) as never,
      commentaire,
      category: normalizeCategory(row.category),
      date: row.date.slice(0, 10),
      shift: normalizeShift(lockedShift ?? row.shift),
      heure_production: Number(row.heure_production) as never,
      temps_arret_min: row.temps_arret_min,
      ...(isCcb ? {} : { diversite: parsed.diversite }),
    });
  };

  const onSubmit = form.handleSubmit((values) => {
    const cause = isCcb
      ? values.commentaire.trim()
      : `[diversite:${(values as BerceauFormValues).diversite}] ${values.commentaire}`.trim();
    saveMutation.mutate({
      module_id: values.module_id,
      poste_id: values.poste_id,
      moyen_id: values.moyen_id,
      panne_type_id: values.panne_type_id,
      category: values.category,
      date: values.date,
      shift: (lockedShift ?? values.shift) as "A" | "B" | "N",
      heure_production: values.heure_production,
      temps_arret_min: values.temps_arret_min,
      cause,
      solution: values.commentaire,
      equipe,
    });
  });

  const totalAlertes = data?.total ?? 0;
  const activeFilters = [filterDate, filterShift, filterPosteId, filterCategory].filter(Boolean).length;
  const objectifA1 = Number(objectifs.A1 ?? 0);
  const objectifA3 = Number(objectifs.A3 ?? 0);
  const prodRowForImpact = objectifA1Query.data ?? null;
  const shiftHourlyTotal = useMemo(() => sumAllHourlyObjectifs(prodRowForImpact), [prodRowForImpact]);
  const graphRows = useMemo(() => arretsGraphQuery.data ?? [], [arretsGraphQuery.data]);

  const graphImpact = useMemo(() => {
    if (!graphEnabled) return null;
    const objectifShift = shiftHourlyTotal;
    const buckets = new Map<string, number>();
    for (const row of graphRows) {
      addRowToParetoMinuteBuckets(buckets, row, prodRowForImpact);
    }
    return analyzeParetoMinuteBuckets(buckets, objectifShift);
  }, [graphEnabled, graphRows, prodRowForImpact, shiftHourlyTotal]);

  const graphData = useMemo(() => {
    if (!graphImpact) return [];
    const rows = Array.from(graphImpact.byType.values());
    rows.sort((a, b) => b.pctA1 + b.pctA3 - (a.pctA1 + a.pctA3));
    return rows.slice(0, 20);
  }, [graphImpact]);

  const totalPct = useMemo(() => {
    if (!graphImpact) return { a1: 0, a3: 0 };
    return { a1: graphImpact.totalPctA1, a3: graphImpact.totalPctA3 };
  }, [graphImpact]);

  const groupedRowsByDate = useMemo(() => {
    const groups = new Map<string, AlertePanneRow[]>();
    for (const row of data?.results ?? []) {
      const d = row.date.slice(0, 10);
      if (!groups.has(d)) groups.set(d, []);
      groups.get(d)!.push(row);
    }
    return Array.from(groups.entries()).map(([dateKey, rows]) => ({ dateKey, rows }));
  }, [data?.results]);

  return (
    <Stack spacing={2.5}>
      <Paper
        elevation={0}
        sx={(t) => ({
          p: { xs: 2, md: 2.5 },
          borderRadius: 3,
          border: "1px solid",
          borderColor: "divider",
          background: `linear-gradient(135deg, ${alpha(t.palette.primary.main, 0.16)} 0%, ${alpha(
            t.palette.secondary.main,
            0.12
          )} 45%, ${alpha(t.palette.background.paper, 0.5)} 100%)`,
        })}
      >
        <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={1.5}>
          <Stack spacing={1}>
            <Typography variant="h5" fontWeight={800}>
              {`Arrêts · UEP ${equipe}`}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Chip label={`${totalAlertes} arrêts`} size="small" color="primary" variant="outlined" />
              {!isCcb && <Chip label={`${modules.length} modules`} size="small" variant="outlined" />}
              <Chip label={`${panneTypes.length} types`} size="small" variant="outlined" />
              {activeFilters > 0 && <Chip label={`${activeFilters} filtre(s)`} size="small" color="warning" variant="outlined" />}
            </Stack>
          </Stack>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button component="a" href={`/api/alertes-pannes/export/?${exportQuery}`} variant="outlined" size="small">
              Export Excel
            </Button>
            <PanneTypesManagerDialog
              equipe={equipe}
              canCreate={canCreate}
              canUpdate={canUpdate}
              canDelete={canDelete}
              variant="toolbar"
            />
            <Button
              startIcon={<AddIcon />}
              variant="contained"
              onClick={() => {
                resetAlerteFormForCreate();
                setOpen(true);
              }}
            >
              Ajouter un arrêt
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Paper
        elevation={0}
        sx={(t) => ({
          p: 1.25,
          borderRadius: 3,
          border: "1px solid",
          borderColor: "divider",
          background: `linear-gradient(180deg, ${alpha(t.palette.background.paper, 0.72)} 0%, ${alpha(
            t.palette.background.paper,
            0.46
          )} 100%)`,
          backdropFilter: "blur(18px)",
          boxShadow: "0 10px 32px rgba(0,0,0,0.35)",
        })}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={1}
          alignItems={{ md: "center" }}
          sx={{ flexWrap: { md: "wrap" } }}
          useFlexGap
        >
          <Stack direction="row" spacing={1} alignItems="center" sx={{ pr: { md: 0.5 } }}>
            <FilterAltOutlinedIcon fontSize="small" style={{ opacity: 0.9 }} />
            <Typography variant="subtitle2" fontWeight={800} sx={{ letterSpacing: "-0.01em" }}>
              Filtres
            </Typography>
            {activeFilters > 0 && <Chip size="small" color="warning" variant="outlined" label={`${activeFilters}`} />}
          </Stack>

          <GiDatePicker
            label="Date"
            value={filterDate}
            onChange={(v) => {
              setFilterDate(v);
              setPage(0);
            }}
            sx={{ width: { xs: "100%", sm: 220 } }}
          />

          <TextField
            select
            label="Shift"
            value={effectiveFilterShift}
            disabled={!!lockedShift}
            helperText={lockedShift ? "Shift impose (profil PSP)" : undefined}
            onChange={(e) => {
              setFilterShift(e.target.value);
              setPage(0);
            }}
            sx={{ width: { xs: "100%", sm: 180 } }}
          >
            {!lockedShift && <MenuItem value="">Tous</MenuItem>}
            {(lockedShift ? [lockedShift] : ["A", "B", "N"]).map((s) => (
              <MenuItem key={s} value={s}>
                {s}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            select
            label="Poste"
            value={filterPosteId}
            onChange={(e) => {
              setFilterPosteId(e.target.value);
              setPage(0);
            }}
            sx={{ width: { xs: "100%", md: 360 } }}
          >
            <MenuItem value="">Tous les postes</MenuItem>
            {equipePostes.map((p) => (
              <MenuItem key={p.id} value={String(p.id)}>
                {isCcb ? p.name : p.module_name ? `${p.module_name} / ${p.name}` : p.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            select
            label="Catégorie"
            value={filterCategory}
            onChange={(e) => {
              setFilterCategory(e.target.value);
              setPage(0);
            }}
            sx={{ width: { xs: "100%", sm: 240 } }}
          >
            <MenuItem value="">Toutes</MenuItem>
            {ARRET_CATEGORIES.map((c) => (
              <MenuItem key={c.value} value={c.value}>
                {c.label}
              </MenuItem>
            ))}
          </TextField>

          <Box sx={{ flexGrow: 1, display: { xs: "none", md: "block" } }} />

          <Button
            variant="outlined"
            size="small"
            startIcon={<RestartAltRoundedIcon />}
            onClick={() => {
              setFilterDate("");
              if (!lockedShift) setFilterShift("");
              setFilterPosteId("");
              setFilterCategory("");
              setPage(0);
            }}
            sx={{ alignSelf: { xs: "stretch", sm: "flex-start" }, minHeight: 40 }}
          >
            Réinitialiser
          </Button>
        </Stack>
      </Paper>

      {graphEnabled && (
        <Stack spacing={1.5}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.2}>
            <Paper sx={{ p: 1.4, borderRadius: 3, minWidth: 220 }}>
              <Typography variant="caption" color="text.secondary">
                % perte vs objectif (A1)
              </Typography>
              <Typography variant="h6" fontWeight={900}>
                {objectifA1 > 0 ? `${totalPct.a1.toFixed(2)}%` : "-"}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.75 }}>
                Formule: (temps / 1.3) × (100 / objectif du shift, Σ H1–H8)
              </Typography>
            </Paper>
            <Paper sx={{ p: 1.4, borderRadius: 3, minWidth: 220 }}>
              <Typography variant="caption" color="text.secondary">
                % perte vs objectif (A3)
              </Typography>
              <Typography variant="h6" fontWeight={900}>
                {objectifA3 > 0 ? `${totalPct.a3.toFixed(2)}%` : "-"}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.75 }}>
                Formule: (temps / 1.8) × (100 / objectif du shift, Σ H1–H8)
              </Typography>
            </Paper>
            <Paper sx={{ p: 1.4, borderRadius: 3, flex: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Objectifs (production)
              </Typography>
              <Typography variant="body2" fontWeight={800}>
                Σ shift (H1–H8): {shiftHourlyTotal > 0 ? shiftHourlyTotal : "—"} · A1: {objectifA1 > 0 ? objectifA1 : "—"} · A3:{" "}
                {objectifA3 > 0 ? objectifA3 : "—"}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.75 }}>
                Basé sur Production {filterDate} / shift {effectiveFilterShift}
              </Typography>
            </Paper>
          </Stack>

          <Paper sx={{ p: 2, borderRadius: 3 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mb: 1 }}>
              <Typography variant="h6" fontWeight={900}>
                % perte vs objectif par type d'arrêt (A1/A3)
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Top 20 types
              </Typography>
            </Stack>
            <Box sx={{ width: "100%", height: 380, minHeight: 260, ...CHART_OVERFLOW_SX }}>
              <SafeResponsiveContainer minHeight={260} boxSx={{ height: 380 }}>
                <BarChart data={graphData} margin={chart.margins.bar}>
                  <ChartGradientDefs chart={chart} />
                  <CartesianGrid {...chart.grid} />
                  <XAxis
                    dataKey="type"
                    angle={-28}
                    textAnchor="end"
                    height={80}
                    interval={0}
                    tick={chart.axis.tick}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={(v) => `${Number(v).toFixed(0)}%`}
                    width={52}
                    tick={chart.axis.tick}
                    axisLine={false}
                    tickLine={false}
                  />
                  <RechartsTooltip content={<StackedA1A3Tooltip chart={chart} />} />
                  <Legend content={<ChartLegendContent chart={chart} />} />
                  <Bar
                    dataKey="pctA1"
                    name="% A1"
                    stackId="pct"
                    fill={`url(#${chart.ids.barPrimary})`}
                    radius={[6, 6, 0, 0]}
                    isAnimationActive
                    animationDuration={chart.animation.barDuration}
                  />
                  <Bar
                    dataKey="pctA3"
                    name="% A3"
                    stackId="pct"
                    fill={`url(#${chart.ids.barSecondary})`}
                    radius={[6, 6, 0, 0]}
                    isAnimationActive
                    animationDuration={chart.animation.barDuration}
                  />
                </BarChart>
              </SafeResponsiveContainer>
            </Box>
            {!graphData.length && (
              <Typography color="text.secondary" sx={{ mt: 1 }}>
                Aucun arrêt pour ces filtres (ou objectifs manquants).
              </Typography>
            )}
          </Paper>
        </Stack>
      )}

      {errorMsg && (
        <Alert severity="error" onClose={() => setErrorMsg(null)}>
          {errorMsg}
        </Alert>
      )}

      <TableContainer component={Paper} elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: "action.hover" }}>
              <TableCell>Date</TableCell>
              <TableCell>Shift</TableCell>
              <TableCell>Heure</TableCell>
              <TableCell>{isCcb ? "Poste / Moyenne/Module" : "Module / Poste / Moyen"}</TableCell>
              <TableCell>Type arrêt</TableCell>
              <TableCell>Catégorie</TableCell>
              <TableCell>Temps arret</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={8}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <CircularProgress size={16} />
                    <Typography color="text.secondary">Chargement des arrêts...</Typography>
                  </Stack>
                </TableCell>
              </TableRow>
            )}
            {!isLoading && (data?.results.length ?? 0) === 0 && (
              <TableRow>
                <TableCell colSpan={8}>
                  <Typography color="text.secondary">Aucun arrêt trouve pour les filtres actuels.</Typography>
                </TableCell>
              </TableRow>
            )}
            {!isLoading &&
              groupedRowsByDate.map((group) => (
                <Fragment key={`group-${group.dateKey}`}>
                  <TableRow key={`header-${group.dateKey}`} sx={{ bgcolor: "rgba(37, 99, 235, 0.10)" }}>
                    <TableCell colSpan={8}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography fontWeight={800}>Date {group.dateKey}</Typography>
                        <Chip
                          size="small"
                          color="primary"
                          variant="outlined"
                          label={`${group.rows.length} arrêt(s)`}
                        />
                        <Chip
                          size="small"
                          variant="outlined"
                          label={`Shifts: ${Array.from(new Set(group.rows.map((r) => r.shift))).join(" / ")}`}
                        />
                      </Stack>
                    </TableCell>
                  </TableRow>
                  {group.rows.map((row) => (
                    <TableRow key={row.id} hover>
                      <TableCell>{row.date.slice(0, 10)}</TableCell>
                      <TableCell>{row.shift}</TableCell>
                      <TableCell>H{row.heure_production}</TableCell>
                      <TableCell>
                        {isCcb ? `${row.poste_nom} / ${row.moyen_nom}` : `${row.module_nom} / ${row.poste_nom} / ${row.moyen_nom}`}
                      </TableCell>
                      <TableCell>{row.panne_type_nom}</TableCell>
                      <TableCell>{row.category_label}</TableCell>
                      <TableCell>{row.temps_arret_min} min</TableCell>
                      <TableCell align="right">
                        <Tooltip title="Modifier">
                          <IconButton size="small" onClick={() => openEdit(row)}>
                            <EditOutlinedIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        {canDelete && (
                          <Tooltip title="Supprimer">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => window.confirm("Supprimer cet arrêt ?") && deleteMutation.mutate(row.id)}
                            >
                              <DeleteOutlineIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </Fragment>
              ))}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={data?.total ?? 0}
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

      <Dialog
        open={open}
        onClose={() => {
          setOpen(false);
          resetAlerteFormForCreate();
        }}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>{editing ? "Modifier" : "Ajouter"} un arrêt</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 0.5 }}>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {isCcb ? (
                <>
                  <Chip label="Etape 1: Poste" size="small" color={posteId ? "primary" : "default"} />
                  <Chip label="Etape 2: Moyen" size="small" color={moyenId ? "primary" : "default"} />
                  <Chip label="Etape 3: Type d'arrêt" size="small" color={form.watch("panne_type_id") ? "primary" : "default"} />
                </>
              ) : (
                <>
                  <Chip label="Etape 1: Module" size="small" color={moduleId ? "primary" : "default"} />
                  <Chip label="Etape 2: Poste" size="small" color={posteId ? "primary" : "default"} />
                  <Chip label="Etape 3: Moyen" size="small" color={moyenId ? "primary" : "default"} />
                  <Chip label="Etape 4: Type d'arrêt" size="small" color={form.watch("panne_type_id") ? "primary" : "default"} />
                </>
              )}
            </Stack>
            <Divider />
            {isCcb ? (
              <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                <TextField
                  select
                  label="Poste"
                  fullWidth
                  value={posteId || ""}
                  onChange={(e) => {
                    const id = Number(e.target.value);
                    form.setValue("poste_id", id as never);
                    form.setValue("moyen_id", undefined as never);
                  }}
                >
                  {formPostes.map((p) => (
                    <MenuItem key={p.id} value={p.id}>
                      {p.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  select
                  label="Moyen"
                  fullWidth
                  disabled={!posteId}
                  value={moyenId || ""}
                  helperText={
                    !posteId
                      ? "Choisir un poste d'abord — la liste des moyens dépend du poste."
                      : `Moyens pour « ${selectedPoste?.name ?? "…"} »`
                  }
                  onChange={(e) => form.setValue("moyen_id", Number(e.target.value) as never)}
                >
                  {moyens.map((m) => (
                    <MenuItem key={m.id} value={m.id}>
                      {m.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Stack>
            ) : (
              <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                <TextField
                  select
                  label="Module"
                  fullWidth
                  value={moduleId || ""}
                  onChange={(e) => {
                    const id = Number(e.target.value);
                    const next = onModuleChange(
                      { moduleId, posteId: posteId || undefined, moyenId: moyenId || undefined },
                      id
                    );
                    form.setValue("module_id", (next.moduleId ?? 0) as never);
                    form.setValue("poste_id", (next.posteId ?? 0) as never);
                    form.setValue("moyen_id", (next.moyenId ?? 0) as never);
                  }}
                >
                  {modules.map((m) => (
                    <MenuItem key={m.id} value={m.id}>
                      {m.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  select
                  label="Poste"
                  fullWidth
                  disabled={!moduleId}
                  value={posteId || ""}
                  helperText={!moduleId ? "Choisir un module d'abord" : undefined}
                  onChange={(e) => {
                    const id = Number(e.target.value);
                    const next = onPosteChange(
                      { moduleId, posteId: posteId || undefined, moyenId: moyenId || undefined },
                      id
                    );
                    form.setValue("poste_id", (next.posteId ?? 0) as never);
                    form.setValue("moyen_id", (next.moyenId ?? 0) as never);
                  }}
                >
                  {postesByModule.map((p) => (
                    <MenuItem key={p.id} value={p.id}>
                      {p.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  select
                  label="Moyen"
                  fullWidth
                  disabled={!posteId}
                  value={moyenId || ""}
                  helperText={!posteId ? "Choisir un poste d'abord" : undefined}
                  onChange={(e) => form.setValue("moyen_id", Number(e.target.value) as never)}
                >
                  {moyens.map((m) => (
                    <MenuItem key={m.id} value={m.id}>
                      {m.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Stack>
            )}
            
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <TextField
                select
                label="Type d'arrêt"
                fullWidth
                value={form.watch("panne_type_id") || ""}
                onChange={(e) => form.setValue("panne_type_id", Number(e.target.value) as never)}
              >
                {panneTypes.map((pt) => (
                  <MenuItem key={pt.id} value={pt.id}>
                    {pt.name}
                  </MenuItem>
                ))}
              </TextField>
              <PanneTypesManagerDialog
                equipe={equipe}
                canCreate={canCreate}
                canUpdate={canUpdate}
                canDelete={canDelete}
                variant="inline"
                onSelectType={(id) =>
                  form.setValue("panne_type_id", id as never, { shouldValidate: true, shouldDirty: true })
                }
              />
            </Stack>
            <TextField
              select
              label="Catégorie d'arrêt"
              fullWidth
              value={form.watch("category") || ""}
              onChange={(e) => form.setValue("category", e.target.value as never)}
            >
              {ARRET_CATEGORIES.map((c) => (
                <MenuItem key={c.value} value={c.value}>
                  {c.label}
                </MenuItem>
              ))}
            </TextField>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <GiDatePickerRhf control={form.control} name="date" label="Date" fullWidth />
              <TextField
                select
                label="Shift"
                fullWidth
                disabled={!!lockedShift}
                helperText={lockedShift ? "Shift impose (profil PSP)" : undefined}
                value={form.watch("shift") || ""}
                onChange={(e) => form.setValue("shift", e.target.value as never)}
              >
                {(lockedShift ? ([lockedShift] as const) : (["A", "B", "N"] as const)).map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label="Heure production"
                fullWidth
                value={form.watch("heure_production") || ""}
                onChange={(e) => form.setValue("heure_production", Number(e.target.value) as never)}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map((h) => (
                  <MenuItem key={h} value={h}>
                    H{h}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            {!isCcb && (
              <TextField
                select
                label="Diversité (A1 / A3)"
                fullWidth
                disabled={!selectedPoste || (!selectedPoste.a1_enabled && !selectedPoste.a3_enabled)}
                helperText={
                  !selectedPoste
                    ? "Choisir un poste d'abord"
                    : !selectedPoste.a1_enabled && !selectedPoste.a3_enabled
                      ? "A1/A3 non configuré pour ce poste"
                      : undefined
                }
                value={String(form.watch("diversite") ?? "")}
                onChange={(e) => form.setValue("diversite", e.target.value as never)}
              >
                {DIVERSITES.filter((d) => {
                  if (!selectedPoste) return true;
                  if (d.value === "A1") return selectedPoste.a1_enabled;
                  if (d.value === "A3") return selectedPoste.a3_enabled;
                  return true;
                }).map((d) => (
                  <MenuItem key={d.value} value={d.value}>
                    {d.label}
                  </MenuItem>
                ))}
              </TextField>
            )}
            <TextField label="Commentaire" fullWidth multiline minRows={3} {...form.register("commentaire")} />
            <TextField
              label="Temps d'arret (min)"
              type="number"
              required
              fullWidth
              value={tempsArret ?? ""}
              onChange={(e) => {
                const raw = e.target.value;
                form.setValue("temps_arret_min", (raw === "" ? undefined : Number(raw)) as never);
              }}
              helperText={`${autoTimeLabel(autoTime?.found, autoTime?.temps_arret_min)} · Champ obligatoire`}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    {autoTimeEnabled ? (
                      <Chip size="small" color={autoTime?.found ? "success" : "default"} label={autoTime?.found ? "Auto trouve" : "Auto 0"} />
                    ) : null}
                  </InputAdornment>
                ),
              }}
            />
            <Button
              variant="outlined"
              onClick={() => {
                if (autoTime?.found) form.setValue("temps_arret_min", Number(autoTime.temps_arret_min) as never);
                else form.setValue("temps_arret_min", undefined as never);
              }}
              disabled={!autoTimeEnabled}
            >
              Charger valeur auto
            </Button>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => {
              setOpen(false);
              resetAlerteFormForCreate();
            }}
          >
            Annuler
          </Button>
          <Button variant="contained" onClick={onSubmit} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? "Enregistrement..." : "Enregistrer"}
          </Button>
        </DialogActions>
      </Dialog>

    </Stack>
  );
}
