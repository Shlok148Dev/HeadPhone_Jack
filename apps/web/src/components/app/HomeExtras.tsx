"use client";

import Link from "next/link";
import { AnimatePresence } from "motion/react";
import * as motion from "motion/react-m";
import { useState, type CSSProperties } from "react";
import { Artwork, Avatar, IconButton, Icons, Shelf, type ArtworkColors } from "@/components/ds";
import { useBlends } from "@/lib/live";
import { useMotionSafe } from "@/lib/motion";
import { useInbox } from "@/lib/sends";
import { useAuth } from "@/lib/auth";
import { useRituals } from "@/lib/trust";
import { monthName } from "./RecapCard";
import { ambientStyle } from "@/lib/ambient";

interface Slide {
  id: string;
  eyebrow: string;
  title: string;
  body: string;
  href: string;
  cta: string;
  covers: string[];
  colors?: ArtworkColors | null;
}


function useTheme(): "dark" | "light" {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

/** Home hero carousel (UX_SPEC §5.4): battle results, your recap and Blends, in real covers. */
export function HomeHero() {
  const rituals = useRituals();
  const blends = useBlends();
  const theme = useTheme();
  const m = useMotionSafe();
  const [i, setI] = useState(0);

  const slides: Slide[] = [];
  for (const b of rituals.data?.battles ?? []) {
    const win = b.results?.[0];
    if (b.phase === "closed" && win && win.votes > 0)
      slides.push({
        id: `b-${b.id}`,
        eyebrow: `${b.circle.name} · weekly battle`,
        title: `${win.user.display_name} took the week`,
        body: `${win.title} by ${win.artist}, with ${win.votes} ${win.votes === 1 ? "vote" : "votes"}.`,
        href: "/rituals",
        cta: "See the podium",
        covers: b.results!.slice(0, 3).map((r) => r.artwork_url ?? r.artwork_small ?? "").filter(Boolean),
        colors: null,
      });
  }
  const recap = rituals.data?.recap;
  if (recap) {
    const top = recap.data.top_tracks[0];
    slides.push({
      id: `r-${recap.id}`,
      eyebrow: "Your monthly recap",
      title: `Your ${monthName(recap.month)}`,
      body: `About ${recap.data.minutes.toLocaleString()} minutes${recap.data.top_artists[0] ? `, mostly ${recap.data.top_artists[0].name}` : ""}.`,
      href: "/rituals?story=1#recap",
      cta: "Play your recap",
      covers: recap.data.top_tracks.slice(0, 3).map((t) => t.artwork_url ?? "").filter(Boolean),
      colors: top?.artwork_colors ?? null,
    });
  }
  for (const b of (blends.data ?? []).slice(0, 2))
    slides.push({
      id: `bl-${b.id}`,
      eyebrow: "Blend",
      title: b.name,
      body: `${b.track_count} songs, each with a reason it's there.`,
      href: `/blends/${b.id}`,
      cta: "Open the Blend",
      covers: b.covers.slice(0, 3),
      colors: null,
    });

  if (!slides.length) return null;
  const s = slides[Math.min(i, slides.length - 1)]!;
  return (
    <section aria-roledescription="carousel" aria-label="Highlights" className="relative overflow-hidden rounded-[20px]">
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={s.id}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: m.reduced ? 0 : 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="grid min-h-[220px] items-center gap-6 p-6 md:grid-cols-[1fr_auto] md:p-8"
          style={ambientStyle(s.colors, theme)}
          aria-roledescription="slide"
          aria-label={`${slides.indexOf(s) + 1} of ${slides.length}: ${s.title}`}
        >
          <div className="flex max-w-xl flex-col gap-2">
            <p className="font-mono text-xs uppercase tracking-wider text-text-muted">{s.eyebrow}</p>
            <h2 className="font-display text-3xl font-semibold leading-tight md:text-4xl">{s.title}</h2>
            <p className="text-sm text-text-muted">{s.body}</p>
            <Link
              href={s.href}
              className="mt-2 inline-flex min-h-11 w-fit items-center rounded-pill bg-text px-5 text-sm font-semibold text-bg transition-transform duration-150 hover:scale-[1.02] active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)]"
            >
              {s.cta}
            </Link>
        {slides.length > 1 && (
          <div className="mt-1 flex items-center gap-1">
            <IconButton label="Previous highlight" variant="ghost" onClick={() => setI((x) => (x - 1 + slides.length) % slides.length)}>
              <Icons.ChevronLeft size={18} />
            </IconButton>
            <span className="font-mono text-xs text-text-muted" aria-live="polite">
              {slides.indexOf(s) + 1}/{slides.length}
            </span>
            <IconButton label="Next highlight" variant="ghost" onClick={() => setI((x) => (x + 1) % slides.length)}>
              <Icons.ChevronRight size={18} />
            </IconButton>
          </div>
        )}
          </div>
          {s.covers.length > 0 && (
            <div className="relative hidden h-40 w-56 md:block" aria-hidden>
              {s.covers.slice(0, 3).map((u, k) => (
                <motion.div
                  key={u + k}
                  className="jg-art-glow absolute top-0 h-36 w-36 overflow-hidden rounded-[8px]"
                  style={{ left: k * 40, zIndex: 3 - k, top: k * 6 }}
                  initial={m.reduced ? false : { opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ ...m.spring.soft, delay: m.reduced ? 0 : k * 0.04 }}
                >
                  <Artwork url={u} seed={u} alt="" rounded="none" />
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </section>
  );
}

/** "Sent to you" and "Your Blends" shelves (UX_SPEC §5.4). */
export function HomeShelves() {
  const inbox = useInbox();
  const blends = useBlends();
  const { me } = useAuth();
  void me;
  const sent = (inbox.data ?? []).slice(0, 12);
  return (
    <>
      {sent.length > 0 && (
        <Shelf title="Sent to you" count={sent.length} itemWidth="clamp(136px, 38vw, 184px)">
          {sent.map((d) => {
            const first = d.items[0];
            return (
              <Link key={d.id} href="/inbox" className="group flex flex-col gap-2 rounded-lg p-2 hover:bg-surface-1 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]">
                <div className="jg-art-glow overflow-hidden rounded-[8px]" style={first?.artwork_colors ? ({ "--art": first.artwork_colors.accent } as CSSProperties) : undefined}>
                  <Artwork url={first?.artwork_url} seed={`${first?.artist}|${first?.title}`} alt="" rounded="none" eager tint={first?.artwork_colors?.dominant} sizes="(min-width: 1024px) 260px, 40vw" />
                </div>
                <span className="flex items-center gap-2">
                  <Avatar name={d.sender.display_name} url={d.sender.avatar_url} seed={d.sender.id} size={20} decorative />
                  <span className="truncate text-[13px] font-semibold">{d.sender.display_name}</span>
                </span>
                <span className="truncate text-[15px] font-semibold leading-tight">{d.kind === "mixtape" ? `Mixtape · ${d.items.length}` : first?.title}</span>
                {d.note ? <span className="line-clamp-2 text-[13px] text-text-muted">&ldquo;{d.note}&rdquo;</span> : <span className="truncate text-[13px] text-text-muted">{first?.artist}</span>}
              </Link>
            );
          })}
        </Shelf>
      )}
      {(blends.data ?? []).length > 0 && (
        <Shelf title="Your Blends" itemWidth="clamp(136px, 38vw, 184px)">
          {(blends.data ?? []).map((b) => (
            <Link key={b.id} href={`/blends/${b.id}`} className="flex flex-col gap-2 rounded-lg p-2 hover:bg-surface-1 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]">
              <div className="grid aspect-square grid-cols-2 gap-px overflow-hidden rounded-[8px]">
                {Array.from({ length: 4 }, (_, k) => b.covers[k] ?? b.covers[0]).map((u, k) => (
                  <Artwork key={k} url={u} seed={`${b.id}${k}`} alt="" rounded="none" />
                ))}
              </div>
              <span className="truncate text-[15px] font-semibold">{b.name}</span>
              <span className="font-mono text-xs text-text-muted">{b.track_count} songs</span>
            </Link>
          ))}
        </Shelf>
      )}
    </>
  );
}
