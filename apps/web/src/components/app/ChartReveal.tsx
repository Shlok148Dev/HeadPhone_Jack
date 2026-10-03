"use client";

import { useEffect, useRef, useState } from "react";
import { Artwork, Button, buttonClasses, cn } from "@/components/ds";
import { ambientStyle } from "@/lib/ambient";
import { useMarkChartSeen, type WeeklyCharts } from "@/lib/charts";
import { useMotionSafe } from "@/lib/motion";
import { useTheme } from "@/lib/theme";

type Final = NonNullable<WeeklyCharts["last_final"]>;

const STEP_MS = 750;

/**
 * The Monday reveal (JNG-15-03, D-CHART-06): last week's frozen top 5 counts down #5 → #1.
 * - Starts from its button, or (notification link / Replay) automatically, but only once the card is
 *   actually on screen, so the countdown is never spent off-screen.
 * - Reduced motion keeps the step-by-step countdown, just without movement.
 * - Marked seen (once per week, any device) only after #1 has been shown; Replay never marks.
 * Artwork stays whole and uncovered.
 */
export function ChartReveal({
  final,
  range,
  autoStart = false,
  replay = false,
  onDone,
}: {
  final: Final;
  range: string;
  autoStart?: boolean;
  replay?: boolean;
  onDone?: () => void;
}) {
  const { theme } = useTheme();
  const m = useMotionSafe();
  const seen = useMarkChartSeen();
  const songs = final.songs.slice(0, 5);
  const top = songs[0];
  // shown = how many ranks are revealed, counting from #5 upward (0 = none yet).
  const [shown, setShown] = useState(0);
  const [started, setStarted] = useState(false);
  const marked = useRef(false);
  const root = useRef<HTMLElement>(null);

  const markSeen = () => {
    if (marked.current || replay) return;
    marked.current = true;
    seen.mutate(final.week_start);
  };

  const start = () => setStarted(true);

  // Auto-start (notification link, Replay): bring the card into view, then start once 60% visible.
  useEffect(() => {
    if (!(autoStart || replay) || started || !root.current) return;
    const el = root.current;
    el.scrollIntoView({ block: "center", behavior: m.reduced ? "auto" : "smooth" });
    if (typeof IntersectionObserver === "undefined") {
      setStarted(true);
      return;
    }
    const io = new IntersectionObserver(
      ([e]) => {
        if (e?.isIntersecting) {
          io.disconnect();
          setStarted(true);
        }
      },
      { threshold: 0.6 },
    );
    io.observe(el);
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart, replay]);

  useEffect(() => {
    if (!started || shown >= songs.length) return;
    const t = window.setTimeout(() => setShown((n) => n + 1), shown === 0 ? 300 : STEP_MS);
    return () => window.clearTimeout(t);
  }, [started, shown, songs.length]);

  useEffect(() => {
    if (shown >= songs.length && started) markSeen();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shown, started]);

  if (!top) return null;
  const done = shown >= songs.length;

  return (
    <section
      ref={root}
      aria-labelledby="reveal-h"
      className="relative min-w-0 overflow-hidden rounded-[28px] border border-border/60"
      style={done ? ambientStyle(top.artwork_colors, theme) : { background: "var(--surface-1)" }}
    >
      <div className="flex flex-col gap-6 p-5 sm:p-8">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.14em] text-text-muted">Last week&rsquo;s final chart · {range}</p>
            <h2 id="reveal-h" className="font-display text-2xl font-semibold tracking-tight md:text-3xl">
              {replay || done ? "Your people's Song of the Week" : "Your people's Song of the Week is in"}
            </h2>
          </div>
          {done && onDone && (
            <Button
              variant="secondary"
              onClick={() => {
                markSeen();
                onDone();
              }}
            >
              Done
            </Button>
          )}
          {!started && (
            <div className="flex gap-2">
              <Button variant="inverse" onClick={start}>
                Reveal #5 → #1
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setStarted(true);
                  setShown(songs.length);
                  markSeen();
                }}
              >
                Skip
              </Button>
            </div>
          )}
        </header>

        {started && (
          <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]" aria-live="polite">
            {/* #5 → #2, revealed bottom-up */}
            <ol className="flex flex-col gap-2" aria-label="Songs 2 to 5">
              {songs
                .slice(1)
                .map((s) => s)
                .reverse()
                .map((s) => {
                  const visible = shown >= songs.length - s.rank + 1;
                  return (
                    <li
                      key={s.key}
                      className={cn("flex min-w-0 items-center gap-3 rounded-xl p-2", visible ? "jg-enter" : "")}
                      aria-hidden={!visible}
                    >
                      <span className="w-8 shrink-0 text-center font-mono text-2xl font-semibold text-text-muted">{s.rank}</span>
                      {visible ? (
                        <>
                          <div className="h-14 w-14 shrink-0 overflow-hidden rounded-[var(--r-art-sm)]">
                            <Artwork url={s.artwork_small ?? s.artwork_url ?? null} seed={`${s.artist}|${s.title}`} alt="" rounded="none" tint={s.artwork_colors?.dominant} sizes="56px" />
                          </div>
                          <div className="min-w-0">
                            <p className="truncate font-semibold">{s.title}</p>
                            <p className="truncate text-sm text-text-muted">{s.artist}</p>
                          </div>
                        </>
                      ) : (
                        <div className="h-14 flex-1 rounded-xl bg-surface-2" />
                      )}
                    </li>
                  );
                })}
            </ol>

            {/* #1 */}
            <div className="flex min-w-0 items-center gap-5">
              {done ? (
                <div className="jg-enter flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center">
                  <div className="jg-art-glow w-[min(56vw,220px)] shrink-0 overflow-hidden rounded-[var(--r-art-lg)]" style={{ ["--art" as string]: top.artwork_colors?.accent ?? "transparent" }}>
                    <Artwork url={top.artwork_url ?? null} seed={`${top.artist}|${top.title}`} alt={`${top.title} by ${top.artist}`} rounded="none" tint={top.artwork_colors?.dominant} sizes="220px" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-mono text-5xl font-semibold leading-none">#1</p>
                    <p className="mt-2 font-display text-3xl font-semibold leading-tight tracking-tight [text-wrap:balance] md:text-4xl">{top.title}</p>
                    <p className="text-text-muted">{top.artist}</p>
                    <p className="mt-2 font-mono text-xs text-text-muted">
                      {top.listeners} friends · {top.plays} plays{top.weeks && top.weeks > 1 ? ` · ${top.weeks} weeks in the top 5` : ""}
                    </p>
                    {top.you_played && <p className="mt-3 inline-flex h-7 items-center rounded-pill border border-border/70 px-3 text-xs font-medium">You helped make this #1</p>}
                    {final.artists[0] && (
                      <p className="mt-3 text-sm">
                        <span className="text-text-muted">Artist of the Week: </span>
                        <span className="font-semibold">{final.artists[0].name}</span>
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <div className={buttonClasses("secondary", "lg", "pointer-events-none h-auto w-full justify-center py-10 font-mono text-text-muted")}>#1 …</div>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
