"use client";

import { useState, type CSSProperties, type ReactNode } from "react";
import { ChartReveal } from "./ChartReveal";
import { shareChartCard } from "@/lib/shareChart";
import { Artwork, AvatarStack, Icons, PlatformMark, Skeleton, buttonClasses, cn, useToast, type Platform } from "@/components/ds";
import { ambientStyle } from "@/lib/ambient";
import { useWeeklyCharts, type ChartArtist, type ChartSong, type Movement, type WeeklyCharts as WeeklyChartsData } from "@/lib/charts";
import { useDropSong, useDropsToday } from "@/lib/drops";
import { useOpenSend } from "@/lib/send";
import type { Song } from "@/lib/sends";
import { useTheme } from "@/lib/theme";
import { tuneIn, type Tunable } from "@/lib/tunein";

/**
 * Song of the Week and Artist of the Week (JNG-15-01/02, D-CHART-01..04): the top 5 among your
 * people this week, by breadth not loops. Real counts only; artwork is never cropped or covered.
 */
export function WeeklyCharts({ myPlatform }: { myPlatform?: Platform }) {
  const q = useWeeklyCharts();
  // From the "it's in" notification (/home?reveal=1): start the countdown straight away.
  const [replaying, setReplaying] = useState(false);
  if (q.isLoading)
    return (
      <div className="flex flex-col gap-8" aria-busy="true">
        <Skeleton className="h-[420px]" rounded="lg" />
        <Skeleton className="h-[380px]" rounded="lg" />
      </div>
    );
  const c = q.data;
  if (!c || q.isError) return null;
  const lf = c.last_final;
  // Replay last week's frozen chart inline, any time (never marks anything).
  const reveal =
    replaying && lf ? <ChartReveal final={lf} range={weekRange(lf.week_start, lf.week_end)} replay onDone={() => setReplaying(false)} /> : null;
  if (!c.enough || !c.songs.length)
    return (
      <div className="flex min-w-0 flex-col gap-8">
        {reveal}
        <section aria-labelledby="charts-h" className="rounded-[24px] border border-border bg-surface-1 p-6">
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-text-muted">Song &amp; Artist of the Week</p>
          <h2 id="charts-h" className="mt-1 font-display text-2xl font-semibold tracking-tight">Your people&rsquo;s chart is warming up</h2>
          <p className="mt-2 max-w-xl text-sm text-text-muted">
            Once three or more of your friends have played music this week, the top songs and artists among you show up here, ranked by
            how many of you are into them, not by who loops hardest.
          </p>
        </section>
      </div>
    );
  const range = weekRange(c.week_start, c.week_end);
  const lastTop = lf && !lf.reveal_pending && !replaying ? lf.songs[0] : undefined;
  return (
    <div className="flex min-w-0 flex-col gap-8">
      {reveal}
      <SongOfTheWeek
        songs={c.songs}
        range={range}
        current={c.is_current}
        updated={c.updated_at}
        myPlatform={myPlatform}
        lastTop={lastTop}
        onReplay={() => setReplaying(true)}
      />
      {c.artists.length > 0 && <ArtistOfTheWeek artists={c.artists} range={range} myPlatform={myPlatform} />}
    </div>
  );
}

// ---- Song of the Week ---------------------------------------------------------------------

