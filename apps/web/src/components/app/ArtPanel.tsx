"use client";

import { useQuery } from "@tanstack/react-query";
import { Artwork, Pulse } from "@/components/ds";
import { api } from "@/lib/api";

interface Cover {
  url: string;
  url_small: string;
  color: string | null;
  label: string;
}

const PEOPLE: [string, "live" | "recent"][] = [
  ["Aanya", "live"],
  ["Kabir", "recent"],
  ["Meera", "live"],
];

/** Sign-in / sign-up / onboarding side panel: real covers drifting, friends' Pulse rings. */
export function ArtPanel() {
  const q = useQuery({ queryKey: ["artwork-wall"], queryFn: () => api<{ covers: Cover[] }>("/artwork/wall"), staleTime: 3600_000 });
  const covers = q.data?.covers ?? [];
  const cols = [0, 1, 2].map((c) => Array.from({ length: 6 }, (_, i) => covers[(c * 6 + i * 2 + c) % Math.max(1, covers.length)]));
  return (
    <div aria-hidden className="jg-enter-late hidden h-dvh min-h-0 p-3 lg:block">
      <div className="flex h-full flex-col overflow-hidden rounded-[24px] bg-surface-1">
      <div className="grid min-h-0 flex-1 grid-cols-3 gap-4 overflow-hidden p-4">
        {cols.map((col, c) => (
          <div key={c} className="jg-drift flex flex-col gap-3" style={{ animationDuration: `${46 + c * 8}s`, animationDirection: c % 2 ? "reverse" : "normal" }}>
            {[...col, ...col].map((cv, i) => (
              <div key={i} className="jg-art-glow aspect-square shrink-0 overflow-hidden rounded-[8px]" style={{ ["--art" as string]: cv?.color ?? "#000" }}>
                <Artwork url={cv?.url || cv?.url_small || null} seed={cv?.label ?? `${c}${i}`} alt="" rounded="none" sizes="(min-width: 1440px) 300px, 22vw" eager={i < 4} tint={cv?.color} />
              </div>
            ))}
          </div>
        ))}
      </div>
      {/* Words live below the art, never on it. */}
      <div className="shrink-0 border-t border-border px-8 py-6">
        <div className="mb-3 flex -space-x-2">
          {PEOPLE.map(([n, s]) => (
            <Pulse key={n} state={s} name={n} seed={n} size={36} />
          ))}
        </div>
        <p className="font-display text-3xl font-semibold leading-tight tracking-tight">Your friends are playing right now.</p>
        <p className="mt-1 text-sm text-text-muted">On Spotify, Apple Music, YouTube Music and Amazon Music.</p>
      </div>
      </div>
    </div>
  );
}
