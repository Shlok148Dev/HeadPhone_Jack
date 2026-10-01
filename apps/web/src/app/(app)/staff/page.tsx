"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, EmptyState, ErrorState, Skeleton, Tabs, useToast } from "@/components/ds";
import { TextField } from "@/components/app/forms";
import { api, json } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useStaff } from "@/lib/trust";

interface ReportRow {
  id: string;
  target_type: string;
  reason: string;
  details: string;
  created_at: string;
  reporter: string | null;
  content: string;
  responsible: { id: string; username: string; display_name: string } | null;
  other_reports: number;
  past_actions: number;
}

function useStaffAction() {
  const qc = useQueryClient();
  const toast = useToast();
  return async (path: string, method: string, body?: unknown, done?: string) => {
    try {
      await api(path, { method, ...(body ? json(body) : {}) });
      if (done) toast.toast({ title: done, tone: "success" });
      await qc.invalidateQueries({ queryKey: ["staff"] });
    } catch (e) {
      toast.toast({ title: e instanceof Error ? e.message : "That didn't work.", tone: "danger" });
    }
  };
}

function Loading<T>({ q, children }: { q: { isLoading: boolean; isError: boolean; data?: T; refetch: () => unknown }; children: (d: T) => React.ReactNode }) {
  if (q.isLoading) return <Skeleton className="h-40" rounded="lg" />;
  if (q.isError || !q.data) return <ErrorState message="Couldn't load this." onRetry={() => void q.refetch()} />;
  return <>{children(q.data)}</>;
}

function ReportCard({ r }: { r: ReportRow }) {
  const act = useStaffAction();
  const [reason, setReason] = useState("");
  const [days, setDays] = useState(3);
  const decide = (kind: string) =>
    void act(`/mod/reports/${r.id}/action`, "POST", { kind, reason, days: kind === "mute" || kind === "suspend" ? days : undefined }, kind === "dismiss" ? "Dismissed" : "Action recorded");
  return (
    <li className="flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-4">
      <div className="flex flex-wrap justify-between gap-2">
        <p className="font-medium">{r.reason} · {r.target_type}</p>
        <p className="font-mono text-xs text-text-muted">{new Date(r.created_at).toLocaleString()} · by @{r.reporter ?? "deleted"}</p>
      </div>
      <p className="text-sm">{r.content}</p>
      {r.details && <p className="text-sm text-text-muted">&ldquo;{r.details}&rdquo;</p>}
      <p className="font-mono text-xs text-text-muted">
        Responsible: {r.responsible ? `@${r.responsible.username}` : "—"} · {r.other_reports} other reports · {r.past_actions} past actions
      </p>
      <div className="flex flex-wrap items-end gap-2">
        <TextField label="Reason (the person sees it)" value={reason} onChange={(e) => setReason(e.target.value)} />
        <label className="flex flex-col gap-1 text-sm">
          Days
          <input type="number" min={1} max={365} value={days} onChange={(e) => setDays(Number(e.target.value) || 1)} className="min-h-11 w-20 rounded-md border border-border bg-surface-2 px-3" />
        </label>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="ghost" onClick={() => decide("dismiss")}>Dismiss</Button>
        <Button variant="secondary" disabled={!reason.trim()} onClick={() => decide("warn")}>Warn</Button>
        <Button variant="secondary" disabled={!reason.trim()} onClick={() => decide("mute")}>Mute</Button>
        <Button variant="secondary" disabled={!reason.trim()} onClick={() => decide("suspend")}>Suspend</Button>
        <Button variant="danger" disabled={!reason.trim()} onClick={() => decide("ban")}>Ban</Button>
      </div>
    </li>
  );
}

function Reports() {
  const q = useStaff<{ results: ReportRow[] }>("/mod/reports");
  return (
    <Loading q={q}>
      {(d) => (d.results.length ? <ul className="flex flex-col gap-3">{d.results.map((r) => <ReportCard key={r.id} r={r} />)}</ul> : <EmptyState pose="wave" title="No open reports" />)}
    </Loading>
  );
}

