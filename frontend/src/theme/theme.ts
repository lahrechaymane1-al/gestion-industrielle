import { alpha, createTheme } from "@mui/material/styles";
import type {} from "@mui/x-date-pickers/themeAugmentation";
import { designTokens } from "./designTokens";

const { brand, navy, accent, glass, shadow } = designTokens;

const fontStack = '"Plus Jakarta Sans", "Inter", "Segoe UI", system-ui, sans-serif';

const textPrimary = brand.text;
const textSecondary = "rgba(148, 163, 184, 0.95)";
const textDisabled = "rgba(148, 163, 184, 0.42)";

/**
 * Global MUI theme — Slate Horizon: ardoise, verre, lueur cyan, accents ambre.
 */
export const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: brand.sky,
      light: brand.skySoft,
      dark: "#0ea5e9",
      contrastText: brand.ink,
    },
    secondary: {
      main: brand.amber,
      light: "#fde68a",
      dark: "#d97706",
      contrastText: brand.ink,
    },
    background: {
      default: brand.slate,
      /** Solid dark — évite alpha(paper, 0.9) qui devient gris clair si paper est rgba blanc. */
      paper: brand.slateLight,
    },
    text: {
      primary: textPrimary,
      secondary: textSecondary,
      disabled: textDisabled,
    },
    divider: glass.border,
    success: { main: accent.emerald },
    warning: { main: "#fbbf24" },
    error: { main: "#fca5a5" },
  },
  typography: {
    fontFamily: fontStack,
    h4: { fontWeight: 700, letterSpacing: "-0.03em" },
    h5: { fontWeight: 700, letterSpacing: "-0.025em" },
    h6: { fontWeight: 600, letterSpacing: "-0.02em" },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
    button: { fontWeight: 600, letterSpacing: "0.01em" },
    body2: { lineHeight: 1.6 },
    overline: { fontWeight: 700, letterSpacing: "0.12em" },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        html: { scrollBehavior: "smooth" },
        body: {
          margin: 0,
          minHeight: "100vh",
          backgroundColor: brand.ink,
          backgroundImage: "none",
          backgroundAttachment: "fixed",
          color: textPrimary,
        },
        "input[type=number]::-webkit-outer-spin-button, input[type=number]::-webkit-inner-spin-button": {
          WebkitAppearance: "none",
          margin: 0,
        },
        "input[type=number]": {
          MozAppearance: "textfield",
        },
        "::-webkit-scrollbar": { width: 8, height: 8 },
        "::-webkit-scrollbar-thumb": {
          background: alpha(brand.sky, 0.28),
          borderRadius: 8,
          border: "2px solid transparent",
          backgroundClip: "padding-box",
        },
        "::-webkit-scrollbar-thumb:hover": {
          background: alpha(brand.sky, 0.42),
        },
        "::-webkit-scrollbar-track": { background: alpha(brand.ink, 0.5) },
        ".recharts-wrapper, .recharts-surface": {
          background: "transparent !important",
        },
        /* Native date inputs: match dark theme where the browser allows */
        'input[type="date"], input[type="datetime-local"]': {
          colorScheme: "dark",
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          textTransform: "none",
          borderRadius: 10,
          paddingInline: 18,
          minHeight: 40,
          transition:
            "transform 0.22s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.25s ease, background 0.22s ease, border-color 0.22s ease, opacity 0.2s ease",
        },
        contained: {
          boxShadow: shadow.glowPrimary,
          "&:hover": {
            transform: "translateY(-1px)",
            boxShadow: `0 12px 40px ${alpha(accent.cyan, 0.28)}`,
          },
        },
        containedSecondary: {
          boxShadow: shadow.glowSecondary,
          "&:hover": {
            transform: "translateY(-1px)",
            boxShadow: `0 12px 40px ${alpha(accent.violet, 0.26)}`,
          },
        },
        outlined: {
          borderWidth: 1,
          borderColor: alpha(accent.cyan, 0.35),
          color: accent.cyan,
          "&:hover": {
            borderWidth: 1,
            backgroundColor: alpha(accent.cyan, 0.08),
            borderColor: alpha(accent.cyan, 0.5),
          },
        },
        text: {
          "&:hover": { backgroundColor: alpha("#fff", 0.06) },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: glass.fill,
          backdropFilter: glass.blur,
          WebkitBackdropFilter: glass.blur,
          boxShadow: shadow.card,
          border: `1px solid ${glass.border}`,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, borderRadius: 8, height: 28 },
        outlined: { borderWidth: 1 },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "transparent",
          backdropFilter: "none",
          boxShadow: "none",
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: `1px solid ${glass.border}`,
          backgroundColor: glass.fill,
          backdropFilter: glass.blur,
          WebkitBackdropFilter: glass.blur,
          backgroundImage: "none",
          boxShadow: "none",
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: `1px solid ${glass.border}`,
        },
        head: {
          fontWeight: 700,
          fontSize: "0.68rem",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          color: textSecondary,
          backgroundColor: alpha(brand.sky, 0.08),
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          transition: "background-color 0.18s ease",
          "&:hover": { backgroundColor: alpha("#fff", 0.03) },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          backgroundColor: alpha("#fff", 0.03),
          transition: "box-shadow 0.2s ease, background 0.2s ease, border-color 0.2s ease",
          "&:hover": { backgroundColor: alpha("#fff", 0.05) },
          "&.Mui-focused": {
            backgroundColor: alpha(brand.sky, 0.06),
            boxShadow: `0 0 0 2px ${alpha(brand.sky, 0.45)}, 0 0 22px ${alpha(brand.sky, 0.22)}`,
          },
        },
        input: {
          paddingTop: 10,
          paddingBottom: 10,
        },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: { fontWeight: 600 },
      },
    },
    MuiSelect: {
      styleOverrides: {
        select: {
          paddingTop: 10,
          paddingBottom: 10,
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 16,
          border: `1px solid ${glass.borderStrong}`,
          backgroundColor: glass.fillHover,
          backdropFilter: glass.blurHeavy,
          WebkitBackdropFilter: glass.blurHeavy,
          boxShadow: shadow.dialog,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 14,
          backgroundColor: glass.fill,
          backdropFilter: glass.blur,
          WebkitBackdropFilter: glass.blur,
          border: `1px solid ${glass.border}`,
          boxShadow: shadow.card,
          transition: "transform 0.25s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.25s ease",
          "&:hover": {
            boxShadow: `${shadow.card}, 0 0 32px ${alpha(brand.sky, 0.1)}`,
            borderColor: glass.borderStrong,
          },
        },
      },
    },
    MuiTextField: {
      defaultProps: { size: "small" },
    },
    MuiPickersPopper: {
      styleOverrides: {
        paper: {
          backgroundImage: "none",
          borderRadius: 0,
          border: `1px solid ${glass.borderStrong}`,
          backgroundColor: glass.fillHover,
          backdropFilter: glass.blur,
          WebkitBackdropFilter: glass.blur,
          boxShadow: shadow.dialog,
          overflow: "hidden",
          width: "100%",
          maxWidth: "min(100vw - 24px, 400px)",
        },
      },
    },
    MuiPickersLayout: {
      styleOverrides: {
        root: {
          width: "100%",
          borderRadius: 0,
          backgroundColor: alpha(navy.elevated, 0.45),
        },
        contentWrapper: {
          width: "100%",
          padding: "8px 0 4px",
        },
        actionBar: {
          borderTop: `1px solid ${glass.border}`,
          padding: "8px 10px 10px",
          gap: 8,
          backgroundColor: alpha(navy.deep, 0.65),
          "& .MuiButton-root": {
            textTransform: "none",
            fontWeight: 700,
            borderRadius: 2,
            minHeight: 36,
          },
          "& .MuiButton-text": {
            color: accent.cyan,
          },
        },
      },
    },
    MuiPickersCalendarHeader: {
      styleOverrides: {
        root: {
          paddingLeft: 10,
          paddingRight: 8,
          marginBottom: 0,
          width: "100%",
          maxWidth: "100%",
        },
        labelContainer: {
          fontWeight: 800,
          letterSpacing: "-0.02em",
          color: textPrimary,
        },
        switchViewButton: {
          borderRadius: 2,
          fontWeight: 700,
          color: textPrimary,
          "&:hover": {
            backgroundColor: alpha(accent.cyan, 0.1),
          },
        },
      },
    },
    MuiPickersArrowSwitcher: {
      styleOverrides: {
        root: { gap: 0 },
        button: {
          borderRadius: 2,
          color: accent.cyan,
          "&:hover": {
            backgroundColor: alpha(accent.cyan, 0.12),
          },
        },
      },
    },
    MuiDateCalendar: {
      styleOverrides: {
        root: {
          backgroundColor: "transparent",
          color: textPrimary,
          width: "100%",
          maxWidth: "100%",
        },
      },
    },
    MuiPickersSlideTransition: {
      styleOverrides: {
        root: {
          width: "100%",
          overflowX: "hidden",
        },
      },
    },
    MuiDayCalendar: {
      styleOverrides: {
        root: {
          width: "100%",
          paddingLeft: 8,
          paddingRight: 8,
        },
        header: {
          justifyContent: "space-between",
        },
        weekDayLabel: {
          fontWeight: 800,
          fontSize: "0.6875rem",
          letterSpacing: "0.1em",
            color: textSecondary,
          margin: 0,
          width: "14.28%",
          maxWidth: "none",
        },
        weekContainer: {
          margin: 0,
          justifyContent: "space-between",
          width: "100%",
        },
      },
    },
    MuiMonthCalendar: {
      styleOverrides: {
        root: {
          padding: "4px 2px 8px",
        },
      },
    },
    MuiPickersMonth: {
      styleOverrides: {
        monthButton: {
          borderRadius: 2,
          fontWeight: 600,
          color: textPrimary,
          "&:hover": {
            backgroundColor: alpha(accent.cyan, 0.1),
          },
          "&.Mui-selected": {
            background: `linear-gradient(145deg, ${accent.cyan} 0%, ${alpha(accent.cyan, 0.85)} 100%)`,
            color: "#0a0a0b",
            fontWeight: 800,
            boxShadow: shadow.glowPrimary,
            "&:hover": {
              background: `linear-gradient(145deg, ${accent.cyan} 0%, ${alpha(accent.violet, 0.55)} 100%)`,
            },
          },
        },
      },
    },
    MuiYearCalendar: {
      styleOverrides: {
        root: {
          padding: "4px 2px 8px",
          maxHeight: 300,
        },
      },
    },
    MuiPickersYear: {
      styleOverrides: {
        yearButton: {
          borderRadius: 2,
          fontWeight: 600,
          color: textPrimary,
          "&:hover": {
            backgroundColor: alpha(accent.cyan, 0.1),
          },
          "&.Mui-selected": {
            background: `linear-gradient(145deg, ${accent.cyan} 0%, ${alpha(accent.cyan, 0.85)} 100%)`,
            color: "#0a0a0b",
            fontWeight: 800,
            boxShadow: shadow.glowPrimary,
            "&:hover": {
              background: `linear-gradient(145deg, ${accent.cyan} 0%, ${alpha(accent.violet, 0.55)} 100%)`,
            },
          },
        },
      },
    },
    MuiPickersDay: {
      styleOverrides: {
        root: {
          borderRadius: 2,
          fontWeight: 600,
          fontSize: "0.8125rem",
          color: textPrimary,
          transition: "background 0.18s ease, box-shadow 0.2s ease, color 0.18s ease",
          "&:hover": {
            backgroundColor: alpha(accent.cyan, 0.14),
          },
          "&.Mui-disabled": {
            color: textDisabled,
          },
          "&.MuiPickersDay-dayOutsideMonth": {
            color: textDisabled,
          },
        },
        today: {
          border: `1px solid ${alpha(accent.cyan, 0.55)}`,
          fontWeight: 800,
          backgroundColor: "transparent",
        },
        selected: {
          background: `linear-gradient(145deg, ${accent.cyan} 0%, ${accent.teal} 100%)`,
          color: brand.ink,
          fontWeight: 800,
          boxShadow: shadow.glowPrimary,
          "&:hover": {
            background: `linear-gradient(145deg, ${accent.cyan} 0%, ${alpha(accent.violet, 0.72)} 100%)`,
            color: brand.ink,
          },
          "&:focus": {
            background: accent.cyan,
          },
        },
      },
    },
    MuiSkeleton: {
      styleOverrides: {
        root: {
          backgroundColor: alpha("#fff", 0.06),
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 10 },
        filledInfo: {
          backgroundColor: "#0e7490",
        },
        filledSuccess: {
          backgroundColor: "#047857",
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          transition: "background 0.2s ease, transform 0.2s ease",
          "&:hover": {
            backgroundColor: alpha("#fff", 0.06),
          },
        },
      },
    },
  },
});
