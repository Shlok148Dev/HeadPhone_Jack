"use client";

import { CoverMosaic } from "@/components/app/CoverMosaic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Artwork, AvatarStack, Blip, Button, Dialog, EmptyState, ErrorState, Skeleton } from "@/components/ds";
import { PeoplePicker, type Picked } from "@/components/app/PeoplePicker";
import { useBlendActions, useBlends, useSessions, useStartSession } from "@/lib/live";

function ago(iso: string | null): string {
  if (!iso) return "not mixed yet";
  const h = Math.round((Date.now() - Date.parse(iso)) / 3_600_000);
  return h < 1 ? "updated just now" : h < 24 ? `updated ${h} h ago` : `updated ${Math.round(h / 24)} d ago`;
}

const EMPTY: Picked = { users: new Set(), circle: null };

function NewBlend({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { create } = useBlendActions();
  const router = useRouter();
  const [picked, setPicked] = useState<Picked>(EMPTY);
  const ready = picked.circle !== null || picked.users.size >= 1;
  return (
    <Dialog open={open} onClose={onClose} title="New Blend" description="Pick up to 5 friends, or a circle. We'll find songs you'll all like.">
      {create.isPending ? (
        <div className="flex flex-col items-center gap-3 py-8" role="status">
          <Blip pose="idle" size={72} decorative />
          <p className="text-sm text-text-muted">Mixing your Blend…</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {create.error && <p role="alert" className="text-sm text-danger">{create.error.message}</p>}
          <PeoplePicker value={picked} onChange={setPicked} maxFriends={5} />
          <Button
            disabled={!ready}
            onClick={() =>
              create.mutate(
                picked.circle ? { circle_id: picked.circle } : { user_ids: [...picked.users] },
                { onSuccess: (b) => router.push(`/blends/${b.id}`) },
              )
            }
          >
            Make Blend
          </Button>
        </div>
      )}
    </Dialog>
  );
}

function StartSession({ open, onClose }: { open: boolean; onClose: () => void }) {
  const start = useStartSession();
  const router = useRouter();
  const [picked, setPicked] = useState<Picked>(EMPTY);
  return (
    <Dialog open={open} onClose={onClose} title="Listen together" description="Everyone plays on their own app. The room shares one queue and votes on what's next.">
      <div className="flex flex-col gap-4">
        {start.error && <p role="alert" className="text-sm text-danger">{start.error.message}</p>}
        <PeoplePicker value={picked} onChange={setPicked} />
        <Button
          loading={start.isPending}
          loadingLabel="Starting"
          onClick={() =>
            start.mutate(picked.circle ? { circle_id: picked.circle } : { user_ids: [...picked.users] }, {
              onSuccess: (s) => router.push(`/sessions/${s.id}`),
            })
          }
        >
          Start session
        </Button>
      </div>
    </Dialog>
  );
}

/** Blends list (UX_SPEC §5.8; JNG-07-01) plus live sessions you can join (JNG-07-05). */
export default function BlendsPage() {
  const blends = useBlends();
  const sessions = useSessions();
  const [dialog, setDialog] = useState<null | "blend" | "session">(null);

  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Blends</h1>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setDialog("session")}>Listen together</Button>
          <Button onClick={() => setDialog("blend")}>New Blend</Button>
        </div>
      </div>

      {!!sessions.data?.length && (
        <section aria-labelledby="live-sessions-h" className="flex flex-col gap-3">
          <h2 id="live-sessions-h" className="font-display text-xl font-semibold">Live sessions</h2>
          <ul className="flex flex-col gap-2">
            {sessions.data.map((s) => (
              <li key={s.id}>
                <Link href={`/sessions/${s.id}`} className="flex min-h-16 items-center justify-between gap-3 rounded-lg border border-border bg-surface-1 px-4 py-3 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]">
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{s.title}</span>
                    <span className="block font-mono text-xs text-text-muted">
                      Hosted by {s.host.display_name} · {s.participant_count} here{s.circle ? ` · ${s.circle.name}` : ""}
                    </span>
                  </span>
                  <span className="shrink-0 text-sm font-medium">{s.joined ? "Open" : "Join"}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {blends.isLoading ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(200px,1fr))]">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="aspect-square" rounded="lg" />)}
        </div>
      ) : blends.isError ? (
        <ErrorState message="Couldn't load your Blends." onRetry={() => void blends.refetch()} />
      ) : !blends.data?.length ? (
        <EmptyState pose="wave" title="Blends mix your taste with friends'." description="Pick up to 5 friends and we'll find songs you'll all like." action={{ label: "Make a Blend", onClick: () => setDialog("blend") }} />
      ) : (
        <ul className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(200px,1fr))]">
          {blends.data.map((b) => (
            <li key={b.id}>
              <Link href={`/blends/${b.id}`} className="group flex flex-col gap-2 rounded-lg p-2 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]">
                <CoverMosaic covers={b.covers} seed={b.id} />
                <div className="flex items-center gap-2">
                  <AvatarStack size={24} max={4} people={b.members.map((m) => ({ id: m.id, name: m.display_name }))} />
                </div>
                <p className="truncate font-medium">{b.name}</p>
                <p className="font-mono text-xs text-text-muted">{b.track_count} songs · {ago(b.generated_at)}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <NewBlend open={dialog === "blend"} onClose={() => setDialog(null)} />
      <StartSession open={dialog === "session"} onClose={() => setDialog(null)} />
    </div>
  );
}
