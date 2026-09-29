"use client";

import { useId, useState } from "react";
import { cn, hashString, prng } from "./utils";

export type CoverPattern = "orbs" | "rings" | "stripes" | "waves" | "grid";

export type CoverShape =
  | { kind: "circle"; cx: number; cy: number; r: number; fill: string; opacity: number }
  | { kind: "ring"; cx: number; cy: number; r: number; stroke: string; width: number; opacity: number }
  | { kind: "rect"; x: number; y: number; w: number; h: number; rotate: number; fill: string; opacity: number }
  | { kind: "path"; d: string; stroke: string; width: number; opacity: number };

export interface CoverSpec {
  pattern: CoverPattern;
  angle: number;
  colors: [string, string, string];
  shapes: CoverShape[];
}

const PATTERNS: CoverPattern[] = ["orbs", "rings", "stripes", "waves", "grid"];
/** Palette harmonies: hue offsets for [second, third] colour. */
const HARMONIES: Array<[number, number]> = [
  [30, 60], // analogous
  [150, 210], // split complementary
  [120, 240], // triadic
  [180, 30], // complementary + accent
  [-40, 40], // warm/cool spread
];

const r1 = (n: number) => Math.round(n * 10) / 10;

/** Hues 0–20° read as Live coral; shift them so a cover never looks Live. */
const safeHue = (h: number) => {
  const x = ((h % 360) + 360) % 360;
  return x <= 20 ? x + 28 : x;
};

/** Pure, deterministic cover recipe for a seed (e.g. a recording id). */
export function generateCover(seed: string): CoverSpec {
  const h = hashString(seed || "jingle");
  const rand = prng(h);
  const hue = Math.floor(rand() * 360);
  const [o1, o2] = HARMONIES[Math.floor(rand() * HARMONIES.length)]!;
  const sat = 62 + Math.floor(rand() * 25);
  const colors: [string, string, string] = [
    `hsl(${safeHue(hue)} ${sat}% ${30 + Math.floor(rand() * 16)}%)`,
    `hsl(${safeHue(hue + o1)} ${sat}% ${50 + Math.floor(rand() * 14)}%)`,
    `hsl(${safeHue(hue + o2)} ${Math.min(95, sat + 10)}% ${62 + Math.floor(rand() * 14)}%)`,
  ];
  const pattern = PATTERNS[Math.floor(rand() * PATTERNS.length)]!;
  const angle = Math.floor(rand() * 360);
  const shapes: CoverShape[] = [];
  const pick = () => colors[1 + Math.floor(rand() * 2)]!;

  switch (pattern) {
    case "orbs": {
      const n = 3 + Math.floor(rand() * 3);
      for (let i = 0; i < n; i++)
        shapes.push({ kind: "circle", cx: r1(rand() * 100), cy: r1(rand() * 100), r: r1(12 + rand() * 30), fill: pick(), opacity: r1(0.45 + rand() * 0.45) });
      break;
    }
    case "rings": {
      const cx = r1(20 + rand() * 60);
      const cy = r1(20 + rand() * 60);
      const n = 4 + Math.floor(rand() * 4);
      for (let i = 0; i < n; i++)
        shapes.push({ kind: "ring", cx, cy, r: r1(8 + i * (8 + rand() * 6)), stroke: pick(), width: r1(2 + rand() * 5), opacity: r1(0.5 + rand() * 0.5) });
      break;
    }
    case "stripes": {
      const n = 4 + Math.floor(rand() * 4);
      const rotate = Math.floor(rand() * 180);
      for (let i = 0; i < n; i++)
        shapes.push({ kind: "rect", x: -20, y: r1(-20 + i * (140 / n)), w: 140, h: r1(4 + rand() * 12), rotate, fill: pick(), opacity: r1(0.4 + rand() * 0.5) });
      break;
    }
    case "waves": {
      const n = 3 + Math.floor(rand() * 3);
      for (let i = 0; i < n; i++) {
        const y = 20 + i * (70 / n) + rand() * 8;
        const a = 6 + rand() * 14;
        const d = `M -5 ${r1(y)} C 25 ${r1(y - a)}, 45 ${r1(y + a)}, 70 ${r1(y)} S 100 ${r1(y - a)}, 110 ${r1(y)}`;
        shapes.push({ kind: "path", d, stroke: pick(), width: r1(3 + rand() * 6), opacity: r1(0.55 + rand() * 0.4) });
      }
      break;
    }
    case "grid": {
      const cells = 3 + Math.floor(rand() * 2);
      const size = 100 / cells;
      for (let x = 0; x < cells; x++)
        for (let y = 0; y < cells; y++)
          if (rand() > 0.45)
            shapes.push({ kind: "circle", cx: r1(size * x + size / 2), cy: r1(size * y + size / 2), r: r1(size * (0.18 + rand() * 0.28)), fill: pick(), opacity: r1(0.55 + rand() * 0.4) });
      break;
    }
  }
  return { pattern, angle, colors, shapes };
}

