"use client";

import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { Avatar, Blip, CompatibilityMeter, ErrorState, PLATFORM_NAMES, Skeleton, seedGradient, type Platform } from "@/components/ds";
import { RelationshipButton } from "@/components/app/PersonRow";
import { monthLabel, useCompatibility, useMyStats, useProfile, useTimeline, type Month } from "@/lib/insights";

/** One-hue horizontal bars with direct labels (single series: no legend needed). */
function ShareBars({ title, rows }: { title: string; rows: { label: string; value: number; display: string }[] }) {
  if (!rows.length) return null;
  const max = Math.max(...rows.map((r) => r.value), 1e-9);
  return (
    <section aria-labelledby={`${title}-h`} className="flex flex-col gap-2">
      <h3 id={`${title}-h`} className="text-sm font-medium text-text-muted">{title}</h3>
      <ul className="flex flex-col gap-2">
        {rows.map((r) => (
          <li key={r.label} className="grid grid-cols-[minmax(0,8rem)_1fr_auto] items-center gap-3 text-sm">
            <span className="truncate">{r.label}</span>
            <span className="h-2 rounded-full bg-surface-3" aria-hidden>
              <span className="block h-2 rounded-full bg-[var(--brand-violet)]" style={{ width: `${(100 * r.value) / max}%` }} />
            </span>
            <span className="font-mono text-xs text-text-muted">{r.display}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** JNG-08-03: plays per month for 12 months; hover/focus a bar for its top artist and genres. */
function Timeline({ months }: { months: Month[] }) {
  const [active, setActive] = useState<number | null>(null);
  const max = Math.max(...months.map((m) => m.plays), 1);
  const shown = active !== null ? months[active] : null;
  return (
    <section aria-labelledby="timeline-h" className="flex flex-col gap-3">
      <h2 id="timeline-h" className="font-display text-xl font-semibold">Your year in music</h2>
      <div className="flex h-40 items-end gap-1 border-b border-border" aria-hidden>
        {months.map((m, i) => (
          <div
            key={m.month}
            onMouseEnter={() => setActive(i)}
            onMouseLeave={() => setActive(null)}
            className="flex h-full flex-1 items-end"
          >
            <span
              className={`block w-full rounded-t-[4px] transition-colors ${active === i ? "bg-[var(--brand-cyan)]" : "bg-[var(--brand-violet)]"}`}
              style={{ height: m.plays ? `${Math.max(3, (100 * m.plays) / max)}%` : "0%" }}
            />
          </div>
        ))}
      </div>
      <div className="flex gap-1" aria-hidden>
        {months.map((m) => (
          <span key={m.month} className="flex-1 text-center font-mono text-[10px] text-text-muted">{monthLabel(m.month).slice(0, 1)}</span>
        ))}
      </div>
      <p className="min-h-5 text-sm text-text-muted" aria-live="polite">
        {shown
          ? `${monthLabel(shown.month)}: ${shown.plays} plays${shown.top_artist ? ` · most played ${shown.top_artist}` : ""}${shown.genres.length ? ` · ${shown.genres.map((g) => g.name).join(", ")}` : ""}`
          : "Hover a month to see what you played most."}
      </p>
      <table className="sr-only">
        <caption>Plays per month</caption>
        <thead>
          <tr><th>Month</th><th>Plays</th><th>Most played</th><th>Genres</th></tr>
        </thead>
        <tbody>
          {months.map((m) => (
            <tr key={m.month}>
              <td>{m.month}</td><td>{m.plays}</td><td>{m.top_artist ?? "—"}</td><td>{m.genres.map((g) => g.name).join(", ") || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function MyInsights() {
  const stats = useMyStats(true);
  const timeline = useTimeline(true);
  if (stats.isLoading) return <Skeleton className="h-64" rounded="lg" />;
  if (stats.isError || !stats.data) return <ErrorState message="Couldn't load your stats." onRetry={() => void stats.refetch()} />;
  const s = stats.data;
  if (!s.ready)
    return (
      <section className="flex flex-col items-center gap-3 rounded-lg border border-border bg-surface-1 p-8 text-center">
        <Blip pose="sleepy" size={80} decorative />
        <h2 className="font-display text-xl font-semibold">Your stats are on their way</h2>
        <p className="max-w-md text-sm text-text-muted">
          Stats build over your first 2–4 weeks of listening.
          {s.ready_in_days > 0 ? ` Check back in about ${s.ready_in_days} day${s.ready_in_days === 1 ? "" : "s"}.` : ""}
        </p>
      </section>
    );
  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="month-h" className="flex flex-col gap-4">
        <h2 id="month-h" className="font-display text-xl font-semibold">Last 30 days</h2>
        <dl className="grid grid-cols-2 gap-4 sm:max-w-md">
          <div className="rounded-lg border border-border bg-surface-1 p-4">
            <dt className="text-sm text-text-muted">Minutes listened</dt>
            <dd className="font-display text-3xl font-semibold">about {s.minutes_30d?.toLocaleString()}</dd>
          </div>
          <div className="rounded-lg border border-border bg-surface-1 p-4">
            <dt className="text-sm text-text-muted">Plays</dt>
            <dd className="font-display text-3xl font-semibold">{s.plays_30d?.toLocaleString()}</dd>
          </div>
        </dl>
        <div className="grid gap-8 md:grid-cols-3">
          <ShareBars title="Top artists" rows={(s.top_artists ?? []).map((a) => ({ label: a.name, value: a.plays, display: `${a.plays}` }))} />
          <ShareBars title="Genres" rows={(s.genres ?? []).map((g) => ({ label: g.name, value: g.share, display: `${Math.round(100 * g.share)}%` }))} />
          <ShareBars
            title="Where you listen"
            rows={(s.platforms ?? []).map((p) => ({
              label: p.platform === "UNKNOWN" ? "Other" : PLATFORM_NAMES[p.platform as Exclude<Platform, "UNKNOWN">] ?? p.platform,
              value: p.share,
              display: `${Math.round(100 * p.share)}%`,
            }))}
          />
        </div>
        {s.excluded_note && <p className="text-xs text-text-muted">{s.excluded_note}</p>}
      </section>
      {timeline.data && <Timeline months={timeline.data} />}
    </div>
  );
}

function FriendCompat({ userId, name }: { userId: string; name: string }) {
  const compat = useCompatibility(userId, true);
  if (compat.isLoading) return <Skeleton className="h-40" rounded="lg" />;
  if (compat.isError || !compat.data) return <ErrorState message="Couldn't load your taste match." onRetry={() => void compat.refetch()} />;
  const c = compat.data;
  return (
    <section aria-labelledby="compat-h" className="flex flex-col gap-4 rounded-lg border border-border bg-surface-1 p-5">
      <h2 id="compat-h" className="font-display text-xl font-semibold">You and {name}</h2>
      <CompatibilityMeter
        score={c.score ?? 0}
        breakdown={c.ready ? c.breakdown.map((f) => ({ label: f.label, value: f.value, detail: f.detail })) : []}
      />
      <ul className="flex flex-col gap-1 text-sm text-text-muted">
        {c.notes.map((n) => <li key={n}>{n}</li>)}
        {c.ready && !c.calibrated && <li>Scores settle as more friends join Jingle.</li>}
      </ul>
      {c.shared_artists.length > 0 && (
        <p className="text-sm"><span className="text-text-muted">You both play </span>{c.shared_artists.slice(0, 5).join(", ")}</p>
      )}
    </section>
  );
}

/** Profile (UX_SPEC; JNG-08-01/02 for friends, JNG-08-03/06/07 for me). */
export default function ProfilePage() {
  const { username } = useParams<{ username: string }>();
  const profile = useProfile(username);
  const [from, to] = useMemo(() => seedGradient(username, "deep"), [username]);

  if (profile.isLoading) return <Skeleton className="h-48" rounded="lg" />;
  if (profile.isError || !profile.data) return <ErrorState title="We couldn't find that person." message="They may have changed their username." />;
  const p = profile.data;
  const name = p.person.display_name;
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-wrap items-end gap-5 rounded-xl px-5 pb-6 pt-10 md:px-8" style={{ background: `linear-gradient(160deg, ${from}, ${to})` }}>
        <Avatar name={name} seed={p.person.id} size={96} />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="font-mono text-xs uppercase tracking-wide text-white/80">{p.is_me ? "You" : "Profile"}</p>
          <h1 className="truncate font-display text-3xl font-semibold tracking-tight text-white md:text-5xl">{name}</h1>
          <p className="font-mono text-xs text-white/80">@{p.person.username}{p.college ? ` · ${p.college}` : ""}{p.city ? ` · ${p.city}` : ""}</p>
        </div>
        {!p.is_me && (
          <div className="rounded-full bg-surface-1">
            <RelationshipButton person={p.person} />
          </div>
        )}
      </header>
      {p.is_me ? <MyInsights /> : p.compatibility_available ? <FriendCompat userId={p.person.id} name={name} /> : (
        <p className="text-sm text-text-muted">Add {name} as a friend to compare your taste.</p>
      )}
    </div>
  );
}
