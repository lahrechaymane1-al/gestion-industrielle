import { zodResolver } from "@hookform/resolvers/zod";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import {
  Alert,
  Autocomplete,
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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { useLockedShift, useMe } from "../../auth/AuthContext";
import { GiDatePicker, GiDatePickerRhf } from "../../components/GiDatePicker";
import { api, formatApiError } from "../../api/client";
import type { AbsenceRow, EffectifOption, EquipeScope, Paginated } from "../../api/types";
import { isoCalendarToday } from "../production/productionMetrics";

const absenceSchema = z
  .object({
    nom_complet: z.string().min(1, "Le nom complet est obligatoire"),
    effectif: z.object({ id: z.number(), nom_complet: z.string() }),
    shift: z.enum(["A", "B", "N"]),
    motif: z.string().min(1, "Motif obligatoire"),
    date_absence: z
      .string()
      .min(1, "Date obligatoire")
      .refine((v) => !Number.isNaN(new Date(v).getTime()), "Date d'absence invalide"),
    remplacant_effectif: z
      .object({ id: z.number(), nom_complet: z.string() })
      .nullable()
      .optional(),
    remplacant: z.string().optional(),
    commentaire: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.remplacant_effectif && data.remplacant?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Choisir un remplacant effectif OU un remplacant externe.",
        path: ["remplacant"],
      });
    }
    if (data.remplacant_effectif && data.remplacant_effectif.id === data.effectif.id) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Le remplacant doit etre different de l'absent.",
        path: ["remplacant_effectif"],
      });
    }
    if (!data.remplacant_effectif && !data.remplacant?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Le remplacant est obligatoire.",
        path: ["remplacant"],
      });
    }
  });

type AbsenceFormValues = z.infer<typeof absenceSchema>;