export interface GenerativeCoverProps {
  seed: string;
  /** Accessible label; omit for decorative use. */
  label?: string;
  className?: string;
  rounded?: "sm" | "md" | "lg" | "none";
}

/** Deterministic gradient + shapes artwork. Never a grey placeholder. */
export function GenerativeCover({ seed, label, className, rounded = "md" }: GenerativeCoverProps) {
  const spec = generateCover(seed);
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const gid = `gc-${uid}`;
  const rad = (spec.angle * Math.PI) / 180;
  const x2 = r1(50 + Math.cos(rad) * 50);
  const y2 = r1(50 + Math.sin(rad) * 50);
  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="xMidYMid slice"
      className={cn(
        "block aspect-square w-full overflow-hidden",
        rounded === "sm" && "rounded-sm",
        rounded === "md" && "rounded-md",
        rounded === "lg" && "rounded-lg",
        className,
      )}
      data-seed={seed}
      data-pattern={spec.pattern}
      {...(label ? { role: "img", "aria-label": label } : { "aria-hidden": true })}
      focusable="false"
    >
      <defs>
        <linearGradient id={gid} x1={r1(100 - x2)} y1={r1(100 - y2)} x2={x2} y2={y2} gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor={spec.colors[0]} />
          <stop offset="1" stopColor={spec.colors[1]} />
        </linearGradient>
      </defs>
      <rect width="100" height="100" fill={`url(#${gid})`} />
      {spec.shapes.map((s, i) => {
        switch (s.kind) {
          case "circle":
            return <circle key={i} cx={s.cx} cy={s.cy} r={s.r} fill={s.fill} opacity={s.opacity} />;
          case "ring":
            return <circle key={i} cx={s.cx} cy={s.cy} r={s.r} fill="none" stroke={s.stroke} strokeWidth={s.width} opacity={s.opacity} />;
          case "rect":
            return <rect key={i} x={s.x} y={s.y} width={s.w} height={s.h} fill={s.fill} opacity={s.opacity} transform={`rotate(${s.rotate} 50 50)`} />;
          case "path":
            return <path key={i} d={s.d} fill="none" stroke={s.stroke} strokeWidth={s.width} strokeLinecap="round" opacity={s.opacity} />;
        }
      })}
    </svg>
  );
}

export interface ArtworkProps {
  url?: string | null;
  /** Seed for the generative fallback (recording id, or title+artist). */
  seed: string;
  alt: string;
  className?: string;
  rounded?: "sm" | "md" | "lg" | "none";
}

/** Artwork image with a GenerativeCover fallback (missing url or load error). */
export function Artwork({ url, seed, alt, className, rounded = "md" }: ArtworkProps) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  if (!url || failed) return <GenerativeCover seed={seed} label={alt || undefined} className={className} rounded={rounded} />;
  const round = cn(rounded === "sm" && "rounded-sm", rounded === "md" && "rounded-md", rounded === "lg" && "rounded-lg");
  // The generative cover paints first (never grey); the image fades in over it once loaded.
  return (
    <span className={cn("relative block aspect-square w-full overflow-hidden", round, className)}>
      <GenerativeCover seed={seed} rounded="none" className="absolute inset-0 h-full" />
      {/* eslint-disable-next-line @next/next/no-img-element -- remote artwork hosts vary; plain img keeps the fallback simple */}
      <img
        src={url}
        alt={alt}
        loading="lazy"
        decoding="async"
        onLoad={() => setLoaded(true)}
        onError={() => setFailed(true)}
        className={cn("absolute inset-0 h-full w-full object-cover motion-safe:transition-opacity motion-safe:duration-200", loaded ? "opacity-100" : "opacity-0")}
      />
    </span>
  );
}
