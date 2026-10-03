"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { Artwork, AvatarStack, Avatar, Button, EmptyState, ErrorState, IconButton, Icons, PlatformMark, Skeleton, buttonClasses, useToast } from "@/components/ds";
import { CoverMosaic } from "@/components/app/CoverMosaic";
import { ApiError } from "@/lib/api";
import { useCirclePlaylist, usePlaylistActions, type PlaylistItem } from "@/lib/circles";
import { useMyPlatform } from "@/lib/send";
import { useSongSearch, type Song } from "@/lib/sends";
import { tuneIn } from "@/lib/tunein";

/**
 * A circle's shared playlist (JNG-04-08): any member adds songs they like; every song shows who
 * added it, when, and their note; one tap plays it in your own app. Newest first.
 */
export default function CirclePlaylistPage() {
  const { id } = useParams<{ id: string }>();
  const q = useCirclePlaylist(id);
  const myPlatform = useMyPlatform();

  if (q.isLoading)
    return (
      <div className="flex flex-col gap-6" aria-busy="true">
        <Skeleton className="h-48" rounded="lg" />
        <Skeleton className="h-24" rounded="lg" />
      </div>
    );
  if (q.isError || !q.data) return <ErrorState message="Couldn't load the playlist." onRetry={() => void q.refetch()} />;
  const { circle, items } = q.data;
  return (
    <div className="flex min-w-0 flex-col gap-8">
      <Header circleId={circle.id} name={circle.name} items={items} />
      <AddSong circleId={circle.id} />
      {items.length ? (
        <ol className="flex flex-col gap-1" aria-label="Songs in the playlist">
          {items.map((it, i) => (
            <Row key={it.id} item={it} index={i + 1} circleId={circle.id} myPlatform={myPlatform} />
          ))}
        </ol>
      ) : (
        <section className="rounded-lg border border-border bg-surface-1">
          <EmptyState pose="wave" title="No songs yet" description="Add a song your circle should hear. Everyone sees who added what." />
        </section>
      )}
    </div>
  );
}

function Header({ circleId, name, items }: { circleId: string; name: string; items: PlaylistItem[] }) {
  const covers = items.map((i) => i.artwork_url).filter((u): u is string => !!u);
  const people = useMemo(() => {
    const seen = new Map<string, { id: string; name: string; url: string | null }>();
    for (const i of items) if (i.added_by && !seen.has(i.added_by.id)) seen.set(i.added_by.id, { id: i.added_by.id, name: i.added_by.display_name, url: i.added_by.avatar_url });
    return [...seen.values()];
  }, [items]);
  return (
    <header className="flex flex-col gap-5 sm:flex-row sm:items-end">
      <div className="w-[min(60vw,220px)] shrink-0">
        <CoverMosaic covers={covers} seed={`playlist-${circleId}`} />
      </div>
      <div className="flex min-w-0 flex-col gap-2">
        <Link href={`/circles/${circleId}`} className="w-fit font-mono text-xs uppercase tracking-[0.14em] text-text-muted hover:text-text">
          ← {name}
        </Link>
        <h1 className="font-display text-4xl font-semibold tracking-tight md:text-5xl">Circle playlist</h1>
        <div className="flex items-center gap-3">
          {people.length > 0 && <AvatarStack size={26} max={6} people={people} />}
          <p className="font-mono text-xs text-text-muted">
            {items.length} {items.length === 1 ? "song" : "songs"}
            {people.length ? ` · added by ${people.length} ${people.length === 1 ? "person" : "people"}` : ""}
          </p>
        </div>
      </div>
    </header>
  );
}

