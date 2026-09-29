"use client";

import type { CSSProperties } from "react";
import { useReducedMotion } from "motion/react";
import { PLATFORM_NAMES, type Platform } from "./types";
import { cn, hashString } from "./utils";

export interface PlatformBadgeProps {
  platform: Platform;
  /** "pill" (default) or "inline" text for use inside sentences. */
  variant?: "pill" | "inline";
  className?: string;
}

/** Platform name as neutral TEXT. Never a logo, glyph, brand font or brand colour. UNKNOWN renders nothing. */
export function PlatformBadge({ platform, variant = "pill", className }: PlatformBadgeProps) {
  if (platform === "UNKNOWN") return null;
  if (variant === "inline") return <span className={className}>{PLATFORM_NAMES[platform]}</span>;
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-pill bg-surface-3 px-2 text-xs font-medium text-text-muted",
        className,
      )}
    >
      {PLATFORM_NAMES[platform]}
    </span>
  );
}

/** UX_SPEC §4.7: 4 bars, 0.9/1.3/1.1/1.0 s; static heights 40/100/70/55 % under reduced motion. */
const BARS = [
  { dur: 0.9, rest: 0.4 },
  { dur: 1.3, rest: 1 },
  { dur: 1.1, rest: 0.7 },
  { dur: 1.0, rest: 0.55 },
];

export interface EqualiserBarsProps {
  /** Width in px; height is 10/12 of it. */
  size?: number;
  /** Seeds a 0–300 ms start offset (e.g. card id) so SSR and client match. */
  seed?: string;
  /** Bar colour; defaults to coral. Use "currentColor" on the Live pill. */
  color?: string;
  /** When true the bars are aria-hidden; otherwise labelled "Live". */
  decorative?: boolean;
  className?: string;
}

/** Coral equaliser bars. Animated (transform only); static under reduced motion. Live only. */
export function EqualiserBars({ size = 16, seed = "", color = "var(--live)", decorative = false, className }: EqualiserBarsProps) {
  const reduced = useReducedMotion() ?? false;
  const h = Math.round((size * 10) / 12);
  const gap = size / 12;
  const w = (size - gap * 3) / 4;
  const offset = (hashString(seed) % 300) / 1000;
  return (
    <svg
      width={size}
      height={h}
      viewBox={`0 0 ${size} ${h}`}
      className={cn("shrink-0", className)}
      {...(decorative ? { "aria-hidden": true } : { role: "img", "aria-label": "Live" })}
      focusable="false"
    >
      {BARS.map((b, i) => (
        <rect
          key={i}
          x={i * (w + gap)}
          y={reduced ? h * (1 - b.rest) : 0}
          width={w}
          height={reduced ? h * b.rest : h}
          rx={Math.min(1, w / 2)}
          fill={color}
          className={reduced ? undefined : "ds-eq-bar"}
          style={reduced ? undefined : ({ "--eq-dur": `${b.dur}s`, "--eq-delay": `${-(offset + i * 0.17).toFixed(2)}s` } as CSSProperties)}
        />
      ))}
    </svg>
  );
}

export interface LiveBadgeProps {
  size?: "sm" | "md" | "lg";
  seed?: string;
  className?: string;
}

/** Coral "LIVE" pill with equaliser bars. Render ONLY for state === "LIVE" (and not degraded). */
export function LiveBadge({ size = "md", seed, className }: LiveBadgeProps) {
  return (
    <span
      role="img"
      aria-label="Live"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-pill bg-live px-2 font-bold uppercase tracking-[0.06em] text-on-live",
        size === "sm" && "h-[18px] text-[10px]",
        size === "md" && "h-[22px] text-[11px]",
        size === "lg" && "h-7 text-xs",
        className,
      )}
    >
      <EqualiserBars decorative size={12} seed={seed} color="currentColor" />
      <span aria-hidden="true">Live</span>
    </span>
  );
}

/** Amber "delayed" tag for degraded cards (separate from the label). */
export function DelayedTag({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-pill bg-warning-soft px-2 py-0.5 font-mono text-[11px] font-medium text-warning",
        className,
      )}
    >
      delayed
    </span>
  );
}
