"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Button, EmptyState, ErrorState, Skeleton, Tabs } from "@/components/ds";
import { FindFriends } from "@/components/app/FindFriends";
import { PersonMenu, PersonRow } from "@/components/app/PersonRow";
import { useFriends, useRequests, useSocialActions } from "@/lib/social";

function RowsSkeleton() {
  return (
    <ul aria-busy="true" className="flex flex-col gap-2">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-16" rounded="lg" />
      ))}
    </ul>
  );
}

function FriendsTab({ onFind }: { onFind: () => void }) {
  const friends = useFriends();
  if (friends.isLoading) return <RowsSkeleton />;
  if (friends.isError) return <ErrorState message="Couldn't load your friends." onRetry={() => void friends.refetch()} />;
  if (!friends.data?.length)
    return <EmptyState pose="wave" title="No friends yet" description="Find people you know, or share your invite link." action={{ label: "Find friends", onClick: onFind }} />;
  return (
    <ul className="flex flex-col gap-1">
      {friends.data.map((p) => (
        <PersonRow key={p.id} person={p} actions={<PersonMenu person={p} canRemove />} />
      ))}
    </ul>
  );
}

function RequestsTab() {
  const requests = useRequests();
  const { accept, decline, cancel } = useSocialActions();
  if (requests.isLoading) return <RowsSkeleton />;
  if (requests.isError) return <ErrorState message="Couldn't load requests." onRetry={() => void requests.refetch()} />;
  const incoming = requests.data?.filter((r) => r.direction === "incoming") ?? [];
  const outgoing = requests.data?.filter((r) => r.direction === "outgoing") ?? [];
  if (!incoming.length && !outgoing.length) return <EmptyState pose="sleepy" title="No requests right now" />;
  return (
    <div className="flex flex-col gap-6">
      {incoming.length > 0 && (
        <section aria-labelledby="incoming-h">
          <h2 id="incoming-h" className="mb-2 font-mono text-xs uppercase tracking-wide text-text-muted">Waiting for you</h2>
          <ul className="flex flex-col gap-1">
            {incoming.map((r) => (
              <PersonRow
                key={r.id}
                person={r.user}
                actions={
                  <>
                    <Button loading={accept.isPending && accept.variables === r.id} onClick={() => accept.mutate(r.id)}>
                      Accept
                    </Button>
                    <Button variant="ghost" onClick={() => decline.mutate(r.id)}>
                      Decline
                    </Button>
                    <PersonMenu person={r.user} canRemove={false} />
                  </>
                }
              />
            ))}
          </ul>
        </section>
      )}
      {outgoing.length > 0 && (
        <section aria-labelledby="outgoing-h">
          <h2 id="outgoing-h" className="mb-2 font-mono text-xs uppercase tracking-wide text-text-muted">Sent</h2>
          <ul className="flex flex-col gap-1">
            {outgoing.map((r) => (
              <PersonRow
                key={r.id}
                person={r.user}
                actions={
                  <Button variant="ghost" onClick={() => cancel.mutate(r.id)}>
                    Cancel
                  </Button>
                }
              />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function FriendsPage() {
  const params = useSearchParams();
  const router = useRouter();
  const requests = useRequests();
  const incoming = requests.data?.filter((r) => r.direction === "incoming").length ?? 0;
  const tab = params.get("tab") ?? "friends";
  const go = (id: string) => router.replace(`/friends?tab=${id}`);
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Friends</h1>
      <Tabs
        label="Friends"
        value={tab}
        onChange={go}
        items={[
          { id: "friends", label: "Friends", content: <FriendsTab onFind={() => go("find")} /> },
          { id: "requests", label: incoming ? `Requests (${incoming})` : "Requests", content: <RequestsTab /> },
          { id: "find", label: "Find", content: <FindFriends /> },
        ]}
      />
    </div>
  );
}

export default function Page() {
  return (
    <Suspense>
      <FriendsPage />
    </Suspense>
  );
}
