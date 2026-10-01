"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, ErrorState, Skeleton, useToast } from "@/components/ds";
import { api, json } from "@/lib/api";
import { useMyModeration, type MyAction } from "@/lib/trust";

const KIND: Record<MyAction["kind"], string> = { warn: "Warning", mute: "Muted", suspend: "Suspended", ban: "Banned" };

function AppealForm({ action }: { action: MyAction }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const qc = useQueryClient();
  const toast = useToast();
  async function submit() {
    setBusy(true);
    try {
      await api(`/me/moderation/${action.id}/appeal`, { method: "POST", ...json({ text }) });
      toast.toast({ title: "Appeal sent. A moderator will review it.", tone: "success" });
      await qc.invalidateQueries({ queryKey: ["my-moderation"] });
    } catch (e) {
      toast.toast({ title: e instanceof Error ? e.message : "That didn't work.", tone: "danger" });
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="flex flex-col gap-2">
      <label className="flex flex-col gap-1 text-sm font-medium">
        Why should we look again?
        <textarea value={text} maxLength={1000} rows={3} onChange={(e) => setText(e.target.value)} className="rounded-md border border-border bg-surface-2 px-3 py-2 font-normal" />
      </label>
      <Button disabled={!text.trim()} loading={busy} loadingLabel="Sending" onClick={() => void submit()}>Appeal</Button>
    </div>
  );
}

/** Account standing and appeals (JNG-12-03, 12-08). */
export default function AccountPage() {
  const q = useMyModeration();
  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Account standing</h1>
      {q.isLoading ? (
        <Skeleton className="h-32" rounded="lg" />
      ) : q.isError || !q.data ? (
        <ErrorState message="Couldn't load your account standing." onRetry={() => void q.refetch()} />
      ) : !q.data.actions.length ? (
        <p className="rounded-lg border border-border bg-surface-1 p-4 text-sm">Your account is in good standing.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {q.data.actions.map((a) => (
            <li key={a.id} className="flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-4">
              <p className="font-medium">
                {KIND[a.kind]}
                {a.expires_at && !a.lifted ? ` until ${new Date(a.expires_at).toLocaleString()}` : ""}
                {a.lifted ? " (lifted)" : ""}
              </p>
              <p className="text-sm text-text-muted">Reason: {a.reason}</p>
              {a.appeal ? (
                <p className="text-sm">
                  Appeal: {a.appeal.status === "open" ? "under review" : a.appeal.status}
                  {a.appeal.note ? ` · ${a.appeal.note}` : ""}
                </p>
              ) : (
                !a.lifted && <AppealForm action={a} />
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
