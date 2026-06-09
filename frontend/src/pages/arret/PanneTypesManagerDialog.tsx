import { zodResolver } from "@hookform/resolvers/zod";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api, formatApiError } from "../../api/client";
import type { EquipeScope, PanneTypeOption } from "../../api/types";

const typeSchema = z.object({
  name: z.string().min(1, "Nom obligatoire"),
  description: z.string().optional(),
});

type TypeFormValues = z.infer<typeof typeSchema>;

type PanneTypesManagerDialogProps = {
  equipe: EquipeScope;
  canCreate: boolean;
  canUpdate: boolean;
  canDelete: boolean;
  onSelectType?: (id: number) => void;
  variant?: "toolbar" | "inline";
};

export function PanneTypesManagerDialog({
  equipe,
  canCreate,
  canUpdate,
  canDelete,
  onSelectType,
  variant = "toolbar",
}: PanneTypesManagerDialogProps) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<PanneTypeOption | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [infoMsg, setInfoMsg] = useState<string | null>(null);

  const canManage = canCreate || canUpdate || canDelete;

  const { data: types = [], isLoading } = useQuery({
    queryKey: ["panne-types", equipe, "manage"],
    enabled: open,
    queryFn: async () =>
      (
        await api.get<{ results: PanneTypeOption[] }>("/api/panne-types/", {
          params: { equipe },
        })
      ).data.results,
  });

  const form = useForm<TypeFormValues>({
    resolver: zodResolver(typeSchema),
    defaultValues: { name: "", description: "" },
  });

  useEffect(() => {
    if (!editorOpen) return;
    if (editing) {
      form.reset({ name: editing.name, description: editing.description ?? "" });
    } else {
      form.reset({ name: "", description: "" });
    }
    setErrorMsg(null);
  }, [editorOpen, editing, form]);

  const invalidateTypes = async () => {
    await qc.invalidateQueries({ queryKey: ["panne-types", equipe] });
  };

  const saveMutation = useMutation({
    mutationFn: async (values: TypeFormValues) => {
      const payload = { name: values.name.trim(), description: values.description?.trim() ?? "" };
      if (editing) {
        return (
          await api.patch<PanneTypeOption>(`/api/panne-types/${editing.id}/`, payload, {
            params: { equipe },
          })
        ).data;
      }
      return (await api.post<PanneTypeOption>("/api/panne-types/", payload, { params: { equipe } })).data;
    },
    onSuccess: async (saved) => {
      await invalidateTypes();
      setEditorOpen(false);
      const wasEdit = !!editing;
      setEditing(null);
      setErrorMsg(null);
      onSelectType?.(saved.id);
      setInfoMsg(wasEdit ? "Type modifié." : "Type ajouté.");
    },
    onError: (err) => setErrorMsg(formatApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (row: PanneTypeOption) => {
      const res = await api.delete<{ id: number; removed?: boolean; deactivated?: boolean }>(
        `/api/panne-types/${row.id}/`,
        { params: { equipe } }
      );
      return { id: row.id, deactivated: res.data.deactivated === true };
    },
    onSuccess: async ({ id: deletedId, deactivated }) => {
      qc.setQueryData<PanneTypeOption[]>(["panne-types", equipe, "manage"], (prev) =>
        (prev ?? []).filter((t) => t.id !== deletedId)
      );
      await invalidateTypes();
      setInfoMsg(
        deactivated
          ? "Type retiré de la liste (conservé pour l'historique des arrêts)."
          : "Type supprimé."
      );
      setErrorMsg(null);
    },
    onError: (err) => setErrorMsg(formatApiError(err)),
  });

  const openCreate = () => {
    setEditing(null);
    setEditorOpen(true);
  };

  const openEdit = (row: PanneTypeOption) => {
    setEditing(row);
    setEditorOpen(true);
  };

  const onSave = form.handleSubmit((values) => saveMutation.mutate(values));

  const triggerButton =
    variant === "inline" ? (
      <Button variant="outlined" size="small" onClick={() => setOpen(true)} disabled={!canManage}>
        Gérer les types
      </Button>
    ) : (
      <Button
        variant="outlined"
        size="small"
        startIcon={<SettingsOutlinedIcon />}
        onClick={() => setOpen(true)}
        disabled={!canManage}
      >
        Types d&apos;arrêt
      </Button>
    );

  if (!canManage) return null;

  return (
    <>
      {triggerButton}

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>Types d&apos;arrêt · UEP {equipe}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 0.5 }}>
            <Typography variant="body2" color="text.secondary">
              {equipe === "CCB"
                ? "Phase de démarrage CCB : créez ici tous les types d'arrêt. Ils sont enregistrés en base et proposés dans le formulaire « Ajouter un arrêt »."
                : "Ajoutez, modifiez ou supprimez un type. La suppression retire la ligne immédiatement."}
            </Typography>
            {infoMsg && (
              <Alert severity="success" onClose={() => setInfoMsg(null)}>
                {infoMsg}
              </Alert>
            )}
            {errorMsg && (
              <Alert severity="error" onClose={() => setErrorMsg(null)}>
                {errorMsg}
              </Alert>
            )}
            {canCreate && (
              <Box>
                <Button startIcon={<AddIcon />} variant="contained" size="small" onClick={openCreate}>
                  Ajouter un type
                </Button>
              </Box>
            )}
            <TableContainer sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: "action.hover" }}>
                    <TableCell>Nom</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {isLoading && (
                    <TableRow>
                      <TableCell colSpan={3}>
                        <Typography color="text.secondary">Chargement...</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                  {!isLoading && types.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3}>
                        <Typography color="text.secondary">Aucun type.</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                  {types.map((row) => (
                    <TableRow key={row.id} hover>
                      <TableCell sx={{ fontWeight: 600 }}>{row.name}</TableCell>
                      <TableCell>{row.description || "—"}</TableCell>
                      <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                        {onSelectType && (
                          <Button size="small" onClick={() => onSelectType(row.id)}>
                            Choisir
                          </Button>
                        )}
                        {canUpdate && (
                          <Tooltip title="Modifier">
                            <IconButton size="small" onClick={() => openEdit(row)} aria-label="modifier">
                              <EditOutlinedIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {canDelete && (
                          <Tooltip title="Supprimer">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => {
                                if (window.confirm(`Supprimer le type « ${row.name} » ?`)) {
                                  deleteMutation.mutate(row);
                                }
                              }}
                              aria-label="supprimer"
                            >
                              <DeleteOutlineIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <Typography variant="caption" color="text.secondary">
              {types.length} type(s) dans le menu « Type d&apos;arrêt ».
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setOpen(false)}>Fermer</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={editorOpen} onClose={() => setEditorOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editing ? "Modifier le type d'arrêt" : "Ajouter un type d'arrêt"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 0.5 }}>
            {errorMsg && <Alert severity="error">{errorMsg}</Alert>}
            <TextField
              label="Nom"
              fullWidth
              autoFocus
              {...form.register("name")}
              error={!!form.formState.errors.name}
              helperText={form.formState.errors.name?.message}
            />
            <TextField
              label="Description (optionnel)"
              fullWidth
              multiline
              minRows={2}
              {...form.register("description")}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setEditorOpen(false)}>Annuler</Button>
          <Button variant="contained" onClick={onSave} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? "Enregistrement..." : "Enregistrer"}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
