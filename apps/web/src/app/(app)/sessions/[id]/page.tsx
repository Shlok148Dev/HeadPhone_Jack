"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AvatarStack, Blip, Button, EmptyState, ErrorState, GenerativeCover, IconButton, Skeleton, cn, useToast } from "@/components/ds";
import { TextField } from "@/components/app/forms";
import { OpenLink } from "@/components/app/OpenLink";
import { useAuth } from "@/lib/auth";
import { useSession, useSessionActions, type QueueEntry, type SessionState } from "@/lib/live";
import { useRealtimeStatus } from "@/lib/realtime";
import { useSongSearch } from "@/lib/sends";

function Cover({ e, size }: { e: { title: string; artist: string }; size: number }) {
  return (
    <div className="shrink-0 overflow-hidden rounded-md" style={{ width: size, height: size }}>
      <GenerativeCover seed={`${e.artist}|${e.title}`.toLowerCase()} rounded="none" />
    </div>
  );
}

function QueueRow({ e, mine, onVote }: { e: QueueEntry; mine: number; onVote: (v: 1 | -1 | 0) => void }) {
  return (
    <li className="flex min-h-16 items-center gap-3 border-b border-border py-2 last:border-0">
      <Cover e={e} size={44} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{e.title}</p>
        <p className="truncate text-xs text-text-muted">
          {e.artist} · {e.added_by ? `added by ${e.added_by.display_name}` : "added anonymously"}
        </p>
      </div>
      <div className="flex items-center gap-1" role="group" aria-label={`Vote on ${e.title}`}>
        <IconButton label={`Vote up ${e.title}`} variant="ghost" aria-pressed={mine === 1} onClick={() => onVote(mine === 1 ? 0 : 1)}>
          <span aria-hidden className={cn("text-lg", mine === 1 && "text-[var(--brand-violet)]")}>▲</span>
        </IconButton>
        <span className="w-6 text-center font-mono text-sm" aria-label={`Score ${e.score}`}>{e.score}</span>
        <IconButton label={`Vote down ${e.title}`} variant="ghost" aria-pressed={mine === -1} onClick={() => onVote(mine === -1 ? 0 : -1)}>
          <span aria-hidden className={cn("text-lg", mine === -1 && "text-[var(--brand-violet)]")}>▼</span>
        </IconButton>
      </div>
      <OpenLink song={{ recording_id: e.recording_id, title: e.title, artist: e.artist }} compact />
    </li>
  );
}

function AddSong({ sessionId }: { sessionId: string }) {
  const [q, setQ] = useState("");
  const [anon, setAnon] = useState(false);
  const results = useSongSearch(q);
  const { add } = useSessionActions(sessionId);
  const toast = useToast();
  return (
    <section aria-labelledby="add-h" className="flex flex-col gap-2">
      <h2 id="add-h" className="font-display text-lg font-semibold">Add a song</h2>
      <TextField label="Find a song" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Song or artist" />
      <label className="flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={anon} onChange={(e) => setAnon(e.target.checked)} className="h-5 w-5 accent-[var(--brand-violet)]" />
        Add anonymously
      </label>
      {q.trim().length >= 2 && (
        <ul className="flex flex-col" aria-label="Search results">
          {results.data?.length ? (
            results.data.map((s) => (
              <li key={`${s.artist}|${s.title}`} className="flex min-h-14 items-center gap-3">
                <Cover e={s} size={40} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{s.title}</p>
                  <p className="truncate text-xs text-text-muted">{s.artist}</p>
                </div>
                <Button
                  variant="secondary"
                  onClick={() =>
                    add.mutate(
                      { recording_id: s.recording_id, title: s.title, artist: s.artist, anonymous: anon },
                      {
                        onSuccess: () => {
                          setQ("");
                          toast.toast({ title: `Added ${s.title}`, tone: "success" });
                        },
                        onError: (e) => toast.toast({ title: e.message, tone: "danger" }),
                      },
                    )
                  }
                >
                  Add
                </Button>
              </li>
            ))
          ) : (
            <li className="py-2 text-sm text-text-muted">{results.isLoading ? "Searching…" : "No songs found."}</li>
          )}
        </ul>
      )}
    </section>
  );
}

/** Toasts for room changes the user should know about (JNG-07-08, JNG-07-09). */
function useRoomNotices(s: SessionState | undefined) {
  const toast = useToast();
  const status = useRealtimeStatus();
  const host = useRef<string | null>(null);
  const wasDown = useRef(false);
  useEffect(() => {
    if (!s) return;
    if (host.current && host.current !== s.host.id) toast.toast({ title: `${s.host.display_name} is now the host.` });
    host.current = s.host.id;
  }, [s, toast]);
  useEffect(() => {
    if (status === "reconnecting") wasDown.current = true;
    else if (status === "live" && wasDown.current) {
      wasDown.current = false;
      toast.toast({ title: "Back in sync", tone: "success" });
    }
  }, [status, toast]);
  return status;
}

