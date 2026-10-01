"use client";

import type { ReactNode } from "react";
import { Avatar } from "./Avatar";
import { cn } from "./utils";

export type PulseState = "live" | "recent" | "none";

export interface PulseProps {
  /** Server state only (BR-01): pass "live" just when the card's state is LIVE and not degraded. */
  state: PulseState;
  name: string;
  url?: string | null;
  seed?: string;
  size?: number;
  className?: string;
  decorative?: boolean;
  children?: ReactNode;
}

/**
 * The Pulse (docs/ux/DECISIONS.md D-SIG-01): presence readable without words.
 * - live: a coral ring that breathes (transform/opacity only; still under reduced motion).
 * - recent: a calm, still neutral ring.
 * Coral is reserved for Live; nothing else in the product uses it.
 */
export function Pulse({ state, name, url, seed, size = 32, className, decorative = true }: PulseProps) {
  const ring = Math.min(4, Math.max(2, Math.round(size / 14)));
  const gap = Math.min(4, Math.max(2, Math.round(size / 16)));
  const outer = size + (ring + gap) * 2;
  return (
    <span
      className={cn("relative inline-flex shrink-0 items-center justify-center", className)}
      style={{ width: outer, height: outer }}
      data-pulse={state}
    >
      {state !== "none" && (
        <span
          aria-hidden="true"
          className={cn("absolute inset-0 rounded-pill", state === "live" ? "jg-pulse-ring" : "")}
          style={{ boxShadow: `inset 0 0 0 ${ring}px ${state === "live" ? "var(--live)" : "var(--border-strong)"}` }}
        />
      )}
      {state === "live" && (
        <span aria-hidden="true" className="jg-pulse-halo absolute inset-0 rounded-pill" style={{ boxShadow: `0 0 0 ${ring}px var(--live)` }} />
      )}
      <Avatar name={name} url={url} seed={seed} size={size} decorative={decorative} />
    </span>
  );
}
