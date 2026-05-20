import { Box, type BoxProps } from "@mui/material";
import { useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ResponsiveContainer } from "recharts";

type Size = { width: number; height: number };

function readNumericMinHeight(minHeight: number | string | undefined): number {
  if (typeof minHeight === "number" && Number.isFinite(minHeight)) return minHeight;
  if (typeof minHeight === "string") {
    const n = parseInt(minHeight, 10);
    if (Number.isFinite(n)) return n;
  }
  return 240;
}

export function SafeResponsiveContainer({
  minHeight = 240,
  children,
  boxSx,
}: {
  /** Ensures layout never collapses; also used while measuring. */
  minHeight?: number | string;
  /** Rendered only when container has real size. */
  children: ReactNode;
  /** Extra sx for the wrapper Box. */
  boxSx?: BoxProps["sx"];
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState<Size>({ width: 0, height: 0 });
  const minH = readNumericMinHeight(minHeight);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    const measure = () => {
      const r = el.getBoundingClientRect();
      let width = Math.round(r.width);
      let height = Math.round(r.height);
      // Flex / first-paint: rect can be 0 even when the box will get space — use fallbacks so Recharts still mounts.
      if (width < 2) {
        width = Math.max(
          Math.round(el.offsetWidth),
          Math.round((el.parentElement?.getBoundingClientRect().width ?? 0) * 0.98),
          320
        );
      }
      if (height < 2) {
        height = Math.max(Math.round(el.offsetHeight), Math.round(r.height), minH);
      }
      setSize((prev) => (prev.width === width && prev.height === height ? prev : { width, height }));
    };

    measure();
    let raf1 = 0;
    let raf2 = 0;
    // Defer: parent height (e.g. %) sometimes resolves after first layout pass.
    raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => measure());
    });

    const ro = new ResizeObserver(() => measure());
    ro.observe(el);
    const par = el.parentElement;
    if (par) ro.observe(par);

    return () => {
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
      ro.disconnect();
    };
  }, [minH]);

  const canRender = useMemo(() => size.width > 0 && size.height > 0, [size.width, size.height]);

  return (
    <Box ref={ref} sx={{ width: "100%", height: "100%", minHeight: minH, ...boxSx }}>
      {canRender ? (
        <ResponsiveContainer width={size.width} height={size.height}>
          {children}
        </ResponsiveContainer>
      ) : null}
    </Box>
  );
}

