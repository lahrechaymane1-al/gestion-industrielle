import SaveIcon from "@mui/icons-material/Save";
import {
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  barIntegerValueLabel,
  ChartGradientDefs,
  ChartLegendContent,
  CHART_OVERFLOW_SX,
  StockEntreeSortieTooltip,
  useChartTheme,
} from "../../components/charts";
import { SafeResponsiveContainer } from "../../components/SafeResponsiveContainer";
import { api, formatApiError } from "../../api/client";
import type { EquipeScope, StockJournalResponse, StockJournalRow } from "../../api/types";
import { useMe } from "../../auth/AuthContext";
import {
  buildChartData,
  CHART_WORKING_DAYS,
  displaySortie,
  stockLineLabel,
} from "./stockJournalUtils";

type StockDiversitySectionProps = {
  equipe: EquipeScope;
  line: "A1" | "A3" | "LHD" | "RHD";
  date: string;
  canWrite: boolean;
  onError: (message: string | null) => void;
};

export default function StockDiversitySection({
  equipe,
  line,
  date,
  canWrite,
  onError,
}: StockDiversitySectionProps) {
  const me = useMe();
  const isPsp = me?.role === "PSP";
  const chart = useChartTheme();
  const qc = useQueryClient();
  const [sortie, setSortie] = useState<number | "">("");
  const [note, setNote] = useState("");
  const hydratedKeyRef = useRef("");

  const diversityTitle =
    line === "A1" || line === "A3" || line === "LHD" || line === "RHD"
      ? `Diversité ${line}`
      : "Stock UEP";
  const sortieLabel = `Sortie montage (${stockLineLabel(line)})`;
  const entreeBarName = line ? `Entree stock ${line}` : "Entree stock";
  const sortieBarName = line ? `Sortie montage (stock ${line})` : "Sortie montage";
  const loadKey = `${equipe}|${line ?? ""}|${date}`;

  const stockQuery = useQuery({
    queryKey: ["stock-journal", equipe, line ?? null, date],
    queryFn: async () =>
      (
        await api.get<StockJournalResponse>("/api/stock/journal/", {
          params: {
            equipe,
            line,
            date,
            days: Math.max(10, CHART_WORKING_DAYS),
          },
        })
      ).data,
  });

  const current = stockQuery.data?.current;
  const history = stockQuery.data?.history ?? [];

  const hydrateFromRow = (row: StockJournalRow) => {
    const sm = isPsp ? displaySortie(row) : row.sortie_montage;
    const n = sm != null ? Number(sm) : NaN;
    setSortie(!Number.isNaN(n) && n !== 0 ? n : "");
    setNote(row.note ?? "");
  };

  useEffect(() => {
    if (!current) return;
    if (hydratedKeyRef.current === loadKey) return;
    hydratedKeyRef.current = loadKey;
    hydrateFromRow(current);
  }, [current, loadKey, isPsp]);

  const chartData = useMemo(() => buildChartData(history), [history]);

  const saveMutation = useMutation({
    mutationFn: async (payload: { sortie_montage: number; note: string }) =>
      (
        await api.post("/api/stock/journal/update/", {
          equipe,
          line,
          date,
          ...payload,
        })
      ).data,
    onSuccess: async (data: StockJournalRow) => {
      onError(null);
      hydratedKeyRef.current = loadKey;
      hydrateFromRow(data);
      await qc.invalidateQueries({ queryKey: ["stock-journal"] });
    },
    onError: (err) => onError(formatApiError(err)),
  });

  return (
    <Paper sx={{ p: 2.2, borderRadius: 3 }}>
      <Typography variant="h6" fontWeight={800} sx={{ mb: 0.5 }}>
        {diversityTitle}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Entrées production et sorties montage prélevées sur le {stockLineLabel(line)} · jour du {date}
      </Typography>

      {stockQuery.isLoading && (
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          Chargement...
        </Typography>
      )}

      {current && !stockQuery.isLoading && (
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.2} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
          <Chip
            color={current.stock_fin < 0 ? "error" : "success"}
            label={`Stock actuel ${line ?? ""}: ${current.stock_fin}`.trim()}
          />
          <Chip color="primary" label={`Shift A: ${current.entree_par_shift.A}`} />
          <Chip color="primary" variant="outlined" label={`Shift B: ${current.entree_par_shift.B}`} />
          <Chip color="primary" variant="outlined" label={`Shift N: ${current.entree_par_shift.N}`} />
          <Chip label={`Stock debut: ${current.stock_debut}`} />
          <Chip label={`Entree totale: ${current.entree_calculee}`} />
        </Stack>
      )}

      {current && (
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mb: 2.5 }}>
          <TextField
            type="text"
            inputMode="numeric"
            label={sortieLabel}
            placeholder="0"
            value={sortie === "" ? "" : String(sortie)}
            onChange={(e) => {
              const raw = e.target.value.trim();
              if (raw === "") {
                setSortie("");
                return;
              }
              if (!/^\d+$/.test(raw)) return;
              const n = Number(raw);
              if (!Number.isNaN(n)) setSortie(Math.min(Number.MAX_SAFE_INTEGER, Math.max(0, n)));
            }}
            disabled={!canWrite}
            sx={{ maxWidth: 280 }}
            helperText={
              isPsp
                ? "Sortie imputée à votre shift (prorata des entrées du jour)"
                : line
                  ? `Quantité sortie du stock ${line} vers le montage`
                  : "Quantité sortie vers le montage"
            }
          />
          <TextField
            label="Note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            disabled={!canWrite}
            fullWidth
          />
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            disabled={!canWrite || saveMutation.isPending}
            onClick={() => saveMutation.mutate({ sortie_montage: sortie === "" ? 0 : sortie, note })}
          >
            Enregistrer
          </Button>
        </Stack>
      )}

      <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
        Graphique · {diversityTitle}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {CHART_WORKING_DAYS} derniers jours ouvrés
      </Typography>
      {stockQuery.isLoading && (
        <Typography color="text.secondary">Chargement du graphique...</Typography>
      )}
      {!stockQuery.isLoading && chartData.length === 0 && (
        <Typography color="text.secondary">Pas assez de donnees sur cette periode.</Typography>
      )}
      {!stockQuery.isLoading && chartData.length > 0 && (
        <Box sx={{ width: "100%", height: 300, minHeight: 240, ...CHART_OVERFLOW_SX }}>
          <SafeResponsiveContainer minHeight={240} boxSx={{ height: 300 }}>
            <BarChart data={chartData} margin={{ ...chart.margins.bar, top: 32 }}>
              <ChartGradientDefs chart={chart} />
              <CartesianGrid {...chart.grid} />
              <XAxis
                dataKey="label"
                interval={0}
                angle={-32}
                textAnchor="end"
                height={72}
                tick={chart.axis.tick}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                width={48}
                tick={chart.axis.tick}
                axisLine={false}
                tickLine={false}
              />
              <RechartsTooltip
                content={<StockEntreeSortieTooltip chart={chart} stockLine={line} />}
                cursor={chart.tooltip.barCursor}
              />
              <Legend content={<ChartLegendContent chart={chart} />} />
              <Bar
                dataKey="entree"
                name={entreeBarName}
                fill={`url(#${chart.ids.barPrimary})`}
                radius={[6, 6, 0, 0]}
                maxBarSize={40}
                animationDuration={chart.animation.barDuration}
              >
                <LabelList
                  dataKey="entree"
                  position="top"
                  content={barIntegerValueLabel(chart.colors.primary)}
                />
              </Bar>
              <Bar
                dataKey="sortie"
                name={sortieBarName}
                fill={`url(#${chart.ids.barSecondary})`}
                radius={[6, 6, 0, 0]}
                maxBarSize={40}
                animationDuration={chart.animation.barDuration}
              >
                <LabelList
                  dataKey="sortie"
                  position="top"
                  content={barIntegerValueLabel(chart.colors.secondary)}
                />
              </Bar>
            </BarChart>
          </SafeResponsiveContainer>
        </Box>
      )}
    </Paper>
  );
}
