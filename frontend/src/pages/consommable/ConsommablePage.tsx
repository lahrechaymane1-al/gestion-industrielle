import { zodResolver } from "@hookform/resolvers/zod";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import Inventory2OutlinedIcon from "@mui/icons-material/Inventory2Outlined";
import PaidOutlinedIcon from "@mui/icons-material/PaidOutlined";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
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
import { alpha, useTheme } from "@mui/material/styles";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Tooltip, XAxis, YAxis } from "recharts";
import * as XLSX from "xlsx";
import { z } from "zod";
import { api, formatApiError } from "../../api/client";
import { useMe } from "../../auth/AuthContext";
import { ChartGradientDefs, ChartPlotFrame, useChartTheme } from "../../components/charts";
import { SafeResponsiveContainer } from "../../components/SafeResponsiveContainer";
import { designTokens } from "../../theme/designTokens";
import type {
  ConsommableItemRow,
  ConsommablePurchaseRow,
  ConsommableShiftStat,
  EquipeScope,
  Paginated,
} from "../../api/types";

const DEFAULT_TYPE_OPTIONS = ["EPIs", "AUTRE", "FOURNITURE", "PR BERCEAU", "PR TORCHE MANUELLE", "PRODUIT CHIMIQUE"];
const SHIFT_OPTIONS = ["A", "B", "N"] as const;
const SHIFT_COLORS: Record<string, string> = { A: "#2563eb", B: "#16a34a", N: "#94a3b8" };

const itemSchema = z.object({
  type_materiel: z.string().trim().min(1, "Type obligatoire").max(40, "Max 40 caractères"),
  name: z.string().min(1, "Nom obligatoire"),
  reference: z.string().min(1, "Référence obligatoire"),
  unit_price_eur: z.coerce.number().min(0, "Prix >= 0"),
});

const purchaseSchema = z.object({
  item: z.object({
    id: z.number(),
    type_materiel: z.string(),
    name: z.string(),
    reference: z.string(),
    unit_price_eur: z.string(),
  }),
  shift: z.enum(SHIFT_OPTIONS, { errorMap: () => ({ message: "Shift obligatoire" }) }),
  quantity: z.coerce.number().int().min(1, "Quantité > 0"),
  purchase_date: z.string().min(1, "Date obligatoire"),
  note: z.string().optional(),
});

type ItemFormValues = z.infer<typeof itemSchema>;
type PurchaseFormValues = z.infer<typeof purchaseSchema>;
type ConsommableTypeRow = { type_materiel: string; total: number };

function todayISO() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function currentMonthISO() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function toEuro(value: string | number): string {
  const num = typeof value === "number" ? value : Number(value || 0);
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(Number.isFinite(num) ? num : 0);
}

