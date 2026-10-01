/**
 * Jingle design tokens — the single source for web (and mobile later).
 * The CSS mirror lives in `tokens.css`; a test in apps/web asserts both stay in sync
 * and that every declared text/surface pair meets WCAG AA (4.5:1) in both themes.
 * Spec: .claude/skills/jingle-design-system/SKILL.md and docs/ux/UX_SPEC.md §7.
 */

export const brand = {
  violet: "#8B6BFF",
  cyan: "#3FE7D8",
  /** Coral. Only ever means "playing right now". */
  live: "#FF6B5E",
} as const;

export const gradientBrand = `linear-gradient(135deg, ${brand.violet} 0%, ${brand.cyan} 100%)`;

export type ThemeName = "dark" | "light";

/**
 * Solid colour tokens per theme (hex so contrast can be computed). Keys map 1:1 to CSS variables.
 * `*-soft` values are the UX spec's translucent pills pre-composited over `surface-1`.
 */
export interface ThemeColors {
  bg: string;
  "surface-1": string;
  "surface-2": string;
  "surface-3": string;
  border: string;
  "border-strong": string;
  text: string;
  "text-muted": string;
  "text-subtle": string;
  "accent-text": string;
  "on-brand": string;
  live: string;
  "live-soft": string;
  "live-text": string;
  "on-live": string;
  danger: string;
  "danger-soft": string;
  "danger-bg": string;
  "on-danger": string;
  warning: string;
  "warning-soft": string;
  success: string;
  "success-soft": string;
  "focus-ring": string;
  "focus-ring-2": string;
  skeleton: string;
}

export const themes: Record<ThemeName, ThemeColors> = {
  dark: {
    bg: "#0A090C",
    "surface-1": "#131116",
    "surface-2": "#1B181F",
    "surface-3": "#252129",
    border: "#2F2A33",
    "border-strong": "#776E7E",
    text: "#F6F3EF",
    "text-muted": "#ACA4AE",
    "text-subtle": "#968D99",
    "accent-text": "#A68CFF",
    "on-brand": "#0B0B12",
    live: brand.live,
    "live-soft": "#34201F",
    "live-text": "#FF6B5E",
    "on-live": "#1A0705",
    danger: "#FB7185",
    "danger-soft": "#341F25",
    "danger-bg": "#FB7185",
    "on-danger": "#1A0508",
    warning: "#F5B84A",
    "warning-soft": "#33291D",
    success: "#4ADE80",
    "success-soft": "#1B2E25",
    "focus-ring": "#8B6BFF",
    "focus-ring-2": "#3FE7D8",
    skeleton: "#1B181F",
  },
  light: {
    bg: "#F6F2EC",
    "surface-1": "#FFFDF9",
    "surface-2": "#EFEAE3",
    "surface-3": "#E5DED4",
    border: "#DED5C9",
    "border-strong": "#7B7266",
    text: "#17141A",
    "text-muted": "#574E5C",
    "text-subtle": "#62596A",
    "accent-text": "#5B3FD9",
    "on-brand": "#0B0B12",
    live: brand.live,
    "live-soft": "#FFF0EF",
    "live-text": "#B8401F",
    "on-live": "#1A0705",
    danger: "#BE123C",
    "danger-soft": "#F9E7EC",
    "danger-bg": "#BE123C",
    "on-danger": "#FFFFFF",
    warning: "#8A5300",
    "warning-soft": "#F1EADF",
    success: "#15803D",
    "success-soft": "#F3F8F3",
    "focus-ring": "#5B3FD9",
    "focus-ring-2": "#0E7C74",
    skeleton: "#E5DED4",
  },
};

/** Non-hex theme values (translucent), mirrored in tokens.css. */
export const themeEffects: Record<ThemeName, { "surface-glass": string; scrim: string; "skeleton-shine": string }> = {
  dark: { "surface-glass": "rgba(19,17,22,0.72)", scrim: "rgba(0,0,0,0.60)", "skeleton-shine": "rgba(255,255,255,0.06)" },
  light: { "surface-glass": "rgba(255,253,249,0.74)", scrim: "rgba(17,17,24,0.40)", "skeleton-shine": "rgba(255,255,255,0.7)" },
};

