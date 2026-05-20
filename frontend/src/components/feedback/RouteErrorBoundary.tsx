import { Alert, Box, Button, Typography } from "@mui/material";
import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode };

type State = { error: Error | null };

export class RouteErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[RouteErrorBoundary]", error, info.componentStack);
  }

  private handleRetry = () => {
    this.setState({ error: null });
    window.location.reload();
  };

  render() {
    if (this.state.error) {
      return (
        <Box sx={{ py: 4, px: 2, maxWidth: 560 }}>
          <Alert severity="error" sx={{ mb: 2 }}>
            Une erreur a empêché l&apos;affichage de cette page.
          </Alert>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontFamily: "monospace" }}>
            {this.state.error.message}
          </Typography>
          <Button variant="contained" onClick={this.handleRetry}>
            Recharger la page
          </Button>
        </Box>
      );
    }
    return this.props.children;
  }
}
