"use client";

import { useState } from "react";
import { cn, initials, seedGradient } from "./utils";

export interface AvatarProps {
  name: string;
  url?: string | null;
  /** Seed for the fallback gradient (user id); defaults to name. */
  seed?: string;
  size?: number;
  className?: string;
  /** Hide from assistive tech when the name is already shown next to it. */
  decorative?: boolean;
}

export function Avatar({ name, url, seed, size = 40, className, decorative = false }: AvatarProps) {
  const [failed, setFailed] = useState(false);
  const [a, b] = seedGradient(seed ?? name, "deep");
  const style = { width: size, height: size };
  const a11y = decorative ? { "aria-hidden": true as const } : { role: "img" as const, "aria-label": name };
  if (url && !failed) {
    return (
      <span {...a11y} className={cn("inline-block shrink-0 overflow-hidden rounded-pill bg-surface-3", className)} style={style}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={url} alt="" className="h-full w-full object-cover" onError={() => setFailed(true)} />
      </span>
    );
  }
  return (
    <span
      {...a11y}
      className={cn("inline-flex shrink-0 select-none items-center justify-center rounded-pill font-semibold text-white", className)}
      style={{ ...style, backgroundImage: `linear-gradient(135deg, ${a}, ${b})`, fontSize: Math.round(size * 0.38), textShadow: "0 1px 2px rgba(0,0,0,0.45)" }}
    >
      <span aria-hidden="true">{initials(name)}</span>
    </span>
  );
}

export interface AvatarStackProps {
  people: Array<{ id: string; name: string; url?: string | null }>;
  max?: number;
  size?: number;
  className?: string;
}

export function AvatarStack({ people, max = 4, size = 32, className }: AvatarStackProps) {
  const shown = people.slice(0, max);
  const rest = people.length - shown.length;
  const names = people.map((p) => p.name).join(", ");
  return (
    <span role="img" aria-label={names} className={cn("inline-flex items-center", className)}>
      {shown.map((p, i) => (
        <span key={p.id} className="rounded-pill ring-2 ring-bg" style={{ marginLeft: i === 0 ? 0 : -size / 3 }}>
          <Avatar name={p.name} url={p.url} seed={p.id} size={size} decorative />
        </span>
      ))}
      {rest > 0 && (
        <span
          aria-hidden="true"
          className="inline-flex items-center justify-center rounded-pill bg-surface-3 font-mono text-xs text-text ring-2 ring-bg"
          style={{ width: size, height: size, marginLeft: -size / 3 }}
        >
          +{rest}
        </span>
      )}
    </span>
  );
}