/**
 * Foreground/background pairs that carry text. Each must be >= 4.5:1 in both themes.
 * [foreground token, background token]
 */
export const contrastPairs: ReadonlyArray<readonly [keyof ThemeColors, keyof ThemeColors]> = [
  ["text", "bg"],
  ["text", "surface-1"],
  ["text", "surface-2"],
  ["text", "surface-3"],
  ["text-muted", "bg"],
  ["text-muted", "surface-1"],
  ["text-muted", "surface-2"],
  ["text-muted", "surface-3"],
  ["text-subtle", "bg"],
  ["text-subtle", "surface-1"],
  ["text-subtle", "surface-2"],
  ["text-subtle", "surface-3"],
  ["accent-text", "bg"],
  ["accent-text", "surface-1"],
  ["accent-text", "surface-2"],
  ["live-text", "bg"],
  ["live-text", "surface-1"],
  ["live-text", "surface-2"],
  ["live-text", "live-soft"],
  ["on-live", "live"],
  ["danger", "surface-1"],
  ["danger", "surface-2"],
  ["danger", "danger-soft"],
  ["on-danger", "danger-bg"],
  ["warning", "surface-1"],
  ["warning", "surface-2"],
  ["warning", "warning-soft"],
  ["success", "surface-1"],
  ["success", "success-soft"],
];

/** Text on the brand gradient endpoints (primary button label). Theme-independent. */
export const brandContrastPairs: ReadonlyArray<readonly [string, string]> = [
  ["#0B0B12", brand.violet],
  ["#0B0B12", brand.cyan],
];

export const fonts = {
  display: "Bricolage Grotesque",
  ui: "Inter",
  mono: "JetBrains Mono",
} as const;

/** Radius scale in px. */
export const radius = { sm: 8, md: 12, lg: 20, pill: 999 } as const;

/** 4 px grid. `space(4)` === 16. */
export const space = (n: number): number => n * 4;
export const spacing = { 0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 10: 40, 12: 48, 16: 64 } as const;

/** Min-width breakpoints (px). 360 is the tested floor. */
export const breakpoints = { sm: 390, md: 768, lg: 1024, xl: 1440, "2xl": 1920 } as const;

export const shadows = {
  dark: { 1: "0 1px 2px rgba(0,0,0,0.4)", 2: "0 8px 24px rgba(0,0,0,0.5)" },
  light: { 1: "0 1px 2px rgba(17,17,24,0.08)", 2: "0 8px 24px rgba(17,17,24,0.12)" },
} as const;

export const blur = { sm: 8, md: 16, glass: 20, lg: 32 } as const;

export const zIndex = {
  base: 0,
  sticky: 10,
  sidebar: 20,
  topbar: 30,
  nowPlaying: 40,
  tabbar: 41,
  popover: 50,
  sheet: 60,
  dialog: 70,
  toast: 80,
  skipLink: 90,
} as const;

/** Durations in ms. */
export const duration = { instant: 0, fast: 120, base: 200, slow: 320 } as const;

export const easing = {
  standard: "cubic-bezier(0.2, 0, 0, 1)",
  exit: "cubic-bezier(0.3, 0, 1, 1)",
  linear: "linear",
} as const;

/** Motion springs (consumed by apps/web/src/lib/motion.ts). */
export const springs = {
  soft: { stiffness: 260, damping: 30, mass: 1 },
  snappy: { stiffness: 400, damping: 32, mass: 1 },
  bouncy: { stiffness: 320, damping: 18, mass: 1 },
  gentle: { stiffness: 170, damping: 26, mass: 1 },
} as const;
export const staggerMs = 40;

export { contrastRatio, relativeLuminance, parseHex } from "./contrast";
