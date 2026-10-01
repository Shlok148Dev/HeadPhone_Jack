"use client";

import * as motion from "motion/react-m";
import { useId } from "react";
import { useMotionSafe } from "@/lib/motion";
import { Blip } from "./Blip";
import { cn } from "./utils";

export interface CompatibilityFactor {
  label: string;
  /** 0–100 contribution. */
  value: number;
  detail?: string;
}

export interface CompatibilityMeterProps {
  /** 0–100. */
  score: number;
  /** Required. A score is never shown without the reasons behind it. */
  breakdown: CompatibilityFactor[];
  label?: string;
  size?: number;
  className?: string;
}

/**
 * Score ring + required breakdown (BR-09). Without a breakdown it never shows a bare number:
 * it renders the "limited data" state instead (and warns in dev).
 */
export function CompatibilityMeter({ score, breakdown, label = "Taste match", size = 120, className }: CompatibilityMeterProps) {
  const m = useMotionSafe();
  const gid = `cm-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;

  if (!Array.isArray(breakdown) || breakdown.length === 0) {
    if (process.env.NODE_ENV !== "production") console.warn("CompatibilityMeter: refusing to render a score without a breakdown.");
    return (
      <div className={cn("flex items-center gap-4", className)} data-testid="compat-limited">
        <Blip pose="sleepy" size={56} decorative />
        <p className="max-w-xs text-sm text-text-muted">We need a couple more weeks of listening to compare you two.</p>
      </div>
    );
  }

  const pct = Math.max(0, Math.min(100, Math.round(score)));
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;

  return (
    <figure className={cn("flex flex-col items-center gap-5 sm:flex-row sm:items-start", className)}>
      <div
        className="relative shrink-0"
        style={{ width: size, height: size }}
        role="img"
        aria-label={`${label} ${pct} out of 100`}
      >
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true" focusable="false" className="-rotate-90">
          <defs>
            <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="var(--brand-violet)" />
              <stop offset="1" stopColor="var(--brand-cyan)" />
            </linearGradient>
          </defs>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-3)" strokeWidth={stroke} />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={`url(#${gid})`}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            initial={{ strokeDashoffset: m.reduced ? c * (1 - pct / 100) : c }}
            animate={{ strokeDashoffset: c * (1 - pct / 100) }}
            transition={m.reduced ? { duration: 0 } : { ...m.spring.soft, delay: 0.1 }}
          />
        </svg>
        <div aria-hidden="true" className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-4xl font-semibold leading-none text-text">{pct}</span>
          <span className="mt-1 font-mono text-[11px] text-text-muted">/ 100</span>
        </div>
      </div>
      <figcaption className="w-full min-w-0 flex-1">
        <p className="mb-2 font-mono text-xs text-text-muted">{label}</p>
        <ul className="flex flex-col gap-2.5">
          {breakdown.slice(0, 3).map((f) => (
            <li key={f.label} className="flex flex-col gap-1">
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="text-text">{f.label}</span>
                <span className="font-mono text-xs text-text-muted">{Math.round(f.value)}</span>
              </div>
              <span aria-hidden="true" className="block h-1.5 overflow-hidden rounded-pill bg-surface-3">
                <span className="block h-full rounded-pill bg-gradient-brand" style={{ width: `${Math.max(0, Math.min(100, f.value))}%` }} />
              </span>
              {f.detail && <span className="text-xs text-text-muted">{f.detail}</span>}
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}
