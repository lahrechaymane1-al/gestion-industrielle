import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import HomeRoundedIcon from "@mui/icons-material/HomeRounded";
import SpaceDashboardOutlinedIcon from "@mui/icons-material/SpaceDashboardOutlined";
import EventBusyOutlinedIcon from "@mui/icons-material/EventBusyOutlined";
import Inventory2OutlinedIcon from "@mui/icons-material/Inventory2Outlined";
import NotificationsActiveOutlinedIcon from "@mui/icons-material/NotificationsActiveOutlined";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import MenuIcon from "@mui/icons-material/Menu";
import PrecisionManufacturingOutlinedIcon from "@mui/icons-material/PrecisionManufacturingOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import ShoppingCartOutlinedIcon from "@mui/icons-material/ShoppingCartOutlined";
import {
  Alert,
  AppBar,
  Box,
  Button,
  Chip,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Toolbar,
  Typography,
} from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useMe } from "../auth/AuthContext";
import { RouteErrorBoundary } from "../components/feedback/RouteErrorBoundary";
import AppAmbientBackground from "../components/layout/AppAmbientBackground";
import { STELLANTIS_LOGO_ALT, STELLANTIS_LOGO_SRC } from "../constants/brand";
import { designTokens } from "../theme/designTokens";

const DRAWER_WIDTH = 280;
const NAV_OPEN_STORAGE_KEY = "gi-nav-open";
const SIDEBAR_INSET = 16;
const SIDEBAR_CONTENT_GAP = 16;
const SIDEBAR_RADIUS = 16;
const SOFT_EASING = "cubic-bezier(0.22, 1, 0.36, 1)";

const berceauLinks = [
  { to: "/berceau/production", label: "Production", icon: <PrecisionManufacturingOutlinedIcon /> },
  { to: "/berceau/dashboard", label: "Dashboard", icon: <SpaceDashboardOutlinedIcon /> },
  { to: "/berceau/mode-degrade", label: "Mode dégradé", icon: <WarningAmberOutlinedIcon /> },
  { to: "/berceau/absence", label: "Absence", icon: <EventBusyOutlinedIcon /> },
  { to: "/berceau/effectif", label: "Effectif", icon: <GroupsOutlinedIcon /> },
  { to: "/berceau/stock", label: "Stock", icon: <Inventory2OutlinedIcon /> },
  { to: "/berceau/arret", label: "Arret", icon: <NotificationsActiveOutlinedIcon /> },
  { to: "/berceau/consommable", label: "Consommable", icon: <ShoppingCartOutlinedIcon /> },
];

const ccbLinks = [
  { to: "/ccb/production", label: "Production", icon: <PrecisionManufacturingOutlinedIcon /> },
  { to: "/ccb/mode-degrade", label: "Mode dégradé", icon: <WarningAmberOutlinedIcon /> },
  { to: "/ccb/absence", label: "Absence", icon: <EventBusyOutlinedIcon /> },
  { to: "/ccb/effectif", label: "Effectif", icon: <GroupsOutlinedIcon /> },
  { to: "/ccb/stock", label: "Stock", icon: <Inventory2OutlinedIcon /> },
  { to: "/ccb/arret", label: "Arret", icon: <NotificationsActiveOutlinedIcon /> },
  { to: "/ccb/consommable", label: "Consommable", icon: <ShoppingCartOutlinedIcon /> },
];

