import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import {
  Alert,
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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useLockedShift, useMe } from "../../auth/AuthContext";
import { GiDatePickerRhf } from "../../components/GiDatePicker";
import { api, formatApiError } from "../../api/client";
import type { Paginated, ProductionCCBRow } from "../../api/types";
import { CCB_OBJECTIF_TOTAL_SHIFT, CCB_OBJECTIFS_HORAIRES } from "./ccbProductionConstants";

type HourIndex = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
const HOURS: HourIndex[] = [1, 2, 3, 4, 5, 6, 7, 8];

type ShiftCode = "A" | "B" | "N";

type CcbProductionFormValues = {
  date: string;
  shift: ShiftCode;
  objectif: number;
  retouche: number;
} & {
  [H in HourIndex as `production_h${H}`]: number;
} & {
  [H in HourIndex as `rebut_h${H}`]: number;
};

function ccbHourDefaults(): Pick<
  CcbProductionFormValues,
  | "production_h1"
  | "production_h2"
  | "production_h3"
  | "production_h4"
  | "production_h5"
  | "production_h6"
  | "production_h7"
  | "production_h8"
  | "rebut_h1"
  | "rebut_h2"
  | "rebut_h3"
  | "rebut_h4"
  | "rebut_h5"
  | "rebut_h6"
  | "rebut_h7"
  | "rebut_h8"
> {
  const o: Record<string, number> = {};
  for (const h of HOURS) {
    o[`production_h${h}`] = 0;
    o[`rebut_h${h}`] = 0;
  }
  return o as Pick<
    CcbProductionFormValues,
    | "production_h1"
    | "production_h2"
    | "production_h3"
    | "production_h4"
    | "production_h5"
    | "production_h6"
    | "production_h7"
    | "production_h8"
    | "rebut_h1"
    | "rebut_h2"
    | "rebut_h3"
    | "rebut_h4"
    | "rebut_h5"
    | "rebut_h6"
    | "rebut_h7"
    | "rebut_h8"
  >;
}

function ccbFormDefaults(shift: ShiftCode): CcbProductionFormValues {
  return {
    date: new Date().toISOString().slice(0, 10),
    shift,
    objectif: CCB_OBJECTIF_TOTAL_SHIFT,
    retouche: 0,
    ...ccbHourDefaults(),
  };
}

function rowToFormValues(row: ProductionCCBRow): CcbProductionFormValues {
  const shift = row.shift === "A" || row.shift === "B" || row.shift === "N" ? row.shift : "A";
  return {
    date: row.date.slice(0, 10),
    shift,
    objectif: CCB_OBJECTIF_TOTAL_SHIFT,
    retouche: row.retouche ?? 0,
    ...Object.fromEntries(
      HOURS.flatMap((h) => [
        [`production_h${h}`, row[`production_h${h}` as keyof ProductionCCBRow] as number],
        [`rebut_h${h}`, row[`rebut_h${h}` as keyof ProductionCCBRow] as number],
      ])
    ),
  } as CcbProductionFormValues;
}