function AddSong({ circleId }: { circleId: string }) {
  const [q, setQ] = useState("");
  const [picked, setPicked] = useState<Song | null>(null);
  const [note, setNote] = useState("");
  const results = useSongSearch(picked ? "" : q);
  const { add } = usePlaylistActions(circleId);
  const toast = useToast();

  const submit = () => {
    if (!picked) return;
    add.mutate(
      { title: picked.title, artist: picked.artist, recording_id: picked.recording_id, note: note.trim() || undefined },
      {
        onSuccess: () => {
          toast.toast({ title: `Added ${picked.title}`, tone: "success" });
          setPicked(null);
          setQ("");
          setNote("");
        },
        onError: (e) => toast.toast({ title: e instanceof ApiError ? e.message : "Couldn't add that song.", tone: "danger" }),
      },
    );
  };

  return (
    <section aria-labelledby="add-h" className="flex flex-col gap-3 rounded-[20px] border border-border bg-surface-1 p-4 md:p-5">
      <h2 id="add-h" className="font-medium">
        Add a song you like
      </h2>
      {picked ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="flex min-w-0 flex-1 items-center gap-3 rounded-xl border border-border bg-surface-2 p-2 pr-3">
            <div className="h-12 w-12 shrink-0 overflow-hidden rounded-[var(--r-art-sm)]">
              <Artwork url={picked.artwork_small ?? picked.artwork_url ?? null} seed={`${picked.artist}|${picked.title}`} alt="" rounded="none" tint={picked.artwork_colors?.dominant} sizes="48px" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold">{picked.title}</p>
              <p className="truncate text-sm text-text-muted">{picked.artist}</p>
            </div>
            <Button variant="ghost" onClick={() => setPicked(null)}>
              Change
            </Button>
          </div>
          <label htmlFor="pl-note" className="sr-only">
            A line about it (optional)
          </label>
          <input
            id="pl-note"
            value={note}
            onChange={(e) => setNote(e.target.value.slice(0, 140))}
            placeholder="Why this one? (optional)"
            className="h-11 min-w-0 rounded-xl border border-border bg-surface-2 px-4 text-sm placeholder:text-text-subtle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)] sm:w-64"
          />
          <Button variant="inverse" loading={add.isPending} loadingLabel="Adding" onClick={submit}>
            Add to playlist
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <label htmlFor="pl-q" className="sr-only">
            Search a song or artist
          </label>
          <input
            id="pl-q"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search any song or artist"
            autoComplete="off"
            className="h-12 w-full rounded-xl border border-border bg-surface-2 px-4 text-[15px] placeholder:text-text-subtle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)]"
          />
          {q.trim().length >= 2 && (
            <ul aria-label="Search results" className="flex max-h-72 flex-col overflow-y-auto rounded-xl border border-border bg-surface-2 p-1">
              {(results.data ?? []).slice(0, 8).map((s) => (
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
    </section>
  );
}

function Row({ item, index, circleId, myPlatform }: { item: PlaylistItem; index: number; circleId: string; myPlatform?: ReturnType<typeof useMyPlatform> }) {
  const tune = tuneIn(item, myPlatform, null);
  const { remove } = usePlaylistActions(circleId);
  const toast = useToast();
  const who = item.added_by ? (item.added_by.relationship === "self" ? "you" : item.added_by.display_name) : "a former member";
  return (
    <li
      className="group flex min-w-0 items-center gap-3 rounded-xl p-2 hover:bg-surface-1"
      aria-label={`${index}. ${item.title} by ${item.artist}, added by ${who} ${ago(item.added_at)}`}
    >
      <span className="hidden w-7 shrink-0 text-center font-mono text-sm text-text-muted sm:block">{index}</span>
      <div className="h-14 w-14 shrink-0 overflow-hidden rounded-[var(--r-art-sm)]">
        <Artwork url={item.artwork_small ?? item.artwork_url ?? null} seed={`${item.artist}|${item.title}`} alt="" rounded="none" tint={item.artwork_colors?.dominant} sizes="56px" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold">{item.title}</p>
        <p className="truncate text-sm text-text-muted">{item.artist}</p>
        {item.note && <p className="mt-0.5 line-clamp-1 text-[13px] text-text-muted">&ldquo;{item.note}&rdquo;</p>}
      </div>
      {/* Who added it: their face and name, linked to their profile. */}
      <div className="hidden min-w-0 shrink-0 items-center gap-2 md:flex md:w-48">
        {item.added_by ? (
          <Link href={`/u/${item.added_by.username}`} className="flex min-w-0 items-center gap-2 rounded-pill pr-2 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]">
            <Avatar name={item.added_by.display_name} url={item.added_by.avatar_url} seed={item.added_by.id} size={28} decorative />
            <span className="min-w-0">
              <span className="block truncate text-[13px] font-medium">{item.added_by.relationship === "self" ? "You" : item.added_by.display_name}</span>
              <span className="block font-mono text-[11px] text-text-muted">{ago(item.added_at)}</span>
            </span>
          </Link>
        ) : (
          <span className="text-[13px] text-text-muted">Former member</span>
        )}
      </div>
      {/* Phones: the adder's face only. */}
      <div className="shrink-0 md:hidden">
        {item.added_by ? <Avatar name={item.added_by.display_name} url={item.added_by.avatar_url} seed={item.added_by.id} size={26} decorative /> : null}
      </div>
      {tune && (
        <a href={tune.url} target="_blank" rel="noopener noreferrer" aria-label={`${tune.label}: ${item.title}`} title={tune.label} className={buttonClasses("ghost", "md", "h-10 w-10 shrink-0 p-0")}>
          {tune.platform !== "UNKNOWN" ? <PlatformMark platform={tune.platform} size={17} /> : <Icons.Open size={16} />}
        </a>
      )}
      {item.can_remove && (
        <IconButton
          label={`Remove ${item.title} from the playlist`}
          className="opacity-60 group-hover:opacity-100 focus-visible:opacity-100"
          onClick={() =>
            remove.mutate(item.id, {
              onSuccess: () => toast.toast({ title: `Removed ${item.title}`, tone: "success" }),
              onError: (e) => toast.toast({ title: e instanceof ApiError ? e.message : "Couldn't remove it.", tone: "danger" }),
            })
          }
        >
          <Icons.Close size={16} />
        </IconButton>
      )}
    </li>
  );
}

function ago(iso: string): string {
  const mins = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60_000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const h = Math.round(mins / 60);
  if (h < 24) return `${h} h ago`;
  const d = Math.round(h / 24);
  return d < 30 ? `${d} d ago` : new Date(iso).toLocaleDateString("en", { day: "numeric", month: "short" });
}
