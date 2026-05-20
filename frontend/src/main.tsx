import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { frFR } from "@mui/x-date-pickers/locales";
import dayjs from "dayjs";
import "dayjs/locale/fr";
import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { RedirectIfAnonymous } from "./auth/RedirectIfAnonymous";
import { ToastProvider } from "./components/feedback/ToastProvider";
import { theme } from "./theme/theme";

dayjs.locale("fr");

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          <LocalizationProvider
            dateAdapter={AdapterDayjs}
            adapterLocale="fr"
            localeText={frFR.components.MuiLocalizationProvider.defaultProps?.localeText}
          >
            <CssBaseline />
            <ToastProvider>
              <AuthProvider>
                <RedirectIfAnonymous />
                <App />
              </AuthProvider>
            </ToastProvider>
          </LocalizationProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