export default function CcbProductionPage() {
  const qc = useQueryClient();
  const me = useMe();
  const lockedShift = useLockedShift();
  const canDelete = me?.permissions?.delete === true;
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(15);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ProductionCCBRow | null>(null);
  const [detailRow, setDetailRow] = useState<ProductionCCBRow | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [shiftFilter, setShiftFilter] = useState("");

  useEffect(() => {
    if (lockedShift) setShiftFilter(lockedShift);
  }, [lockedShift]);

  const effectiveShiftParam = lockedShift ?? shiftFilter;

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["prod-ccb", page, rowsPerPage, effectiveShiftParam],
    queryFn: async () => {
      const { data: res } = await api.get<Paginated<ProductionCCBRow>>("/api/ccb/production/", {
        params: {
          page: page + 1,
          per_page: rowsPerPage,
          sort: "-date",
          ...(effectiveShiftParam ? { shift: effectiveShiftParam } : {}),
        },
      });
      return res;
    },
  });

  const form = useForm<CcbProductionFormValues>({ defaultValues: ccbFormDefaults("A") });

  const saveMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      if (editing) {
        await api.patch(`/api/ccb/production/${editing.id}/`, payload);
      } else {
        await api.post("/api/ccb/production/", payload);
      }
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["prod-ccb"] });
      setOpen(false);
      setEditing(null);
      form.reset(ccbFormDefaults((lockedShift === "A" || lockedShift === "B" || lockedShift === "N" ? lockedShift : "A")));
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/api/ccb/production/${id}/`),
    onSuccess: async () => qc.invalidateQueries({ queryKey: ["prod-ccb"] }),
  });

  const openEdit = (row: ProductionCCBRow) => {
    setEditing(row);
    form.reset(rowToFormValues(row));
    setOpen(true);
  };

  const watchedHours = HOURS.map((h) => ({
    h,
    prod: Number(form.watch(`production_h${h}` as const)) || 0,
    reb: Number(form.watch(`rebut_h${h}` as const)) || 0,
  }));

  const totalsLive = {
    vol: watchedHours.reduce((s, x) => s + x.prod, 0),
    reb: watchedHours.reduce((s, x) => s + x.reb, 0),
    ro: CCB_OBJECTIF_TOTAL_SHIFT > 0 ? (watchedHours.reduce((s, x) => s + x.prod, 0) / CCB_OBJECTIF_TOTAL_SHIFT) * 100 : 0,
  };

  const onSubmit = form.handleSubmit((values) =>
    saveMutation.mutate({
      ...(values as Record<string, unknown>),
      objectif: CCB_OBJECTIF_TOTAL_SHIFT,
      retouche: 0,
      ...(lockedShift ? { shift: lockedShift } : {}),
    })
  );

  const tableColSpan = 32;

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" alignItems={{ md: "center" }} spacing={2}>
        <Typography variant="h5" fontWeight={800}>
          Production · UEP CCB
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <TextField
            select
            size="small"
            label="Shift"
            id="prod-ccb-filter-shift"
            name="prod-ccb-filter-shift"
            value={lockedShift ?? shiftFilter}
            disabled={!!lockedShift}
            onChange={(e) => {
              setShiftFilter(e.target.value);
              setPage(0);
            }}
            sx={{ minWidth: 120 }}
          >
            <MenuItem value="">Tous</MenuItem>
            <MenuItem value="A">A</MenuItem>
            <MenuItem value="B">B</MenuItem>
            <MenuItem value="N">N</MenuItem>
          </TextField>
          <Button component="a" href="/ccb/production/export/?format=excel" variant="outlined" size="small">
            Export Excel
          </Button>
          <Button component="a" href="/ccb/production/export/?format=pdf" variant="outlined" size="small">
            Export PDF
          </Button>
          <Button
            startIcon={<AddIcon />}
            variant="contained"
            onClick={() => {
              setEditing(null);
              form.reset(ccbFormDefaults((lockedShift === "A" || lockedShift === "B" || lockedShift === "N" ? lockedShift : "A")));
              setErrorMsg(null);
              setOpen(true);
            }}
          >
            Ajouter
          </Button>
        </Stack>
      </Stack>

      {errorMsg && (
        <Paper sx={{ p: 2, borderRadius: 2, bgcolor: "error.light", color: "error.contrastText" }}>
          {errorMsg}
        </Paper>
      )}

      {isError && (
        <Alert severity="error">{formatApiError(error)}</Alert>
      )}

      <TableContainer
        component={Paper}
        elevation={0}
        sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3, overflowX: "auto" }}
      >
        <Table size="small" sx={{ minWidth: 720 }}>
          <TableHead>
            <TableRow sx={{ bgcolor: "action.hover" }}>
              <TableCell rowSpan={2}>Date</TableCell>
              <TableCell rowSpan={2}>Shift</TableCell>
              {HOURS.map((h) => (
                <TableCell key={h} align="center" colSpan={3} sx={{ borderLeft: "1px solid", borderColor: "divider" }}>
                  H{h}
                </TableCell>
              ))}
              <TableCell rowSpan={2} align="right">
                Vol. Σ
              </TableCell>
              <TableCell rowSpan={2} align="right">
                Obj. Σ
              </TableCell>
              <TableCell rowSpan={2} align="right">
                RO %
              </TableCell>
              <TableCell rowSpan={2} align="right">
                Rebut Σ
              </TableCell>
              <TableCell rowSpan={2} align="right">
                Arrêts
              </TableCell>
              <TableCell rowSpan={2} align="right">
                Actions
              </TableCell>
            </TableRow>
            <TableRow sx={{ bgcolor: "action.hover" }}>
              {HOURS.flatMap((h) => [
                <TableCell key={`${h}-o`} align="right" sx={{ borderLeft: "1px solid", borderColor: "divider", fontSize: 11, py: 0.5 }}>
                  Obj.
                </TableCell>,
                <TableCell key={`${h}-v`} align="right" sx={{ fontSize: 11, py: 0.5 }}>
                  Vol.
                </TableCell>,
                <TableCell key={`${h}-r`} align="right" sx={{ fontSize: 11, py: 0.5 }}>
                  Reb.
                </TableCell>,
              ])}
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={tableColSpan}>
                  <Typography color="text.secondary">Chargement...</Typography>
                </TableCell>
              </TableRow>
            )}
            {!isLoading &&
              data?.results.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell>{row.date.slice(0, 10)}</TableCell>
                  <TableCell>{row.shift}</TableCell>
                  {HOURS.map((h) => {
                    const obj = row[`objectif_h${h}` as keyof ProductionCCBRow];
                    const o = typeof obj === "number" ? obj : CCB_OBJECTIFS_HORAIRES[h - 1];
                    const p = row[`production_h${h}` as keyof ProductionCCBRow] as number;
                    const r = row[`rebut_h${h}` as keyof ProductionCCBRow] as number;
                    return (
                      <Fragment key={`${row.id}-h${h}`}>
                        <TableCell align="right" sx={{ borderLeft: "1px solid", borderColor: "divider" }}>
                          {o}
                        </TableCell>
                        <TableCell align="right">{p}</TableCell>
                        <TableCell align="right">{r}</TableCell>
                      </Fragment>
                    );
                  })}
                  <TableCell align="right">{row.volume}</TableCell>
                  <TableCell align="right">{row.objectif}</TableCell>
                  <TableCell align="right">{row.ro_percent}</TableCell>
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
                          if (window.confirm("Supprimer ?")) deleteMutation.mutate(row.id);
                        }}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
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

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{editing ? "Modifier production CCB" : "Nouvelle production CCB"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 0.5 }}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <GiDatePickerRhf control={form.control} name="date" label="Date" fullWidth />
              <TextField
                select
                label="Shift"
                id="prod-ccb-dialog-shift"
                fullWidth
                disabled={!!lockedShift}
                helperText={lockedShift ? "Shift impose (profil PSP)" : undefined}
                {...form.register("shift")}
              >
                {(lockedShift ? ([lockedShift] as const) : (["A", "B", "N"] as const)).map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2 }}>
              <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                Totaux (calculés)
              </Typography>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                <TextField size="small" label="Volume total" value={totalsLive.vol} InputProps={{ readOnly: true }} fullWidth />
                <TextField size="small" label="Rebut total" value={totalsLive.reb} InputProps={{ readOnly: true }} fullWidth />
                <TextField
                  size="small"
                  label="Objectif shift (fixe)"
                  value={CCB_OBJECTIF_TOTAL_SHIFT}
                  InputProps={{ readOnly: true }}
                  fullWidth
                />
                <TextField size="small" label="RO %" value={totalsLive.ro.toFixed(1)} InputProps={{ readOnly: true }} fullWidth />
              </Stack>
            </Paper>
            <Typography variant="subtitle2" fontWeight={700}>
              Saisie par heure (objectif fixe · volume · rebut)
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
                  <Stack spacing={1}>
                    <Typography variant="caption" color="text.secondary">
                      H{h} — objectif {CCB_OBJECTIFS_HORAIRES[h - 1]}
                    </Typography>
                    <TextField
                      size="small"
                      type="number"
                      label="Volume"
                      fullWidth
                      {...form.register(`production_h${h}` as const, { valueAsNumber: true })}
                    />
                    <TextField
                      size="small"
                      type="number"
                      label="Rebut"
                      fullWidth
                      {...form.register(`rebut_h${h}` as const, { valueAsNumber: true })}
                    />
                  </Stack>
                </Paper>
              ))}
            </Box>
            <input type="hidden" {...form.register("objectif", { valueAsNumber: true })} />
            <input type="hidden" {...form.register("retouche", { valueAsNumber: true })} />
            <Typography variant="caption" color="text.secondary">
              Les temps d&apos;arrêt sont calculés automatiquement à partir des alertes panne CCB (date et shift).
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setOpen(false)}>Annuler</Button>
          <Button variant="contained" onClick={onSubmit} disabled={saveMutation.isPending}>
            Enregistrer
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!detailRow} onClose={() => setDetailRow(null)} fullWidth maxWidth="sm">
        <DialogTitle>Detail production CCB</DialogTitle>
        <DialogContent>
          {detailRow && (
            <Stack spacing={1.2} sx={{ mt: 1 }}>
              <Typography>
                <strong>Date:</strong> {detailRow.date.slice(0, 10)}
              </Typography>
              <Typography>
                <strong>Shift:</strong> {detailRow.shift}
              </Typography>
              <Typography>
                <strong>Objectif total (shift):</strong> {detailRow.objectif}
              </Typography>
              <Typography>
                <strong>Volume total:</strong> {detailRow.volume}
              </Typography>
              <Typography>
                <strong>Rebut total:</strong> {detailRow.rebut}
              </Typography>
              <Typography variant="subtitle2" sx={{ mt: 1 }}>
                Détail par heure
              </Typography>
              {HOURS.map((h) => {
                const keyO = `objectif_h${h}` as keyof ProductionCCBRow;
                const vO = detailRow[keyO];
                const o = typeof vO === "number" ? vO : CCB_OBJECTIFS_HORAIRES[h - 1];
                const p = detailRow[`production_h${h}` as keyof ProductionCCBRow] as number;
                const r = detailRow[`rebut_h${h}` as keyof ProductionCCBRow] as number;
                const ta = detailRow[`temps_arrets_h${h}` as keyof ProductionCCBRow] ?? 0;
                return (
                  <Typography key={h} variant="body2">
                    H{h}: objectif {o} · volume {p} · rebut {r} · arrêt {String(ta)} min
                  </Typography>
                );
              })}
              <Typography>
                <strong>RO %:</strong> {detailRow.ro_percent}
              </Typography>
              <Typography>
                <strong>Temps arrêts (total min):</strong> {detailRow.temps_arrets}
              </Typography>
            </Stack>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDetailRow(null)}>Fermer</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
