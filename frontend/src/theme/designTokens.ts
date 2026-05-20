/**
 * Theme « Slate Horizon » — tableau de bord industriel sombre, verre et lueur cyan.
 * Fond ardoise profond, texte clair, accents ciel + ambre pour la hiérarchie visuelle.
 */
export const brandColors = {
  ink: "#0b1120",
  slate: "#141c2e",
  sky: "#38bdf8",
  text: "#f8fafc",
} as const;

export const designTokens = {
  brand: {
    ...brandColors,
    slateLight: "#1a2538",
    slateMid: "#1e293b",
    skySoft: "#7dd3fc",
    skyGlow: "rgba(56, 189, 248, 0.38)",
    amber: "#fbbf24",
    amberSoft: "rgba(251, 191, 36, 0.22)",
  },
  canvas: {
    gradientTop: "#1a2538",
    gradientMid: "#141c2e",
    black: "#0b1120",
  },
  navy: {
    void: "#0b1120",
    deep: "#141c2e",
    surface: "rgba(248, 250, 252, 0.06)",
    elevated: "rgba(248, 250, 252, 0.1)",
  },
  accent: {
    /** Compatibilité thème MUI — primaire = cyan ciel */
    cyan: brandColors.sky,
    cyanMuted: "rgba(56, 189, 248, 0.14)",
    teal: "#22d3ee",
    tealGlow: "rgba(34, 211, 238, 0.28)",
    violet: "#fbbf24",
    emerald: "#34d399",
  },
  glass: {
    border: "rgba(248, 250, 252, 0.09)",
    borderStrong: "rgba(56, 189, 248, 0.35)",
    fill: "rgba(20, 28, 46, 0.72)",
    fillHover: "rgba(26, 37, 56, 0.88)",
    blur: "blur(22px) saturate(165%)",
    blurHeavy: "blur(36px) saturate(175%)",
  },
  shadow: {
    card:
      "0 12px 40px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(248, 250, 252, 0.06), 0 0 48px rgba(56, 189, 248, 0.12)",
    dialog:
      "0 28px 72px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(56, 189, 248, 0.18), 0 0 64px rgba(56, 189, 248, 0.14)",
    glowPrimary: "0 8px 32px rgba(56, 189, 248, 0.32), 0 0 20px rgba(56, 189, 248, 0.1)",
    glowSecondary: "0 8px 28px rgba(251, 191, 36, 0.22)",
  },
  motion: {
    easeOut: [0.22, 1, 0.36, 1] as const,
    duration: 0.38,
  },
} as const;
