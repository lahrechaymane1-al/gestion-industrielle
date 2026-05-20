import { zodResolver } from "@hookform/resolvers/zod";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import {
  Alert,
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
import { alpha, type Theme } from "@mui/material/styles";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { useIsPSP, useLockedShift, useMe } from "../../auth/AuthContext";
import { GiDatePickerRhf } from "../../components/GiDatePicker";
import { api, formatApiError } from "../../api/client";
import type { EffectifOption, EffectifRow, EquipeScope, Paginated } from "../../api/types";

const effectifSchema = z.object({
  nom_complet: z.string().min(1),
  shift: z.enum(["A", "B", "N"]),
  cin: z.string().min(1),
  type_contrat: z.enum(["CDI", "CDD", "ANAPEC"]),
  date_naissance: z.string().min(1),
  sexe: z.enum(["Homme", "Femme"]),
  date_entree: z.string().min(1),
  identifiant: z.string().min(1),
  matricule: z.string().min(1, "Matricule requis"),
  num_tel: z
    .string()
    .trim()
    .refine((v) => v === "" || /^\+?[0-9]{8,15}$/.test(v), {
      message: "Telephone invalide",
    }),
  fonction: z.enum(["PSP", "OPERATEUR"]),
  psp_lead: z.string().optional(),
  ville_actuelle: z.string().min(1),
  niveau_etude: z.string().min(1),
  numero_casier: z.string().min(1),
  parada_transport: z.string().min(1),
  pointure_chaussure: z.coerce.number().int().min(1),
  specialite: z.string().min(1),
  taille_pantalon: z.string().min(1),
  taille_veste: z.string().min(1),
  ville_origine: z.string().min(1),
});

type EffectifForm = z.infer<typeof effectifSchema>;
type EffectifPayload = Omit<EffectifForm, "psp_lead"> & {
  psp_lead: number | null;
  equipe: EquipeScope;
};

/** Ordre d’affichage dans un shift : PSP puis opérateurs. */
function fonctionRank(fonction: string): number {
  if (fonction === "PSP") return 0;
  return 1;
}

type EffectifChunk = { kind: "shift_header"; shift: string } | { kind: "row"; row: EffectifRow };

export default function EffectifListPage({ equipe }: { equipe: EquipeScope }) {
  const qc = useQueryClient();
  const me = useMe();
  const isPsp = useIsPSP();
  const lockedShift = useLockedShift();
  const canDelete = me?.permissions?.delete === true;
  const [page, setPage] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [shiftFilter, setShiftFilter] = useState("");
  const effectiveShift = lockedShift ?? shiftFilter;
  /** Vue tous shifts : charger assez de lignes pour voir A + B sur une « page » API (sinon la pagination masque le shift B). */
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<EffectifRow | null>(null);
  const [detailRow, setDetailRow] = useState<EffectifRow | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: lockedShift
      ? ["effectifs", equipe, page, rowsPerPage, lockedShift, searchQuery]
      : ["effectifs", equipe, "all-shifts", rowsPerPage, effectiveShift, searchQuery],
    queryFn: async () => {
      const multiShift = !lockedShift;
      const { data: res } = await api.get<Paginated<EffectifRow>>("/api/effectifs/", {
        params: {
          equipe,
          ...(effectiveShift ? { shift: effectiveShift } : {}),
          ...(searchQuery.trim() ? { q: searchQuery.trim() } : {}),
          page: multiShift ? 1 : page + 1,
          per_page: multiShift ? Math.min(500, Math.max(rowsPerPage, 100)) : rowsPerPage,
          sort: lockedShift ? "nom_complet" : "shift_sections",
        },
      });
      return res;
    },
  });

  /** Par shift : une ligne « Shift X » puis toutes les lignes (PSP, opérateurs), tri ordre métier. */
  const effectifTableChunks = useMemo((): EffectifChunk[] => {
    const rows = [...(data?.results ?? [])];
    if (!rows.length) return [];

    rows.sort((a, b) => {
      const byShift = a.shift.localeCompare(b.shift);
      if (byShift !== 0) return byShift;
      const byFn = fonctionRank(a.fonction) - fonctionRank(b.fonction);
      if (byFn !== 0) return byFn;
      return a.nom_complet.localeCompare(b.nom_complet, "fr", { sensitivity: "base" });
    });

    const out: EffectifChunk[] = [];
    let i = 0;
    while (i < rows.length) {
      const shiftKey = rows[i].shift;
      const block: EffectifRow[] = [];
      while (i < rows.length && rows[i].shift === shiftKey) {
        block.push(rows[i]);
        i += 1;
      }
      if (!lockedShift) {
        out.push({ kind: "shift_header", shift: shiftKey });
      }
      for (const row of block) {
        out.push({ kind: "row", row });
      }
    }
    return out;
  }, [data?.results, lockedShift]);

  const form = useForm<EffectifForm>({
    resolver: zodResolver(effectifSchema),
    defaultValues: {
      nom_complet: "",
      shift: (lockedShift ?? "A") as "A" | "B" | "N",
      cin: "",
      type_contrat: "CDI",
      date_naissance: "1990-01-01",
      sexe: "Homme",
      date_entree: "2010-01-01",
      identifiant: "",
      num_tel: "+212600000000",
      fonction: "OPERATEUR",
      psp_lead: isPsp && me?.effectif_id ? String(me.effectif_id) : "",
      ville_actuelle: "",
      niveau_etude: "Bac",
      numero_casier: "",
      parada_transport: "",
      pointure_chaussure: 42,
      specialite: "",
      taille_pantalon: "M",
      taille_veste: "M",
      ville_origine: "",
    },
  });

  useEffect(() => {
    if (editing) {
      const rawShift = String(editing.shift ?? "").trim();
      const shiftNorm = (["A", "B", "N"] as const).includes(rawShift as "A" | "B" | "N")
        ? (rawShift as "A" | "B" | "N")
        : "A";
      const rawFn = String(editing.fonction ?? "").trim();
      const fonctionNorm = (rawFn === "RU" ? "OPERATEUR" : rawFn) as "PSP" | "OPERATEUR";
      const contrat = String(editing.type_contrat ?? "").trim();
      const typeContratNorm = (["CDI", "CDD", "ANAPEC"] as const).includes(contrat as "CDI" | "CDD" | "ANAPEC")
        ? (contrat as "CDI" | "CDD" | "ANAPEC")
        : "CDI";
      const sx = String(editing.sexe ?? "").trim();
      const sexeNorm = sx === "Femme" ? "Femme" : "Homme";

      form.reset({
        nom_complet: editing.nom_complet,
        shift: (lockedShift ?? shiftNorm) as "A" | "B" | "N",
        cin: editing.cin,
        type_contrat: typeContratNorm,
        date_naissance: String(editing.date_naissance ?? "").slice(0, 10),
        sexe: sexeNorm,
        date_entree: String(editing.date_entree ?? "").slice(0, 10),
        identifiant: editing.identifiant,
        matricule: editing.matricule ?? "",
        num_tel:
          editing.num_tel != null && String(editing.num_tel).trim() !== ""
            ? String(editing.num_tel)
            : "",
        fonction: fonctionNorm === "PSP" ? "PSP" : "OPERATEUR",
        psp_lead: editing.psp_lead ? String(editing.psp_lead) : "",
        ville_actuelle: editing.ville_actuelle,
        niveau_etude: editing.niveau_etude,
        numero_casier: editing.numero_casier,
        parada_transport: editing.parada_transport,
        pointure_chaussure: editing.pointure_chaussure,
        specialite: editing.specialite,
        taille_pantalon: editing.taille_pantalon,
        taille_veste: editing.taille_veste,
        ville_origine: editing.ville_origine,
      });
    } else {
      form.reset({
        nom_complet: "",
        shift: (lockedShift ?? "A") as "A" | "B" | "N",
        cin: "",
        type_contrat: "CDI",
        date_naissance: "1990-01-01",
        sexe: "Homme",
        date_entree: "2010-01-01",
        identifiant: "",
        matricule: "",
        num_tel: "+212600000000",
        fonction: "OPERATEUR",
        psp_lead: isPsp && me?.effectif_id ? String(me.effectif_id) : "",
        ville_actuelle: "",
        niveau_etude: "Bac",
        numero_casier: "",
        parada_transport: "",
        pointure_chaussure: 42,
        specialite: "",
        taille_pantalon: "M",
        taille_veste: "M",
        ville_origine: "",
      });
    }
  }, [editing, form, lockedShift, isPsp, me?.effectif_id]);

  const pspLeadValue = form.watch("psp_lead");

  const saveMutation = useMutation({
    mutationFn: async (payload: EffectifPayload) => {
      if (editing) {
        await api.put(`/api/effectifs/${editing.id}/`, payload);
      } else {
        await api.post("/api/effectifs/", payload);
      }
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["effectifs"] });
      await qc.invalidateQueries({ queryKey: ["effectif-options"] });
      await qc.invalidateQueries({ queryKey: ["effectif-options-psp"] });
      await qc.invalidateQueries({ queryKey: ["absences"] });
      setOpen(false);
      setEditing(null);
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/api/effectifs/${id}/`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["effectifs"] });
      await qc.invalidateQueries({ queryKey: ["effectif-options"] });
      await qc.invalidateQueries({ queryKey: ["effectif-options-psp"] });
      await qc.invalidateQueries({ queryKey: ["absences"] });
    },
  });

  const exportHref = `/api/effectifs/?equipe=${encodeURIComponent(equipe)}&export=excel${
    effectiveShift ? `&shift=${encodeURIComponent(effectiveShift)}` : ""
  }${searchQuery.trim() ? `&q=${encodeURIComponent(searchQuery.trim())}` : ""}`;
  const { data: pspOptionsData } = useQuery({
    queryKey: ["effectif-options-psp", equipe],
    queryFn: async () =>
      (
        await api.get<{ results: EffectifOption[] }>("/api/effectifs/options/", {
          params: { equipe, fonction: "PSP" },
        })
      ).data.results,
  });
  const pspOptions = pspOptionsData ?? [];

  const onSubmit = form.handleSubmit((values) => {
    const pspLeadId = isPsp && me?.effectif_id ? me.effectif_id : values.psp_lead ? Number(values.psp_lead) : null;
    const payload: EffectifPayload = {
      ...values,
      equipe,
      shift: (lockedShift ?? values.shift) as "A" | "B" | "N",
      fonction: isPsp && (!editing || editing.id !== me?.effectif_id) ? "OPERATEUR" : values.fonction,
      psp_lead: pspLeadId,
    };
    saveMutation.mutate(payload);
  });

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "center" }}>
        <Typography variant="h5" fontWeight={800}>
          Effectif · UEP {equipe}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button component="a" href={exportHref} variant="outlined" size="small">
            Export Excel
          </Button>
          <Button
            startIcon={<AddIcon />}
            variant="contained"
            onClick={() => {
              setEditing(null);
              setErrorMsg(null);
              setOpen(true);
            }}
          >
            Ajouter
          </Button>
        </Stack>
      </Stack>
      {errorMsg && (
        <Alert severity="error" onClose={() => setErrorMsg(null)}>
          {errorMsg}
        </Alert>
      )}
      <Stack direction={{ xs: "column", md: "row" }} spacing={1} flexWrap="wrap" useFlexGap>
        <TextField
          size="small"
          label="Rechercher (nom, CIN, identifiant, matricule)"
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 260, flex: 1 }}
        />
        <TextField
          select
          size="small"
          label="Shift"
          id="effectif-filter-shift"
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
      </Stack>
      <TableContainer component={Paper} elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: "action.hover" }}>
              <TableCell>Nom</TableCell>
              <TableCell>CIN</TableCell>
              <TableCell>Identifiant</TableCell>
              <TableCell>Matricule</TableCell>
              <TableCell>Contrat</TableCell>
              <TableCell>Shift</TableCell>
              <TableCell>Fonction</TableCell>
              <TableCell>Ville</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={9}>
                  <Typography color="text.secondary">Chargement...</Typography>
                </TableCell>
              </TableRow>
            )}
            {!isLoading &&
              effectifTableChunks.map((chunk, idx) => {
                if (chunk.kind === "shift_header") {
                  return (
                    <TableRow key={`shift-head-${chunk.shift}-${idx}`} sx={{ bgcolor: "action.selected" }}>
                      <TableCell colSpan={9} sx={{ py: 1.25, borderBottom: "none" }}>
                        <Typography variant="subtitle1" fontWeight={800} color="primary">
                          Shift {chunk.shift}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  );
                }
                const rawFn = String(chunk.row.fonction);
                const fn: "PSP" | "OPERATEUR" = rawFn === "RU" ? "OPERATEUR" : (chunk.row.fonction as "PSP" | "OPERATEUR");
                const rowSx = {
                  bgcolor: (t: Theme) =>
                    fn === "PSP"
                      ? alpha(t.palette.primary.main, 0.06)
                      : alpha(t.palette.text.primary, 0.02),
                  borderLeftWidth: 4,
                  borderLeftStyle: "solid" as const,
                  borderLeftColor: (t: Theme) =>
                    fn === "PSP" ? t.palette.primary.main : t.palette.divider,
                };
                const fonctionCellSx =
                  fn === "PSP"
                    ? {
                        fontWeight: 700,
                        color: "primary.main",
                        fontStyle: "italic",
                      }
                    : {};
                return (
                  <TableRow key={chunk.row.id} hover sx={rowSx}>
                    <TableCell sx={{ fontWeight: 600 }}>{chunk.row.nom_complet}</TableCell>
                    <TableCell>{chunk.row.cin}</TableCell>
                    <TableCell>{chunk.row.identifiant}</TableCell>
                    <TableCell>{chunk.row.matricule || "—"}</TableCell>
                    <TableCell>{chunk.row.type_contrat}</TableCell>
                    <TableCell>{chunk.row.shift}</TableCell>
                    <TableCell sx={fonctionCellSx}>{fn}</TableCell>
                    <TableCell>{chunk.row.ville_actuelle}</TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => setDetailRow(chunk.row)} aria-label="detail">
                        <VisibilityOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => {
                          setEditing(chunk.row);
                          setErrorMsg(null);
                          setOpen(true);
                        }}
                      >
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      {canDelete && (
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => {
                            if (window.confirm("Supprimer ce collaborateur ?")) deleteMutation.mutate(chunk.row.id);
                          }}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
          </TableBody>
        </Table>
        {lockedShift ? (
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
            rowsPerPageOptions={[10, 25, 50, 100]}
          />
        ) : (
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ sm: "center" }}
            spacing={0.5}
            sx={{ px: 2, py: 1.25 }}
          >
            <Typography variant="caption" color="text.secondary">
              {data?.total ?? 0} personne(s) · liste groupée par shift (chargement élargi pour afficher A, B, N sur la même vue)
            </Typography>
            {(data?.total ?? 0) > 500 && (
              <Typography variant="caption" color="warning.main" fontWeight={600}>
                Plus de 500 personnes : seules les 500 premières sont renvoyées par l’API.
              </Typography>
            )}
          </Stack>
        )}
      </TableContainer>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{editing ? "Modifier collaborateur" : "Nouveau collaborateur"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 0.5 }}>
            {[
              ["nom_complet", "Nom complet"],
              ["cin", "CIN"],
              ["identifiant", "Identifiant"],
              ["matricule", "Matricule"],
              ["num_tel", "Telephone"],
              ["ville_actuelle", "Ville actuelle"],
              ["ville_origine", "Ville origine"],
              ["niveau_etude", "Niveau d'etude"],
              ["numero_casier", "Numero casier"],
              ["parada_transport", "Parada transport"],
              ["specialite", "Specialite"],
              ["taille_pantalon", "Taille pantalon"],
              ["taille_veste", "Taille veste"],
            ].map(([name, label]) => (
              <TextField key={name} label={label} fullWidth {...form.register(name as keyof EffectifForm)} />
            ))}
            {!isPsp || (editing && editing.id === me?.effectif_id) ? (
              <Controller
                name="fonction"
                control={form.control}
                render={({ field }) => (
                  <TextField select label="Fonction" fullWidth {...field}>
                    <MenuItem value="OPERATEUR">OPERATEUR</MenuItem>
                    <MenuItem value="PSP">PSP</MenuItem>
                  </TextField>
                )}
              />
            ) : (
              <TextField label="Fonction" fullWidth value="OPERATEUR" disabled helperText="Les PSP ne créent que des opérateurs de leur équipe." />
            )}
            {!isPsp && (
              <TextField
                select
                label="PSP lead"
                fullWidth
                helperText="Optionnel : PSP responsable pour les opérateurs de l’UEP."
                value={pspLeadValue ?? ""}
                onChange={(e) =>
                  form.setValue("psp_lead", e.target.value, { shouldDirty: true, shouldValidate: true })
                }
              >
                <MenuItem value="">Aucun</MenuItem>
                {[...pspOptions]
                  .sort((a, b) => {
                    const s = a.shift.localeCompare(b.shift);
                    if (s !== 0) return s;
                    return a.nom_complet.localeCompare(b.nom_complet, "fr", { sensitivity: "base" });
                  })
                  .map((opt) => (
                    <MenuItem key={opt.id} value={String(opt.id)} sx={{ pl: 2 }}>
                      <Typography component="span" variant="body2">
                        [{opt.shift}] {opt.nom_complet}
                      </Typography>
                    </MenuItem>
                  ))}
              </TextField>
            )}
            <Controller
              name="shift"
              control={form.control}
              render={({ field }) => (
                <TextField
                  select
                  label="Shift"
                  fullWidth
                  disabled={!!lockedShift}
                  helperText={lockedShift ? "Shift impose (profil PSP)" : undefined}
                  {...field}
                >
                  {(lockedShift ? ([lockedShift] as const) : (["A", "B", "N"] as const)).map((s) => (
                    <MenuItem key={s} value={s}>
                      {s}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
            <Controller
              name="type_contrat"
              control={form.control}
              render={({ field }) => (
                <TextField select label="Contrat" fullWidth {...field}>
                  {(["CDI", "CDD", "ANAPEC"] as const).map((s) => (
                    <MenuItem key={s} value={s}>
                      {s}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
            <Controller
              name="sexe"
              control={form.control}
              render={({ field }) => (
                <TextField select label="Sexe" fullWidth {...field}>
                  <MenuItem value="Homme">Homme</MenuItem>
                  <MenuItem value="Femme">Femme</MenuItem>
                </TextField>
              )}
            />
            <TextField type="number" label="Pointure" fullWidth {...form.register("pointure_chaussure", { valueAsNumber: true })} />
            <GiDatePickerRhf control={form.control} name="date_naissance" label="Naissance" fullWidth />
            <GiDatePickerRhf control={form.control} name="date_entree" label="Date entree" fullWidth />
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
        <DialogTitle>Detail collaborateur</DialogTitle>
        <DialogContent>
          {detailRow && (
            <Stack spacing={1.1} sx={{ mt: 1 }}>
              <Typography><strong>Nom:</strong> {detailRow.nom_complet}</Typography>
              <Typography><strong>Shift:</strong> {detailRow.shift}</Typography>
              <Typography><strong>CIN:</strong> {detailRow.cin}</Typography>
              <Typography><strong>Identifiant:</strong> {detailRow.identifiant}</Typography>
              <Typography><strong>Matricule:</strong> {detailRow.matricule || "—"}</Typography>
              <Typography><strong>Contrat:</strong> {detailRow.type_contrat}</Typography>
              <Typography><strong>Fonction:</strong> {detailRow.fonction}</Typography>
              <Typography><strong>PSP lead:</strong> {detailRow.psp_lead_nom || "-"}</Typography>
              <Typography><strong>Ville actuelle:</strong> {detailRow.ville_actuelle}</Typography>
              <Typography><strong>Date entree:</strong> {detailRow.date_entree.slice(0, 10)}</Typography>
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
