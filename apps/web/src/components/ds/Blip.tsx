"use client";

import { useId } from "react";
import { useReducedMotion } from "motion/react";
import { cn } from "./utils";

export type BlipPose = "idle" | "wave" | "cheer" | "sleepy";

const POSE_LABEL: Record<BlipPose, string> = {
  idle: "Blip, the Jingle mascot",
  wave: "Blip waving",
  cheer: "Blip cheering",
  sleepy: "Blip, sleepy",
};

export interface BlipProps {
  pose?: BlipPose;
  size?: number;
  className?: string;
  /** Decorative when the surrounding copy already says everything. */
  decorative?: boolean;
}

/** Blip: an original rounded music-note blob with eyes. Subtle idle bob; static under reduced motion. */
export function Blip({ pose = "idle", size = 96, className, decorative = false }: BlipProps) {
  const reduced = useReducedMotion() ?? false;
  const gid = `blip-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const ink = "#15121F";
  const a11y = decorative ? { "aria-hidden": true as const } : { role: "img" as const, "aria-label": POSE_LABEL[pose] };

  return (
    <svg width={size} height={size} viewBox="0 0 120 120" className={cn("shrink-0 overflow-visible", className)} data-pose={pose} focusable="false" {...a11y}>
      <defs>
        <linearGradient id={gid} x1="20" y1="110" x2="100" y2="10" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#8B6BFF" />
          <stop offset="1" stopColor="#3FE7D8" />
        </linearGradient>
      </defs>
      <g className={reduced || pose === "sleepy" ? undefined : "ds-blip-bob"}>
        {/* Ground shadow */}
        <ellipse cx="56" cy="113" rx="30" ry="4" fill="currentColor" opacity="0.12" />

        {/* Arms (behind body) */}
        {pose === "idle" && (
          <g stroke={`url(#${gid})`} strokeWidth="7" strokeLinecap="round" fill="none">
            <path d="M24 84 Q16 92 18 100" />
            <path d="M86 88 Q94 96 92 102" />
          </g>
        )}
        {pose === "wave" && (
          <g stroke={`url(#${gid})`} strokeWidth="7" strokeLinecap="round" fill="none">
            <path d="M26 74 Q12 62 14 46" />
            <path d="M86 88 Q94 96 92 102" />
          </g>
        )}
        {pose === "cheer" && (
          <g stroke={`url(#${gid})`} strokeWidth="7" strokeLinecap="round" fill="none">
            <path d="M26 72 Q14 58 12 42" />
            <path d="M86 70 Q100 58 104 44" />
          </g>
        )}
        {pose === "sleepy" && (
          <g stroke={`url(#${gid})`} strokeWidth="7" strokeLinecap="round" fill="none">
            <path d="M26 90 Q24 98 30 102" />
            <path d="M84 92 Q86 100 80 104" />
          </g>
        )}

        {/* Note stem + flag */}
        <path d="M80 70 L80 16 Q80 10 86 12 Q104 18 108 34 Q100 28 88 28 L88 70 Z" fill={`url(#${gid})`} />
        {/* Note head body (the blob) */}
        <path
          d="M56 50 C78 48 90 60 88 80 C86 100 70 110 52 108 C32 106 20 94 22 78 C24 60 38 51 56 50 Z"
          fill={`url(#${gid})`}
        />
        {/* Soft highlight */}
        <ellipse cx="42" cy="64" rx="10" ry="6" fill="#FFFFFF" opacity="0.22" transform="rotate(-20 42 64)" />

        {/* Face */}
        {pose === "sleepy" ? (
          <g stroke={ink} strokeWidth="3" strokeLinecap="round" fill="none">
            <path d="M38 80 Q43 84 48 80" />
            <path d="M60 80 Q65 84 70 80" />
          </g>
        ) : pose === "cheer" ? (
          <g stroke={ink} strokeWidth="3" strokeLinecap="round" fill="none">
            <path d="M38 80 Q43 73 48 80" />
            <path d="M60 80 Q65 73 70 80" />
          </g>
        ) : (
          <g>
            <ellipse cx="43" cy="78" rx="5.5" ry="7" fill="#FFFFFF" />
            <ellipse cx="65" cy="78" rx="5.5" ry="7" fill="#FFFFFF" />
            <circle cx={pose === "wave" ? 42 : 44} cy="79" r="3.2" fill={ink} />
            <circle cx={pose === "wave" ? 64 : 66} cy="79" r="3.2" fill={ink} />
            <circle cx={pose === "wave" ? 41 : 43} cy="77.6" r="1" fill="#FFFFFF" />
            <circle cx={pose === "wave" ? 63 : 65} cy="77.6" r="1" fill="#FFFFFF" />
          </g>
        )}

        {/* Cheeks */}
        <circle cx="34" cy="90" r="4" fill="#FF9EC7" opacity="0.55" />
        <circle cx="74" cy="90" r="4" fill="#FF9EC7" opacity="0.55" />

        {/* Mouth */}
        {pose === "cheer" ? (
          <path d="M47 89 Q54 99 61 89 Z" fill={ink} />
        ) : pose === "sleepy" ? (
          <ellipse cx="54" cy="92" rx="2.5" ry="2" fill={ink} />
        ) : (
          <path d="M48 90 Q54 95 60 90" stroke={ink} strokeWidth="3" strokeLinecap="round" fill="none" />
        )}

        {/* Extras */}
        {pose === "cheer" && (
          <g fill="#3FE7D8">
            <path d="M18 24 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2z" />
            <path d="M100 8 l1.5 4 4 1.5 -4 1.5 -1.5 4 -1.5 -4 -4 -1.5 4 -1.5z" fill="#8B6BFF" />
          </g>
        )}
        {pose === "sleepy" && (
          <g fill="currentColor" opacity="0.7" fontFamily="var(--font-jetbrains), monospace" fontWeight="700">
            <text x="98" y="56" fontSize="12">z</text>
            <text x="106" y="44" fontSize="9">z</text>
          </g>
        )}
      </g>
    </svg>
  );
}