export default function ConsommablePage({ equipe }: { equipe: EquipeScope }) {
  const theme = useTheme();
  const chart = useChartTheme();
  const me = useMe();
  const canAccess = me?.role ? me.role === "RU" || me.role === "ADMIN" : true;
  const qc = useQueryClient();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [itemsManagerOpen, setItemsManagerOpen] = useState(false);
  const [managerItem, setManagerItem] = useState<ConsommableItemRow | null>(null);
  const [purchaseOpen, setPurchaseOpen] = useState(false);
  const [editingPurchase, setEditingPurchase] = useState<ConsommablePurchaseRow | null>(null);
  const [typeManagerOpen, setTypeManagerOpen] = useState(false);
  const [selectedType, setSelectedType] = useState("");
  const [newTypeName, setNewTypeName] = useState("");
  const [exporting, setExporting] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(15);
  const [search, setSearch] = useState("");
  // Graph 1 (money per shift): period filter = day or month
  const [moneyMode, setMoneyMode] = useState<"day" | "month">("day");
  const [moneyDay, setMoneyDay] = useState(todayISO());
  const [moneyMonth, setMoneyMonth] = useState(currentMonthISO());
  // Graph 2 (quantity per shift): period + shift + type filters
  const [qtyMode, setQtyMode] = useState<"day" | "month">("day");
  const [qtyDay, setQtyDay] = useState(todayISO());
  const [qtyMonth, setQtyMonth] = useState(currentMonthISO());
  const [qtyShift, setQtyShift] = useState<"" | "A" | "B" | "N">("");
  const [qtyType, setQtyType] = useState("");

  const { data: itemsRes } = useQuery({
    queryKey: ["consommable-items", equipe],
    enabled: canAccess,
    queryFn: async () => {
      const { data } = await api.get<{ results: ConsommableItemRow[] }>("/api/consommables/items/", { params: { equipe } });
      return data.results;
    },
  });
  const items = useMemo(() => itemsRes ?? [], [itemsRes]);
  const { data: typeStatsRes } = useQuery({
    queryKey: ["consommable-types", equipe],
    enabled: canAccess,
    queryFn: async () => {
      const { data } = await api.get<{ results: ConsommableTypeRow[] }>("/api/consommables/types/", { params: { equipe } });
      return data.results;
    },
  });
  const typeStats = useMemo(() => typeStatsRes ?? [], [typeStatsRes]);
  const typeOptions = useMemo(() => {
    const values = new Set(DEFAULT_TYPE_OPTIONS);
    for (const row of typeStats) {
      const type = row.type_materiel?.trim();
      if (type) values.add(type);
    }
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }, [typeStats]);

  const { data: purchases, isLoading } = useQuery({
    queryKey: ["consommable-purchases", equipe, page, rowsPerPage, search],
    enabled: canAccess,
    queryFn: async () => {
      const { data } = await api.get<Paginated<ConsommablePurchaseRow>>("/api/consommables/purchases/", {
        params: { equipe, page: page + 1, per_page: rowsPerPage, ...(search.trim() ? { q: search.trim() } : {}) },
      });
      return data;
    },
  });

  const { data: moneyStats } = useQuery({
    queryKey: ["consommable-money", equipe, moneyMode, moneyDay, moneyMonth],
    enabled: canAccess,
    queryFn: async () => {
      const params =
        moneyMode === "month"
          ? { equipe, mode: "month", month: moneyMonth }
          : { equipe, mode: "day", date: moneyDay };
      const { data } = await api.get<{ results: ConsommableShiftStat[] }>("/api/consommables/stats/", { params });
      return data.results;
    },
  });
  const { data: qtyStats } = useQuery({
    queryKey: ["consommable-qty", equipe, qtyMode, qtyDay, qtyMonth, qtyShift, qtyType],
    enabled: canAccess,
    queryFn: async () => {
      const periodParams =
        qtyMode === "month" ? { mode: "month", month: qtyMonth } : { mode: "day", date: qtyDay };
      const { data } = await api.get<{ results: ConsommableShiftStat[] }>("/api/consommables/stats/", {
        params: {
          equipe,
          ...periodParams,
          ...(qtyShift ? { shift: qtyShift } : {}),
          ...(qtyType ? { type_materiel: qtyType } : {}),
        },
      });
      return data.results;
    },
  });

  const moneyChartData = useMemo(
    () =>
      (moneyStats ?? []).map((row) => ({
        shift: `Shift ${row.shift}`,
        key: row.shift,
        total_eur: Number(row.total_eur || 0),
      })),
    [moneyStats]
  );
  const qtyChartData = useMemo(
    () =>
      (qtyStats ?? [])
        .filter((row) => (qtyShift ? row.shift === qtyShift : true))
        .map((row) => ({
          shift: `Shift ${row.shift}`,
          key: row.shift,
          total_qty: row.total_qty,
        })),
    [qtyStats, qtyShift]
  );

  const itemForm = useForm<ItemFormValues>({
    resolver: zodResolver(itemSchema),
    defaultValues: { type_materiel: "AUTRE", name: "", reference: "", unit_price_eur: 0 },
  });

  const purchaseForm = useForm<PurchaseFormValues>({
    resolver: zodResolver(purchaseSchema),
    defaultValues: {
      item: items[0]
        ? {
            id: items[0].id,
            type_materiel: items[0].type_materiel,
            name: items[0].name,
            reference: items[0].reference,
            unit_price_eur: items[0].unit_price_eur,
          }
        : { id: 0, type_materiel: "", name: "", reference: "", unit_price_eur: "0.00" },
      shift: "A",
      quantity: 1,
      purchase_date: todayISO(),
      note: "",
    },
  });

  const watchedItem = purchaseForm.watch("item");
  const watchedQty = purchaseForm.watch("quantity");
  const unitPrice = Number(watchedItem?.unit_price_eur || 0);
  const total = Number.isFinite(unitPrice) ? unitPrice * (Number(watchedQty) || 0) : 0;
  const chartCardSx = {
    minHeight: 400,
    border: "1px solid",
    borderColor: alpha(theme.palette.divider, 0.5),
    borderRadius: 3,
    bgcolor: designTokens.glass.fill,
    overflow: "hidden",
    boxShadow: `0 8px 32px ${alpha(theme.palette.common.black, 0.18)}`,
    transition: `box-shadow 0.3s ease, transform 0.3s cubic-bezier(${designTokens.motion.easeOut.join(",")})`,
    "&:hover": {
      boxShadow: `0 12px 48px ${alpha(theme.palette.common.black, 0.32)}`,
    },
  };
  const chartAxis = chart.axis;

  const resetManagerForm = () => {
    setManagerItem(null);
    itemForm.reset({ type_materiel: "AUTRE", name: "", reference: "", unit_price_eur: 0 });
  };

  const saveItemMutation = useMutation({
    mutationFn: async (payload: ItemFormValues) => {
      if (managerItem) {
        await api.patch(`/api/consommables/items/${managerItem.id}/`, { ...payload, equipe });
      } else {
        await api.post("/api/consommables/items/", { ...payload, equipe });
      }
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["consommable-items", equipe] });
      await qc.invalidateQueries({ queryKey: ["consommable-types", equipe] });
      if (!managerItem) {
        resetManagerForm();
      }
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const deleteItemMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/api/consommables/items/${id}/`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["consommable-items", equipe] });
      await qc.invalidateQueries({ queryKey: ["consommable-types", equipe] });
      resetManagerForm();
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const savePurchaseMutation = useMutation({
    mutationFn: async (payload: PurchaseFormValues) => {
      const body = {
        equipe,
        item_id: payload.item.id,
        shift: payload.shift,
        quantity: payload.quantity,
        purchase_date: payload.purchase_date,
        note: payload.note ?? "",
      };
      if (editingPurchase) {
        await api.patch(`/api/consommables/purchases/${editingPurchase.id}/`, body);
      } else {
        await api.post("/api/consommables/purchases/", body);
      }
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["consommable-purchases", equipe] });
      await qc.invalidateQueries({ queryKey: ["consommable-money", equipe] });
      await qc.invalidateQueries({ queryKey: ["consommable-qty", equipe] });
      setPurchaseOpen(false);
      setEditingPurchase(null);
      if (items[0]) {
        purchaseForm.reset({
          item: {
            id: items[0].id,
            type_materiel: items[0].type_materiel,
            name: items[0].name,
            reference: items[0].reference,
            unit_price_eur: items[0].unit_price_eur,
          },
          shift: "A",
          quantity: 1,
          purchase_date: todayISO(),
          note: "",
        });
      }
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const deletePurchaseMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/api/consommables/purchases/${id}/`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["consommable-purchases", equipe] });
      await qc.invalidateQueries({ queryKey: ["consommable-money", equipe] });
      await qc.invalidateQueries({ queryKey: ["consommable-qty", equipe] });
    },
  });

  const renameTypeMutation = useMutation({
    mutationFn: async ({ oldType, newType }: { oldType: string; newType: string }) => {
      await api.patch("/api/consommables/types/", { equipe, old_type: oldType, new_type: newType });
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["consommable-types", equipe] });
      await qc.invalidateQueries({ queryKey: ["consommable-items", equipe] });
      await qc.invalidateQueries({ queryKey: ["consommable-purchases", equipe] });
      setSelectedType("");
      setNewTypeName("");
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const deleteTypeMutation = useMutation({
    mutationFn: async ({ oldType, replacement }: { oldType: string; replacement: string }) => {
      await api.delete("/api/consommables/types/", {
        data: { equipe, old_type: oldType, replacement_type: replacement || "AUTRE" },
      });
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["consommable-types", equipe] });
      await qc.invalidateQueries({ queryKey: ["consommable-items", equipe] });
      await qc.invalidateQueries({ queryKey: ["consommable-purchases", equipe] });
      setSelectedType("");
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const openItemsManager = (item?: ConsommableItemRow | null) => {
    if (item) {
      setManagerItem(item);
      itemForm.reset({
        type_materiel: item.type_materiel,
        name: item.name,
        reference: item.reference,
        unit_price_eur: Number(item.unit_price_eur || 0),
      });
    } else {
      resetManagerForm();
    }
    setItemsManagerOpen(true);
  };

  const onCreatePurchase = () => {
    setEditingPurchase(null);
    if (items[0]) {
      purchaseForm.reset({
        item: {
          id: items[0].id,
          type_materiel: items[0].type_materiel,
          name: items[0].name,
          reference: items[0].reference,
          unit_price_eur: items[0].unit_price_eur,
        },
        shift: "A",
        quantity: 1,
        purchase_date: todayISO(),
        note: "",
      });
    }
    setPurchaseOpen(true);
  };

  const onExportExcel = async () => {
    setExporting(true);
    setErrorMsg(null);
    try {
      const all: ConsommablePurchaseRow[] = [];
      let pageNum = 1;
      let totalPages = 1;
      do {
        const { data } = await api.get<Paginated<ConsommablePurchaseRow>>("/api/consommables/purchases/", {
          params: { equipe, page: pageNum, per_page: 100, ...(search.trim() ? { q: search.trim() } : {}) },
        });
        all.push(...data.results);
        totalPages = data.pages || 1;
        pageNum += 1;
      } while (pageNum <= totalPages);

      if (!all.length) {
        setErrorMsg("Aucun achat à exporter pour cette UEP.");
        return;
      }

      const headers = [
        "Date",
        "Référence",
        "Type de matériel",
        "Shift",
        "Article",
        "Prix / pièce (€)",
        "Quantité",
        "Total (€)",
        "Note",
      ];
      const body = all.map((r) => [
        r.purchase_date,
        r.item_reference,
        r.item_type,
        r.shift,
        r.item_name,
        Number(r.unit_price_eur || 0),
        r.quantity,
        Number(r.total_price_eur || 0),
        r.note || "",
      ]);
      const ws = XLSX.utils.aoa_to_sheet([headers, ...body]);
      ws["!cols"] = [
        { wch: 12 },
        { wch: 16 },
        { wch: 20 },
        { wch: 7 },
        { wch: 52 },
        { wch: 14 },
        { wch: 10 },
        { wch: 14 },
        { wch: 30 },
      ];
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Consommables");
      const stamp = todayISO();
      XLSX.writeFile(wb, `consommables_${equipe.toLowerCase()}_${stamp}.xlsx`);
    } catch (e) {
      setErrorMsg(formatApiError(e));
    } finally {
      setExporting(false);
    }
  };

  if (!canAccess) {
    return (
      <Alert severity="warning" sx={{ mt: 2 }}>
        Le module Consommables est réservé aux profils RU et Administrateur.
      </Alert>
    );
  }

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "center" }} gap={1}>
        <Typography variant="h5" fontWeight={800}>
          Consommables · UEP {equipe}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" onClick={() => openItemsManager()}>
            Gérer articles
          </Button>
          <Button variant="outlined" onClick={() => setTypeManagerOpen(true)}>
            Gérer types
          </Button>
          <Button
            variant="outlined"
            startIcon={<FileDownloadOutlinedIcon />}
            onClick={onExportExcel}
            disabled={exporting}
          >
            {exporting ? "Export…" : "Exporter Excel"}
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={onCreatePurchase} disabled={!items.length}>
            Ajouter achat
          </Button>
        </Stack>
      </Stack>

      {!items.length && (
        <Alert severity="info">
          Aucun article consommable pour cette UEP. Commencez par <strong>Gérer articles</strong>.
        </Alert>
      )}

      {errorMsg && (
        <Alert severity="error" onClose={() => setErrorMsg(null)}>
          {errorMsg}
        </Alert>
      )}

      <TextField
        size="small"
        label="Rechercher achat"
        placeholder="Nom, référence ou note"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(0);
        }}
        sx={{ maxWidth: 380 }}
      />

      <TableContainer component={Paper} elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: "action.hover" }}>
              <TableCell>Date</TableCell>
              <TableCell>Shift</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Article</TableCell>
              <TableCell>Référence</TableCell>
              <TableCell align="right">Prix / pièce (€)</TableCell>
              <TableCell align="right">Quantité</TableCell>
              <TableCell align="right">Total (€)</TableCell>
              <TableCell>Note</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={10}>Chargement…</TableCell>
              </TableRow>
            )}
            {!isLoading && !purchases?.results.length && (
              <TableRow>
                <TableCell colSpan={10}>
                  <Typography color="text.secondary">Aucun achat consommable.</Typography>
                </TableCell>
              </TableRow>
            )}
            {purchases?.results.map((row) => (
              <TableRow key={row.id} hover>
                <TableCell>{row.purchase_date}</TableCell>
                <TableCell>{row.shift}</TableCell>
                <TableCell>{row.item_type}</TableCell>
                <TableCell>{row.item_name}</TableCell>
                <TableCell>{row.item_reference}</TableCell>
                <TableCell align="right">{toEuro(row.unit_price_eur)}</TableCell>
                <TableCell align="right">{row.quantity}</TableCell>
                <TableCell align="right">{toEuro(row.total_price_eur)}</TableCell>
                <TableCell>{row.note || "—"}</TableCell>
                <TableCell align="right">
                  <IconButton
                    size="small"
                    onClick={() => {
                      const item = items.find((it) => it.id === row.item_id);
                      if (!item) return;
                      setEditingPurchase(row);
                      purchaseForm.reset({
                        item: {
                          id: item.id,
                          type_materiel: item.type_materiel,
                          name: item.name,
                          reference: item.reference,
                          unit_price_eur: item.unit_price_eur,
                        },
                        shift: row.shift,
                        quantity: row.quantity,
                        purchase_date: row.purchase_date,
                        note: row.note ?? "",
                      });
                      setPurchaseOpen(true);
                    }}
                  >
                    <EditOutlinedIcon fontSize="small" />
                  </IconButton>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => {
                      if (!window.confirm("Supprimer cet achat consommable ?")) return;
                      deletePurchaseMutation.mutate(row.id);
                    }}
                  >
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        component="div"
        page={page}
        count={purchases?.total ?? 0}
        onPageChange={(_, p) => setPage(p)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(e) => {
          setRowsPerPage(parseInt(e.target.value, 10));
          setPage(0);
        }}
        rowsPerPageOptions={[10, 15, 25, 50]}
      />

      <Paper
        elevation={0}
        sx={{
          ...chartCardSx,
          borderLeft: "4px solid",
          borderLeftColor: "primary.main",
          backgroundImage: (t) => `linear-gradient(180deg, ${alpha(t.palette.primary.light, 0.05)} 0%, transparent 36%)`,
        }}
      >
        <Stack spacing={1.5} sx={{ p: 2.25 }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            alignItems={{ xs: "stretch", md: "flex-start" }}
            justifyContent="space-between"
            spacing={1.75}
            sx={{ pb: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
          >
            <Stack direction="row" spacing={1.75} alignItems="flex-start">
              <Box
                sx={{
                  p: 1,
                  borderRadius: 2,
                  bgcolor: alpha(theme.palette.primary.main, 0.12),
                  border: "1px solid",
                  borderColor: alpha(theme.palette.primary.main, 0.32),
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <PaidOutlinedIcon sx={{ color: "primary.light", fontSize: 22 }} />
              </Box>
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="subtitle1" fontWeight={800} sx={{ letterSpacing: "-0.01em" }}>
                  Argent total par shift
                </Typography>
                <Typography variant="caption" sx={{ mt: 0.35, display: "block", lineHeight: 1.5, color: "text.secondary" }}>
                  Montant total des achats consommables (€) · UEP {equipe}
                </Typography>
              </Box>
            </Stack>
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
            <TextField
              select
              size="small"
              label="Période"
              value={moneyMode}
              onChange={(e) => setMoneyMode(e.target.value as "day" | "month")}
              sx={{ minWidth: 130 }}
            >
              <MenuItem value="day">Par jour</MenuItem>
              <MenuItem value="month">Par mois</MenuItem>
            </TextField>
            {moneyMode === "day" ? (
              <TextField
                label="Jour"
                type="date"
                size="small"
                value={moneyDay}
                onChange={(e) => setMoneyDay(e.target.value)}
                InputLabelProps={{ shrink: true }}
                sx={{ minWidth: 190 }}
              />
            ) : (
              <TextField
                label="Mois"
                type="month"
                size="small"
                value={moneyMonth}
                onChange={(e) => setMoneyMonth(e.target.value)}
                InputLabelProps={{ shrink: true }}
                sx={{ minWidth: 190 }}
              />
            )}
          </Stack>
        </Stack>
        {moneyChartData.every((d) => d.total_eur === 0) ? (
          <Alert severity="info">Aucune consommation sur cette période.</Alert>
        ) : (
          <ChartPlotFrame accent="primary">
            <Box sx={{ width: "100%", height: 320, p: 1 }}>
              <SafeResponsiveContainer minHeight={260} boxSx={{ height: "100%" }}>
                <BarChart data={moneyChartData} margin={{ top: 28, right: 18, left: 4, bottom: 18 }} barCategoryGap="34%">
                  <ChartGradientDefs chart={chart} />
                  <CartesianGrid {...chart.grid} />
                  <XAxis dataKey="shift" {...chartAxis} />
                  <YAxis {...chartAxis} width={56} />
                  <Tooltip cursor={chart.tooltip.barCursor} formatter={(v) => toEuro(Number(v))} />
                  <Bar dataKey="total_eur" name="Total (€)" fill={`url(#${chart.ids.barPrimary})`} radius={[8, 8, 0, 0]} maxBarSize={72}>
                  {moneyChartData.map((d) => (
                    <Cell key={d.key} fill={SHIFT_COLORS[d.key] ?? "#2563eb"} />
                  ))}
                  <LabelList dataKey="total_eur" position="top" formatter={(v) => toEuro(Number(v))} />
                </Bar>
              </BarChart>
            </SafeResponsiveContainer>
            </Box>
          </ChartPlotFrame>
        )}
        </Stack>
      </Paper>

      <Paper
        elevation={0}
        sx={{
          ...chartCardSx,
          borderLeft: "4px solid",
          borderLeftColor: designTokens.accent.emerald,
          backgroundImage: `linear-gradient(180deg, ${alpha(designTokens.accent.emerald, 0.05)} 0%, transparent 36%)`,
        }}
      >
        <Stack spacing={1.5} sx={{ p: 2.25 }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            alignItems={{ xs: "stretch", md: "flex-start" }}
            justifyContent="space-between"
            spacing={1.75}
            sx={{ pb: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
          >
            <Stack direction="row" spacing={1.75} alignItems="flex-start">
              <Box
                sx={{
                  p: 1,
                  borderRadius: 2,
                  bgcolor: alpha(designTokens.accent.emerald, 0.12),
                  border: "1px solid",
                  borderColor: alpha(designTokens.accent.emerald, 0.32),
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <Inventory2OutlinedIcon sx={{ color: designTokens.accent.emerald, fontSize: 22 }} />
              </Box>
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="subtitle1" fontWeight={800} sx={{ letterSpacing: "-0.01em" }}>
                  Quantité par shift
                </Typography>
                <Typography variant="caption" sx={{ mt: 0.35, display: "block", lineHeight: 1.5, color: "text.secondary" }}>
                  Quantité totale d'articles consommés · UEP {equipe}
                </Typography>
              </Box>
            </Stack>
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
            <TextField
              select
              size="small"
              label="Période"
              value={qtyMode}
              onChange={(e) => setQtyMode(e.target.value as "day" | "month")}
              sx={{ minWidth: 120 }}
            >
              <MenuItem value="day">Par jour</MenuItem>
              <MenuItem value="month">Par mois</MenuItem>
            </TextField>
            {qtyMode === "day" ? (
              <TextField
                label="Jour"
                type="date"
                size="small"
                value={qtyDay}
                onChange={(e) => setQtyDay(e.target.value)}
                InputLabelProps={{ shrink: true }}
                sx={{ minWidth: 175 }}
              />
            ) : (
              <TextField
                label="Mois"
                type="month"
                size="small"
                value={qtyMonth}
                onChange={(e) => setQtyMonth(e.target.value)}
                InputLabelProps={{ shrink: true }}
                sx={{ minWidth: 175 }}
              />
            )}
            <TextField
              select
              size="small"
              label="Shift"
              value={qtyShift}
              onChange={(e) => setQtyShift(e.target.value as "" | "A" | "B" | "N")}
              sx={{ minWidth: 120 }}
            >
              <MenuItem value="">Tous</MenuItem>
              {SHIFT_OPTIONS.map((s) => (
                <MenuItem key={s} value={s}>
                  Shift {s}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              size="small"
              label="Type de matériel"
              value={qtyType}
              onChange={(e) => setQtyType(e.target.value)}
              sx={{ minWidth: 200 }}
            >
              <MenuItem value="">Tous</MenuItem>
              {typeOptions.map((t) => (
                <MenuItem key={t} value={t}>
                  {t}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
        </Stack>
        {qtyChartData.every((d) => d.total_qty === 0) ? (
          <Alert severity="info">Aucune consommation pour ce filtre.</Alert>
        ) : (
          <ChartPlotFrame accent="success">
            <Box sx={{ width: "100%", height: 320, p: 1 }}>
              <SafeResponsiveContainer minHeight={260} boxSx={{ height: "100%" }}>
                <BarChart data={qtyChartData} margin={{ top: 28, right: 18, left: 4, bottom: 18 }} barCategoryGap="34%">
                  <ChartGradientDefs chart={chart} />
                  <CartesianGrid {...chart.grid} />
                  <XAxis dataKey="shift" {...chartAxis} />
                  <YAxis {...chartAxis} width={56} allowDecimals={false} />
                  <Tooltip cursor={chart.tooltip.barCursor} formatter={(v) => `${Number(v)} pcs`} />
                  <Bar dataKey="total_qty" name="Quantité" fill={`url(#${chart.ids.barGreen})`} radius={[8, 8, 0, 0]} maxBarSize={72}>
                  {qtyChartData.map((d) => (
                    <Cell key={d.key} fill={SHIFT_COLORS[d.key] ?? "#16a34a"} />
                  ))}
                  <LabelList dataKey="total_qty" position="top" />
                </Bar>
              </BarChart>
            </SafeResponsiveContainer>
            </Box>
          </ChartPlotFrame>
        )}
        </Stack>
      </Paper>

      <Dialog
        open={itemsManagerOpen}
        onClose={() => {
          setItemsManagerOpen(false);
          resetManagerForm();
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Gérer les articles</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} mt={0.5}>
            <Autocomplete
              options={items}
              getOptionLabel={(o) => `${o.name} · ${o.reference}`}
              value={managerItem}
              onChange={(_, option) => {
                if (!option) {
                  resetManagerForm();
                  return;
                }
                setManagerItem(option);
                itemForm.reset({
                  type_materiel: option.type_materiel,
                  name: option.name,
                  reference: option.reference,
                  unit_price_eur: Number(option.unit_price_eur || 0),
                });
              }}
              renderInput={(params) => <TextField {...params} label="Article à modifier / supprimer" />}
            />
            <Button
              variant="text"
              size="small"
              startIcon={<AddIcon />}
              onClick={resetManagerForm}
              sx={{ alignSelf: "flex-start" }}
            >
              Nouvel article
            </Button>
            <Controller
              control={itemForm.control}
              name="type_materiel"
              render={({ field }) => (
                <Autocomplete
                  freeSolo
                  options={typeOptions}
                  value={field.value ?? ""}
                  onChange={(_, value) => field.onChange(typeof value === "string" ? value : (value ?? ""))}
                  onInputChange={(_, value, reason) => {
                    if (reason !== "reset") field.onChange(value);
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Type de matériel"
                      error={!!itemForm.formState.errors.type_materiel}
                      helperText={
                        itemForm.formState.errors.type_materiel?.message ??
                        (managerItem ? "Modifie le type de cet article" : "Vous pouvez saisir un nouveau type")
                      }
                    />
                  )}
                />
              )}
            />
            <TextField
              label="Désignation (nom)"
              {...itemForm.register("name")}
              error={!!itemForm.formState.errors.name}
              helperText={itemForm.formState.errors.name?.message}
            />
            <TextField
              label="Référence"
              {...itemForm.register("reference")}
              error={!!itemForm.formState.errors.reference}
              helperText={itemForm.formState.errors.reference?.message}
            />
            <TextField
              label="Prix unitaire (€)"
              type="number"
              inputProps={{ min: 0, step: "0.01" }}
              {...itemForm.register("unit_price_eur", { valueAsNumber: true })}
              error={!!itemForm.formState.errors.unit_price_eur}
              helperText={itemForm.formState.errors.unit_price_eur?.message}
            />
            <Button
              variant="contained"
              disabled={saveItemMutation.isPending}
              onClick={itemForm.handleSubmit((values) => saveItemMutation.mutate(values))}
            >
              {managerItem ? "Enregistrer les modifications" : "Ajouter l'article"}
            </Button>
            {managerItem && (
              <Button
                color="error"
                variant="outlined"
                startIcon={<DeleteOutlineIcon />}
                disabled={deleteItemMutation.isPending}
                onClick={() => {
                  if (
                    !window.confirm(
                      `Supprimer l'article « ${managerItem.name} » ? Il ne sera plus proposé pour de nouveaux achats.`
                    )
                  ) {
                    return;
                  }
                  deleteItemMutation.mutate(managerItem.id);
                }}
              >
                Supprimer l'article
              </Button>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setItemsManagerOpen(false);
              resetManagerForm();
            }}
          >
            Fermer
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={typeManagerOpen} onClose={() => setTypeManagerOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Gérer les types de matériel</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} mt={0.5}>
            <Autocomplete
              options={typeStats.map((t) => t.type_materiel)}
              value={selectedType || null}
              onChange={(_, value) => {
                const next = value ?? "";
                setSelectedType(next);
                setNewTypeName(next);
              }}
              renderInput={(params) => <TextField {...params} label="Type à modifier / supprimer" />}
            />
            <TextField
              label="Nouveau nom du type"
              value={newTypeName}
              onChange={(e) => setNewTypeName(e.target.value)}
              helperText="Renomme ce type pour tous les articles de cette UEP"
            />
            <Button
              variant="contained"
              disabled={!selectedType.trim() || !newTypeName.trim() || renameTypeMutation.isPending}
              onClick={() =>
                renameTypeMutation.mutate({
                  oldType: selectedType.trim(),
                  newType: newTypeName.trim(),
                })
              }
            >
              Renommer le type
            </Button>

            <Button
              color="error"
              variant="outlined"
              startIcon={<DeleteOutlineIcon />}
              disabled={!selectedType.trim() || deleteTypeMutation.isPending}
              onClick={() => {
                if (!window.confirm(`Supprimer le type "${selectedType}" ? (articles déplacés vers AUTRE)`)) return;
                deleteTypeMutation.mutate({
                  oldType: selectedType.trim(),
                  replacement: "AUTRE",
                });
              }}
            >
              Supprimer le type
            </Button>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTypeManagerOpen(false)}>Fermer</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={purchaseOpen} onClose={() => setPurchaseOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingPurchase ? "Modifier achat consommable" : "Ajouter achat consommable"}</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} mt={0.5}>
            <Controller
              control={purchaseForm.control}
              name="item"
              render={({ field }) => (
                <Autocomplete
                  options={items}
                  getOptionLabel={(o) => o.name}
                  value={items.find((i) => i.id === field.value?.id) ?? null}
                  onChange={(_, option) => {
                    field.onChange(
                      option
                        ? {
                            id: option.id,
                            type_materiel: option.type_materiel,
                            name: option.name,
                            reference: option.reference,
                            unit_price_eur: option.unit_price_eur,
                          }
                        : { id: 0, type_materiel: "", name: "", reference: "", unit_price_eur: "0.00" }
                    );
                  }}
                  renderInput={(params) => <TextField {...params} label="Article acheté" />}
                />
              )}
            />
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <TextField label="Type de matériel" value={watchedItem?.type_materiel ?? ""} InputProps={{ readOnly: true }} fullWidth />
              <TextField label="Référence" value={watchedItem?.reference ?? ""} InputProps={{ readOnly: true }} fullWidth />
              <TextField label="Prix / pièce (€)" value={toEuro(unitPrice)} InputProps={{ readOnly: true }} fullWidth />
            </Stack>
            <Controller
              control={purchaseForm.control}
              name="shift"
              render={({ field }) => (
                <TextField
                  select
                  label="Shift de l'achat"
                  value={field.value ?? ""}
                  onChange={field.onChange}
                  error={!!purchaseForm.formState.errors.shift}
                  helperText={purchaseForm.formState.errors.shift?.message ?? "Pour quel shift est cet achat ?"}
                  fullWidth
                >
                  {SHIFT_OPTIONS.map((s) => (
                    <MenuItem key={s} value={s}>
                      Shift {s}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <TextField
                label="Quantité"
                type="number"
                inputProps={{ min: 1, step: "1" }}
                {...purchaseForm.register("quantity", { valueAsNumber: true })}
                error={!!purchaseForm.formState.errors.quantity}
                helperText={purchaseForm.formState.errors.quantity?.message}
                fullWidth
              />
              <TextField label="Total (€)" value={toEuro(total)} InputProps={{ readOnly: true }} fullWidth />
            </Stack>
            <TextField
              label="Date achat"
              type="date"
              InputLabelProps={{ shrink: true }}
              {...purchaseForm.register("purchase_date")}
              error={!!purchaseForm.formState.errors.purchase_date}
              helperText={purchaseForm.formState.errors.purchase_date?.message}
            />
            <TextField label="Note (optionnel)" multiline minRows={2} {...purchaseForm.register("note")} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPurchaseOpen(false)}>Annuler</Button>
          <Button
            variant="contained"
            onClick={purchaseForm.handleSubmit((values) => savePurchaseMutation.mutate(values))}
            disabled={savePurchaseMutation.isPending || !watchedItem?.id}
          >
            Enregistrer
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}

