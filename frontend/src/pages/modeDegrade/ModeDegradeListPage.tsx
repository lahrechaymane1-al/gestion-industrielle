import { zodResolver } from "@hookform/resolvers/zod";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useLockedShift, useMe } from "../../auth/AuthContext";
import { GiDatePickerRhf } from "../../components/GiDatePicker";
import { api, formatApiError } from "../../api/client";
import type { EquipeScope, ModeDegradeRow, Paginated } from "../../api/types";
import { isoCalendarToday } from "../production/productionMetrics";

const mdSchema = z.object({
  shift: z.enum(["A", "B", "N"]),
  action: z.string().min(1),
  probleme: z.string().min(1),
  pilote: z.string().min(1),
  date: z.string().min(1),
  cause: z.string().min(1),
});

type MdForm = z.infer<typeof mdSchema>;

export default function ModeDegradeListPage({ equipe }: { equipe: EquipeScope }) {
  const qc = useQueryClient();
  const me = useMe();
  const lockedShift = useLockedShift();
  const canDelete = me?.permissions?.delete === true;
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(15);
  const [searchQuery, setSearchQuery] = useState("");
  const [shiftFilter, setShiftFilter] = useState("");
  const effectiveShift = lockedShift ?? shiftFilter;
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ModeDegradeRow | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["mode-degrade", equipe, page, rowsPerPage, effectiveShift, searchQuery, lockedShift],
    queryFn: async () => {
      const { data: res } = await api.get<Paginated<ModeDegradeRow>>("/api/mode-degrade/", {
        params: {
          equipe,
          ...(effectiveShift ? { shift: effectiveShift } : {}),
          ...(searchQuery.trim() ? { q: searchQuery.trim() } : {}),
          page: page + 1,
          per_page: rowsPerPage,
          sort: "-date",
        },
      });
      return res;
    },
  });

  const form = useForm<MdForm>({
    resolver: zodResolver(mdSchema),
    defaultValues: {
      shift: (lockedShift ?? "A") as "A" | "B" | "N",
      action: "",
      probleme: "",
      pilote: "",
      date: isoCalendarToday(),
      cause: "",
    },
  });

  useEffect(() => {
    if (editing) {
      form.reset({
        shift: (lockedShift ?? editing.shift) as "A" | "B" | "N",
        action: editing.action,
        probleme: editing.probleme,
        pilote: editing.pilote,
        date: editing.date.slice(0, 10),
        cause: editing.cause,
      });
    } else {
      form.reset({
        shift: (lockedShift ?? "A") as "A" | "B" | "N",
        action: "",
        probleme: "",
        pilote: "",
        date: isoCalendarToday(),
        cause: "",
      });
    }
  }, [editing, form, lockedShift]);

  const saveMutation = useMutation({
    mutationFn: async (payload: MdForm & { equipe: EquipeScope; statut: string }) => {
      if (editing) {
        await api.patch(`/api/mode-degrade/${editing.id}/`, payload);
      } else {
        await api.post("/api/mode-degrade/", payload);
      }
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["mode-degrade", equipe] });
      setOpen(false);
      setEditing(null);
      setErrorMsg(null);
    },
    onError: (e) => setErrorMsg(formatApiError(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/api/mode-degrade/${id}/`),
    onSuccess: async () => qc.invalidateQueries({ queryKey: ["mode-degrade", equipe] }),
  });

  const exportHref = `/api/mode-degrade/?equipe=${encodeURIComponent(equipe)}&export=excel${
    effectiveShift ? `&shift=${encodeURIComponent(effectiveShift)}` : ""
  }${searchQuery.trim() ? `&q=${encodeURIComponent(searchQuery.trim())}` : ""}`;

  const onSubmit = form.handleSubmit((values) =>
    saveMutation.mutate({
      ...values,
      equipe,
      shift: (lockedShift ?? values.shift) as "A" | "B" | "N",
      statut: editing?.statut ?? "Ouvert",
    })
  );

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "center" }}>
        <Typography variant="h5" fontWeight={800}>
          Mode dégradé · UEP {equipe}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button component="a" href={exportHref} variant="outlined" size="small">
            Exporter Excel
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
          label="Rechercher"
          placeholder="Problème, action, pilote, cause…"
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 220, flex: 1 }}
        />
        <TextField
          select
          size="small"
          label="Équipe"
          id="md-filter-shift"
          value={lockedShift ?? shiftFilter}
          disabled={!!lockedShift}
          onChange={(e) => {
            setShiftFilter(e.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 110 }}
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
              <TableCell>Équipe</TableCell>
              <TableCell>Problème</TableCell>
              <TableCell>Action</TableCell>
              <TableCell>Pilote</TableCell>
              <TableCell>Date</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography color="text.secondary">Chargement…</Typography>
                </TableCell>
              </TableRow>
            )}
            {!isLoading &&
              data?.results.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell>{row.shift}</TableCell>
                  <TableCell sx={{ maxWidth: 200 }}>{row.probleme}</TableCell>
                  <TableCell sx={{ maxWidth: 200 }}>{row.action}</TableCell>
                  <TableCell>{row.pilote}</TableCell>
                  <TableCell>{row.date.slice(0, 10)}</TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => {
                        setEditing(row);
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
                          if (window.confirm("Supprimer cet élément ?")) deleteMutation.mutate(row.id);
                        }}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            {!isLoading && data?.results.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography color="text.secondary">Aucun incident en mode dégradé.</Typography>
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
        <DialogTitle>{editing ? "Modifier" : "Ajouter"} un mode dégradé</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 0.5 }}>
            <TextField
              select
              label="Équipe"
              fullWidth
              disabled={!!lockedShift}
              helperText={lockedShift ? "Équipe imposée (profil PSP)" : undefined}
              {...form.register("shift")}
            >
              {(lockedShift ? ([lockedShift] as const) : (["A", "B", "N"] as const)).map((s) => (
                <MenuItem key={s} value={s}>
                  {s}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Problème" fullWidth multiline minRows={2} {...form.register("probleme")} />
            <TextField label="Action" fullWidth multiline minRows={2} {...form.register("action")} />
            <TextField label="Pilote" fullWidth {...form.register("pilote")} />
            <GiDatePickerRhf control={form.control} name="date" label="Date" fullWidth />
            <TextField label="Cause" fullWidth multiline minRows={2} {...form.register("cause")} />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setOpen(false)}>Annuler</Button>
          <Button variant="contained" onClick={onSubmit} disabled={saveMutation.isPending}>
            Enregistrer
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
