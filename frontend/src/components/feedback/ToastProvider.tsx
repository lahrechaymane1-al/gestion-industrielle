import { Alert, Snackbar } from "@mui/material";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export type ToastSeverity = "success" | "error" | "info" | "warning";

type ToastContextValue = {
  showToast: (message: string, severity?: ToastSeverity) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [severity, setSeverity] = useState<ToastSeverity>("info");

  const showToast = useCallback((msg: string, sev: ToastSeverity = "info") => {
    setMessage(msg);
    setSeverity(sev);
    setOpen(true);
  }, []);

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <Snackbar
        open={open}
        autoHideDuration={5200}
        onClose={(_, reason) => {
          if (reason === "clickaway") return;
          setOpen(false);
        }}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        sx={{ zIndex: (t) => t.zIndex.modal + 2 }}
      >
        <Alert
          onClose={() => setOpen(false)}
          severity={severity}
          variant="filled"
          sx={{
            width: "100%",
            minWidth: { xs: 280, sm: 360 },
            boxShadow: "0 12px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06)",
            borderRadius: 2,
          }}
        >
          {message}
        </Alert>
      </Snackbar>
    </ToastContext.Provider>
  );
}

/* eslint-disable react-refresh/only-export-components -- hook colocated with provider */
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  return ctx ?? { showToast: () => {} };
}
