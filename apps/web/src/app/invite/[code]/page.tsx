"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Blip, Button, ButtonLink, Skeleton } from "@/components/ds";
import { FocusShell } from "@/components/app/FocusShell";
import { FormAlert } from "@/components/app/forms";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

import { INVITE_KEY } from "@/lib/invite";

/** JNG-02-07: opening an invite link sends a friend request to its owner (after sign-in if needed). */
export default function InvitePage() {
  const { code } = useParams<{ code: string }>();
  const { status } = useAuth();
  const router = useRouter();
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const preview = useQuery({
    queryKey: ["invite-preview", code],
    queryFn: () => api<{ display_name: string }>(`/invites/${encodeURIComponent(code)}`),
    retry: false,
  });

  useEffect(() => {
    if (status === "signed-out") {
      try {
        sessionStorage.setItem(INVITE_KEY, code);
      } catch {
        /* storage blocked: the user can reopen the link */
      }
    }
  }, [status, code]);

  async function accept() {
    setState("sending");
    try {
      await api(`/invites/${encodeURIComponent(code)}`, { method: "POST" });
      setState("sent");
    } catch (e) {
      setError(e instanceof Error ? e.message : "That didn't work.");
      setState("error");
    }
  }

  const name = preview.data?.display_name;
  return (
    <FocusShell>
      {preview.isLoading || status === "loading" ? (
        <Skeleton className="h-48" rounded="lg" />
      ) : preview.isError ? (
        <div className="flex flex-col items-center gap-3 text-center">
          <Blip pose="sleepy" size={96} decorative />
          <h1 className="font-display text-2xl font-semibold">This invite link doesn&rsquo;t work any more</h1>
          <p className="text-sm text-text-muted">Ask your friend for a new one.</p>
        </div>
      ) : state === "sent" ? (
        <div className="flex flex-col items-center gap-3 text-center">
          <Blip pose="cheer" size={96} decorative />
          <h1 className="font-display text-2xl font-semibold">Request sent to {name}</h1>
          <p className="text-sm text-text-muted">You&rsquo;ll see what they play once they accept.</p>
          <Button onClick={() => router.push("/home")}>Go to my feed</Button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4 text-center">
          <Blip pose="wave" size={96} decorative />
          <h1 className="font-display text-2xl font-semibold">{name} invited you to Jingle</h1>
          <p className="text-sm text-text-muted">See what each other are playing, on any music app.</p>
          {error && <FormAlert>{error}</FormAlert>}
          {status === "signed-in" ? (
            <Button size="lg" loading={state === "sending"} loadingLabel="Sending" onClick={accept}>
              Add {name}
            </Button>
          ) : (
            <div className="flex w-full flex-col gap-2">
              <ButtonLink href="/signup" size="lg">Create an account</ButtonLink>
              <ButtonLink href={`/signin?next=${encodeURIComponent(`/invite/${code}`)}`} variant="secondary">
                I already have an account
              </ButtonLink>
            </div>
          )}
        </div>
      )}
    </FocusShell>
  );
}
