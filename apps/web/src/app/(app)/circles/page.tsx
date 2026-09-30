"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button, Dialog, EmptyState, ErrorState, GenerativeCover, Skeleton, useToast } from "@/components/ds";
import { FormAlert, TextField } from "@/components/app/forms";
import { useCircleActions, useCircleInvites, useCircles, useSuggestedCircles } from "@/lib/circles";

function CreateCircle({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { create } = useCircleActions();
  const router = useRouter();
  const [name, setName] = useState("");
  const [discoverable, setDiscoverable] = useState(false);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate(
      { name: name.trim(), visibility: discoverable ? "discoverable" : "private" },
      { onSuccess: (c) => router.push(`/circles/${c.id}?invite=1`) },
    );
  };
  return (
    <Dialog open={open} onClose={onClose} title="New circle" description="A named group for your crew: its own feed, Blend and weekly battle.">
      <form onSubmit={submit} className="flex flex-col gap-4">
        {create.error && <FormAlert>{create.error.message}</FormAlert>}
        <TextField label="Circle name" value={name} maxLength={60} onChange={(e) => setName(e.target.value)} placeholder="College hip-hop crew" />
        <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
          <span>
            <span className="block font-medium">Let people at my college find it</span>
            <span className="text-text-muted">Private circles are invite only.</span>
          </span>
          <input type="checkbox" role="switch" checked={discoverable} onChange={(e) => setDiscoverable(e.target.checked)} className="h-5 w-5 accent-[var(--brand-violet)]" />
        </label>
        <Button type="submit" disabled={!name.trim()} loading={create.isPending} loadingLabel="Creating">
          Create circle
        </Button>
      </form>
    </Dialog>
  );
}

/** Circles list (UX_SPEC §5.7; JNG-04-01, 04-02, 04-05). */
export default function CirclesPage() {
  const circles = useCircles();
  const invites = useCircleInvites();
  const suggested = useSuggestedCircles();
  const actions = useCircleActions();
  const toast = useToast();
  const router = useRouter();
  const [creating, setCreating] = useState(false);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Circles</h1>
        <Button onClick={() => setCreating(true)}>New circle</Button>
      </div>

      {!!invites.data?.length && (
        <section aria-labelledby="inv-h" className="flex flex-col gap-3">
          <h2 id="inv-h" className="font-mono text-xs uppercase tracking-wide text-text-muted">Invitations</h2>
          <ul className="flex flex-col gap-2">
            {invites.data.map((i) => (
              <li key={i.id} className="flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm">
                  <span className="font-medium">{i.from.display_name}</span> invited you to{" "}
                  <span className="font-medium">{i.circle.name}</span>
                  <span className="font-mono text-xs text-text-muted"> · {i.circle.member_count} members</span>
                </p>
                <div className="flex gap-2">
                  <Button onClick={() => actions.acceptInvite.mutate(i.id, { onSuccess: (c) => router.push(`/circles/${c.id}`), onError: (e) => toast.toast({ title: e.message, tone: "danger" }) })}>
                    Join
                  </Button>
                  <Button variant="ghost" onClick={() => actions.declineInvite.mutate(i.id)}>Not now</Button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!!suggested.data?.length && (
        <section aria-labelledby="sug-h" className="flex flex-col gap-3">
          <h2 id="sug-h" className="font-mono text-xs uppercase tracking-wide text-text-muted">Suggested for you</h2>
          {suggested.data.map((s) => (
            <div key={s.id} className="flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm">
                Make a circle with {s.members.map((m) => m.display_name).join(", ")}?{" "}
                <span className="text-text-muted">We&rsquo;ll call it &ldquo;{s.name}&rdquo;. They&rsquo;ll each get an invite.</span>
              </p>
              <div className="flex gap-2">
                <Button onClick={() => actions.useSuggestion.mutate({ id: s.id, name: s.name, userIds: s.members.map((m) => m.id) }, { onSuccess: (c) => router.push(`/circles/${c.id}`) })}>
                  Create and invite
                </Button>
                <Button variant="ghost" onClick={() => actions.dismissSuggestion.mutate(s.id)}>Dismiss</Button>
              </div>
            </div>
          ))}
        </section>
      )}

      {circles.isLoading ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(200px,1fr))]">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="aspect-square" rounded="lg" />)}
        </div>
      ) : circles.isError ? (
        <ErrorState message="Couldn't load your circles." onRetry={() => void circles.refetch()} />
      ) : !circles.data?.length ? (
        <EmptyState pose="wave" title="No circles yet" description="Start one for your crew and battle over the best song every week." action={{ label: "New circle", onClick: () => setCreating(true) }} />
      ) : (
        <ul className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(200px,1fr))]">
          {circles.data.map((c) => (
            <li key={c.id}>
              <Link href={`/circles/${c.id}`} className="group flex flex-col gap-2 rounded-lg p-2 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]">
                <div className="aspect-square overflow-hidden rounded-lg transition-transform group-hover:scale-[1.02]">
                  <GenerativeCover seed={c.id} />
                </div>
                <p className="truncate font-medium">{c.name}</p>
                <p className="font-mono text-xs text-text-muted">
                  {c.member_count} members{c.my_role !== "member" ? ` · ${c.my_role}` : ""}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <CreateCircle open={creating} onClose={() => setCreating(false)} />
    </div>
  );
}