export default function AbsenceListPage({ equipe }: { equipe: EquipeScope }) {
  const qc = useQueryClient();
  const me = useMe();
  const lockedShift = useLockedShift();
  const canDelete = me?.permissions?.delete === true;
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(15);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<AbsenceRow | null>(null);
  const [detailRow, setDetailRow] = useState<AbsenceRow | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [dateFilter, setDateFilter] = useState("");
  const [shiftFilter, setShiftFilter] = useState("");
  const [nameFilter, setNameFilter] = useState("");
  const [matriculeFilter, setMatriculeFilter] = useState("");
  const effectiveShift = lockedShift ?? shiftFilter;

  useEffect(() => {
    if (lockedShift) setShiftFilter(lockedShift);
  }, [lockedShift]);

  const { data, isLoading } = useQuery({
    queryKey: [
      "absences",
      equipe,
      page,
      rowsPerPage,
      dateFilter,
      effectiveShift,
      nameFilter,
      matriculeFilter,
      lockedShift,
    ],
    queryFn: async () => {
      const { data: res } = await api.get<Paginated<AbsenceRow>>("/api/absences/", {
        params: {
          equipe,
          ...(effectiveShift ? { shift: effectiveShift } : {}),
          page: page + 1,
          per_page: rowsPerPage,
          sort: "-date_absence",
          ...(dateFilter ? { date_absence: dateFilter } : {}),
          ...(nameFilter ? { nom: nameFilter } : {}),
          ...(matriculeFilter ? { matricule: matriculeFilter } : {}),
        },
      });
      return res;
    },
  });

  const { data: optionsData } = useQuery({
    queryKey: ["effectif-options", equipe],
    queryFn: async () => {
      const { data: res } = await api.get<{ results: EffectifOption[] }>("/api/effectifs/options/", {
        params: { equipe },
      });
      return res.results;
    },
  });

  const options = useMemo(() => optionsData ?? [], [optionsData]);

  /** Ordre shift A/B/N, puis PSP, puis nom (aligne sur l'API effectif-options). */
  const optionsSorted = useMemo(() => {
    const copy = [...options];
    copy.sort((a, b) => {
      const byShift = a.shift.localeCompare(b.shift);
      if (byShift !== 0) return byShift;
      const ap = a.fonction === "PSP" ? 0 : 1;
      const bp = b.fonction === "PSP" ? 0 : 1;
      if (ap !== bp) return ap - bp;
      return a.nom_complet.localeCompare(b.nom_complet, "fr", { sensitivity: "base" });
    });
    return copy;
  }, [options]);

  const absenceTableChunks = useMemo(() => {
    const rows = data?.results ? [...data.results] : [];
    if (!rows.length) return [];
    if (lockedShift) {
      return rows.map((row) => ({ kind: "row" as const, row }));
    }
    rows.sort((a, b) => {
      const byShift = a.shift.localeCompare(b.shift);
      if (byShift !== 0) return byShift;
      return a.nom_absent.localeCompare(b.nom_absent, "fr", { sensitivity: "base" });
    });
    const out: Array<{ kind: "header"; shift: string } | { kind: "row"; row: AbsenceRow }> = [];
    let prev = "";
    for (const row of rows) {
      if (row.shift !== prev) {
        prev = row.shift;
        out.push({ kind: "header", shift: row.shift });
      }
      out.push({ kind: "row", row });
    }
    return out;
  }, [data?.results, lockedShift]);

  const defaultValues = useMemo(
    (): AbsenceFormValues => ({
      nom_complet: optionsSorted[0]?.nom_complet ?? "",
      effectif: optionsSorted[0]
        ? { id: optionsSorted[0].id, nom_complet: optionsSorted[0].nom_complet }
        : { id: 0, nom_complet: "" },
      shift: ((lockedShift ?? "A") as "A" | "B" | "N"),
      motif: "",
      date_absence: isoCalendarToday(),
      remplacant_effectif: null,
      remplacant: "",
      commentaire: "",
    }),
    [optionsSorted, lockedShift]
  );

  const form = useForm<AbsenceFormValues>({
    resolver: zodResolver(absenceSchema),
    defaultValues,
  });

  const watchedEffectifId = form.watch("effectif")?.id;
  const selectedEffectif = useMemo(
    () => optionsSorted.find((o) => o.id === watchedEffectifId) ?? null,
    [optionsSorted, watchedEffectifId]
  );

  // RU/ADMIN: shift comes from selected effectif and is not editable here.
  // PSP: shift is imposed via lockedShift (and hidden in UI below).
  useEffect(() => {
    if (lockedShift) {
      form.setValue("shift", lockedShift as "A" | "B" | "N", { shouldValidate: true });
      return;
    }
    if (selectedEffectif?.shift) {
      form.setValue("shift", selectedEffectif.shift as "A" | "B" | "N", { shouldValidate: true });
    }
  }, [form, lockedShift, selectedEffectif?.shift]);

  const saveMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      if (editing) {
        await api.patch(`/api/absences/${editing.id}/`, payload);
      } else {
        await api.post("/api/absences/", payload);
      }
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["absences", equipe] });
      setOpen(false);
      setEditing(null);
      form.reset(defaultValues);
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/api/absences/${id}/`),
    onSuccess: async () => qc.invalidateQueries({ queryKey: ["absences", equipe] }),
  });

  const openCreate = () => {
    setEditing(null);
    form.reset(defaultValues);
    setErrorMsg(null);
    setOpen(true);
  };

  const openEdit = (row: AbsenceRow) => {
    setEditing(row);
    const eff = optionsSorted.find((o) => o.id === row.effectif);
    const rep = optionsSorted.find((o) => o.id === row.remplacant_effectif);
    form.reset({
      effectif: eff
        ? { id: eff.id, nom_complet: eff.nom_complet }
        : { id: row.effectif ?? 0, nom_complet: row.nom_absent },
      nom_complet: row.nom_complet || row.nom_absent,
      shift: row.shift as "A" | "B" | "N",
      motif: row.motif,
      date_absence: row.date_absence.slice(0, 10),
      remplacant_effectif: rep ? { id: rep.id, nom_complet: rep.nom_complet } : null,
      remplacant: row.remplacant ?? "",
      commentaire: row.commentaire ?? "",
    });
    setErrorMsg(null);
    setOpen(true);
  };

  const onSubmit = form.handleSubmit((values) => {
    const payload: Record<string, unknown> = {
      equipe,
      effectif: values.effectif.id,
      nom_complet: values.nom_complet,
      shift: lockedShift ?? values.shift,
      motif: values.motif,
      date_absence: values.date_absence,
      remplacant_effectif: values.remplacant_effectif?.id ?? null,
      remplacant: values.remplacant?.trim() || "",
      commentaire: values.commentaire?.trim() || "",
    };
    saveMutation.mutate(payload);
  });

  const exportHref = `/api/absences/?equipe=${encodeURIComponent(equipe)}${
    effectiveShift ? `&shift=${encodeURIComponent(effectiveShift)}` : ""
  }${matriculeFilter ? `&matricule=${encodeURIComponent(matriculeFilter)}` : ""}${
    dateFilter ? `&date_absence=${encodeURIComponent(dateFilter)}` : ""
  }${nameFilter ? `&nom=${encodeURIComponent(nameFilter)}` : ""}&export=excel`;

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "center" }}>
        <Typography variant="h5" fontWeight={800}>
          Absences · UEP {equipe}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button component="a" href={exportHref} variant="outlined" size="small">
            Export Excel
          </Button>
          <Button startIcon={<AddIcon />} variant="contained" onClick={openCreate}>
            Ajouter
          </Button>
        </Stack>
      </Stack>
      <Stack direction={{ xs: "column", md: "row" }} spacing={1} flexWrap="wrap" useFlexGap>
        <GiDatePicker
          label="Filtrer par date"
          value={dateFilter}
          onChange={(v) => {
            setDateFilter(v);
            setPage(0);
          }}
          sx={{ minWidth: 180 }}
        />
        <TextField
          select
          size="small"
          label="Shift"
          id="absence-filter-shift"
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
        <TextField
          size="small"
          label="Filtrer par nom"
          value={nameFilter}
          onChange={(e) => {
            setNameFilter(e.target.value);
            setPage(0);
          }}
        />
        <TextField
          size="small"
          label="Filtrer par matricule"
          value={matriculeFilter}
          onChange={(e) => {
            setMatriculeFilter(e.target.value);
            setPage(0);
          }}
        />
      </Stack>

      {errorMsg && (
        <Alert severity="error" onClose={() => setErrorMsg(null)}>
          {errorMsg}
        </Alert>
      )}

      <TableContainer component={Paper} elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: "action.hover" }}>
              <TableCell>NOM_COMPLET</TableCell>
              <TableCell>Shift</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Motif</TableCell>
              <TableCell>Remplacant</TableCell>
              <TableCell>Statut</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={7}>
                  <Typography color="text.secondary">Chargement...</Typography>
                </TableCell>
              </TableRow>
            )}
            {!isLoading &&
              absenceTableChunks.map((chunk, idx) =>
                chunk.kind === "header" ? (
                  <TableRow key={`abs-shift-${chunk.shift}-${idx}`} sx={{ bgcolor: "action.selected" }}>
                    <TableCell colSpan={7} sx={{ py: 1.25, borderBottom: "none" }}>
                      <Typography variant="subtitle2" fontWeight={800} color="primary">
                        Shift {chunk.shift}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  <TableRow key={chunk.row.id} hover>
                    <TableCell sx={{ fontWeight: 600 }}>{chunk.row.nom_absent}</TableCell>
                    <TableCell>{chunk.row.shift}</TableCell>
                    <TableCell>{chunk.row.date_absence.slice(0, 10)}</TableCell>
                    <TableCell>{chunk.row.motif}</TableCell>
                    <TableCell>{chunk.row.nom_remplacant}</TableCell>
                    <TableCell>
                      {chunk.row.migration_status === "a_corriger" ? (
                        <Chip size="small" label="A corriger" color="warning" />
                      ) : (
                        <Chip size="small" label="OK" variant="outlined" />
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => setDetailRow(chunk.row)}
                        aria-label="detail"
                        title="Detail"
                      >
                        <VisibilityOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={() => openEdit(chunk.row)} aria-label="modifier">
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      {canDelete && (
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => {
                            if (window.confirm("Supprimer cette absence ?")) deleteMutation.mutate(chunk.row.id);
                          }}
                          aria-label="supprimer"
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                )
              )}
            {!isLoading && data?.results.length === 0 && (
              <TableRow>
                <TableCell colSpan={7}>
                  <Typography color="text.secondary">Aucune absence.</Typography>
                </TableCell>
              </TableRow>
            )}
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

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editing ? "Modifier absence" : "Nouvelle absence"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Controller
              name="effectif"
              control={form.control}
              render={({ field }) => (
                <Autocomplete
                  options={optionsSorted}
                  groupBy={(o) => `Shift ${o.shift}`}
                  getOptionLabel={(o) =>
                    `${o.nom_complet} (${o.fonction === "PSP" ? "PSP" : "Operateur"})`
                  }
                  value={optionsSorted.find((o) => o.id === field.value.id) ?? null}
                  onChange={(_, v) => {
                    const selected = v
                      ? { id: v.id, nom_complet: v.nom_complet }
                      : defaultValues.effectif;
                    field.onChange(selected);
                    form.setValue("nom_complet", selected.nom_complet, { shouldValidate: true });
                    if (!lockedShift) {
                      form.setValue("shift", (v?.shift ?? "A") as "A" | "B" | "N", { shouldValidate: true });
                    }
                  }}
                  renderInput={(params) => (
                    <TextField {...params} label="Personne absente" error={!!form.formState.errors.effectif} />
                  )}
                />
              )}
            />
            <TextField
              label="NOM_COMPLET"
              {...form.register("nom_complet")}
              fullWidth
              InputProps={{ readOnly: true }}
              error={!!form.formState.errors.nom_complet}
              helperText={form.formState.errors.nom_complet?.message}
            />
            {lockedShift ? null : (
              <TextField
                id="absence-shift-display"
                label="Shift"
                value={selectedEffectif?.shift ?? form.getValues("shift")}
                fullWidth
                disabled
                helperText="Shift lie a l'effectif selectionne (modifiable dans Effectif)."
              />
            )}
            <TextField label="Motif" {...form.register("motif")} fullWidth error={!!form.formState.errors.motif} />
            <GiDatePickerRhf control={form.control} name="date_absence" label="Date d'absence" fullWidth />
            <Controller
              name="remplacant_effectif"
              control={form.control}
              render={({ field }) => (
                <Autocomplete
                  options={optionsSorted}
                  groupBy={(o) => `Shift ${o.shift}`}
                  getOptionLabel={(o) =>
                    `${o.nom_complet} (${o.fonction === "PSP" ? "PSP" : "Operateur"})`
                  }
                  value={optionsSorted.find((o) => o.id === field.value?.id) ?? null}
                  onChange={(_, v) => field.onChange(v ? { id: v.id, nom_complet: v.nom_complet } : null)}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Remplacant (effectif)"
                      error={!!form.formState.errors.remplacant_effectif}
                    />
                  )}
                />
              )}
            />
            <TextField
              label="Remplacant externe"
              {...form.register("remplacant")}
              fullWidth
              error={!!form.formState.errors.remplacant}
              helperText={form.formState.errors.remplacant?.message ?? "Saisir un remplacant si non choisi dans l'effectif"}
            />
            <TextField label="Commentaire" {...form.register("commentaire")} fullWidth multiline minRows={2} />
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
        <DialogTitle>Detail absence</DialogTitle>
        <DialogContent>
          {detailRow && (
            <Stack spacing={1.2} sx={{ mt: 1 }}>
              <Typography><strong>NOM_COMPLET:</strong> {detailRow.nom_complet || detailRow.nom_absent}</Typography>
              <Typography><strong>Shift:</strong> {detailRow.shift}</Typography>
              <Typography><strong>Date:</strong> {detailRow.date_absence.slice(0, 10)}</Typography>
              <Typography><strong>Motif:</strong> {detailRow.motif}</Typography>
              <Typography><strong>Remplacant:</strong> {detailRow.nom_remplacant}</Typography>
              <Typography><strong>Commentaire:</strong> {detailRow.commentaire || "-"}</Typography>
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