function Appeals() {
  const q = useStaff<{ results: { id: string; text: string; user: { username: string }; action: { kind: string; reason: string } }[] }>("/mod/appeals");
  const act = useStaffAction();
  return (
    <Loading q={q}>
      {(d) =>
        d.results.length ? (
          <ul className="flex flex-col gap-3">
            {d.results.map((a) => (
              <li key={a.id} className="flex flex-col gap-2 rounded-lg border border-border bg-surface-1 p-4">
                <p className="font-medium">@{a.user.username} · {a.action.kind}: {a.action.reason}</p>
                <p className="text-sm">&ldquo;{a.text}&rdquo;</p>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => void act(`/mod/appeals/${a.id}/decide`, "POST", { overturn: true }, "Overturned")}>Overturn</Button>
                  <Button variant="ghost" onClick={() => void act(`/mod/appeals/${a.id}/decide`, "POST", { overturn: false }, "Upheld")}>Uphold</Button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState pose="sleepy" title="No open appeals" />
        )
      }
    </Loading>
  );
}

function Audit() {
  const q = useStaff<{ results: { at: string; actor: string | null; action: string; target: string }[] }>("/mod/audit");
  return (
    <Loading q={q}>
      {(d) => (
        <table className="w-full text-sm">
          <caption className="sr-only">Audit log</caption>
          <thead><tr className="text-left text-text-muted"><th className="py-2 font-normal">When</th><th className="font-normal">Who</th><th className="font-normal">Action</th><th className="font-normal">Target</th></tr></thead>
          <tbody>
            {d.results.map((e, i) => (
              <tr key={i} className="border-t border-border"><td className="py-2 font-mono text-xs">{new Date(e.at).toLocaleString()}</td><td>{e.actor ?? "—"}</td><td>{e.action}</td><td className="font-mono text-xs">{e.target}</td></tr>
            ))}
          </tbody>
        </table>
      )}
    </Loading>
  );
}

function Flags() {
  const q = useStaff<{ results: { name: string; enabled: boolean; note: string }[] }>("/admin/flags");
  const act = useStaffAction();
  return (
    <Loading q={q}>
      {(d) => (
        <ul className="flex flex-col">
          {d.results.map((f) => (
            <li key={f.name} className="flex min-h-14 items-center justify-between gap-4 border-b border-border py-2">
              <span>
                <span className="block font-mono text-sm">{f.name}</span>
                {f.note && <span className="text-xs text-text-muted">{f.note}</span>}
              </span>
              <input type="checkbox" role="switch" aria-label={f.name} checked={f.enabled} onChange={(e) => void act("/admin/flags", "PUT", { name: f.name, enabled: e.target.checked }, `${f.name} ${e.target.checked ? "on" : "off"}`)} className="h-5 w-5 accent-[var(--brand-violet)]" />
            </li>
          ))}
        </ul>
      )}
    </Loading>
  );
}

function Budgets() {
  const q = useStaff<{ available: boolean; sources: { source: string; capacity: number; per_second: number; used_last_minute: number; used_last_hour: number; rejected_last_hour: number }[] }>("/admin/budgets");
  return (
    <Loading q={q}>
      {(d) =>
        !d.available ? (
          <p className="text-sm text-text-muted">Ingest isn&rsquo;t answering right now. Budgets will show when it&rsquo;s back.</p>
        ) : (
          <table className="w-full text-sm">
            <caption className="sr-only">Per-source rate budgets and live usage</caption>
            <thead><tr className="text-left text-text-muted"><th className="py-2 font-normal">Source</th><th className="font-normal">Budget</th><th className="font-normal">Last minute</th><th className="font-normal">Last hour</th><th className="font-normal">Refused (hour)</th></tr></thead>
            <tbody>
              {d.sources.map((s) => (
                <tr key={s.source} className="border-t border-border">
                  <td className="py-2">{s.source}</td><td className="font-mono">{s.per_second}/s (burst {s.capacity})</td><td className="font-mono">{s.used_last_minute}</td><td className="font-mono">{s.used_last_hour}</td><td className="font-mono">{s.rejected_last_hour}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      }
    </Loading>
  );
}

function Allowlist() {
  const q = useStaff<{ emails: string[]; max: number; from_env: string[] }>("/admin/allowlist");
  const act = useStaffAction();
  const [email, setEmail] = useState("");
  return (
    <Loading q={q}>
      {(d) => (
        <div className="flex flex-col gap-4">
          <p className="text-sm text-text-muted">Spotify&rsquo;s development mode allows {d.max} testers on the direct route. Everyone else connects through the Last.fm link.</p>
          <ul className="flex flex-col">
            {d.from_env.map((e) => <li key={e} className="py-1 font-mono text-sm">{e} <span className="text-xs text-text-muted">(.env)</span></li>)}
            {d.emails.map((e) => (
              <li key={e} className="flex items-center justify-between py-1">
                <span className="font-mono text-sm">{e}</span>
                <Button variant="ghost" onClick={() => void act("/admin/allowlist", "DELETE", { email: e }, "Removed")}>Remove</Button>
              </li>
            ))}
          </ul>
          <div className="flex items-end gap-2">
            <TextField label="Add a tester's email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <Button disabled={!email.includes("@")} onClick={() => void act("/admin/allowlist", "POST", { email }, "Added").then(() => setEmail(""))}>Add</Button>
          </div>
        </div>
      )}
    </Loading>
  );
}

/** Staff console (EP-12: JNG-12-02…06, 08). */
export default function StaffPage() {
  const { me } = useAuth();
  const [tab, setTab] = useState("reports");
  if (!me?.is_staff) return <ErrorState title="Staff only" message="This page is for Jingle's moderators." />;
  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Staff console</h1>
      <Tabs
        label="Staff console"
        value={tab}
        onChange={setTab}
        items={[
          { id: "reports", label: "Reports", content: <Reports /> },
          { id: "appeals", label: "Appeals", content: <Appeals /> },
          { id: "audit", label: "Audit log", content: <Audit /> },
          { id: "flags", label: "Flags", content: <Flags /> },
          { id: "budgets", label: "Budgets", content: <Budgets /> },
          { id: "allowlist", label: "Spotify testers", content: <Allowlist /> },
        ]}
      />
    </div>
  );
}
