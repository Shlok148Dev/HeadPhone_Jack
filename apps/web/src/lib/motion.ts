import { useReducedMotion, type Transition } from "motion/react";
import { springs, staggerMs } from "@jingle/design-tokens";

/** Motion presets (UX_SPEC §6). Only animate transform and opacity. */
export const spring = {
  soft: { type: "spring", ...springs.soft } satisfies Transition,
  snappy: { type: "spring", ...springs.snappy } satisfies Transition,
  /** Celebrations only. */
  bouncy: { type: "spring", ...springs.bouncy } satisfies Transition,
  /** Large surfaces (sheets, shared-element to detail). */
  gentle: { type: "spring", ...springs.gentle } satisfies Transition,
} as const;

export const ease = {
  standard: [0.2, 0, 0, 1] as [number, number, number, number],
  exit: [0.3, 0, 1, 1] as [number, number, number, number],
  linear: "linear" as const,
};

/** Stagger between list children, in seconds (40 ms). At most 8 items stagger; the rest enter together. */
export const stagger = staggerMs / 1000;
export const MAX_STAGGERED = 8;

const instant: Transition = { duration: 0 };

type SpringSet = { soft: Transition; snappy: Transition; bouncy: Transition; gentle: Transition };

export interface MotionSafe {
  reduced: boolean;
  spring: SpringSet;
  stagger: number;
  /** `card.enter` props for a list item at `index`. */
  enter: (index?: number) => {
    initial: { opacity: number; y?: number; scale?: number };
    animate: { opacity: number; y?: number; scale?: number };
    transition: Transition;
  };
}

/** Returns motion presets, or instant/opacity-only transitions when the user prefers reduced motion. */
export function useMotionSafe(): MotionSafe {
  const reduced = useReducedMotion() ?? false;
  if (reduced) {
    return {
      reduced,
      spring: { soft: instant, snappy: instant, bouncy: instant, gentle: instant },
      stagger: 0,
      enter: () => ({ initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { duration: 0.12, ease: "linear" } }),
    };
  }
  return {
    reduced,
    spring,
    stagger,
    enter: (index = 0) => ({
      initial: { opacity: 0, y: 12, scale: 0.98 },
      animate: { opacity: 1, y: 0, scale: 1 },
      transition: { ...spring.soft, delay: Math.min(index, MAX_STAGGERED) * stagger },
    }),
  };
}
