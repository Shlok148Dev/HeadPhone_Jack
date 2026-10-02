"use client";

import { useParams, useRouter } from "next/navigation";
import { useMemo } from "react";
import { AvatarStack, Button, EmptyState, ErrorState, Icons, Skeleton, seedGradient, useToast, Artwork } from "@/components/ds";
import { OpenLink } from "@/components/app/OpenLink";
import { useBlend, useBlendActions } from "@/lib/live";

/** Blend detail (UX_SPEC §5.8; JNG-07-02 reasons, 07-03 pins + regenerate, 07-04 honest save). */
export default function BlendPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const blend = useBlend(id);
  const { regenerate, pin, leave } = useBlendActions();
  const toast = useToast();
  const [from, to] = useMemo(() => seedGradient(id, "deep"), [id]);

  if (blend.isLoading)
    return (
      <div className="flex flex-col gap-4" aria-busy="true">
        <Skeleton className="h-48" rounded="lg" />
        {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-14" />)}
      </div>
    );
  if (blend.isError || !blend.data)
    return <ErrorState message="Couldn't load this Blend." onRetry={() => void blend.refetch()} />;

  const b = blend.data;
  const tracks = b.tracks ?? [];
  const copy = () => {
    const text = tracks.map((t, i) => `${i + 1}. ${t.artist} – ${t.title}`).join("\n");
    void navigator.clipboard?.writeText(`${b.name}\n${text}`).then(() => toast.toast({ title: "Song list copied", tone: "success" }));
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="relative overflow-hidden rounded-xl px-5 pb-6 pt-10 md:px-8 md:pt-16" style={{ background: `linear-gradient(160deg, ${from}, ${to})` }}>
        <div className="relative flex flex-col gap-3">
          <p className="font-mono text-xs uppercase tracking-wide text-white/80">Blend{b.circle ? ` · ${b.circle.name}` : ""}</p>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-white md:text-5xl">{b.name}</h1>
          <div className="flex items-center gap-3">
            <AvatarStack size={28} people={b.members.map((m) => ({ id: m.id, name: m.display_name, url: m.avatar_url }))} />
            <p className="font-mono text-xs text-white/80">{tracks.length} songs</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              loading={regenerate.isPending}
              loadingLabel="Mixing"
              leadingIcon={<Icons.Refresh size={16} />}
              onClick={() => regenerate.mutate(b.id, { onSuccess: () => toast.toast({ title: "Fresh Blend ready", tone: "success" }) })}
            >
              Regenerate
            </Button>
            <Button variant="secondary" onClick={copy} disabled={!tracks.length}>Copy song list</Button>
            <Button variant="secondary" onClick={() => leave.mutate(b.id, { onSuccess: () => router.push("/blends") })}>Leave Blend</Button>
          </div>
        </div>
      </header>
      {!b.save.available && <p className="text-sm text-text-muted">{b.save.message}</p>}
      {b.left_out.length > 0 && (
        <p className="rounded-lg border border-border bg-surface-1 p-3 text-sm text-text-muted">
          <Icons.Lock size={14} className="mr-1 inline" />
          {b.left_out.map((p) => p.display_name).join(", ")}
          {b.left_out.length === 1 ? "'s plays aren't" : " — their plays aren't"} used here, because not everyone in this Blend can see them.
        </p>
      )}

      {!tracks.length ? (
        <EmptyState pose="sleepy" title="Not enough listening to blend yet." description="Give it a few days of listening and try again." />
      ) : (
        <ol className="flex flex-col" aria-label="Songs">
          {tracks.map((t, i) => (
            <li key={t.id} className="flex min-h-16 items-center gap-3 border-b border-border py-2 last:border-0">
              <span className="w-6 shrink-0 text-right font-mono text-xs text-text-muted">{i + 1}</span>
              <div className="h-11 w-11 shrink-0 overflow-hidden rounded-sm">
                <Artwork url={t.artwork_small ?? t.artwork_url ?? null} seed={`${t.artist}|${t.title}`.toLowerCase()} alt="" rounded="none" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{t.title}</p>
                <p className="truncate text-xs text-text-muted">{t.artist}</p>
                <p className="truncate text-xs">{t.reason}</p>
              </div>
              <Button
                variant="ghost"
                aria-pressed={t.pinned}
                aria-label={`${t.pinned ? "Unpin" : "Pin"} ${t.title}`}
                onClick={() => pin.mutate({ blendId: b.id, trackId: t.id, on: !t.pinned })}
              >
                {t.pinned ? "Pinned" : "Pin"}
              </Button>
              <OpenLink song={t} compact />
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
