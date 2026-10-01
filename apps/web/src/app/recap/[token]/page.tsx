"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { Blip, ButtonLink, Skeleton } from "@/components/ds";
import { FocusShell } from "@/components/app/FocusShell";
import { RecapCard, monthName } from "@/components/app/RecapCard";
import { api } from "@/lib/api";
import type { RecapData } from "@/lib/trust";

/** A recap someone chose to share (JNG-09-06). Public: only the card and a first name. */
export default function SharedRecapPage() {
  const { token } = useParams<{ token: string }>();
  const q = useQuery({
    queryKey: ["shared-recap", token],
    queryFn: () => api<{ name: string; month: string; data: RecapData }>(`/recaps/shared/${encodeURIComponent(token)}`),
    retry: false,
  });
  return (
    <FocusShell>
      {q.isLoading ? (
        <Skeleton className="h-80" rounded="lg" />
      ) : q.isError || !q.data ? (
        <div className="flex flex-col items-center gap-3 text-center">
          <Blip pose="sleepy" size={96} decorative />
          <h1 className="font-display text-2xl font-semibold">This recap isn&rsquo;t shared any more</h1>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4 text-center">
          <h1 className="font-display text-2xl font-semibold">{q.data.name}&rsquo;s {monthName(q.data.month)}</h1>
          <RecapCard data={q.data.data} name={q.data.name} />
          <p className="text-sm text-text-muted">See what your friends play, on any music app.</p>
          <ButtonLink href="/signup">Join Jingle</ButtonLink>
        </div>
      )}
    </FocusShell>
  );
}
