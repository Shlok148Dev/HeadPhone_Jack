"use client";

import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState, type ReactNode } from "react";
import { Artwork, Blip, ButtonLink, EqualiserBars, FeedCard, Icons, Pulse, type FeedCardData } from "@/components/ds";
import type { WallCover } from "./data";

const EASE = [0.22, 1, 0.36, 1] as const;
const FRIENDS = ["Aanya", "Kabir", "Meera", "Dev", "Zoya", "Ishaan", "Riya", "Arjun", "Tara", "Sana"];

/** Opening wall: real covers drifting in columns, with friends' Pulse rings between them. */
export function CoverWall({ covers }: { covers: WallCover[] }) {
  const reduced = useReducedMotion() ?? false;
  const cols = 5;
  const columns = Array.from({ length: cols }, (_, c) => {
    const items: ({ kind: "cover"; c: WallCover } | { kind: "friend"; name: string; live: boolean })[] = [];
    for (let i = 0; i < 7; i++) {
      const idx = (c * 7 + i) % Math.max(1, covers.length);
      if ((c + i) % 4 === 1) items.push({ kind: "friend", name: FRIENDS[(c * 3 + i) % FRIENDS.length]!, live: (c + i) % 3 !== 0 });
      else items.push({ kind: "cover", c: covers[idx] ?? { url: "", url_small: "", color: null, label: `${c}-${i}` } });
    }
    return items;
  });
  return (
    <div className="group relative h-[520px] overflow-hidden md:h-[640px]" aria-hidden>
      <div className="grid h-full grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-5">
        {columns.map((col, c) => (
          <div
            key={c}
            className={`flex flex-col gap-3 ${c >= 3 ? "hidden sm:flex" : ""} ${c >= 4 ? "sm:hidden lg:flex" : ""} ${reduced ? "" : "jg-drift group-hover:[animation-play-state:paused]"}`}
            style={{ animationDuration: `${38 + c * 6}s`, animationDirection: c % 2 ? "reverse" : "normal", marginTop: c % 2 ? -60 : 0 }}
          >
            {[...col, ...col].map((it, i) =>
              it.kind === "cover" ? (
                <div key={i} className="jg-art-glow aspect-square shrink-0 overflow-hidden rounded-[8px]" style={{ ["--art" as string]: it.c.color ?? "#000" }}>
                  <Artwork url={it.c.url_small || it.c.url || null} seed={it.c.label} alt="" rounded="none" />
                </div>
              ) : (
                <div key={i} className="flex aspect-square shrink-0 flex-col items-center justify-center gap-2 rounded-[12px] border border-border bg-surface-1">
                  <Pulse state={it.live ? "live" : "recent"} name={it.name} seed={it.name} size={44} />
                  <span className="text-xs font-medium">{it.name}</span>
                  {it.live ? <EqualiserBars size={14} seed={it.name} decorative /> : <span className="font-mono text-[10px] text-text-muted">2 h ago</span>}
                </div>
              ),
            )}
          </div>
        ))}
      </div>
      <div className="pointer-events-none absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-[var(--bg)] to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[var(--bg)] to-transparent" />
    </div>
  );
}

/** Scroll-driven reveal (CSS, no JS); `step` staggers by shifting the scroll range. */
export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  const off = Math.round(delay * 200); // 0.035 s → ~7 % of the entry range
  return (
    <div className={`jg-reveal ${className ?? ""}`} style={{ ["--r0" as string]: `${off}%`, ["--r1" as string]: `${45 + off}%` }}>
      {children}
    </div>
  );
}

/** "Your friends, live": real covers, the Pulse, honest times. */
export function LiveFeedDemo({ covers }: { covers: WallCover[] }) {
  const rows: [string, string, string, string, "LIVE" | "RECENT", string][] = [
    ["Aanya", "Kesariya", "Arijit Singh", "SPOTIFY", "LIVE", "Live on Spotify"],
    ["Meera", "cold/mess", "Prateek Kuhad", "APPLE_MUSIC", "RECENT", "2 h ago on Apple Music"],
    ["Dev", "Excuses", "AP Dhillon", "YOUTUBE_MUSIC", "LIVE", "Live on YouTube Music"],
    ["Zoya", "Creep", "Radiohead", "AMAZON_MUSIC", "RECENT", "20 min ago on Amazon Music"],
  ];
  const k = (x: string) => x.toLowerCase().replace(/[^a-z0-9]/g, "");
  const find = (t: string) => covers.find((c) => k(c.label) === k(t));
  const cards: FeedCardData[] = rows.map(([name, title, artist, platform, state, label], i) => ({
    friend: { id: `ex-${name}`, username: name.toLowerCase(), display_name: name, avatar_url: null },
    state,
    platform: platform as FeedCardData["platform"],
    recording: { id: `ex-${i}`, title, artist, artwork_url: find(title)?.url ?? null, links: {} },
    freshness_label: label,
    degraded: false,
    attribution: null,
  }));
  return (
    <ul className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {cards.map((c, i) => (
        <li key={c.friend.id}>
          <Reveal delay={i * 0.035}>
            <FeedCard card={c} sharedLayout={false} />
          </Reveal>
        </li>
      ))}
    </ul>
  );
}

