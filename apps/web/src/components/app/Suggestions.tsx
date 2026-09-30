"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Chip, EmptyState, Shelf, Skeleton, SuggestionCard, useToast } from "@/components/ds";
import { api, json } from "@/lib/api";
import type { Person } from "@/lib/social";

interface SuggestionItem {
  user: Person;
  score: number;
  reasons: string[];
}

interface SuggestionsResponse {
  results: SuggestionItem[];
  pending: boolean;
  cold_start: boolean;
}

export function useSuggestions() {
  return useQuery({
    queryKey: ["suggestions"],
    queryFn: () => api<SuggestionsResponse>("/suggestions"),
    // A first request schedules the computation; check back shortly.
    refetchInterval: (q) => (q.state.data?.pending ? 8_000 : false),
  });
}

function useSuggestionActions() {
  const qc = useQueryClient();
  const toast = useToast();
  const drop = (id: string) =>
    qc.setQueryData<SuggestionsResponse>(["suggestions"], (prev) =>
      prev ? { ...prev, results: prev.results.filter((r) => r.user.id !== id) } : prev,
    );
  const add = useMutation({
    mutationFn: (id: string) => api("/friends/requests", { method: "POST", ...json({ user_id: id }) }),
    onMutate: (id) => drop(id), // optimistic: the card leaves at once
    onSuccess: () => {
      toast.toast({ title: "Request sent", tone: "success" });
      void qc.invalidateQueries({ queryKey: ["friends"] });
    },
    onError: (e) => {
      toast.toast({ title: e.message, tone: "danger" });
      void qc.invalidateQueries({ queryKey: ["suggestions"] });
    },
  });
  const dismiss = useMutation({
    mutationFn: (id: string) => api(`/suggestions/${id}/dismiss`, { method: "POST" }),
    onMutate: (id) => drop(id),
    onError: () => void qc.invalidateQueries({ queryKey: ["suggestions"] }),
  });
  return { add, dismiss };
}

function Card({ s, actions }: { s: SuggestionItem; actions: ReturnType<typeof useSuggestionActions> }) {
  return (
    <SuggestionCard
      person={{ id: s.user.id, name: s.user.display_name, username: s.user.username, avatar_url: s.user.avatar_url }}
      reasons={s.reasons}
      onAction={() => actions.add.mutate(s.user.id)}
      onDismiss={() => actions.dismiss.mutate(s.user.id)}
    />
  );
}

/** JNG-03-01: up to 20 people with ≤ 3 reasons each. Grid for Friends/onboarding. */
export function SuggestionsGrid() {
  const q = useSuggestions();
  const actions = useSuggestionActions();
  if (q.isLoading || (q.data?.pending && !q.data.results.length)) {
    return (
      <div className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-4" aria-busy="true">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-56" rounded="lg" />
        ))}
      </div>
    );
  }
  if (!q.data?.results.length) {
    return (
      <EmptyState
        pose="wave"
        title="No suggestions yet"
        description={
          q.data?.cold_start
            ? "Tell us a few artists or genres you love, or invite a friend, and suggestions will show up here."
            : "Invite a friend and you'll see people you may know here."
        }
      />
    );
  }
  return (
    <ul className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(184px,1fr))]">
      {q.data.results.map((s) => (
        <li key={s.user.id}>
          <Card s={s} actions={actions} />
        </li>
      ))}
    </ul>
  );
}

/** Home: "People you may know" shelf (hidden when empty). */
export function SuggestionsShelf() {
  const q = useSuggestions();
  const actions = useSuggestionActions();
  const items = q.data?.results ?? [];
  if (!items.length) return null;
  return (
    <Shelf title="People you may know" count={items.length} itemWidth="clamp(160px, 42vw, 200px)">
      {items.map((s) => (
        <Card key={s.user.id} s={s} actions={actions} />
      ))}
      <Link href="/friends?tab=suggestions" className="flex h-full min-h-44 items-center justify-center rounded-lg border border-dashed border-border text-sm text-text-muted hover:text-text">
        See all
      </Link>
    </Shelf>
  );
}

interface Taste {
  artists: string[];
  genres: string[];
  genre_options: string[];
}

/** Cold start (JNG-03-07, Tech Bible 5.3): pick 3+ genres or artists for a provisional taste. */
export function TastePicker({ onSaved }: { onSaved?: () => void }) {
  const qc = useQueryClient();
  const taste = useQuery({ queryKey: ["taste"], queryFn: () => api<Taste>("/me/taste") });
  const [genres, setGenres] = useState<string[] | null>(null);
  const [artists, setArtists] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: (body: { genres: string[]; artists: string[] }) => api<Taste>("/me/taste", { method: "PUT", ...json(body) }),
    onSuccess: (data) => {
      qc.setQueryData(["taste"], data);
      void qc.invalidateQueries({ queryKey: ["suggestions"] });
      onSaved?.();
    },
  });
  if (taste.isLoading || !taste.data) return <Skeleton className="h-32" rounded="lg" />;
  const picked = genres ?? taste.data.genres;
  const artistText = artists ?? taste.data.artists.join(", ");
  const toggle = (g: string) => setGenres(picked.includes(g) ? picked.filter((x) => x !== g) : [...picked, g]);
  const artistList = artistText.split(",").map((a) => a.trim()).filter(Boolean).slice(0, 20);
  return (
    <div className="flex flex-col gap-3">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-medium">Genres you love</legend>
        <div className="flex flex-wrap gap-2">
          {taste.data.genre_options.map((g) => (
            <Chip key={g} selected={picked.includes(g)} onSelectedChange={() => toggle(g)}>
              {g}
            </Chip>
          ))}
        </div>
      </fieldset>
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Favourite artists (comma separated)
        <input
          value={artistText}
          onChange={(e) => setArtists(e.target.value)}
          placeholder="Arijit Singh, Prateek Kuhad"
          className="h-11 rounded-md border border-border bg-surface-2 px-3 text-sm font-normal"
        />
      </label>
      <p className="text-xs text-text-muted">Pick three or more. This helps us suggest people with similar taste.</p>
      <button
        type="button"
        onClick={() => save.mutate({ genres: picked, artists: artistList })}
        disabled={picked.length + artistList.length < 3 || save.isPending}
        className="min-h-11 self-start rounded-pill border border-border px-4 text-sm font-medium hover:bg-surface-2 disabled:opacity-50"
      >
        {save.isSuccess ? "Saved ✓" : save.isPending ? "Saving…" : "Save my taste"}
      </button>
    </div>
  );
}
