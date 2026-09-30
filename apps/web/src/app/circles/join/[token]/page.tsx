"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { Blip, Button, ButtonLink, Skeleton } from "@/components/ds";
import { FocusShell } from "@/components/app/FocusShell";
import { FormAlert } from "@/components/app/forms";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Circle } from "@/lib/circles";

/** JNG-04-02: a 7-day circle link. Joining is always the invitee's own tap (BR-08). */
export default function JoinCirclePage() {
  const { token } = useParams<{ token: string }>();
  const { status } = useAuth();
  const router = useRouter();
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const path = `/circles/join/${encodeURIComponent(token)}`;
  const preview = useQuery({
    queryKey: ["circle-link", token],
    queryFn: () => api<{ name: string; member_count: number; full: boolean }>(path),
    retry: false,
  });

  async function join() {
    setJoining(true);
    setError(null);
    try {
      const c = await api<Circle>(path, { method: "POST" });
      router.push(`/circles/${c.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "That didn't work.");
      setJoining(false);
    }
  }

  const p = preview.data;
  return (
    <FocusShell>
      {preview.isLoading || status === "loading" ? (
        <Skeleton className="h-48" rounded="lg" />
      ) : preview.isError || !p ? (
        <div className="flex flex-col items-center gap-3 text-center">
          <Blip pose="sleepy" size={96} decorative />
          <h1 className="font-display text-2xl font-semibold">This invite link doesn&rsquo;t work any more</h1>
          <p className="text-sm text-text-muted">Links last 7 days. Ask for a new one.</p>
        </div>
      ) : p.full ? (
        <div className="flex flex-col items-center gap-3 text-center">
          <Blip pose="sleepy" size={96} decorative />
          <h1 className="font-display text-2xl font-semibold">This circle is full</h1>
          <p className="text-sm text-text-muted">{p.name} already has 50 members.</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4 text-center">
          <Blip pose="wave" size={96} decorative />
          <h1 className="font-display text-2xl font-semibold">Join {p.name}</h1>
          <p className="font-mono text-xs text-text-muted">{p.member_count} members</p>
          <p className="text-sm text-text-muted">See what the circle is playing and battle over the best song each week.</p>
          {error && <FormAlert>{error}</FormAlert>}
          {status === "signed-in" ? (
            <Button size="lg" loading={joining} loadingLabel="Joining" onClick={join}>
              Join circle
            </Button>
          ) : (
            <div className="flex w-full flex-col gap-2">
              <ButtonLink href={`/signup?next=${encodeURIComponent(`/circles/join/${token}`)}`} size="lg">Create an account</ButtonLink>
              <ButtonLink href={`/signin?next=${encodeURIComponent(`/circles/join/${token}`)}`} variant="secondary">
                I already have an account
              </ButtonLink>
            </div>
          )}
        </div>
      )}
    </FocusShell>
  );
}
