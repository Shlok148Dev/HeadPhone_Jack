"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Dialog,
  EmptyState,
  ErrorState,
  FeedCard,
  FeedCardSkeleton,
  Shelf,
  Skeleton,
  seedGradient,
  useToast,
  buttonClasses,
} from "@/components/ds";
import { PersonRow } from "@/components/app/PersonRow";
import { useAuth } from "@/lib/auth";
import { songFromCard, useOpenSend } from "@/lib/send";
import { useCircle, useCircleActions, useCircleFeed, type Circle, type Role } from "@/lib/circles";
import { isFreshLive } from "@/lib/feed";
import { useBlendActions, useStartSession } from "@/lib/live";
import { useFriends } from "@/lib/social";

function InviteSheet({ circle, open, onClose }: { circle: Circle; open: boolean; onClose: () => void }) {
  const friends = useFriends();
  const { invite, link } = useCircleActions();
  const toast = useToast();
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [url, setUrl] = useState<string | null>(null);
  const inCircle = new Set(circle.members?.map((m) => m.user.id));
  const candidates = (friends.data ?? []).filter((f) => !inCircle.has(f.id));

  const toggle = (id: string) =>
    setPicked((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  return (
    <Dialog open={open} onClose={onClose} variant="sheet" title={`Invite to ${circle.name}`} description="They join when they accept. Nobody is added without saying yes.">
      <div className="flex flex-col gap-4">
        {candidates.length ? (
          <ul className="flex max-h-72 flex-col overflow-y-auto">
            {candidates.map((f) => (
              <PersonRow
                key={f.id}
                person={f}
                actions={
                  <input
                    type="checkbox"
                    aria-label={`Invite ${f.display_name}`}
                    checked={picked.has(f.id)}
                    onChange={() => toggle(f.id)}
                    className="h-5 w-5 accent-[var(--brand-violet)]"
                  />
                }
              />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-text-muted">All your friends are already here. Share a link instead.</p>
        )}
        <Button
          disabled={!picked.size}
          loading={invite.isPending}
          loadingLabel="Inviting"
          onClick={() =>
            invite.mutate(
              { id: circle.id, userIds: [...picked] },
              {
                onSuccess: () => {
                  toast.toast({ title: picked.size === 1 ? "Invite sent" : `${picked.size} invites sent`, tone: "success" });
                  setPicked(new Set());
                  onClose();
                },
                onError: (e) => toast.toast({ title: e.message, tone: "danger" }),
              },
            )
          }
        >
          {picked.size ? `Invite ${picked.size}` : "Invite"}
        </Button>
        <div className="flex flex-col gap-2 border-t border-border pt-4">
          <p className="text-sm font-medium">Or share a link</p>
          {url ? (
            <div className="flex flex-col gap-2 sm:flex-row">
              <input readOnly value={url} aria-label="Circle invite link" className="min-h-11 flex-1 rounded-md border border-border bg-surface-2 px-3 font-mono text-xs" />
              <Button
                variant="secondary"
                onClick={() => {
                  void navigator.clipboard?.writeText(url).then(() => toast.toast({ title: "Link copied", tone: "success" }));
                }}
              >
                Copy
              </Button>
            </div>
          ) : (
            <Button variant="secondary" loading={link.isPending} loadingLabel="Making link" onClick={() => link.mutate(circle.id, { onSuccess: (r) => setUrl(r.url), onError: (e) => toast.toast({ title: e.message, tone: "danger" }) })}>
              Make a link
            </Button>
          )}
          <p className="font-mono text-xs text-text-muted">Links work for 7 days.</p>
        </div>
      </div>
    </Dialog>
  );
}

function MemberActions({ circle, userId, name, role, myRole }: { circle: Circle; userId: string; name: string; role: Role; myRole: Role }) {
  const { setRole, remove, transfer } = useCircleActions();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  if (role === "owner" || myRole === "member" || (role === "admin" && myRole !== "owner")) return null;
  const done = (title: string) => () => {
    setOpen(false);
    toast.toast({ title, tone: "success" });
  };
  const fail = (e: Error) => toast.toast({ title: e.message, tone: "danger" });
  return (
    <>
      <Button variant="ghost" aria-label={`Options for ${name}`} onClick={() => setOpen(true)}>•••</Button>
      <Dialog open={open} onClose={() => setOpen(false)} title={name}>
        <div className="flex flex-col gap-2">
          {myRole === "owner" && (
            <Button variant="secondary" onClick={() => setRole.mutate({ id: circle.id, userId, role: role === "admin" ? "member" : "admin" }, { onSuccess: done(role === "admin" ? "No longer an admin" : "Made an admin"), onError: fail })}>
              {role === "admin" ? "Remove as admin" : "Make admin"}
            </Button>
          )}
          {myRole === "owner" && (
            <Button variant="secondary" onClick={() => transfer.mutate({ id: circle.id, userId }, { onSuccess: done(`${name} owns the circle now`), onError: fail })}>
              Make owner
            </Button>
          )}
          <Button variant="danger" onClick={() => remove.mutate({ id: circle.id, userId }, { onSuccess: done(`Removed ${name}`), onError: fail })}>
            Remove from circle
          </Button>
        </div>
      </Dialog>
    </>
  );
}

function SettingsDialog({ circle, open, onClose }: { circle: Circle; open: boolean; onClose: () => void }) {
  const { update } = useCircleActions();
  const [name, setName] = useState(circle.name);
  const [canInvite, setCanInvite] = useState(circle.members_can_invite);
  const [discoverable, setDiscoverable] = useState(circle.visibility === "discoverable");
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Circle settings"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button
            loading={update.isPending}
            loadingLabel="Saving"
            disabled={!name.trim()}
            onClick={() =>
              update.mutate(
                { id: circle.id, patch: { name: name.trim(), members_can_invite: canInvite, visibility: discoverable ? "discoverable" : "private" } },
                { onSuccess: onClose },
              )
            }
          >
            Save
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Name
          <input value={name} maxLength={60} onChange={(e) => setName(e.target.value)} className="min-h-11 rounded-md border border-border bg-surface-2 px-3 font-normal" />
        </label>
        <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
          Members can invite people
          <input type="checkbox" role="switch" checked={canInvite} onChange={(e) => setCanInvite(e.target.checked)} className="h-5 w-5 accent-[var(--brand-violet)]" />
        </label>
        <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
          People at my college can find it
          <input type="checkbox" role="switch" checked={discoverable} onChange={(e) => setDiscoverable(e.target.checked)} className="h-5 w-5 accent-[var(--brand-violet)]" />
        </label>
        {update.error && <p role="alert" className="text-sm text-danger">{update.error.message}</p>}
      </div>
    </Dialog>
  );
}

/** Circle page (UX_SPEC §5.7; JNG-04-02…04-07): ambient header, feed, members, admin tools. */
export default function CirclePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const search = useSearchParams();
  const { me } = useAuth();
  const openSend = useOpenSend();
  const circle = useCircle(id);
  const feed = useCircleFeed(id);
  const { leave } = useCircleActions();
  const blendActions = useBlendActions();
  const startSession = useStartSession();
  const toast = useToast();
  const [dialog, setDialog] = useState<null | "invite" | "settings" | "leave">(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 15_000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (search.get("invite") !== "1") return;
    setDialog("invite");
    router.replace(`/circles/${id}`); // one-shot: a reload shouldn't reopen the sheet
  }, [search, router, id]);

  const [from, to] = useMemo(() => seedGradient(id, "deep"), [id]);
  const cards = feed.data ?? [];
  const live = cards.filter((c) => isFreshLive(c, now));
  const liveIds = new Set(live.map((c) => c.friend.id));
  const rest = cards.filter((c) => !liveIds.has(c.friend.id));

  if (circle.isLoading) return <Skeleton className="h-48" rounded="lg" />;
  if (circle.isError || !circle.data)
    return <ErrorState title="We couldn't find that circle." message="It may have closed, or you're not in it." onRetry={() => router.push("/circles")} />;

  const c = circle.data;
  const myRole = c.my_role ?? "member";
  const isAdmin = myRole !== "member";
  const canInvite = isAdmin || c.members_can_invite;
  const soleOwner = myRole === "owner" && c.member_count > 1;

  return (
    <div className="flex flex-col gap-8">
      <header
        className="relative overflow-hidden rounded-xl px-5 pb-6 pt-10 md:px-8 md:pt-16"
        style={{ background: `linear-gradient(160deg, ${from}, ${to})` }}
      >
        <div className="relative flex flex-col gap-3">
          <p className="font-mono text-xs uppercase tracking-wide text-white/80">Circle · {c.visibility === "private" ? "Private" : "Discoverable"}</p>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-white md:text-5xl">{c.name}</h1>
          <p className="font-mono text-xs text-white/80">
            {c.member_count} members{live.length ? ` · ${live.length} live now` : ""}
          </p>
          <div className="flex flex-wrap gap-2">
            {canInvite && <Button onClick={() => setDialog("invite")}>Invite</Button>}
            <Button
              variant="secondary"
              loading={blendActions.create.isPending}
              loadingLabel="Mixing"
              onClick={() => blendActions.create.mutate({ circle_id: c.id }, { onSuccess: (b) => router.push(`/blends/${b.id}`), onError: (e) => toast.toast({ title: e.message, tone: "danger" }) })}
            >
              Make a Blend
            </Button>
            <Button
              variant="secondary"
              loading={startSession.isPending}
              loadingLabel="Starting"
              onClick={() => startSession.mutate({ circle_id: c.id }, { onSuccess: (x) => router.push(`/sessions/${x.id}`), onError: (e) => toast.toast({ title: e.message, tone: "danger" }) })}
            >
              Listen together
            </Button>
            {/* JNG-04-08: the circle's shared playlist. */}
            <Link href={`/circles/${c.id}/playlist`} className={buttonClasses("secondary", "md", "gap-2")}>
              Playlist
            </Link>
            {isAdmin && <Button variant="secondary" onClick={() => setDialog("settings")}>Settings</Button>}
            <Button variant="secondary" onClick={() => setDialog("leave")}>Leave</Button>
          </div>
        </div>
      </header>

      {feed.isLoading ? (
        <div className="flex gap-4 overflow-hidden">
          {[0, 1, 2].map((i) => (
            <div key={i} className="w-[148px] shrink-0 md:w-[184px]"><FeedCardSkeleton /></div>
          ))}
        </div>
      ) : feed.isError ? (
        <ErrorState message="Couldn't load what the circle is playing." onRetry={() => void feed.refetch()} />
      ) : !cards.length ? (
        <section className="rounded-lg border border-border bg-surface-1">
          <EmptyState pose="wave" title="It's just you so far" description="Invite your crew to see what they're playing." action={canInvite ? { label: "Invite", onClick: () => setDialog("invite") } : undefined} />
        </section>
      ) : (
        <>
          {!!live.length && (
            <Shelf title="Live now" live count={live.length} itemWidth="clamp(148px, 40vw, 200px)">
              {live.map((card, i) => <FeedCard key={card.friend.id} card={card} index={i} sharedLayout={false} onSend={(x) => openSend({ song: songFromCard(x) })} />)}
            </Shelf>
          )}
          {!!rest.length && (
            <section aria-labelledby="circle-feed-h" className="flex flex-col gap-3">
              <h2 id="circle-feed-h" className="font-display text-xl font-semibold">{live.length ? "Everyone else" : "The circle"}</h2>
              <ul className="grid grid-cols-[repeat(auto-fill,minmax(148px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(184px,1fr))]">
                {rest.map((card, i) => (
                  <li key={card.friend.id}><FeedCard card={card} index={i} sharedLayout={false} onSend={(x) => openSend({ song: songFromCard(x) })} /></li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      <section aria-labelledby="members-h" className="flex flex-col gap-3">
        <h2 id="members-h" className="font-display text-xl font-semibold">Members</h2>
        <ul className="flex flex-col">
          {c.members?.map((m) => (
            <PersonRow
              key={m.user.id}
              person={m.user}
              actions={
                <>
                  {m.role !== "member" && <span className="font-mono text-xs text-text-muted">{m.role === "owner" ? "Owner" : "Admin"}</span>}
                  {m.user.id !== me?.id && <MemberActions circle={c} userId={m.user.id} name={m.user.display_name} role={m.role} myRole={myRole} />}
                </>
              }
            />
          ))}
        </ul>
      </section>

      {canInvite && <InviteSheet circle={c} open={dialog === "invite"} onClose={() => setDialog(null)} />}
      {isAdmin && dialog === "settings" && <SettingsDialog circle={c} open onClose={() => setDialog(null)} />}
      <Dialog
        open={dialog === "leave"}
        onClose={() => setDialog(null)}
        title={soleOwner ? "Hand it over first" : `Leave ${c.name}?`}
        description={
          soleOwner
            ? "You own this circle. Make someone else the owner from their options in Members, then you can leave."
            : c.member_count === 1
              ? "You're the last one here, so the circle closes."
              : "You can rejoin only with a new invite."
        }
        footer={
          soleOwner ? (
            <Button onClick={() => setDialog(null)}>Got it</Button>
          ) : (
            <>
              <Button variant="ghost" onClick={() => setDialog(null)}>Cancel</Button>
              <Button
                variant="danger"
                loading={leave.isPending}
                loadingLabel="Leaving"
                onClick={() =>
                  leave.mutate(c.id, {
                    onSuccess: () => {
                      toast.toast({ title: `You left ${c.name}`, tone: "success" });
                      router.push("/circles");
                    },
                  })
                }
              >
                Leave
              </Button>
            </>
          )
        }
      />
    </div>
  );
}
