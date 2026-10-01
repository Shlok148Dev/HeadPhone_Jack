"use client";

import { motion } from "motion/react";
import { useSearchParams } from "next/navigation";
import { lazy, Suspense, useState } from "react";
import { Blip, Button, EmptyState, ErrorState, Skeleton, cn, useToast, Artwork } from "@/components/ds";
import { TextField } from "@/components/app/forms";
import { OpenLink } from "@/components/app/OpenLink";
import { DownloadRecap, RecapCard, monthName } from "@/components/app/RecapCard";
import { useMotionSafe } from "@/lib/motion";
import { useSongSearch } from "@/lib/sends";
import { useBattleActions, useRituals, useSeason, type Battle, type Recap, type ResultRow } from "@/lib/trust";

function when(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", { weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata" });
}

const PHASE_LINE: Record<Battle["phase"], (b: Battle) => string> = {
  upcoming: (b) => `Nominations open ${when(b.nominate_opens)}`,
  nominating: (b) => `Nominate until ${when(b.vote_opens)} · ${b.nomination_count} in`,
  voting: (b) => `Vote until ${when(b.closes_at)} · ${b.votes_left} of 3 votes left`,
  closed: () => "Results are in",
  skipped: () => "Skipped this week. The season carries on next week.",
};

function Podium({ rows }: { rows: ResultRow[] }) {
  const m = useMotionSafe();
  const top = rows.filter((r) => r.votes > 0).slice(0, 3);
  if (!top.length) return <p className="text-sm text-text-muted">No votes this week.</p>;
  // Visual order 2-1-3 like a podium; the list below is the reading order.
  const order = [top[1], top[0], top[2]].filter(Boolean) as ResultRow[];
  const height = { 1: "h-28", 2: "h-20", 3: "h-14" } as Record<number, string>;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-end justify-center gap-3" aria-hidden>
        {order.map((r) => (
          <motion.div
            key={r.nomination_id}
            className="flex w-24 flex-col items-center gap-2"
            initial={m.reduced ? { opacity: 0 } : { opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...m.spring.bouncy, delay: m.reduced ? 0 : (3 - r.rank) * 0.25 }}
          >
            <div className="h-16 w-16 overflow-hidden rounded-md">
              <Artwork url={r.artwork_small ?? r.artwork_url ?? null} seed={`${r.artist}|${r.title}`.toLowerCase()} alt="" rounded="none" />
            </div>
            <p className="w-full truncate text-center text-xs font-medium">{r.user.display_name}</p>
            <div className={cn("flex w-full items-start justify-center rounded-t-md pt-2 font-display text-xl font-semibold", height[r.rank] ?? "h-12", r.rank === 1 ? "bg-[var(--brand-violet)] text-white" : "bg-surface-3")}>
              {r.rank}
            </div>
          </motion.div>
        ))}
      </div>
      <ol className="flex flex-col gap-1 text-sm" aria-label="Results">
        {rows.map((r) => (
          <li key={r.nomination_id} className="flex items-center gap-2">
            <span className="w-5 font-mono text-text-muted">{r.rank}</span>
            <span className="min-w-0 flex-1 truncate">{r.title} · {r.artist} <span className="text-text-muted">by {r.user.display_name}</span></span>
            <span className="font-mono text-xs text-text-muted">{r.votes} {r.votes === 1 ? "vote" : "votes"}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Nominate({ battle }: { battle: Battle }) {
  const [q, setQ] = useState("");
  const results = useSongSearch(q);
  const { nominate } = useBattleActions();
  const toast = useToast();
  return (
    <div className="flex flex-col gap-2">
      {battle.my_nomination && (
        <p className="text-sm">Your pick: <span className="font-medium">{battle.my_nomination.title}</span> · {battle.my_nomination.artist}</p>
      )}
      <TextField label={battle.my_nomination ? "Change your pick" : "Nominate a song"} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Song or artist" />
      {q.trim().length >= 2 && (
        <ul className="flex flex-col" aria-label="Search results">
          {(results.data ?? []).slice(0, 5).map((s) => (
            <li key={`${s.artist}|${s.title}`} className="flex min-h-12 items-center gap-3">
              <span className="min-w-0 flex-1 truncate text-sm">{s.title} · <span className="text-text-muted">{s.artist}</span></span>
              <Button
                variant="secondary"
                onClick={() =>
                  nominate.mutate(
                    { circleId: battle.circle.id, song: s },
                    { onSuccess: () => { setQ(""); toast.toast({ title: "Nominated", tone: "success" }); }, onError: (e) => toast.toast({ title: e.message, tone: "danger" }) },
                  )
                }
              >
                Nominate
              </Button>
            </li>
          ))}
          {results.data?.length === 0 && <li className="text-sm text-text-muted">No songs found.</li>}
        </ul>
      )}
    </div>
  );
}

function Vote({ battle }: { battle: Battle }) {
  const { vote } = useBattleActions();
  const toast = useToast();
  if (!battle.nominations.length) return <p className="text-sm text-text-muted">No nominations this week.</p>;
  return (
    <ul className="flex flex-col" aria-label="Nominations">
      {battle.nominations.map((n) => (
        <li key={n.id} className="flex min-h-14 flex-wrap items-center gap-3 border-b border-border py-2 last:border-0">
          <div className="h-10 w-10 shrink-0 overflow-hidden rounded-sm">
            <Artwork url={n.artwork_small ?? n.artwork_url ?? null} seed={`${n.artist}|${n.title}`.toLowerCase()} alt="" rounded="none" />
          </div>
          <span className="min-w-0 flex-1 truncate text-sm">{n.title} · <span className="text-text-muted">{n.artist}</span></span>
          <OpenLink song={n} compact />
          {n.mine ? (
            <span className="px-3 font-mono text-xs text-text-muted">Your pick</span>
          ) : (
            <Button
              variant={n.my_vote ? "primary" : "secondary"}
              aria-pressed={n.my_vote}
              aria-label={`${n.my_vote ? "Remove vote for" : "Vote for"} ${n.title}`}
              disabled={!n.my_vote && battle.votes_left === 0}
              onClick={() => vote.mutate({ battleId: battle.id, nominationId: n.id, on: !n.my_vote }, { onError: (e) => toast.toast({ title: e.message, tone: "danger" }) })}
            >
              {n.my_vote ? "Voted" : "Vote"}
            </Button>
          )}
        </li>
      ))}
    </ul>
  );
}

function SeasonTable({ circleId }: { circleId: string }) {
  const [open, setOpen] = useState(false);
  const season = useSeason(circleId, open);
  return (
    <div>
      <Button variant="ghost" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? "Hide season" : "Season table"}</Button>
      {open && season.data && (
        <div className="mt-2 flex flex-col gap-1 text-sm">
          <p className="font-mono text-xs text-text-muted">{season.data.weeks} of {season.data.of} weeks played</p>
          {season.data.table.length ? (
            <ol>
              {season.data.table.map((r, i) => (
                <li key={r.user.id} className="flex justify-between"><span><span className="font-mono text-text-muted">{i + 1}</span> {r.user.display_name}</span><span className="font-mono">{r.wins} {r.wins === 1 ? "win" : "wins"}</span></li>
              ))}
            </ol>
          ) : (
            <p className="text-text-muted">No wins yet this season.</p>
          )}
        </div>
      )}
    </div>
  );
}

function BattleCard({ battle }: { battle: Battle }) {
  const { skip } = useBattleActions();
  return (
    <article aria-labelledby={`b-${battle.id}`} className="flex flex-col gap-4 rounded-lg border border-border bg-surface-1 p-5">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-mono text-xs uppercase tracking-wide text-text-muted">Weekly battle</p>
          <h2 id={`b-${battle.id}`} className="font-display text-xl font-semibold">{battle.circle.name}</h2>
          <p className="text-sm text-text-muted">{PHASE_LINE[battle.phase](battle)}</p>
        </div>
        {battle.can_skip && <Button variant="ghost" onClick={() => skip.mutate(battle.circle.id)}>Skip this week</Button>}
      </header>
      {battle.phase === "nominating" && <Nominate battle={battle} />}
      {battle.phase === "voting" && <Vote battle={battle} />}
      {battle.phase === "closed" && battle.results && <Podium rows={battle.results} />}
      <SeasonTable circleId={battle.circle.id} />
    </article>
  );
}

const RecapStory = lazy(() => import("@/components/app/RecapStory").then((m) => ({ default: m.RecapStory })));

function RecapSection({ recap }: { recap: Recap }) {
  const { share } = useBattleActions();
  const toast = useToast();
  const params = useSearchParams();
  const [story, setStory] = useState(params.get("story") === "1");
  const link = recap.share_url ? `${window.location.origin}${recap.share_url}` : null;
  return (
    <section id="recap" aria-labelledby="recap-h" className="flex flex-col gap-4">
      <h2 id="recap-h" className="font-display text-xl font-semibold">Your {monthName(recap.month)} recap</h2>
      <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
        <RecapCard data={recap.data} />
        <div className="flex flex-col gap-3">
          <Button onClick={() => setStory(true)} leadingIcon={<span aria-hidden>▶</span>}>Play your recap</Button>
          <p className="text-sm text-text-muted">Sharing is off until you turn it on. Anyone with the link sees this card and your first name.</p>
          {link ? (
            <>
              <input readOnly value={link} aria-label="Recap link" className="min-h-11 rounded-md border border-border bg-surface-2 px-3 font-mono text-xs" />
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" onClick={() => void navigator.clipboard?.writeText(link).then(() => toast.toast({ title: "Link copied", tone: "success" }))}>Copy link</Button>
                <Button variant="ghost" onClick={() => share.mutate({ id: recap.id, on: false })}>Stop sharing</Button>
              </div>
            </>
          ) : (
            <Button onClick={() => share.mutate({ id: recap.id, on: true })}>Share a link</Button>
          )}
          <DownloadRecap data={recap.data} />
          {story && (
            <Suspense fallback={null}>
              <RecapStory data={recap.data} onClose={() => setStory(false)} />
            </Suspense>
          )}
        </div>
      </div>
    </section>
  );
}

/** Rituals (UX_SPEC §5.10; JNG-09-01…06, 08). */
export default function RitualsPage() {
  const rituals = useRituals();
  if (rituals.isLoading)
    return (
      <div className="flex flex-col gap-4" aria-busy="true">
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-56" rounded="lg" />
      </div>
    );
  if (rituals.isError || !rituals.data) return <ErrorState message="Couldn't load your rituals." onRetry={() => void rituals.refetch()} />;
  const { battles, recap } = rituals.data;
  return (
    <div className="flex flex-col gap-10">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Rituals</h1>
      {recap ? (
        <RecapSection recap={recap} />
      ) : (
        <section className="flex items-center gap-3 rounded-lg border border-border bg-surface-1 p-4">
          <Blip pose="sleepy" size={48} decorative />
          <p className="text-sm text-text-muted">Your first monthly recap arrives at the start of next month.</p>
        </section>
      )}
      <section aria-label="Battles" className="flex flex-col gap-4">
        {battles.length ? (
          <div className="grid gap-4 lg:grid-cols-2">{battles.map((b) => <BattleCard key={b.id} battle={b} />)}</div>
        ) : (
          <EmptyState pose="wave" title="Battles happen in circles" description="Join or start a circle to battle over the best song each week." />
        )}
      </section>
    </div>
  );
}
