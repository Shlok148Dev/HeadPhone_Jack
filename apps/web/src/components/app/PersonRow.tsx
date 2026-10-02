"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { Avatar, Button, Dialog, IconButton, Icons, PlatformMark, Pulse, cn, useToast, type FeedCardData } from "@/components/ds";
import { pulseOf } from "@/components/app/Presence";
import { songFromCard, useOpenSend } from "@/lib/send";
import { useSocialActions, type Person } from "@/lib/social";

const REASONS = [
  ["spam", "Spam"],
  ["harassment", "Harassment or bullying"],
  ["hate", "Hate speech"],
  ["impersonation", "Pretending to be someone else"],
  ["inappropriate", "Inappropriate name or content"],
  ["other", "Something else"],
] as const;

/** A person, with what they are playing when a feed card is known (the Pulse, then song and freshness). */
export function PersonRow({ person, actions, card }: { person: Person; actions?: ReactNode; card?: FeedCardData }) {
  const openSend = useOpenSend();
  const state = card ? pulseOf(card, Date.now()) : "none";
  const rec = card?.state !== "HIDDEN" ? card?.recording : null;
  return (
    <li className="group flex min-h-16 items-center gap-3 rounded-lg px-2 py-2 hover:bg-surface-2">
      {card ? (
        <Pulse state={state} name={person.display_name} url={card.friend.avatar_url} seed={person.id} size={44} />
      ) : (
        <Avatar name={person.display_name} seed={person.id} size={44} decorative />
      )}
      <div className="min-w-0 flex-1">
        <Link href={`/u/${person.username}`} className="block truncate font-medium hover:underline focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]">
          {person.display_name}
        </Link>
        {rec ? (
          <>
            <p className="truncate text-sm text-text-muted">
              <span className="text-text">{rec.title}</span> · {rec.artist}
            </p>
            <p className={cn("flex min-w-0 items-center gap-1.5 font-mono text-xs", state === "live" ? "text-live-text" : "text-text-subtle")}>
              {card!.platform !== "UNKNOWN" && card!.platform !== "AMAZON_MUSIC" && <PlatformMark platform={card!.platform} size={12} />}
              <span className="truncate">{card!.freshness_label}</span>
            </p>
          </>
        ) : (
          <p className="truncate font-mono text-xs text-text-muted">@{person.username}</p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-1">
        {rec && (
          <IconButton label={`Send ${person.display_name} something back`} className="opacity-70 group-hover:opacity-100 focus-visible:opacity-100" onClick={() => openSend({ song: songFromCard(card!) })}>
            <Icons.Send size={16} />
          </IconButton>
        )}
        {actions}
      </div>
    </li>
  );
}

/** Add / Requested / Friends button driven by the relationship (JNG-02-02). */
export function RelationshipButton({ person }: { person: Person }) {
  const { add } = useSocialActions();
  const toast = useToast();
  const [sent, setSent] = useState(false); // optimistic
  if (person.relationship === "friends") return <span className="px-3 font-mono text-xs text-text-muted">Friends</span>;
  if (person.relationship === "outgoing" || sent) return <span className="px-3 font-mono text-xs text-text-muted">Requested</span>;
  return (
    <Button
     
      variant={person.relationship === "incoming" ? "primary" : "secondary"}
      onClick={() => {
        setSent(true);
        add.mutate(person.id, {
          onError: (e) => {
            setSent(false);
            toast.toast({ title: e.message, tone: "danger" });
          },
        });
      }}
    >
      {person.relationship === "incoming" ? "Accept" : "Add"}
    </Button>
  );
}

/** Remove, block and report, each confirmed (JNG-02-03, JNG-02-04, JNG-12-01). */
export function PersonMenu({ person, canRemove }: { person: Person; canRemove: boolean }) {
  const { remove, block, report } = useSocialActions();
  const toast = useToast();
  const [dialog, setDialog] = useState<null | "menu" | "remove" | "block" | "report">(null);
  const [reason, setReason] = useState<string>("");
  const [details, setDetails] = useState("");
  const name = person.display_name;
  const close = () => setDialog(null);

  return (
    <>
      <IconButton label={`More options for ${name}`} onClick={() => setDialog("menu")}>
        <Icons.More size={18} />
      </IconButton>
      <Dialog open={dialog === "menu"} onClose={close} title={name}>
        <div className="flex flex-col gap-2">
          {canRemove && (
            <Button variant="secondary" onClick={() => setDialog("remove")}>
              Remove friend
            </Button>
          )}
          <Button variant="secondary" onClick={() => setDialog("block")}>
            Block {name}
          </Button>
          <Button variant="ghost" onClick={() => setDialog("report")}>
            Report {name}
          </Button>
        </div>
      </Dialog>
      <Dialog
        open={dialog === "remove"}
        onClose={close}
        title={`Remove ${name}?`}
        description="They stop seeing what you play right away. They won't be told."
        footer={
          <>
            <Button variant="ghost" onClick={close}>Cancel</Button>
            <Button variant="danger" loading={remove.isPending} loadingLabel="Removing"
              onClick={() => remove.mutate(person.id, { onSuccess: () => { close(); toast.toast({ title: `Removed ${name}`, tone: "success" }); } })}>
              Remove
            </Button>
          </>
        }
      />
      <Dialog
        open={dialog === "block"}
        onClose={close}
        title={`Block ${name}?`}
        description="You won't see each other anywhere on Jingle, and any friendship or request ends. They won't be told."
        footer={
          <>
            <Button variant="ghost" onClick={close}>Cancel</Button>
            <Button variant="danger" loading={block.isPending} loadingLabel="Blocking"
              onClick={() => block.mutate(person.id, { onSuccess: () => { close(); toast.toast({ title: `Blocked ${name}`, tone: "success" }); } })}>
              Block
            </Button>
          </>
        }
      />
      <Dialog
        open={dialog === "report"}
        onClose={close}
        title={`Report ${name}`}
        description="Reports are private. Our moderators review every one."
        footer={
          <>
            <Button variant="ghost" onClick={close}>Cancel</Button>
            <Button disabled={!reason} loading={report.isPending} loadingLabel="Sending"
              onClick={() => report.mutate({ userId: person.id, reason, details }, { onSuccess: () => { close(); toast.toast({ title: "Thanks. We'll take a look.", tone: "success" }); } })}>
              Send report
            </Button>
          </>
        }
      >
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 text-sm font-medium">What's wrong?</legend>
          {REASONS.map(([v, l]) => (
            <label key={v} className="flex min-h-11 items-center gap-3 text-sm">
              <input type="radio" name="reason" value={v} checked={reason === v} onChange={() => setReason(v)} className="accent-[var(--brand-violet)]" />
              {l}
            </label>
          ))}
        </fieldset>
        <label className="mt-3 flex flex-col gap-1.5 text-sm">
          Anything else? (optional)
          <textarea
            maxLength={1000}
            value={details}
            onChange={(e) => setDetails(e.target.value)}
            className="min-h-20 rounded-md border border-border bg-surface-2 p-3 text-sm"
          />
        </label>
      </Dialog>
    </>
  );
}
