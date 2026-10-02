"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Avatar, Button, Dialog, EmptyState, ErrorState, Icons, Skeleton, Tabs, cn, Artwork } from "@/components/ds";
import { OpenLink } from "@/components/app/OpenLink";
import { useOpenSend } from "@/lib/send";
import { REACTIONS, STATUSES, useInbox, useSendActions, useSent, type Received, type SendStatus, type Sent, type Song } from "@/lib/sends";

const STATUS_LABEL: Record<SendStatus, string> = { sent: "Sent", delivered: "Delivered", viewed: "Viewed", played: "Played" };

function ago(iso: string, now = Date.now()): string {
  const m = Math.max(0, Math.round((now - Date.parse(iso)) / 60_000));
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} h ago`;
  const d = Math.round(h / 24);
  return d < 7 ? `${d} d ago` : new Date(iso).toLocaleDateString();
}

function Cover({ song, size = 56 }: { song: Song; size?: number }) {
  return (
    <div className="shrink-0 overflow-hidden rounded-md" style={{ width: size, height: size }}>
      <Artwork url={song.artwork_small ?? song.artwork_url ?? null} seed={`${song.artist}|${song.title}`.toLowerCase()} alt="" rounded="none" />
    </div>
  );
}

/** Sent → Delivered → Viewed → Played as a 4-step track (UX_SPEC StatusChips). */
function StatusChips({ status, name }: { status: SendStatus; name?: string }) {
  const reached = STATUSES.indexOf(status);
  return (
    <ol className="flex flex-wrap gap-1" aria-label={name ? `Status for ${name}: ${STATUS_LABEL[status]}` : `Status: ${STATUS_LABEL[status]}`}>
      {STATUSES.map((s, i) => (
        <li
          key={s}
          aria-current={i === reached ? "step" : undefined}
          className={cn(
            "inline-flex h-7 items-center gap-1 rounded-full px-2.5 font-mono text-[11px]",
            i <= reached ? "bg-surface-3 text-text" : "border border-border text-text-muted",
            i === reached && "ring-1 ring-[var(--brand-violet)]",
          )}
        >
          {i <= reached && <Icons.Check size={12} />}
          {STATUS_LABEL[s]}
        </li>
      ))}
    </ol>
  );
}

function ReceivedRow({ item }: { item: Received }) {
  const { view, react } = useSendActions();
  const openSend = useOpenSend();
  const ref = useRef<HTMLLIElement>(null);
  const [reacting, setReacting] = useState(false);
  const [open, setOpen] = useState(false);
  const isNew = item.status !== "viewed" && item.status !== "played";
  const first = item.items[0];
  const name = item.sender.display_name;

  // Seeing the row marks it Viewed (UX_SPEC §5.12).
  useEffect(() => {
    if (!isNew || !ref.current || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e?.isIntersecting) {
          io.disconnect();
          view.mutate(item.id);
        }
      },
      { threshold: 0.6 },
    );
    io.observe(ref.current);
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isNew, item.id]);

  return (
    <li ref={ref} className="relative flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-4" aria-label={`${item.kind === "mixtape" ? "Mixtape" : first?.title} from ${name}`}>
      {isNew && <span aria-label="New" className="absolute left-2 top-2 h-1.5 w-1.5 rounded-full bg-[var(--brand-violet)]" />}
      <div className="flex items-start gap-3">
        {first && <Cover song={first} />}
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2 text-sm text-text-muted">
            <Avatar name={name} url={item.sender.avatar_url} seed={item.sender.id} size={20} decorative />
            <span>
              <span className="font-medium text-text">{name}</span>
              {item.is_reply ? " replied with a song" : item.circle ? ` · ${item.circle.name}` : ""}
            </span>
          </p>
          <p className="truncate font-medium">{item.kind === "mixtape" ? `Mixtape · ${item.items.length} songs` : first?.title}</p>
          {item.kind === "track" && <p className="truncate text-sm text-text-muted">{first?.artist}</p>}
          {item.note && <p className="mt-1 line-clamp-2 text-sm">&ldquo;{item.note}&rdquo;</p>}
          <p className="mt-1 font-mono text-xs text-text-muted">
            {ago(item.sent_at)}
            {item.reaction && ` · You reacted ${item.reaction}`}
          </p>
        </div>
      </div>
      {item.kind === "mixtape" && (
        <div>
          <Button variant="ghost" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? "Hide songs" : "Show songs"}
          </Button>
          {open && (
            <ol className="mt-2 flex flex-col gap-3">
              {item.items.map((s, i) => (
                <li key={i} className="flex flex-wrap items-center gap-3">
                  <Cover song={s} size={40} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{s.title}</p>
                    <p className="truncate text-xs text-text-muted">{s.artist}</p>
                  </div>
                  <OpenLink song={s} />
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
      <div className="flex flex-wrap items-end gap-2">
        {item.kind === "track" && first && <OpenLink song={first} />}
        <Button variant="ghost" onClick={() => setReacting(true)}>React</Button>
        <Button variant="ghost" onClick={() => openSend({ replyTo: { deliveryId: item.id, name } })}>Reply with a song</Button>
      </div>
      <Dialog open={reacting} onClose={() => setReacting(false)} title={`React to ${name}`}>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Reactions">
          {REACTIONS.map((r) => (
            <Button
              key={r}
              variant={item.reaction === r ? "primary" : "secondary"}
              aria-pressed={item.reaction === r}
              onClick={() => react.mutate({ id: item.id, reaction: item.reaction === r ? "" : r }, { onSuccess: () => setReacting(false) })}
            >
              <span className="text-xl">{r}</span>
            </Button>
          ))}
        </div>
      </Dialog>
    </li>
  );
}

function SentRow({ item }: { item: Sent }) {
  const first = item.items[0];
  const credits = item.recipients.filter((r) => r.credit_artist);
  return (
    <li className="flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-4">
      <div className="flex items-start gap-3">
        {first && <Cover song={first} />}
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">{item.kind === "mixtape" ? `Mixtape · ${item.items.length} songs` : first?.title}</p>
          {item.kind === "track" && <p className="truncate text-sm text-text-muted">{first?.artist}</p>}
          {item.note && <p className="mt-1 line-clamp-2 text-sm">&ldquo;{item.note}&rdquo;</p>}
          <p className="mt-1 font-mono text-xs text-text-muted">{ago(item.sent_at)}</p>
          {credits.length > 0 && (
            <p className="mt-2 inline-flex items-center gap-1 rounded-full bg-surface-3 px-2.5 py-1 font-mono text-[11px]">
              <Icons.Sparkle size={12} /> Discovery credit · {credits.map((c) => c.user.display_name).join(", ")} found {credits[0]?.credit_artist}
            </p>
          )}
        </div>
      </div>
      <ul className="flex flex-col gap-2">
        {item.recipients.map((r) => (
          <li key={r.user.id} className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="flex min-w-32 items-center gap-2 text-sm">
              <Avatar name={r.user.display_name} url={r.user.avatar_url} seed={r.user.id} size={24} decorative />
              {r.user.display_name}
              {r.reaction && <span aria-label={`reacted ${r.reaction}`}>{r.reaction}</span>}
            </span>
            <StatusChips status={r.status} name={r.user.display_name} />
          </li>
        ))}
      </ul>
    </li>
  );
}

function RowsSkeleton() {
  return (
    <div className="flex flex-col gap-3" aria-busy="true">
      {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-24" rounded="lg" />)}
    </div>
  );
}

function ReceivedTab() {
  const inbox = useInbox();
  const openSend = useOpenSend();
  if (inbox.isLoading) return <RowsSkeleton />;
  if (inbox.isError) return <ErrorState message="Couldn't load your inbox." onRetry={() => void inbox.refetch()} />;
  if (!inbox.data?.length)
    return <EmptyState pose="wave" title="Nothing here yet." description="When friends send you songs, they land here." action={{ label: "Send a song first", onClick: () => openSend() }} />;
  return <ul className="flex flex-col gap-3">{inbox.data.map((r) => <ReceivedRow key={r.id} item={r} />)}</ul>;
}

function SentTab() {
  const sent = useSent();
  const openSend = useOpenSend();
  if (sent.isLoading) return <RowsSkeleton />;
  if (sent.isError) return <ErrorState message="Couldn't load your inbox." onRetry={() => void sent.refetch()} />;
  if (!sent.data?.length)
    return <EmptyState pose="sleepy" title="You haven't sent anything yet." action={{ label: "Send a song", onClick: () => openSend() }} />;
  return <ul className="flex flex-col gap-3">{sent.data.map((s) => <SentRow key={s.id} item={s} />)}</ul>;
}

/** Inbox of sends (UX_SPEC §5.12; JNG-06-04, 06-06, 06-07). */
export default function InboxPage() {
  const params = useSearchParams();
  const router = useRouter();
  const openSend = useOpenSend();
  const tab = params.get("tab") === "sent" ? "sent" : "received";
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Inbox</h1>
        <Button onClick={() => openSend()} leadingIcon={<Icons.Send size={16} />}>Send a song</Button>
      </div>
      <Tabs
        label="Inbox"
        value={tab}
        onChange={(id) => router.replace(`/inbox?tab=${id}`)}
        items={[
          { id: "received", label: "Received", content: <ReceivedTab /> },
          { id: "sent", label: "Sent", content: <SentTab /> },
        ]}
      />
    </div>
  );
}
