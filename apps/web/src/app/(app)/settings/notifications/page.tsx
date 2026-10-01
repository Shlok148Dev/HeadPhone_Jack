"use client";

import { useEffect, useState } from "react";
import { Button, ErrorState, Skeleton, useToast } from "@/components/ds";
import { disablePush, enablePush, useNotificationActions, useNotificationSettings, type NotificationSettings } from "@/lib/trust";

const PUSH_RESULT: Record<string, string> = {
  on: "Push notifications are on for this browser",
  denied: "Your browser blocked notifications. You can allow them in its site settings.",
  unsupported: "This browser doesn't support push notifications.",
  unavailable: "Push isn't set up on this server yet.",
};

/** Notification settings (JNG-11-02, 03, 04, 07). */
export default function NotificationSettingsPage() {
  const q = useNotificationSettings();
  const { save } = useNotificationActions();
  const toast = useToast();
  const [draft, setDraft] = useState<NotificationSettings | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (q.data) setDraft(q.data);
  }, [q.data]);

  if (q.isLoading || (!draft && !q.isError)) return <Skeleton className="h-80" rounded="lg" />;
  if (q.isError || !draft) return <ErrorState message="Couldn't load your notification settings." onRetry={() => void q.refetch()} />;

  const set = (type: string, channel: "in_app" | "push", value: boolean) =>
    setDraft({ ...draft, types: { ...draft.types, [type]: { ...draft.types[type]!, [channel]: value } } });

  async function togglePush(on: boolean) {
    setBusy(true);
    try {
      if (on) toast.toast({ title: PUSH_RESULT[await enablePush()] ?? "Done" });
      else {
        await disablePush();
        toast.toast({ title: "Push notifications are off" });
      }
      await q.refetch();
    } catch (e) {
      toast.toast({ title: e instanceof Error ? e.message : "That didn't work.", tone: "danger" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex max-w-2xl flex-col gap-8">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Notifications</h1>

      <section aria-labelledby="push-h" className="flex flex-col gap-2 rounded-lg border border-border bg-surface-1 p-4">
        <h2 id="push-h" className="font-medium">Push notifications</h2>
        <p className="text-sm text-text-muted">
          Off until you allow them. At most {draft.push_daily_cap} a day, and none during quiet hours.
        </p>
        {!draft.push_available ? (
          <p className="text-sm text-text-muted">{PUSH_RESULT.unavailable}</p>
        ) : draft.push_subscribed ? (
          <Button variant="secondary" loading={busy} loadingLabel="Turning off" onClick={() => void togglePush(false)}>Turn off push</Button>
        ) : (
          <Button loading={busy} loadingLabel="Asking your browser" onClick={() => void togglePush(true)}>Allow push notifications</Button>
        )}
      </section>

      <section aria-labelledby="types-h" className="flex flex-col gap-2">
        <h2 id="types-h" className="font-medium">What to tell you about</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-muted">
              <th className="py-2 font-normal">Type</th>
              <th className="w-20 py-2 text-center font-normal">In app</th>
              <th className="w-20 py-2 text-center font-normal">Push</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(draft.labels).map(([type, label]) => (
              <tr key={type} className="border-t border-border">
                <td className="py-2">{label}</td>
                <td className="text-center">
                  <input type="checkbox" aria-label={`${label} in app`} checked={draft.types[type]?.in_app ?? true} onChange={(e) => set(type, "in_app", e.target.checked)} className="h-5 w-5 accent-[var(--brand-violet)]" />
                </td>
                <td className="text-center">
                  <input type="checkbox" aria-label={`${label} push`} checked={draft.types[type]?.push ?? true} onChange={(e) => set(type, "push", e.target.checked)} className="h-5 w-5 accent-[var(--brand-violet)]" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section aria-labelledby="quiet-h" className="flex flex-col gap-3">
        <h2 id="quiet-h" className="font-medium">Quiet hours</h2>
        <div className="flex flex-wrap gap-4">
          <label className="flex flex-col gap-1 text-sm">
            From
            <input type="time" value={draft.quiet_start} onChange={(e) => setDraft({ ...draft, quiet_start: e.target.value })} className="min-h-11 rounded-md border border-border bg-surface-2 px-3" />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            To
            <input type="time" value={draft.quiet_end} onChange={(e) => setDraft({ ...draft, quiet_end: e.target.value })} className="min-h-11 rounded-md border border-border bg-surface-2 px-3" />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Pushes a day
            <input type="number" min={1} max={20} value={draft.push_daily_cap} onChange={(e) => setDraft({ ...draft, push_daily_cap: Number(e.target.value) || 5 })} className="min-h-11 w-24 rounded-md border border-border bg-surface-2 px-3" />
          </label>
        </div>
        <p className="font-mono text-xs text-text-muted">Times are in {draft.tz}.</p>
      </section>

      <div>
        <Button
          loading={save.isPending}
          loadingLabel="Saving"
          onClick={() => save.mutate(draft, { onSuccess: () => toast.toast({ title: "Saved", tone: "success" }), onError: (e) => toast.toast({ title: e.message, tone: "danger" }) })}
        >
          Save
        </Button>
      </div>
    </div>
  );
}