/** Live session (UX_SPEC §5.9; JNG-07-05…09). */
export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { me } = useAuth();
  const session = useSession(id);
  const actions = useSessionActions(id);
  const s = session.data;
  const status = useRoomNotices(s);

  if (session.isLoading)
    return (
      <div className="flex flex-col gap-4" aria-busy="true">
        <Skeleton className="h-24" rounded="lg" />
        <Skeleton className="h-40" rounded="lg" />
        {Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-14" />)}
      </div>
    );
  if (session.isError || !s)
    return <ErrorState title="This session has ended." message="Start a new one from Blends." onRetry={() => router.push("/blends")} />;

  if (s.ended)
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <Blip pose="cheer" size={96} decorative />
        <h1 className="font-display text-2xl font-semibold">Session ended</h1>
        <Button onClick={() => router.push("/blends")}>Back to Blends</Button>
      </div>
    );

  if (!s.joined)
    return (
      <div className="flex flex-col items-center gap-4 py-12 text-center">
        <Blip pose="wave" size={96} decorative />
        <h1 className="font-display text-2xl font-semibold">{s.title}</h1>
        <p className="text-sm text-text-muted">Hosted by {s.host.display_name} · {s.participants.length} here</p>
        {actions.join.error && <p role="alert" className="text-sm text-danger">{actions.join.error.message}</p>}
        <Button loading={actions.join.isPending} loadingLabel="Joining" onClick={() => actions.join.mutate()}>Join session</Button>
      </div>
    );

  const isHost = me?.id === s.host.id;
  const np = s.now_playing;
  const npSong = np ? { recording_id: np.recording_id, title: np.title, artist: np.artist, ...(s.now_playing_links ?? {}) } : null;

  return (
    <div className="flex flex-col gap-6">
      {status === "reconnecting" && (
        <p role="status" className="rounded-md border border-border bg-surface-2 px-4 py-2 text-sm">Reconnecting… your votes are saved.</p>
      )}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <p className="font-mono text-xs uppercase tracking-wide text-text-muted">Live session</p>
          <h1 className="font-display text-3xl font-semibold tracking-tight">{s.title}</h1>
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <span>Hosted by {isHost ? "you" : s.host.display_name}</span>
            <AvatarStack size={24} max={5} people={s.participants.map((p) => ({ id: p.id, name: p.display_name }))} />
            <span className="font-mono text-xs">{s.participants.filter((p) => p.online).length || s.participants.length} here</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {isHost && (
            <Button onClick={() => actions.next.mutate()} disabled={!s.queue.length}>Play next</Button>
          )}
          {isHost ? (
            <Button variant="secondary" onClick={() => actions.end.mutate()}>End session</Button>
          ) : null}
          <Button variant="secondary" onClick={() => actions.leave.mutate(undefined, { onSuccess: () => router.push("/blends") })}>Leave</Button>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className={cn("flex flex-col gap-6 lg:col-span-8", status === "reconnecting" && "opacity-70")}>
          <section aria-labelledby="now-h" className="flex items-center gap-4 rounded-lg border border-border bg-surface-1 p-4">
            <h2 id="now-h" className="sr-only">Now playing</h2>
            {np && npSong ? (
              <>
                <Cover e={np} size={96} />
                <div className="min-w-0 flex-1">
                  <p className="font-mono text-xs uppercase text-text-muted">Now</p>
                  <p className="truncate font-display text-xl font-semibold">{np.title}</p>
                  <p className="truncate text-sm text-text-muted">{np.artist}</p>
                  <OpenLink song={npSong} className="mt-2" />
                </div>
              </>
            ) : (
              <p className="text-sm text-text-muted">{isHost ? "Add songs, then tap Play next to start." : "Waiting for the host to start the first song."}</p>
            )}
          </section>

          <section aria-labelledby="queue-h" className="flex flex-col gap-2">
            <h2 id="queue-h" className="font-display text-lg font-semibold">Up next</h2>
            {s.queue.length ? (
              <ol className="flex flex-col" aria-label="Queue">
                {s.queue.map((e) => (
                  <QueueRow key={e.id} e={e} mine={s.my_votes[e.id] ?? 0} onVote={(v) => actions.vote.mutate({ entryId: e.id, value: v })} />
                ))}
              </ol>
            ) : (
              <EmptyState pose="wave" title="The queue is empty." description="Add the first song." />
            )}
          </section>
        </div>
        <aside className="flex flex-col gap-6 lg:col-span-4">
          <AddSong sessionId={s.id} />
          <section aria-labelledby="people-h" className="flex flex-col gap-2">
            <h2 id="people-h" className="font-display text-lg font-semibold">People</h2>
            <ul className="flex flex-col gap-1">
              {s.participants.map((p) => (
                <li key={p.id} className="flex items-center justify-between text-sm">
                  <span>{p.display_name}{p.id === s.host.id ? " · host" : ""}</span>
                  <span className="font-mono text-xs text-text-muted">{p.online ? "here" : "away"}</span>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}
