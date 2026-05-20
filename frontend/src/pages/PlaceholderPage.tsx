import { Button, Paper, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

export default function PlaceholderPage({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <Paper sx={{ p: 4, borderRadius: 3 }}>
      <Typography variant="h5" gutterBottom fontWeight={700}>
        {title}
      </Typography>
      <Typography color="text.secondary" paragraph>
        {subtitle}
      </Typography>
      <Button component={RouterLink} to="/" variant="contained">
        Retour tableau de bord
      </Button>
    </Paper>
  );
}
