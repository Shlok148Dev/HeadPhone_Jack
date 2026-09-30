"use client";

import { useEffect, useState } from "react";
import { Skeleton } from "@/components/ds";
import { useSearch } from "@/lib/social";
import { InviteCard } from "./InviteCard";
import { PersonRow, RelationshipButton } from "./PersonRow";
import { TextField } from "./forms";

/** JNG-02-01 search + JNG-02-07 invite, shared by the Friends page and onboarding. */
export function FindFriends() {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 250);
    return () => clearTimeout(t);
  }, [q]);
  const results = useSearch(debounced);
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <TextField label="Search by username or name" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="@username" autoComplete="off" />
        {debounced.length >= 2 &&
          (results.isLoading ? (
            <Skeleton className="h-16" rounded="lg" />
          ) : results.data?.length ? (
            <ul className="flex flex-col gap-1" aria-live="polite">
              {results.data.map((p) => (
                <PersonRow key={p.id} person={p} actions={<RelationshipButton person={p} />} />
              ))}
            </ul>
          ) : (
            <p className="text-sm text-text-muted" aria-live="polite">
              No one found for &ldquo;{debounced}&rdquo;. Try their exact username, or send your invite link.
            </p>
          ))}
      </div>
      <InviteCard />
    </div>
  );
}

