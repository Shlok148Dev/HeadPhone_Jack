"use client";

import Link from "next/link";
import { useState } from "react";
import { Artwork, Avatar, Button, Icons, PlatformMark, Skeleton, buttonClasses, cn, useToast, type Platform } from "@/components/ds";
import { ApiError } from "@/lib/api";
import { useDropSong, useDropsToday, type Drop } from "@/lib/drops";
import { useSongSearch, type Song } from "@/lib/sends";
import type { Person } from "@/lib/social";
import { tuneIn } from "@/lib/tunein";

/**
 * Daily Drop (JNG-14-01, D-DROP-01): one song a day. Friends' picks stay sealed until you post
 * yours; you see who dropped, never what. That trade is the daily reason to open Jingle.
 */
export function DailyDrop({ myPlatform }: { myPlatform?: Platform }) {
  const today = useDropsToday();
  if (today.isLoading) return <Skeleton className="h-[280px]" rounded="lg" />;
  if (!today.data) return null;
  const t = today.data;
  return (
    <section aria-labelledby="drop-h" className="flex min-w-0 flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-text-muted">Today&apos;s Drop</p>
          <h2 id="drop-h" className="font-display text-2xl font-semibold tracking-tight md:text-3xl">
            {t.locked ? "One song. Your pick for today." : "What everyone dropped today"}
          </h2>
        </div>
        {t.streak > 0 && (
          <p className="inline-flex h-8 items-center gap-1.5 rounded-pill border border-border bg-surface-1 px-3 font-mono text-xs">
            <span aria-hidden className="text-[var(--brand-cyan)]">●</span>
            {t.streak}-day streak
          </p>
        )}
      </header>
      {t.locked ? <DropPicker dropped={t.dropped} /> : <Revealed mine={t.mine} friends={t.friends} myPlatform={myPlatform} />}
    </section>
  );
}

function DropPicker({ dropped }: { dropped: Person[] }) {
  const [q, setQ] = useState("");
  const [picked, setPicked] = useState<Song | null>(null);
  const [note, setNote] = useState("");
  const results = useSongSearch(picked ? "" : q);
  const drop = useDropSong();
  const toast = useToast();
  const who = dropped.slice(0, 5);

  return (
    <div className="grid gap-6 rounded-[24px] border border-border bg-surface-1 p-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:p-7">
      {/* The sealed side: who dropped, never what. */}
      <div className="flex flex-col justify-between gap-5">
        <div className="grid grid-cols-3 gap-2" aria-hidden>
          {[0, 1, 2].map((i) => {
            const p = dropped[i];
            return (
              <div key={i} className="relative grid aspect-square place-items-center overflow-hidden rounded-[var(--r-art-lg)] border border-border bg-[linear-gradient(160deg,var(--surface-3),var(--surface-2))]">
                {p ? (
                  <div className="flex flex-col items-center gap-2">
                    <Avatar name={p.display_name} url={p.avatar_url} seed={p.id} size={40} decorative />
                    <span className="inline-flex items-center gap-1 font-mono text-[11px] text-text-muted">
                      <Icons.Lock size={11} /> sealed
                    </span>
                  </div>
                ) : (
                  <Icons.Lock size={18} className="text-text-subtle" />
                )}
              </div>
            );
          })}
        </div>
        <div>
          {who.length ? (
            <div className="flex items-center gap-3">
              <div className="flex -space-x-2">
                {who.map((p) => (
                  <Avatar key={p.id} name={p.display_name} url={p.avatar_url} seed={p.id} size={30} decorative className="ring-2 ring-[var(--surface-1)]" />
                ))}
              </div>
              <p className="text-sm text-text-muted">
                <span className="font-semibold text-text">{who[0]!.display_name}</span>
                {dropped.length > 1 ? ` and ${dropped.length - 1} more` : ""} dropped today. Drop yours to see what.
              </p>
            </div>
          ) : (
            <p className="text-sm text-text-muted">Be the first of your friends to drop today. Theirs unlock for you as they come in.</p>
          )}
        </div>
      </div>

      {/* Your pick. */}
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!picked) return;
          drop.mutate(
            { title: picked.title, artist: picked.artist, recording_id: picked.recording_id, note: note.trim() || undefined },
            {
              onSuccess: () => toast.toast({ title: "Dropped. Here's everyone's.", tone: "success" }),
              onError: (err) => toast.toast({ title: err instanceof ApiError ? err.message : "Couldn't drop that.", tone: "danger" }),
            },
          );
        }}
      >
        {picked ? (
          <div className="flex items-center gap-3 rounded-xl border border-border bg-surface-2 p-2 pr-3">
            <div className="h-14 w-14 shrink-0 overflow-hidden rounded-[var(--r-art-sm)]">
              <Artwork url={picked.artwork_url ?? null} seed={`${picked.artist}|${picked.title}`} alt="" rounded="none" tint={picked.artwork_colors?.dominant} sizes="56px" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold">{picked.title}</p>
              <p className="truncate text-sm text-text-muted">{picked.artist}</p>
            </div>
            <Button variant="ghost" onClick={() => setPicked(null)}>
              Change
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <label htmlFor="drop-q" className="text-sm font-medium">
              Your song for today
            </label>
            <input
              id="drop-q"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search a song or artist"
              autoComplete="off"
              className="h-12 w-full rounded-xl border border-border bg-surface-2 px-4 text-[15px] placeholder:text-text-subtle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)]"
            />
            {q.trim().length >= 2 && (
              <ul aria-label="Songs" className="flex max-h-56 flex-col overflow-y-auto rounded-xl border border-border bg-surface-2 p-1">
                {(results.data ?? []).slice(0, 6).map((s) => (
                  <li key={`${s.artist}|${s.title}`}>
                    <button
                      type="button"
                      onClick={() => setPicked(s)}
                      className="flex w-full items-center gap-3 rounded-lg p-1.5 text-left hover:bg-surface-3 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]"
                    >
                      <div className="h-10 w-10 shrink-0 overflow-hidden rounded-[var(--r-art-sm)]">
                        <Artwork url={s.artwork_small ?? s.artwork_url ?? null} seed={`${s.artist}|${s.title}`} alt="" rounded="none" tint={s.artwork_colors?.dominant} sizes="40px" />
                      </div>
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium">{s.title}</span>
                        <span className="block truncate text-xs text-text-muted">{s.artist}</span>
                      </span>
                    </button>
                  </li>
                ))}
                {results.data?.length === 0 && <li className="p-3 text-sm text-text-muted">No songs found. Try the artist&apos;s name.</li>}
              </ul>
            )}
          </div>
        )}
        <label htmlFor="drop-note" className="sr-only">
          A line about it (optional)
        </label>
        <input
          id="drop-note"
          value={note}
          onChange={(e) => setNote(e.target.value.slice(0, 140))}
          placeholder="A line about it (optional)"
          className="h-11 w-full rounded-xl border border-border bg-surface-2 px-4 text-sm placeholder:text-text-subtle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)]"
        />
        <button
          type="submit"
          disabled={!picked || drop.isPending}
          className={buttonClasses("secondary", "lg", "border-transparent bg-text text-bg hover:bg-text hover:opacity-90 disabled:bg-surface-3 disabled:text-text-muted disabled:opacity-100")}
        >
          {drop.isPending ? "Dropping…" : "Drop it"}
        </button>
        <p className="text-xs text-text-muted">One a day, and it can&apos;t be changed. Your friends see it.</p>
      </form>
    </div>
  );
}

