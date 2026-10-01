"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Button, EmptyState, ErrorState, Skeleton, cn } from "@/components/ds";
import { useNotificationActions, useNotifications } from "@/lib/trust";

function ago(iso: string): string {
  const m = Math.round((Date.now() - Date.parse(iso)) / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  return h < 24 ? `${h} h ago` : `${Math.round(h / 24)} d ago`;
}

/** Notification centre (JNG-11-01). Opening it marks everything read. */
export default function NotificationsPage() {
  const q = useNotifications();
  const { readAll } = useNotificationActions();
  const unread = q.data?.unread ?? 0;
  useEffect(() => {
    if (unread > 0) readAll.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unread]);

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Notifications</h1>
        <Link href="/settings/notifications" className="text-sm text-text-muted underline-offset-4 hover:text-text hover:underline">Settings</Link>
      </div>
      {q.isLoading ? (
        <div className="flex flex-col gap-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-14" />)}</div>
      ) : q.isError || !q.data ? (
        <ErrorState message="Couldn't load your notifications." onRetry={() => void q.refetch()} />
      ) : !q.data.results.length ? (
        <EmptyState pose="sleepy" title="All quiet" description="Friend requests, songs, battles and recaps show up here." />
      ) : (
        <ul className="flex flex-col">
          {q.data.results.map((n) => (
            <li key={n.id}>
              <Link
                href={n.url || "/home"}
                className={cn(
                  "flex min-h-14 items-center justify-between gap-3 rounded-md px-3 py-2 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]",
                  !n.read && "font-medium",
                )}
              >
                <span className="flex items-center gap-2">
                  {!n.read && <span className="h-2 w-2 shrink-0 rounded-full bg-[var(--brand-violet)]" aria-label="New" />}
                  {n.title}
                </span>
                <span className="shrink-0 font-mono text-xs text-text-muted">{ago(n.created_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {readAll.isError && <Button variant="ghost" onClick={() => readAll.mutate()}>Mark all read</Button>}
    </div>
  );
}
