"use client";

import { Artwork, GenerativeCover } from "@/components/ds";

/**
 * A group's face, made from real covers (D-ART): four or more make a 2×2 grid, fewer show the
 * first cover whole, none shows the honest generative cover. Nothing is ever drawn on top.
 */
export function CoverMosaic({ covers, seed }: { covers: string[]; seed: string }) {
  return (
    <div className="jg-art-glow aspect-square overflow-hidden rounded-[var(--r-art-lg)] bg-surface-2">
      {covers.length >= 4 ? (
        <div className="grid h-full grid-cols-2 gap-px">
          {covers.slice(0, 4).map((u) => (
            <Artwork key={u} url={u} seed={u} alt="" rounded="none" />
          ))}
        </div>
      ) : covers.length ? (
        <Artwork url={covers[0]!} seed={covers[0]!} alt="" rounded="none" />
      ) : (
        <GenerativeCover seed={seed} />
      )}
    </div>
  );
}