function SongOfTheWeek({ songs, range, current, updated, myPlatform, lastTop, onReplay }: { songs: ChartSong[]; range: string; current: boolean; updated: string | null; myPlatform?: Platform; lastTop?: ChartSong; onReplay?: () => void }) {
  const { theme } = useTheme();
  const top = songs[0]!;
  const rest = songs.slice(1);
  const openSend = useOpenSend();
  const drops = useDropsToday();
  const drop = useDropSong();
  const toast = useToast();
  const tune = tuneIn(top, myPlatform, null);
  const canDrop = drops.data?.locked === true;

  return (
    <section aria-labelledby="sotw-h" className="relative min-w-0 overflow-hidden rounded-[28px] border border-border/60" style={ambientStyle(top.artwork_colors, theme)}>
      <ChartHeader
        eyebrow="Song of the Week"
        id="sotw-h"
        title="What your people played most"
        meta={`${current ? "So far this week" : "Final"} · ${range}${updated ? ` · updated ${ago(updated)}` : ""}`}
        sub={
          lastTop ? (
            <button
              type="button"
              onClick={onReplay}
              className="inline-flex max-w-full items-center gap-1.5 rounded-md text-left underline-offset-4 hover:text-text hover:underline focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]"
            >
              <span className="truncate">
                Last week&rsquo;s #1: {lastTop.title} · {lastTop.artist}
              </span>
              <span className="shrink-0 font-medium text-text">· Replay</span>
            </button>
          ) : undefined
        }
        action={
          <button
            type="button"
            className={buttonClasses("secondary", "md", "min-h-9 gap-2 px-3 text-[13px]")}
            onClick={async () => {
              const r = await shareChartCard(songs, range);
              if (r === "failed") toast.toast({ title: "Couldn't make the image.", tone: "danger" });
              else if (r === "downloaded") toast.toast({ title: "Chart image saved", tone: "success" });
            }}
          >
            <Icons.Send size={14} /> Share
          </button>
        }
      />
      <div className="grid gap-8 px-5 pb-6 sm:px-8 md:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] md:pb-8">
        {/* #1 */}
        <div className="flex min-w-0 flex-col gap-5 sm:flex-row md:flex-col lg:flex-row">
          <div
            className="jg-art-glow w-[min(62vw,240px)] shrink-0 self-start overflow-hidden rounded-[var(--r-art-lg)] lg:w-[220px] xl:w-[250px]"
            style={{ ["--art" as string]: top.artwork_colors?.accent ?? "transparent" }}
          >
            <Artwork url={top.artwork_url ?? null} seed={`${top.artist}|${top.title}`} alt={`${top.title} by ${top.artist}`} rounded="none" tint={top.artwork_colors?.dominant} sizes="(min-width: 1280px) 250px, 240px" />
          </div>
          <div className="flex min-w-0 flex-col gap-3">
            <div className="flex items-center gap-2">
              <span className="font-mono text-4xl font-semibold leading-none tracking-tight">#1</span>
              <MovementBadge m={top.movement} />
              <Weeks n={top.weeks} />
            </div>
            <div className="min-w-0">
              <p className="line-clamp-2 font-display text-3xl font-semibold leading-[1.02] tracking-tight [text-wrap:balance] md:text-4xl">{top.title}</p>
              <p className="mt-1 truncate text-base text-text-muted">{top.artist}</p>
            </div>
            <People people={top.people} label={`${top.listeners} ${top.listeners === 1 ? "friend" : "friends"} · ${top.plays} plays`} />
            <div className="flex flex-wrap gap-2">
              {top.found_first && <Chip>{top.found_first.relationship === "self" ? "You found it first" : `${first(top.found_first.display_name)} found it first`}</Chip>}
              {top.you_played && <Chip>You helped make this #1</Chip>}
            </div>
            <div className="mt-1 flex flex-wrap gap-2">
              {tune && <TuneButton tune={tune} title={top.title} solid />}
              <button type="button" className={buttonClasses("secondary", "md", "gap-2")} onClick={() => openSend({ song: songFromChart(top) })}>
                <Icons.Send size={16} /> Send
              </button>
              {canDrop && (
                <button
                  type="button"
                  className={buttonClasses("ghost", "md", "gap-2")}
                  disabled={drop.isPending}
                  onClick={() =>
                    drop.mutate(
                      { title: top.title, artist: top.artist, recording_id: top.recording_id },
                      { onSuccess: () => toast.toast({ title: `Dropped ${top.title} as today's song`, tone: "success" }) },
                    )
                  }
                >
                  Make it your Drop
                </button>
              )}
            </div>
          </div>
        </div>

        {/* #2–#5 */}
        {rest.length > 0 && (
          <ol className="flex min-w-0 flex-col gap-1 self-start" aria-label="Songs 2 to 5">
            {rest.map((s, i) => {
              const t = tuneIn(s, myPlatform, null);
              return (
                <li
                  key={`${s.artist}|${s.title}`}
                  className="jg-enter group flex min-w-0 items-center gap-3 rounded-xl p-2 hover:bg-[color-mix(in_srgb,var(--text)_6%,transparent)]"
                  style={{ animationDelay: `${(i + 1) * 70}ms` } as CSSProperties}
                  aria-label={`Number ${s.rank}, ${s.title} by ${s.artist}, ${moveWords(s.movement)}, played by ${s.listeners} ${s.listeners === 1 ? "friend" : "friends"}`}
                >
                  <span className="w-8 shrink-0 text-center font-mono text-2xl font-semibold text-text-muted">{s.rank}</span>
                  <div className="h-14 w-14 shrink-0 overflow-hidden rounded-[var(--r-art-sm)]">
                    <Artwork url={s.artwork_small ?? s.artwork_url ?? null} seed={`${s.artist}|${s.title}`} alt="" rounded="none" tint={s.artwork_colors?.dominant} sizes="56px" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold">{s.title}</p>
                    <p className="flex min-w-0 items-center gap-2 text-sm text-text-muted">
                      <span className="truncate">{s.artist}</span>
                    </p>
                  </div>
                  <div className="hidden shrink-0 sm:block">
                    <AvatarStack size={22} max={3} people={s.people.map((p) => ({ id: p.id, name: p.display_name, url: p.avatar_url }))} />
                  </div>
                  <MovementBadge m={s.movement} />
                  <Weeks n={s.weeks} />
                  {t && <TuneButton tune={t} title={s.title} compact />}
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}

// ---- Artist of the Week -------------------------------------------------------------------

function ArtistOfTheWeek({ artists, range, myPlatform }: { artists: ChartArtist[]; range: string; myPlatform?: Platform }) {
  const { theme } = useTheme();
  const top = artists[0]!;
  const rest = artists.slice(1);
  const song = top.top_song;
  const tune = song.title ? tuneIn(song as Tunable, myPlatform, null) : null;

  return (
    <section aria-labelledby="aotw-h" className="relative min-w-0 overflow-hidden rounded-[28px] border border-border/60" style={ambientStyle(top.image_colors, theme)}>
      <ChartHeader eyebrow="Artist of the Week" id="aotw-h" title="The artist your people can't stop playing" meta={range} />
      <div className="flex flex-col gap-8 px-5 pb-6 sm:px-8 md:pb-8">
        <div className="flex min-w-0 flex-col gap-6 sm:flex-row sm:items-center">
          <div className="jg-art-glow w-[min(56vw,220px)] shrink-0 overflow-hidden rounded-[var(--r-art-lg)]" style={{ ["--art" as string]: top.image_colors?.accent ?? "transparent" }}>
            <Artwork url={top.image_url} seed={top.name} alt={top.name} rounded="none" tint={top.image_colors?.dominant} sizes="220px" />
          </div>
          <div className="flex min-w-0 flex-col gap-3">
            <div className="flex items-center gap-2">
              <span className="font-mono text-4xl font-semibold leading-none tracking-tight">#1</span>
              <MovementBadge m={top.movement} />
            </div>
            <p className="font-display text-4xl font-semibold leading-[0.98] tracking-tight [text-wrap:balance] md:text-6xl">{top.name}</p>
            <People people={top.people} label={`Played by ${top.listeners} of your people · ${top.plays} plays`} />
            {top.new_fans.length > 0 && (
              <p className="text-sm">
                <span className="text-text-muted">New fans this week: </span>
                <span className="font-medium">{names(top.new_fans)}</span>
              </p>
            )}
            {song.title && (
              <div className="mt-1 flex min-w-0 items-center gap-3 rounded-xl border border-border/60 bg-[color-mix(in_srgb,var(--bg)_35%,transparent)] p-2 pr-3">
                <div className="h-12 w-12 shrink-0 overflow-hidden rounded-[var(--r-art-sm)]">
                  <Artwork url={song.artwork_small ?? song.artwork_url ?? null} seed={`${song.artist}|${song.title}`} alt="" rounded="none" tint={song.artwork_colors?.dominant} sizes="48px" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-mono text-[11px] uppercase tracking-wide text-text-muted">Their song of the week</p>
                  <p className="truncate font-semibold">{song.title}</p>
                </div>
                {tune && <TuneButton tune={tune} title={song.title ?? ""} compact />}
              </div>
            )}
          </div>
        </div>

        {rest.length > 0 && (
          <ol className="grid grid-cols-2 gap-4 sm:grid-cols-4" aria-label="Artists 2 to 5">
            {rest.map((a, i) => (
              <li
                key={a.name}
                className="jg-enter flex min-w-0 flex-col gap-2"
                style={{ animationDelay: `${(i + 1) * 70}ms` } as CSSProperties}
                aria-label={`Number ${a.rank}, ${a.name}, ${moveWords(a.movement)}, played by ${a.listeners} of your people`}
              >
                <div className="jg-art-glow overflow-hidden rounded-[var(--r-art-lg)]" style={{ ["--art" as string]: a.image_colors?.accent ?? "transparent" }}>
                  <Artwork url={a.image_url} seed={a.name} alt="" rounded="none" tint={a.image_colors?.dominant} sizes="(min-width: 640px) 200px, 45vw" />
                </div>
                <div className="flex min-w-0 items-center gap-2">
                  <span className="font-mono text-lg font-semibold text-text-muted">{a.rank}</span>
                  <p className="min-w-0 flex-1 truncate font-semibold">{a.name}</p>
                  <MovementBadge m={a.movement} />
                </div>
                <p className="-mt-1 text-xs text-text-muted">
                  {a.listeners} {a.listeners === 1 ? "friend" : "friends"}
                </p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}

// ---- small parts --------------------------------------------------------------------------

function ChartHeader({ eyebrow, id, title, meta, sub, action }: { eyebrow: string; id: string; title: string; meta: string; sub?: ReactNode; action?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-3 px-5 pb-5 pt-6 sm:px-8 md:pt-8">
      <div className="min-w-0">
        <p className="font-mono text-xs uppercase tracking-[0.14em] text-text-muted">{eyebrow}</p>
        <h2 id={id} className="font-display text-2xl font-semibold tracking-tight md:text-3xl">
          {title}
        </h2>
        {sub && <div className="mt-1 min-w-0 text-sm text-text-muted">{sub}</div>}
      </div>
      <div className="flex flex-col items-end gap-2">
        {action}
        <p className="font-mono text-xs text-text-muted">{meta}</p>
      </div>
    </header>
  );
}

/** "3 wks" once an entry has held the top 5 for two weeks or more. */
function Weeks({ n }: { n?: number }) {
  if (!n || n < 2) return null;
  return <span className="shrink-0 font-mono text-[11px] text-text-muted" title={`${n} weeks in the top 5`}>{n} wks</span>;
}

function People({ people, label }: { people: ChartSong["people"]; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <AvatarStack size={26} max={5} people={people.map((p) => ({ id: p.id, name: p.display_name, url: p.avatar_url }))} />
      <p className="font-mono text-xs text-text-muted">{label}</p>
    </div>
  );
}

function MovementBadge({ m }: { m: Movement }) {
  if (m.kind === "new")
    return (
      <span className="inline-flex h-5 shrink-0 items-center rounded-pill bg-[color-mix(in_srgb,var(--brand-violet)_24%,transparent)] px-2 font-mono text-[10px] font-semibold uppercase tracking-wide">
        New
      </span>
    );
  if (m.kind === "same") return <span aria-hidden className="w-6 shrink-0 text-center font-mono text-xs text-text-subtle">=</span>;
  const up = m.kind === "up";
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-0.5 font-mono text-xs font-semibold", up ? "text-success" : "text-text-muted")}>
      <span aria-hidden>{up ? "▲" : "▼"}</span>
      {m.by}
    </span>
  );
}

function TuneButton({ tune, title, solid = false, compact = false }: { tune: NonNullable<ReturnType<typeof tuneIn>>; title: string; solid?: boolean; compact?: boolean }) {
  const mark = tune.platform !== "UNKNOWN" ? <PlatformMark platform={tune.platform} size={compact ? 16 : 17} mono={solid} /> : <Icons.Open size={16} />;
  if (compact)
    return (
      <a href={tune.url} target="_blank" rel="noopener noreferrer" aria-label={`${tune.label}: ${title}`} title={tune.label} className={buttonClasses("ghost", "md", "h-10 w-10 shrink-0 p-0")}>
        {mark}
      </a>
    );
  return (
    <a
      href={tune.url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${tune.label}: ${title}`}
      className={buttonClasses(solid ? "inverse" : "secondary", "md", "gap-2")}
    >
      {mark}
      {tune.label}
    </a>
  );
}

function Chip({ children }: { children: ReactNode }) {
  return <span className="inline-flex h-7 items-center rounded-pill border border-border/70 px-3 text-xs font-medium">{children}</span>;
}

const first = (name: string) => name.split(" ")[0] ?? name;
const names = (ps: { display_name: string }[]) => (ps.length > 2 ? `${ps.slice(0, 2).map((p) => first(p.display_name)).join(", ")} and ${ps.length - 2} more` : ps.map((p) => first(p.display_name)).join(" and "));

function moveWords(m: Movement): string {
  return m.kind === "new" ? "new this week" : m.kind === "same" ? "no change" : `${m.kind} ${m.by}`;
}

function weekRange(start: string, end: string): string {
  const f = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString("en", { day: "numeric", month: "short" });
  return `${f(start)} – ${f(end)}`;
}

function ago(iso: string): string {
  const mins = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60_000));
  return mins < 1 ? "just now" : mins < 60 ? `${mins} min ago` : `${Math.round(mins / 60)} h ago`;
}

/** A chart song as the Send sheet's Song (artwork included). */
function songFromChart(s: ChartSong): Song {
  return {
    recording_id: s.recording_id,
    title: s.title,
    artist: s.artist,
    links: s.links,
    search_links: s.search_links,
    artwork_url: s.artwork_url ?? null,
    artwork_small: s.artwork_small ?? null,
    artwork_colors: s.artwork_colors ?? null,
  };
}

/**
 * Last week's reveal while it's waiting (D-CHART-06): shown at the top of Home so it can't be missed.
 * Kept on screen for this visit once it appears (seen flips server-side mid-reveal) until Done.
 * Shares the charts query (no extra request).
 */
export function PendingReveal() {
  const q = useWeeklyCharts();
  const [fromNotification] = useState(() => typeof window !== "undefined" && new URLSearchParams(window.location.search).get("reveal") === "1");
  const [held, setHeld] = useState<NonNullable<WeeklyChartsData["last_final"]> | null>(null);
  const [dismissed, setDismissed] = useState(false);
  // The notification link always plays it (again, if already seen); otherwise only while waiting.
  const pending = q.data?.last_final && (q.data.last_final.reveal_pending || fromNotification) ? q.data.last_final : null;
  if (pending && !held && !dismissed) setHeld(pending);
  if (!held || dismissed) return null;
  return <ChartReveal final={held} range={weekRange(held.week_start, held.week_end)} autoStart={fromNotification} onDone={() => setDismissed(true)} />;
}