/** "One button per app": each presses into Connected, one after another. */
export function ConnectDemo() {
  const reduced = useReducedMotion() ?? false;
  const apps = ["Spotify", "Apple Music", "YouTube Music", "Amazon Music"];
  const [done, setDone] = useState(reduced ? apps.length : 0);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    if (!seen || reduced || done >= apps.length) return;
    const t = setTimeout(() => setDone((d) => d + 1), 520);
    return () => clearTimeout(t);
  }, [seen, done, reduced, apps.length]);
  return (
    <motion.ul className="grid grid-cols-2 gap-3 md:grid-cols-4" onViewportEnter={() => setSeen(true)} viewport={{ once: true }}>
      {apps.map((a, i) => {
        const on = i < done;
        return (
          <li key={a} className="flex min-h-24 flex-col justify-between rounded-[12px] border border-border bg-surface-1 p-4">
            <span className="text-sm font-semibold">{a}</span>
            <motion.span
              animate={on ? { scale: [1, 0.96, 1] } : {}}
              transition={{ duration: 0.22, ease: EASE }}
              className={`inline-flex min-h-9 w-fit items-center gap-1.5 rounded-pill px-3 text-xs font-semibold ${on ? "bg-success-soft text-success" : "bg-surface-3 text-text-muted"}`}
            >
              {on ? <><Icons.Check size={14} /> Connected</> : `Connect ${a}`}
            </motion.span>
          </li>
        );
      })}
    </motion.ul>
  );
}

/** "Taste, explained": two people's artists as constellations, overlapping where they meet. */
export function ConstellationDemo({ covers }: { covers: WallCover[] }) {
  const pick = (n: number, off: number) => Array.from({ length: n }, (_, i) => covers[(off + i * 3) % Math.max(1, covers.length)]);
  const left = pick(5, 1);
  const right = pick(5, 2);
  const shared = pick(3, 5);
  const star = (c: WallCover | undefined, x: number, y: number, s: number, d: number) => (
    <div
      className="jg-reveal jg-art-glow absolute overflow-hidden rounded-full"
      style={{ left: `${x}%`, top: `${y}%`, width: s, height: s, ["--art" as string]: c?.color ?? "#000", ["--r0" as string]: `${Math.round(d * 60)}%`, ["--r1" as string]: `${50 + Math.round(d * 60)}%` }}
    >
      <Artwork url={c?.url_small || null} seed={c?.label ?? `${x}${y}`} alt="" rounded="none" />
    </div>
  );
  return (
    <div className="grid items-center gap-8 md:grid-cols-[1.2fr_1fr]">
      <div className="relative h-72" aria-hidden>
        {/* Two overlapping fields: you (left), Aanya (right); shared artists sit in the overlap. */}
        <div className="absolute left-[6%] top-[4%] h-[92%] w-[56%] rounded-full border border-border bg-[color-mix(in_srgb,var(--brand-violet)_6%,transparent)]" />
        <div className="absolute right-[6%] top-[4%] h-[92%] w-[56%] rounded-full border border-border bg-[color-mix(in_srgb,var(--brand-cyan)_6%,transparent)]" />
        <span className="absolute left-[10%] top-0 font-mono text-[11px] text-text-muted">You</span>
        <span className="absolute right-[10%] top-0 font-mono text-[11px] text-text-muted">Aanya</span>
        {left.map((c, i) => star(c, [10, 22, 8, 24, 16][i]!, [20, 36, 52, 66, 80][i]!, 40, i * 0.04))}
        {right.map((c, i) => star(c, [80, 70, 84, 68, 76][i]!, [18, 34, 50, 66, 80][i]!, 40, 0.2 + i * 0.04))}
        {shared.map((c, i) => star(c, [43, 47, 41][i]!, [18, 42, 66][i]!, 54, 0.45 + i * 0.06))}
      </div>
      <div className="flex flex-col gap-3">
        <p className="font-display text-6xl font-semibold tracking-tight">82</p>
        <p className="text-sm text-text-muted">Taste match, Aanya and you. Always with the reasons:</p>
        <ul className="flex flex-col gap-2 text-sm">
          <li className="rounded-[12px] bg-surface-1 px-4 py-3"><span className="font-mono text-xs text-text-muted">Artists · 78</span><br />9 of your top artists are hers too</li>
          <li className="rounded-[12px] bg-surface-1 px-4 py-3"><span className="font-mono text-xs text-text-muted">Genres · 86</span><br />Bollywood, indie pop, acoustic</li>
          <li className="rounded-[12px] bg-surface-1 px-4 py-3"><span className="font-mono text-xs text-text-muted">Sound</span><br />Sound comparison unavailable. We say so.</li>
        </ul>
      </div>
    </div>
  );
}

/** "Rituals": the Sunday podium rises 3, 2, 1. */
export function PodiumDemo({ covers }: { covers: WallCover[] }) {
  const order = [
    { rank: 2, c: covers[3], h: 96, who: "Kabir" },
    { rank: 1, c: covers[7], h: 140, who: "Aanya" },
    { rank: 3, c: covers[11], h: 70, who: "Dev" },
  ];
  return (
    <div className="flex items-end justify-center gap-4" aria-hidden>
      {order.map((p) => (
        <div
          key={p.rank}
          className="jg-reveal flex w-28 flex-col items-center gap-2"
          style={{ ["--r0" as string]: `${(3 - p.rank) * 18}%`, ["--r1" as string]: `${45 + (3 - p.rank) * 18}%` }}
        >
          <div className="jg-art-glow h-24 w-24 overflow-hidden rounded-[8px]" style={{ ["--art" as string]: p.c?.color ?? "#000" }}>
            <Artwork url={p.c?.url_small || null} seed={`podium${p.rank}`} alt="" rounded="none" />
          </div>
          <span className="text-xs font-semibold">{p.who}</span>
          <div className={`flex w-full items-start justify-center rounded-t-[12px] pt-2 font-display text-2xl font-semibold ${p.rank === 1 ? "bg-gradient-brand text-[var(--on-brand)]" : "bg-surface-3"}`} style={{ height: p.h }}>
            {p.rank}
          </div>
        </div>
      ))}
    </div>
  );
}

export function FinalBlip() {
  return <Blip pose="wave" size={120} decorative />;
}
