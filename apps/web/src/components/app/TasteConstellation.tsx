"use client";

import { Artwork } from "@/components/ds";

export interface Star {
  name: string;
  image_url?: string | null;
}

/**
 * Taste Constellation (D-SIG-03): two overlapping fields of real artist images. Artists you
 * share sit in the overlap and are larger. Decorative; the list below it carries the meaning.
 */
export function TasteConstellation({ mine, theirs, theirName }: { mine: Star[]; theirs: Star[]; theirName: string }) {
  const key = (s: Star) => s.name.toLowerCase();
  const theirKeys = new Set(theirs.map(key));
  const shared = mine.filter((s) => theirKeys.has(key(s))).slice(0, 4);
  const sharedKeys = new Set(shared.map(key));
  const onlyMine = mine.filter((s) => !sharedKeys.has(key(s))).slice(0, 5);
  const onlyTheirs = theirs.filter((s) => !sharedKeys.has(key(s))).slice(0, 5);

  const place = (list: Star[], xs: number[], ys: number[], size: number, delayBase: number) =>
    list.map((s, i) => (
      <div
        key={s.name}
        className="jg-reveal jg-art-glow absolute overflow-hidden rounded-full"
        title={s.name}
        style={{
          left: `${xs[i % xs.length]}%`,
          top: `${ys[i % ys.length]}%`,
          width: size,
          height: size,
          transform: "translate(-50%, -50%)",
          ["--r0" as string]: `${delayBase + i * 4}%`,
          ["--r1" as string]: `${45 + delayBase + i * 4}%`,
        }}
      >
        <Artwork url={s.image_url ?? null} seed={s.name} alt="" rounded="none" />
      </div>
    ));

  return (
    <figure className="flex flex-col gap-3">
      <div className="relative h-64 w-full" aria-hidden>
        <div className="absolute left-[4%] top-[4%] h-[92%] w-[58%] rounded-full border border-border bg-[color-mix(in_srgb,var(--brand-violet)_7%,transparent)]" />
        <div className="absolute right-[4%] top-[4%] h-[92%] w-[58%] rounded-full border border-border bg-[color-mix(in_srgb,var(--brand-cyan)_7%,transparent)]" />
        <span className="absolute left-[8%] top-1 font-mono text-[11px] text-text-muted">You</span>
        <span className="absolute right-[8%] top-1 font-mono text-[11px] text-text-muted">{theirName}</span>
        {place(onlyMine, [16, 26, 13, 28, 20], [26, 42, 58, 70, 84], 40, 0)}
        {place(onlyTheirs, [84, 74, 87, 72, 80], [26, 42, 58, 70, 84], 40, 10)}
        {place(shared, [44, 56, 44, 56], [26, 40, 62, 76], 44, 20)}
      </div>
      <figcaption className="text-sm text-text-muted">
        {shared.length ? (
          <>
            You both love <span className="font-medium text-text">{shared.map((s) => s.name).join(", ")}</span>.
          </>
        ) : (
          "No top artists in common yet; your taste is still each your own."
        )}
      </figcaption>
    </figure>
  );
}
