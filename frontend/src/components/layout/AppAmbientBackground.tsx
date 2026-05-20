import { Box } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { designTokens } from "../../theme/designTokens";

/**
 * Full-viewport canvas — ardoise profonde + halos cyan et ambre.
 */
export default function AppAmbientBackground() {
  const { canvas, brand, accent } = designTokens;
  return (
    <Box
      aria-hidden
      sx={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
        overflow: "hidden",
        bgcolor: canvas.black,
        backgroundImage: `
          radial-gradient(ellipse 90% 55% at 50% -15%, ${alpha(brand.sky, 0.16)}, transparent 52%),
          radial-gradient(ellipse 65% 45% at 100% 10%, ${alpha(accent.teal, 0.1)}, transparent 48%),
          radial-gradient(ellipse 55% 42% at 0% 95%, ${alpha(brand.amber, 0.07)}, transparent 50%),
          linear-gradient(180deg, ${canvas.gradientTop} 0%, ${canvas.gradientMid} 46%, ${brand.ink} 100%)
        `,
        backgroundAttachment: "fixed",
      }}
    />
  );
}
