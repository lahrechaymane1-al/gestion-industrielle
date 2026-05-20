import { Box, type BoxProps } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { designTokens } from "../../theme/designTokens";

/**
 * Reusable glass-style panel (blur + hairline border). Use for custom shells;
 * most tables/cards already inherit global MUI theme.
 */
export function Surface({ children, sx, ...props }: BoxProps) {
  const { glass, shadow, brand } = designTokens;
  return (
    <Box
      {...props}
      sx={[
        {
          borderRadius: 2,
          border: `1px solid ${glass.border}`,
          bgcolor: glass.fill,
          backdropFilter: glass.blur,
          WebkitBackdropFilter: glass.blur,
          boxShadow: shadow.card,
          transition: "box-shadow 0.28s ease, border-color 0.28s ease",
          "&:hover": {
            borderColor: glass.borderStrong,
            boxShadow: `${shadow.card}, 0 0 28px ${alpha(brand.sky, 0.12)}`,
          },
        },
        ...(sx ? (Array.isArray(sx) ? sx : [sx]) : []),
      ]}
    >
      {children}
    </Box>
  );
}
