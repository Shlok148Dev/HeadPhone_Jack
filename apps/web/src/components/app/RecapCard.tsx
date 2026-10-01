"use client";

import * as motion from "motion/react-m";
import { useState } from "react";
import { Artwork, Button, seedGradient } from "@/components/ds";
import { useMotionSafe } from "@/lib/motion";
import type { RecapData } from "@/lib/trust";

export function monthName(m: string): string {
  const [y, mo] = m.split("-").map(Number);
  return new Date(Date.UTC(y!, (mo ?? 1) - 1, 1)).toLocaleString("en", { month: "long", year: "numeric", timeZone: "UTC" });
}

function Front({ data, name }: { data: RecapData; name?: string }) {
  // The month takes its colour from its most-played cover (contrast-checked ambient); else a seeded gradient.
  const top = data.top_tracks[0];
  const amb = top?.artwork_colors?.ambient_dark;
  const [from, to] = amb ? [amb, `color-mix(in srgb, ${amb} 55%, #000)`] : seedGradient(`recap-${data.month}`, "deep");
  const covers = data.top_tracks.slice(0, 3).filter((t) => t.artwork_small || t.artwork_url);
  return (
    <div className="flex h-full flex-col justify-between rounded-xl p-6 text-white" style={{ background: `linear-gradient(150deg, ${from}, ${to})` }}>
      <div className="flex items-start justify-between gap-3">
        <p className="font-mono text-xs uppercase tracking-wide text-white/80">{name ? `${name}'s ` : "Your "}{monthName(data.month)}</p>
        {covers.length > 0 && (
          <div className="flex -space-x-3" aria-hidden>
            {covers.map((t) => (
              <div key={`${t.title}|${t.artist}`} className="h-11 w-11 shrink-0 overflow-hidden rounded-[var(--r-art-sm)] shadow-2 ring-2 ring-black/30">
                <Artwork url={t.artwork_small ?? t.artwork_url ?? null} seed={t.title} alt="" rounded="none" />
              </div>
            ))}
          </div>
        )}
      </div>
      <div>
        <p className="font-display text-5xl font-semibold tabular-nums">{data.minutes.toLocaleString()}</p>
        <p className="text-sm text-white/85">minutes of music (estimated)</p>
      </div>
      <p className="text-sm text-white/85">Tap to see what you played</p>
    </div>
  );
}

function Back({ data }: { data: RecapData }) {
  return (
    <div className="flex h-full flex-col gap-4 overflow-hidden rounded-xl border border-border bg-surface-1 p-6">
      <div>
        <p className="text-xs uppercase tracking-wide text-text-muted">Top artists</p>
        <ol className="mt-1 text-sm">
          {data.top_artists.slice(0, 3).map((a, i) => (
            <li key={a.name} className="truncate"><span className="font-mono text-text-muted">{i + 1}</span> {a.name}</li>
          ))}
        </ol>
      </div>
      <div>
        <p className="text-xs uppercase tracking-wide text-text-muted">Top songs</p>
        <ol className="mt-1 text-sm">
          {data.top_tracks.slice(0, 3).map((t, i) => (
            <li key={`${t.title}-${t.artist}`} className="truncate"><span className="font-mono text-text-muted">{i + 1}</span> {t.title} · {t.artist}</li>
          ))}
        </ol>
      </div>
      <dl className="mt-auto grid grid-cols-3 gap-2 text-center">
        <div><dt className="text-xs text-text-muted">Sent</dt><dd className="font-display text-xl font-semibold">{data.sends}</dd></div>
        <div><dt className="text-xs text-text-muted">Got</dt><dd className="font-display text-xl font-semibold">{data.received}</dd></div>
        <div><dt className="text-xs text-text-muted">Battle wins</dt><dd className="font-display text-xl font-semibold">{data.battle_wins}</dd></div>
      </dl>
      {data.top_genre && <p className="text-xs text-text-muted">Mostly {data.top_genre}</p>}
    </div>
  );
}

/** Monthly recap card with a flip reveal (UX: flip-card; reduced motion swaps instantly). */
export function RecapCard({ data, name }: { data: RecapData; name?: string }) {
  const [flipped, setFlipped] = useState(false);
  const m = useMotionSafe();
  return (
    <div className="flex w-full max-w-xs shrink-0 flex-col gap-2 sm:w-72">
      <button
        type="button"
        onClick={() => setFlipped(!flipped)}
        aria-pressed={flipped}
        aria-label={flipped ? `Recap for ${monthName(data.month)}, details. Show the front` : `Recap for ${monthName(data.month)}. Show details`}
        className="relative aspect-[4/5] w-full max-w-xs rounded-xl text-left [perspective:1200px] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)]"
      >
        {m.reduced ? (
          <div className="absolute inset-0">{flipped ? <Back data={data} /> : <Front data={data} name={name} />}</div>
        ) : (
          <motion.div
            className="absolute inset-0 [transform-style:preserve-3d]"
            animate={{ rotateY: flipped ? 180 : 0 }}
            transition={m.spring.gentle}
          >
            <div className="absolute inset-0 [backface-visibility:hidden]"><Front data={data} name={name} /></div>
            <div className="absolute inset-0 [backface-visibility:hidden] [transform:rotateY(180deg)]"><Back data={data} /></div>
          </motion.div>
        )}
      </button>
      <span className="sr-only" aria-live="polite">
        {flipped
          ? `Top artist ${data.top_artists[0]?.name ?? "none"}. ${data.plays} plays.`
          : ""}
      </span>
    </div>
  );
}

export function DownloadRecap({ data }: { data: RecapData }) {
  // JNG-09-06: an image to share anywhere, drawn locally (no third-party service).
  const download = () => {
    const c = document.createElement("canvas");
    c.width = 1080;
    c.height = 1350;
    const g = c.getContext("2d");
    if (!g) return;
    const [from, to] = seedGradient(`recap-${data.month}`, "deep");
    const grad = g.createLinearGradient(0, 0, 1080, 1350);
    grad.addColorStop(0, from);
    grad.addColorStop(1, to);
    g.fillStyle = grad;
    g.fillRect(0, 0, 1080, 1350);
    g.fillStyle = "#ffffff";
    g.font = "600 48px Inter, sans-serif";
    g.fillText(`My ${monthName(data.month)} on Jingle`, 80, 140);
    g.font = "700 160px Inter, sans-serif";
    g.fillText(data.minutes.toLocaleString(), 80, 400);
    g.font = "500 44px Inter, sans-serif";
    g.fillText("minutes of music", 80, 470);
    g.font = "600 40px Inter, sans-serif";
    g.fillText("Top artists", 80, 620);
    g.font = "400 44px Inter, sans-serif";
    data.top_artists.slice(0, 5).forEach((a, i) => g.fillText(`${i + 1}. ${a.name}`, 80, 690 + i * 64));
    g.font = "400 36px Inter, sans-serif";
    g.fillText(`${data.battle_wins} battle wins · ${data.sends} songs sent`, 80, 1220);
    const a = document.createElement("a");
    a.href = c.toDataURL("image/png");
    a.download = `jingle-recap-${data.month}.png`;
    a.click();
  };
  return <Button variant="secondary" onClick={download}>Save as image</Button>;
}
