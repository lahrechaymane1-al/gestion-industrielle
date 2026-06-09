import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useQueries } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { GiDatePicker } from "../../components/GiDatePicker";
import { api } from "../../api/client";
import type { EquipeScope, StockJournalResponse, StockJournalRow } from "../../api/types";
import { useMe } from "../../auth/AuthContext";
import { isoCalendarToday } from "../production/productionMetrics";
import StockDiversitySection from "./StockDiversitySection";
import {
  displaySortie,
  formatDetailDate,
  fmtQty,
  HISTORY_DAYS,
} from "./stockJournalUtils";

type StockJournalPageProps = {
  equipe: EquipeScope;
};

const BERCEAU_LINES = ["A1", "A3"] as const;
const CCB_LINES = ["LHD", "RHD"] as const;

export default function StockJournalPage({ equipe }: StockJournalPageProps) {
  const me = useMe();
  const [date, setDate] = useState(isoCalendarToday);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [detailRow, setDetailRow] = useState<StockJournalRow | null>(null);

  const canWrite = me?.role === "RU" || me?.role === "ADMIN";
  const lines = equipe === "Berceau" ? BERCEAU_LINES : CCB_LINES;

  const historyQueries = useQueries({
    queries: lines.map((line) => ({
      queryKey: ["stock-journal", equipe, line ?? null, date, "history-only"],
      queryFn: async () =>
        (
          await api.get<StockJournalResponse>("/api/stock/journal/", {
            params: { equipe, line, date, days: HISTORY_DAYS },
          })
        ).data,
    })),
  });

  const historyLoading = historyQueries.some((q) => q.isLoading);

  const mergedHistory = useMemo(() => {
    const rows: StockJournalRow[] = [];
    historyQueries.forEach((q) => {
      rows.push(...(q.data?.history ?? []));
    });
    return rows.sort((a, b) => b.date.localeCompare(a.date) || (a.line ?? "").localeCompare(b.line ?? ""));
  }, [historyQueries]);

  const exportLinks = useMemo(() => {
    return lines.map((line) => {
      const params = new URLSearchParams({
        equipe,
        line,
        date,
        days: String(HISTORY_DAYS),
        export: "excel",
      });
      return { line, href: `/api/stock/journal/?${params.toString()}` };
    });
  }, [equipe, date, lines]);

  return (
    <Stack spacing={2.5}>
      <Paper sx={{ p: 2.2, borderRadius: 3 }}>
        <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={1.5}>
          <Stack>
            <Typography variant="h5" fontWeight={800}>
              {`Stock · UEP ${equipe}`}
            </Typography>
            {equipe === "Berceau" ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                Stock A1 et stock A3 sont suivis séparément : chaque diversité a sa saisie sortie montage et son
                graphique.
              </Typography>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                Stock LHD et stock RHD sont suivis séparément, comme les diversités Berceau.
              </Typography>
            )}
          </Stack>
          <GiDatePicker label="Date" value={date} onChange={setDate} size="small" sx={{ minWidth: 170 }} />
        </Stack>
      </Paper>

      {errorMsg && <Alert severity="error">{errorMsg}</Alert>}

      {lines.map((line) => (
        <StockDiversitySection
          key={line}
          equipe={equipe}
          line={line}
          date={date}
          canWrite={canWrite}
          onError={setErrorMsg}
        />
      ))}

      <TableContainer component={Paper} sx={{ borderRadius: 3 }}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          flexWrap="wrap"
          gap={1}
          sx={{ px: 2, pt: 2 }}
        >
          <Typography variant="h6" fontWeight={800}>
            Historique stock ({HISTORY_DAYS} jours)
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography variant="body2" color="text.secondary">
              Jusqu&apos;au {date}
            </Typography>
            {exportLinks.map(({ line, href }) => (
              <Button
                key={line ?? "ccb"}
                component="a"
                href={href}
                variant="outlined"
                size="small"
              >
                {line ? `Export Excel ${line}` : "Export Excel"}
              </Button>
            ))}
          </Stack>
        </Stack>
        <Table size="small" sx={{ mt: 1 }}>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Diversité</TableCell>
              <TableCell align="right">Entree Shift A</TableCell>
              <TableCell align="right">Entree Shift B</TableCell>
              <TableCell align="right">Entree Shift N</TableCell>
              <TableCell align="right">Stock debut</TableCell>
              <TableCell align="right">Entree</TableCell>
              <TableCell align="right">Sortie montage</TableCell>
              <TableCell align="right">Stock fin</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {historyLoading && (
              <TableRow>
                <TableCell colSpan={10}>
                  <Typography color="text.secondary">Chargement...</Typography>
                </TableCell>
              </TableRow>
            )}
            {!historyLoading && mergedHistory.length === 0 && (
              <TableRow>
                <TableCell colSpan={10}>
                  <Typography color="text.secondary">Aucune donnee sur cette periode.</Typography>
                </TableCell>
              </TableRow>
            )}
            {!historyLoading &&
              mergedHistory.slice(0, HISTORY_DAYS * lines.length).map((row) => (
                <TableRow key={`${row.date}-${row.equipe}-${row.line ?? "all"}`} hover>
                  <TableCell>{row.date}</TableCell>
                  <TableCell>{row.line ?? "—"}</TableCell>
                  <TableCell align="right">{row.entree_par_shift.A}</TableCell>
                  <TableCell align="right">{row.entree_par_shift.B}</TableCell>
                  <TableCell align="right">{row.entree_par_shift.N}</TableCell>
                  <TableCell align="right">{row.stock_debut}</TableCell>
                  <TableCell align="right">{row.entree_calculee}</TableCell>
                  <TableCell align="right">{displaySortie(row)}</TableCell>
                  <TableCell align="right">{row.stock_fin}</TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => setDetailRow(row)}
                      aria-label={`Detail stock ${row.date}`}
                    >
                      <VisibilityOutlinedIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={!!detailRow} onClose={() => setDetailRow(null)} fullWidth maxWidth="sm">
        <DialogTitle>Detail journal stock</DialogTitle>
        <DialogContent>
          {detailRow && (
            <Stack spacing={1.1} sx={{ mt: 1 }}>
              <Typography>
                <strong>Date:</strong> {formatDetailDate(detailRow.date)}
              </Typography>
              <Typography>
                <strong>UEP:</strong> {detailRow.equipe}
              </Typography>
              {detailRow.line ? (
                <Typography>
                  <strong>Stock (diversité):</strong> {detailRow.line}
                </Typography>
              ) : null}
              <Typography>
                <strong>Entree shift A:</strong> {fmtQty(detailRow.entree_par_shift.A)}
              </Typography>
              <Typography>
                <strong>Entree shift B:</strong> {fmtQty(detailRow.entree_par_shift.B)}
              </Typography>
              <Typography>
                <strong>Entree shift N:</strong> {fmtQty(detailRow.entree_par_shift.N)}
              </Typography>
              <Typography>
                <strong>Stock debut:</strong> {fmtQty(detailRow.stock_debut)}
              </Typography>
              <Typography>
                <strong>Entree totale:</strong> {fmtQty(detailRow.entree_calculee)}
              </Typography>
              <Typography>
                <strong>
                  Sortie montage
                  {detailRow.line ? ` (stock ${detailRow.line})` : ""}:
                </strong>{" "}
                {fmtQty(detailRow.sortie_montage)}
              </Typography>
              {detailRow.sortie_imputee != null &&
                detailRow.sortie_imputee !== detailRow.sortie_montage && (
                  <Typography>
                    <strong>Sortie imputée (shift):</strong> {fmtQty(detailRow.sortie_imputee)}
                  </Typography>
                )}
              <Typography>
                <strong>Stock fin:</strong> {fmtQty(detailRow.stock_fin)}
              </Typography>
              <Typography>
                <strong>Note:</strong> {(detailRow.note ?? "").trim() || "—"}
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
