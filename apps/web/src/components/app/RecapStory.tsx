"use client";

import { AnimatePresence } from "motion/react";
import * as motion from "motion/react-m";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Artwork, Blip, IconButton, Icons } from "@/components/ds";
import { useMotionSafe } from "@/lib/motion";
import type { RecapData } from "@/lib/trust";
import { monthName } from "./RecapCard";

const SLIDE_MS = 5200;

/**
 * Monthly recap as a full-screen story (D-SIG-05): progress bars, tap right/left (or ←/→),
 * hold to pause, Esc to close. Real covers; the room light comes from the top track's colours.
 */
export function RecapStory({ data, name, onClose }: { data: RecapData; name?: string; onClose: () => void }) {
  const m = useMotionSafe();
  const top = data.top_tracks[0];
  const colors = top?.artwork_colors;
  const dark = typeof document === "undefined" || document.documentElement.dataset.theme !== "light";
  const base = colors ? (dark ? colors.ambient_dark : colors.ambient_light) : "var(--surface-2)";
  const slides: { key: string; label: string; body: ReactNode }[] = [
    {
      key: "intro",
      label: `${name ? `${name}'s` : "Your"} ${monthName(data.month)}`,
      body: (
        <div className="flex flex-col items-start gap-4">
          <p className="font-mono text-sm uppercase tracking-[0.2em] text-text-muted">{name ? `${name}'s` : "Your"} {monthName(data.month)}</p>
          <p className="font-display text-[clamp(4rem,18vw,9rem)] font-semibold leading-[0.9] tracking-tight">{data.minutes.toLocaleString()}</p>
          <p className="text-2xl">minutes of music (estimated). {data.plays.toLocaleString()} plays.</p>
        </div>
      ),
    },
    data.top_artists[0] && {
      key: "artist",
      label: "Top artist",
      body: (
        <div className="flex flex-col items-start gap-5">
          <p className="font-mono text-sm uppercase tracking-[0.2em] text-text-muted">Your top artist</p>
          <div className="jg-art-glow h-56 w-56 overflow-hidden rounded-full" style={colors ? { ["--art" as string]: colors.accent } : undefined}>
            <Artwork url={data.top_artists[0].image_url ?? null} seed={data.top_artists[0].name} alt="" rounded="none" />
          </div>
          <p className="font-display text-5xl font-semibold tracking-tight">{data.top_artists[0].name}</p>
          <p className="font-mono text-sm text-text-muted">{data.top_artists[0].plays} plays</p>
        </div>
      ),
    },
    data.top_tracks.length > 0 && {
      key: "tracks",
      label: "Top songs",
      body: (
        <div className="flex w-full flex-col gap-4">
          <p className="font-mono text-sm uppercase tracking-[0.2em] text-text-muted">Your top songs</p>
          <ol className="flex flex-col gap-3">
            {data.top_tracks.slice(0, 5).map((t, i) => (
              <motion.li
                key={`${t.title}${t.artist}`}
                className="flex items-center gap-4"
                initial={m.reduced ? false : { opacity: 0, x: 24 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ ...m.spring.soft, delay: m.reduced ? 0 : 0.1 + i * 0.07 }}
              >
                <span className="w-6 font-mono text-lg text-text-muted">{i + 1}</span>
                <span className="h-16 w-16 shrink-0 overflow-hidden rounded-[4px]">
                  <Artwork url={t.artwork_small ?? t.artwork_url ?? null} seed={`${t.artist}|${t.title}`} alt="" rounded="none" />
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-xl font-semibold">{t.title}</span>
                  <span className="block truncate text-text-muted">{t.artist}</span>
                </span>
              </motion.li>
            ))}
          </ol>
        </div>
      ),
    },
    {
      key: "social",
      label: "With friends",
      body: (
        <div className="flex flex-col items-start gap-6">
          <p className="font-mono text-sm uppercase tracking-[0.2em] text-text-muted">With your friends</p>
          {[
            [data.sends, "songs you sent"],
            [data.received, "songs sent to you"],
            [data.battle_wins, data.battle_wins === 1 ? "battle won" : "battles won"],
          ].map(([n, l]) => (
            <p key={l as string} className="flex items-baseline gap-4">
              <span className="font-display text-7xl font-semibold tracking-tight">{n as number}</span>
              <span className="text-xl text-text-muted">{l as string}</span>
            </p>
          ))}
          {data.top_genre && <p className="text-xl">Mostly <span className="font-semibold">{data.top_genre}</span>.</p>}
        </div>
      ),
    },
    {
      key: "end",
      label: "See you next month",
      body: (
        <div className="flex flex-col items-start gap-4">
          <Blip pose="cheer" size={120} decorative />
          <p className="font-display text-5xl font-semibold tracking-tight">That was {monthName(data.month).split(" ")[0]}.</p>
          <p className="text-xl text-text-muted">Share it from the recap card, or keep it to yourself.</p>
        </div>
      ),
    },
  ].filter(Boolean) as { key: string; label: string; body: ReactNode }[];

  const [i, setI] = useState(0);
  const [paused, setPaused] = useState(false);
  const [progress, setProgress] = useState(0);
  const start = useRef(performance.now());
  const close = useRef<HTMLButtonElement>(null);

  const go = useCallback(
    (d: number) => {
      setI((x) => {
        const n = x + d;
        if (n >= slides.length) {
          onClose();
          return x;
        }
        return Math.max(0, n);
      });
      setProgress(0);
      start.current = performance.now();
    },
    [slides.length, onClose],
  );

  useEffect(() => close.current?.focus(), []);
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
      else if (e.key === " ") {
        e.preventDefault();
        setPaused((p) => !p);
      }
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [go, onClose]);
  useEffect(() => {
    if (paused || m.reduced) return; // reduced motion: no auto-advance; tap or arrows
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start.current) / SLIDE_MS);
      setProgress(p);
      if (p >= 1) go(1);
      else raf = requestAnimationFrame(tick);
    };
    start.current = performance.now() - progress * SLIDE_MS;
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i, paused, m.reduced]);

  const slide = slides[i]!;
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Monthly recap, ${monthName(data.month)}`}
      className="fixed inset-0 z-[75] flex items-stretch justify-center bg-bg"
      style={{ background: `radial-gradient(120% 90% at 80% 10%, ${colors ? `color-mix(in srgb, ${colors.accent} 40%, ${base})` : base} 0%, ${base} 50%, var(--bg) 100%)` }}
    >
      <div className="relative flex w-full max-w-md flex-col px-6 pb-10 pt-6">
        <div className="flex gap-1.5" aria-hidden>
          {slides.map((s, k) => (
            <span key={s.key} className="h-1 flex-1 overflow-hidden rounded-pill bg-[color-mix(in_srgb,var(--text)_22%,transparent)]">
              <span className="block h-full origin-left bg-text" style={{ transform: `scaleX(${k < i ? 1 : k === i ? progress : 0})` }} />
            </span>
          ))}
        </div>
        <div className="mt-3 flex items-center justify-between">
          <p className="font-mono text-xs text-text-muted" aria-live="polite">
            {i + 1} of {slides.length}: {slide.label}
          </p>
          <div className="flex gap-1">
            <IconButton label={paused ? "Play" : "Pause"} variant="ghost" onClick={() => setPaused((p) => !p)}>
              <span aria-hidden className="font-mono text-xs">{paused ? "▶" : "❚❚"}</span>
            </IconButton>
            <IconButton ref={close} label="Close recap" variant="ghost" onClick={onClose}>
              <Icons.Close size={18} />
            </IconButton>
          </div>
        </div>
        <div
          className="relative flex flex-1 items-center"
          onPointerDown={() => setPaused(true)}
          onPointerUp={(e) => {
            setPaused(false);
            const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
            go(e.clientX - r.left < r.width / 3 ? -1 : 1);
          }}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={slide.key}
              className="w-full"
              initial={m.reduced ? { opacity: 0 } : { opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: m.reduced ? 0.12 : 0.36, ease: [0.22, 1, 0.36, 1] }}
            >
              {slide.body}
            </motion.div>
          </AnimatePresence>
        </div>
        <div className="flex justify-between">
          <IconButton label="Previous" variant="ghost" onClick={() => go(-1)} disabled={i === 0}>
            <Icons.ChevronLeft size={20} />
          </IconButton>
          <IconButton label={i === slides.length - 1 ? "Finish" : "Next"} variant="ghost" onClick={() => go(1)}>
            <Icons.ChevronRight size={20} />
          </IconButton>
        </div>
      </div>
    </div>
  );
}