function NavSection({
  title,
  links,
}: {
  title: string;
  links: { to: string; label: string; icon: ReactNode }[];
}) {
  const theme = useTheme();
  return (
    <Box sx={{ px: 1.25, py: 1.25 }}>
      <Typography
        variant="overline"
        sx={{
          px: 1.5,
          color: "text.secondary",
          fontWeight: 700,
          letterSpacing: "0.14em",
          fontSize: "0.65rem",
          opacity: 0.9,
        }}
      >
        {title}
      </Typography>
      <List dense disablePadding>
        {links.map((item) => (
          <ListItemButton
            key={item.to}
            component={NavLink}
            to={item.to}
            sx={{
              borderRadius: 1.25,
              mx: 0.5,
              mb: 0.35,
              py: 1,
              px: 1.25,
              color: "text.secondary",
              borderLeft: "2px solid transparent",
              transition:
                `background 0.24s ${SOFT_EASING}, color 0.2s ease, border-color 0.2s ease, transform 0.24s ${SOFT_EASING}`,
              "&:hover": {
                bgcolor: alpha(theme.palette.common.white, 0.05),
                transform: "translateX(2px)",
                color: "text.primary",
              },
              "&.active": {
                bgcolor: alpha(theme.palette.primary.main, 0.1),
                borderLeftColor: "primary.main",
                color: "primary.light",
                fontWeight: 600,
                "& .MuiListItemIcon-root": {
                  color: "primary.light",
                },
              },
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: 40,
                color: "inherit",
                transition: "color 0.2s ease",
              }}
            >
              {item.icon}
            </ListItemIcon>
            <ListItemText primary={item.label} primaryTypographyProps={{ fontWeight: 600, fontSize: "0.9rem" }} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
}

function readDesktopNavOpen(): boolean {
  try {
    return localStorage.getItem(NAV_OPEN_STORAGE_KEY) !== "0";
  } catch {
    return true;
  }
}

export default function AppLayout() {
  const theme = useTheme();
  const { brand, glass, shadow } = designTokens;
  const sidebarShadow = shadow.card;
  const headerShadowElevated = `0 10px 36px rgba(0, 0, 0, 0.42), 0 0 0 1px ${glass.border}, 0 0 48px ${alpha(brand.sky, 0.14)}`;
  const headerShadowResting = `0 6px 24px rgba(0, 0, 0, 0.32), 0 0 0 1px ${glass.border}`;
  const [mobileOpen, setMobileOpen] = useState(false);
  const [desktopNavOpen, setDesktopNavOpen] = useState(readDesktopNavOpen);
  const [appBarHidden, setAppBarHidden] = useState(false);
  const [appBarElevated, setAppBarElevated] = useState(false);
  const me = useMe();
  const location = useLocation();
  const navigate = useNavigate();
  const isPsp = me?.role === "PSP";
  const pspEquipe = (me?.equipe ?? "").trim().toUpperCase();
  const canSeeBerceau = !isPsp || pspEquipe === "BERCEAU";
  const canSeeCcb = !isPsp || pspEquipe === "CCB";
  const pspMissingScope = isPsp && !canSeeBerceau && !canSeeCcb;
  const visibleBerceauLinks = useMemo(
    () => (canSeeBerceau ? berceauLinks.filter((l) => !(isPsp && l.to.includes("/consommable"))) : []),
    [canSeeBerceau, isPsp]
  );
  const visibleCcbLinks = useMemo(
    () => (canSeeCcb ? ccbLinks.filter((l) => !(isPsp && l.to.includes("/consommable"))) : []),
    [canSeeCcb, isPsp]
  );
  const allVisibleLinks = useMemo(
    () => [...visibleBerceauLinks, ...visibleCcbLinks],
    [visibleBerceauLinks, visibleCcbLinks]
  );
  const title =
    allVisibleLinks.find((l) => location.pathname === l.to || location.pathname.startsWith(`${l.to}/`))
      ?.label ?? "Tableau de bord";

  useEffect(() => {
    if (!isPsp) return;
    const p = location.pathname.toLowerCase();
    if (pspEquipe === "CCB" && p.includes("/berceau/")) {
      navigate("/ccb/production", { replace: true });
      return;
    }
    if (pspEquipe === "BERCEAU" && p.includes("/ccb/")) {
      navigate("/berceau/production", { replace: true });
    }
  }, [isPsp, pspEquipe, location.pathname, navigate]);

  useEffect(() => {
    let lastY = 0;
    let raf = 0;

    const getScrollTop = (evt?: Event) => {
      const target = evt?.target;
      if (!target || target === document) return window.scrollY ?? 0;
      if (target === document.scrollingElement) return window.scrollY ?? 0;
      if (target instanceof HTMLElement) return target.scrollTop ?? 0;
      return window.scrollY ?? 0;
    };

    const onScroll = (evt: Event) => {
      const y = getScrollTop(evt);
      cancelAnimationFrame(raf);
      raf = window.requestAnimationFrame(() => {
        const delta = y - lastY;
        const abs = Math.abs(delta);

        // Elevation should react even to small scrolls.
        setAppBarElevated(y > 8);

        // Only react to intentional scrolls (ignore tiny jitter / trackpad noise).
        if (abs < 14) {
          lastY = y;
          return;
        }

        // Header: hide on scroll down, show on scroll up.
        if (y > 96 && delta > 0) setAppBarHidden(true);
        if (delta < 0) setAppBarHidden(false);

        lastY = y;
      });
    };

    // Capture scroll events from any scrollable container (scroll doesn't bubble).
    document.addEventListener("scroll", onScroll, { passive: true, capture: true });
    return () => {
      document.removeEventListener("scroll", onScroll, { capture: true } as AddEventListenerOptions);
      cancelAnimationFrame(raf);
    };
  }, []);

  const toggleDesktopNav = () => {
    setDesktopNavOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(NAV_OPEN_STORAGE_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  const drawer = (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "transparent",
      }}
    >
      <Toolbar sx={{ py: 2, minHeight: 64 }}>
        <Box
          component="img"
          src={STELLANTIS_LOGO_SRC}
          alt={STELLANTIS_LOGO_ALT}
          sx={{
            width: "100%",
            maxWidth: 220,
            height: 36,
            objectFit: "contain",
            display: "block",
            mixBlendMode: "screen",
          }}
        />
      </Toolbar>
      <Divider sx={{ borderColor: "divider" }} />
      <Box sx={{ flex: 1, overflowY: "auto", py: 0.5 }}>
        {pspMissingScope && (
          <Alert severity="warning" sx={{ mx: 1.5, mt: 1, mb: 0.5 }}>
            Menu vide : le profil PSP n’a pas d’UEP Berceau ou CCB liée (effectif manquant). Contactez un admin.
          </Alert>
        )}
        {canSeeBerceau && <NavSection title="UEP Berceau" links={visibleBerceauLinks} />}
        {canSeeBerceau && canSeeCcb && <Divider sx={{ my: 1, mx: 2, borderColor: "divider" }} />}
        {canSeeCcb && <NavSection title="UEP CCB" links={visibleCcbLinks} />}
      </Box>
      <Divider sx={{ borderColor: "divider" }} />
      <Box sx={{ p: 2 }}>
        <Typography variant="caption" color="text.secondary" fontWeight={600} display="block">
          Session sécurisée
        </Typography>
        <Typography variant="caption" sx={{ opacity: 0.55 }} fontWeight={500}>
          Interface React
        </Typography>
      </Box>
    </Box>
  );

  return (
    <>
      <AppAmbientBackground />
      <Box
        sx={{
          position: "relative",
          zIndex: 1,
          minHeight: "100vh",
          bgcolor: "transparent",
          boxSizing: "border-box",
          p: { xs: 0, md: `${SIDEBAR_INSET}px` },
          pt: { xs: 0, md: `${SIDEBAR_INSET}px` },
          pb: { xs: 0, md: `${SIDEBAR_INSET}px` },
        }}
      >
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": {
            boxSizing: "border-box",
            width: DRAWER_WIDTH,
            borderTopRightRadius: SIDEBAR_RADIUS,
            borderBottomRightRadius: SIDEBAR_RADIUS,
            border: "none",
            boxShadow: sidebarShadow,
            bgcolor: designTokens.glass.fill,
            backdropFilter: "blur(22px) saturate(140%)",
            WebkitBackdropFilter: "blur(22px) saturate(140%)",
          },
        }}
      >
        {drawer}
      </Drawer>

      <Paper
        component="nav"
        elevation={0}
        aria-hidden={!desktopNavOpen}
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          position: "fixed",
          left: SIDEBAR_INSET,
          top: SIDEBAR_INSET,
          width: DRAWER_WIDTH,
          height: `calc(100vh - ${SIDEBAR_INSET * 2}px)`,
          maxHeight: `calc(100vh - ${SIDEBAR_INSET * 2}px)`,
          zIndex: (t) => t.zIndex.drawer,
          borderRadius: `${SIDEBAR_RADIUS}px`,
          overflow: "hidden",
          border: `1px solid ${alpha(theme.palette.common.white, 0.08)}`,
          backgroundImage: "none",
          boxShadow: sidebarShadow,
          bgcolor: designTokens.glass.fill,
          backdropFilter: designTokens.glass.blur,
          WebkitBackdropFilter: designTokens.glass.blur,
          willChange: "transform",
          transition: `transform 0.42s ${SOFT_EASING}, box-shadow 0.45s ease, border-color 0.35s ease, opacity 0.32s ease`,
          transform: desktopNavOpen
            ? "translate3d(0, 0, 0)"
            : `translate3d(calc(-100% - ${SIDEBAR_INSET}px), 0, 0)`,
          opacity: desktopNavOpen ? 1 : 0,
          pointerEvents: desktopNavOpen ? "auto" : "none",
          "&:hover": {
            boxShadow: `${sidebarShadow}, 0 0 56px ${alpha(brand.sky, 0.14)}`,
            borderColor: glass.borderStrong,
          },
        }}
      >
        {drawer}
      </Paper>

      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
          minHeight: { xs: "100vh", md: `calc(100vh - ${SIDEBAR_INSET * 2}px)` },
          ml: {
            md: desktopNavOpen ? `${DRAWER_WIDTH + SIDEBAR_CONTENT_GAP}px` : 0,
          },
          transition: `margin-left 0.42s ${SOFT_EASING}`,
        }}
      >
          <AppBar
            position="sticky"
            elevation={0}
            sx={{
              top: 0,
              border: "none",
              bgcolor: { xs: "transparent", md: "transparent" },
              backdropFilter: "none",
              boxShadow: "none",
              zIndex: (theme) => theme.zIndex.drawer + 1,
              transition: `transform 0.38s ${SOFT_EASING}, opacity 0.28s ease`,
              transform: appBarHidden ? "translate3d(0, -72px, 0)" : "translate3d(0, 0, 0)",
              opacity: appBarHidden ? 0.0 : 1,
              pointerEvents: appBarHidden ? "none" : "auto",
            }}
          >
            <Toolbar
              sx={{
                minHeight: 64,
                px: { xs: 2, md: 0.5 },
              }}
            >
              <Box
                sx={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  px: { xs: 0.5, md: 1.5 },
                  py: { xs: 0.35, md: 0.85 },
                  borderRadius: { xs: 0, md: `${SIDEBAR_RADIUS}px` },
                  border: { md: `1px solid ${alpha(theme.palette.common.white, 0.08)}` },
                  bgcolor: { xs: designTokens.glass.fillHover, md: designTokens.glass.fill },
                  backdropFilter: { xs: "blur(16px)", md: "blur(20px)" },
                  WebkitBackdropFilter: { xs: "blur(16px)", md: "blur(20px)" },
                  boxShadow: appBarElevated ? headerShadowElevated : headerShadowResting,
                  transition: `box-shadow 0.35s ease, background 0.35s ease, border-color 0.35s ease, transform 0.35s ${SOFT_EASING}`,
                  transform: "translate3d(0, 0, 0)",
                }}
              >
              <IconButton
                edge="start"
                onClick={() => setMobileOpen(true)}
                sx={{
                  mr: 1.5,
                  display: { md: "none" },
                  color: "text.primary",
                  transition: "transform 0.2s ease, background 0.2s ease",
                  "&:hover": { bgcolor: alpha(theme.palette.common.white, 0.08), transform: "scale(1.04)" },
                }}
                aria-label="Ouvrir le menu"
              >
                <MenuIcon />
              </IconButton>
              <IconButton
                edge="start"
                onClick={toggleDesktopNav}
                sx={{
                  mr: 1.5,
                  display: { xs: "none", md: "inline-flex" },
                  color: "text.primary",
                  border: `1px solid ${alpha(theme.palette.common.white, 0.1)}`,
                  transition: "transform 0.2s ease, background 0.2s ease",
                  "&:hover": { bgcolor: alpha(theme.palette.common.white, 0.08), transform: "scale(1.04)" },
                }}
                aria-label={desktopNavOpen ? "Masquer le menu" : "Afficher le menu"}
                aria-expanded={desktopNavOpen}
              >
                {desktopNavOpen ? <ChevronLeftIcon /> : <ChevronRightIcon />}
              </IconButton>
              <IconButton
                component={RouterLink}
                to="/"
                color="primary"
                aria-label="Accueil tableau de bord"
                sx={{
                  mr: 0.5,
                  display: { xs: "inline-flex", sm: "none" },
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.35)}`,
                  borderRadius: 2,
                }}
              >
                <HomeRoundedIcon />
              </IconButton>
              <Button
                component={RouterLink}
                to="/"
                variant="outlined"
                size="small"
                startIcon={<HomeRoundedIcon />}
                sx={{
                  mr: 1.5,
                  flexShrink: 0,
                  borderColor: alpha(theme.palette.primary.main, 0.4),
                  color: "primary.light",
                  fontWeight: 600,
                  display: { xs: "none", sm: "inline-flex" },
                }}
              >
                Accueil
              </Button>
              <Typography variant="h6" component="h1" fontWeight={700} color="text.primary" letterSpacing="-0.02em">
                {title}
              </Typography>
              {me?.authenticated && me.role && (
                <Chip
                  size="small"
                  label={me.shift ? `${me.role} · Shift ${me.shift}` : me.role}
                  sx={{
                    ml: 1.5,
                    fontWeight: 600,
                    borderColor: alpha(theme.palette.primary.main, 0.35),
                    boxShadow: `0 0 20px ${alpha(theme.palette.primary.main, 0.12)}`,
                  }}
                  variant="outlined"
                  color="primary"
                />
              )}
              <Box sx={{ flexGrow: 1 }} />
              <Button
                component="a"
                href="/logout/"
                variant="outlined"
                color="primary"
                size="small"
                sx={{
                  fontWeight: 600,
                  textDecoration: "none",
                  borderWidth: 1,
                  flexShrink: 0,
                }}
              >
                Déconnexion
              </Button>
              </Box>
            </Toolbar>
          </AppBar>
          <Box
            component="main"
            sx={{
              flex: 1,
              p: { xs: 2, md: 3 },
              pt: { xs: 1, md: 2 },
              maxWidth: desktopNavOpen ? 1440 : "none",
              width: "100%",
              mx: desktopNavOpen ? { md: "auto" } : 0,
              transition: `max-width 0.42s ${SOFT_EASING}`,
              bgcolor: designTokens.glass.fill,
              backdropFilter: { md: designTokens.glass.blur },
              WebkitBackdropFilter: { md: designTokens.glass.blur },
              boxShadow: { md: shadow.card },
              borderRadius: { xs: 0, md: 2 },
              border: { xs: "none", md: `1px solid ${alpha(theme.palette.common.white, 0.06)}` },
            }}
          >
            <Box
              key={location.pathname}
              sx={{
                animation: `gi-fade-in 0.42s ${SOFT_EASING} both`,
                willChange: "opacity, transform",
              }}
            >
              <RouteErrorBoundary>
                <Outlet />
              </RouteErrorBoundary>
            </Box>
          </Box>
      </Box>
    </Box>
    </>
  );
}
