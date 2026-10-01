import type { CSSProperties } from "react";
import type { ArtworkColors } from "@/components/ds";

/**
 * Ambient field from the cover's own colours (D-ART-04). The server's ambient tone already reads at
 * ≥ 4.5:1 for body text; blending it further toward the page background can only raise contrast,
 * so muted text holds too. The cover's accent is a small glow, never behind the words' full width.
 */
export function ambientStyle(colors: ArtworkColors | null | undefined, theme: "dark" | "light"): CSSProperties {
  if (!colors) return { background: "var(--surface-2)" };
  const base = `color-mix(in srgb, ${theme === "dark" ? colors.ambient_dark : colors.ambient_light} 62%, var(--bg))`;
  const glow = `color-mix(in srgb, ${colors.accent} 24%, ${base})`;
  return {
    background: `radial-gradient(60% 90% at 92% 0%, ${glow} 0%, transparent 70%), linear-gradient(160deg, ${base} 0%, color-mix(in srgb, ${base} 70%, var(--bg)) 100%)`,
  };
}