function Revealed({ mine, friends, myPlatform }: { mine: Drop | null; friends: Drop[]; myPlatform?: Platform }) {
  const all = [...(mine ? [mine] : []), ...friends];
  return (
    <ul className="ds-scrollbar-none -mx-1 flex w-full min-w-0 max-w-full snap-x gap-4 overflow-x-auto px-1 pb-2">
      {all.map((d) => (
        <DropCard key={d.id} d={d} isMine={d.id === mine?.id} myPlatform={myPlatform} />
      ))}
      {!friends.length && (
        <li className="flex w-64 shrink-0 snap-start flex-col justify-center gap-2 rounded-[20px] border border-dashed border-border p-5 text-sm text-text-muted">
          No friends have dropped yet today. Their songs appear here as they do.
        </li>
      )}
    </ul>
  );
}

function DropCard({ d, isMine, myPlatform }: { d: Drop; isMine: boolean; myPlatform?: Platform }) {
  const tune = tuneIn(d, myPlatform, null);
  return (
    <li className="flex w-[220px] shrink-0 snap-start flex-col gap-3 md:w-[240px]">
      <div className="jg-art-glow overflow-hidden rounded-[var(--r-art-lg)]" style={{ ["--art" as string]: d.artwork_colors?.accent ?? "transparent" }}>
        <Artwork url={d.artwork_url} seed={`${d.artist}|${d.title}`} alt={`${d.title} by ${d.artist}`} rounded="none" tint={d.artwork_colors?.dominant} sizes="240px" />
      </div>
      <div className="min-w-0">
        <p className="truncate font-semibold">{d.title}</p>
        <p className="truncate text-sm text-text-muted">{d.artist}</p>
      </div>
      <div className="flex min-w-0 flex-col gap-1">
        {isMine ? (
          <span className="inline-flex min-h-8 items-center gap-2 text-[13px] font-semibold">
            <Avatar name={d.user.display_name} url={d.user.avatar_url} seed={d.user.id} size={24} decorative />
            Your drop
          </span>
        ) : (
          <Link href={`/u/${d.user.username}`} className="inline-flex min-h-8 w-fit items-center gap-2 rounded-pill pr-2 text-[13px] font-semibold hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]">
            <Avatar name={d.user.display_name} url={d.user.avatar_url} seed={d.user.id} size={24} decorative />
            {d.user.display_name}
          </Link>
        )}
        {d.note && <p className="text-[13px] leading-snug text-text-muted">&ldquo;{d.note}&rdquo;</p>}
      </div>
      {tune && !isMine && (
        <a
          href={tune.url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`${tune.label}: ${d.title}`}
          className={cn(buttonClasses("secondary", "md", "justify-start gap-2 px-3 text-[13px]"))}
        >
          {tune.platform !== "UNKNOWN" ? <PlatformMark platform={tune.platform} size={15} /> : <Icons.Open size={15} />}
          <span className="truncate">{tune.label}</span>
        </a>
      )}
    </li>
  );
}
