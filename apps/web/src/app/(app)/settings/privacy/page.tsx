"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, ErrorState, Skeleton, useToast } from "@/components/ds";
import { PersonRow } from "@/components/app/PersonRow";
import { api, json } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useBlocks, useSocialActions } from "@/lib/social";

interface Privacy {
  activity_visibility: "friends" | "circles" | "nobody";
  show_last_active: boolean;
  concerts_visible: boolean;
  private_mode: { active: boolean; until: string | null } | null;
}

const VISIBILITY = [
  ["friends", "Friends"],
  ["circles", "Only circles I choose"],
  ["nobody", "No one for now"],
] as const;

function untilLabel(until: string | null): string {
  if (!until) return "until you turn it off";
  const d = new Date(until);
  return `until ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

/** Settings → Privacy (JNG-02-05, JNG-02-06, JNG-03-06). Saves instantly; failures revert. */
export default function PrivacySettingsPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const { me, setMe } = useAuth();
  const privacy = useQuery({ queryKey: ["privacy"], queryFn: () => api<Privacy>("/me/privacy") });
  const blocks = useBlocks();
  const { unblock } = useSocialActions();

  const save = useMutation({
    mutationFn: (patch: Record<string, unknown>) => api<Privacy>("/me/privacy", { method: "PATCH", ...json(patch) }),
    onMutate: async (patch) => {
      await qc.cancelQueries({ queryKey: ["privacy"] });
      const prev = qc.getQueryData<Privacy>(["privacy"]);
      if (prev && !("private_mode" in patch)) qc.setQueryData(["privacy"], { ...prev, ...patch });
      return { prev };
    },
    onError: (_e, _p, ctx) => {
      if (ctx?.prev) qc.setQueryData(["privacy"], ctx.prev);
      toast.toast({ title: "Couldn't save. Try again.", tone: "danger" });
    },
    onSuccess: (data) => {
      qc.setQueryData(["privacy"], data);
      void qc.invalidateQueries({ queryKey: ["me", "card"] });
      toast.toast({ title: "Saved", tone: "success" });
    },
  });

  const discover = useMutation({
    mutationFn: (given: boolean) => api(`/me/consents/suggestions_discoverability`, { method: "POST", ...json({ given }) }),
    onSuccess: (_d, given) => me && setMe({ ...me, discoverable: given }),
    onError: () => toast.toast({ title: "Couldn't save. Try again.", tone: "danger" }),
  });

  if (privacy.isLoading) return <Skeleton className="h-80 max-w-2xl" rounded="lg" />;
  if (privacy.isError || !privacy.data) return <ErrorState message="Couldn't load your privacy settings." onRetry={() => void privacy.refetch()} />;
  const p = privacy.data;
  const privateOn = !!p.private_mode?.active;

  return (
    <div className="flex max-w-2xl flex-col gap-8">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Privacy</h1>

      {privateOn && (
        <p role="status" className="rounded-md border border-border bg-surface-2 px-4 py-3 text-sm">
          Private mode is on {untilLabel(p.private_mode?.until ?? null)}. Friends see &ldquo;Hidden&rdquo;.
        </p>
      )}

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-medium">Who can see what you&rsquo;re playing</legend>
        {VISIBILITY.map(([v, l]) => (
          <label key={v} className="flex min-h-11 items-center gap-3 rounded-md border border-border px-3 text-sm has-[:checked]:border-brand-violet">
            <input type="radio" name="visibility" checked={p.activity_visibility === v} onChange={() => save.mutate({ activity_visibility: v })} className="accent-[var(--brand-violet)]" />
            {l}
          </label>
        ))}
      </fieldset>

      <section className="flex flex-col gap-3" aria-labelledby="private-h">
        <h2 id="private-h" className="font-medium">Private mode</h2>
        <p className="text-sm text-text-muted">Hide all your activity for a while. Friends see &ldquo;Hidden&rdquo;.</p>
        <div className="flex flex-wrap gap-2">
          {privateOn ? (
            <Button variant="secondary" onClick={() => save.mutate({ private_mode: "off" })}>Turn off Private mode</Button>
          ) : (
            <>
              <Button variant="secondary" onClick={() => save.mutate({ private_mode: "1h" })}>Hide for 1 hour</Button>
              <Button variant="secondary" onClick={() => save.mutate({ private_mode: "8h" })}>8 hours</Button>
              <Button variant="secondary" onClick={() => save.mutate({ private_mode: "until_off" })}>Until I turn it off</Button>
            </>
          )}
        </div>
      </section>

      <label className="flex min-h-11 items-center justify-between gap-4 text-sm">
        <span>
          <span className="block font-medium">Show my exact play time</span>
          <span className="text-text-muted">When off, friends see &ldquo;Recently on Spotify&rdquo; instead of a time.</span>
        </span>
        <input type="checkbox" role="switch" checked={p.show_last_active} onChange={(e) => save.mutate({ show_last_active: e.target.checked })} className="h-5 w-5 shrink-0 accent-[var(--brand-violet)]" />
      </label>

      <label className="flex min-h-11 items-center justify-between gap-4 text-sm">
        <span>
          <span className="block font-medium">Let people find me in suggestions</span>
          <span className="text-text-muted">People can still find you by your exact username.</span>
        </span>
        <input type="checkbox" role="switch" checked={!!me?.discoverable} onChange={(e) => discover.mutate(e.target.checked)} className="h-5 w-5 shrink-0 accent-[var(--brand-violet)]" />
      </label>

      <section aria-labelledby="blocked-h" className="flex flex-col gap-2">
        <h2 id="blocked-h" className="font-medium">Blocked people</h2>
        {blocks.data?.length ? (
          <ul className="flex flex-col gap-1">
            {blocks.data.map((b) => (
              <PersonRow key={b.id} person={b} actions={<Button variant="ghost" onClick={() => unblock.mutate(b.id)}>Unblock</Button>} />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-text-muted">You haven&rsquo;t blocked anyone.</p>
        )}
      </section>
    </div>
  );
}
