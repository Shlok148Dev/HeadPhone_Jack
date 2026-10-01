"use client";

import { Icons, cn } from "@/components/ds";
import { useMyPlatform } from "@/lib/send";
import { openTarget, type Song } from "@/lib/sends";

/** "Open in {my platform}", or "Not found on {Platform}" + a search there (JNG-06-03). */
export function OpenLink({ song, compact = false, className }: { song: Song; compact?: boolean; className?: string }) {
  const mine = useMyPlatform();
  const t = openTarget(song, mine);
  if (!t) return null;
  return (
    <span className={cn("flex flex-col gap-1", className)}>
      {t.notFound && !compact && <span className="font-mono text-xs text-text-muted">{t.notFound}</span>}
      <a
        href={t.url}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={compact ? `${t.label}: ${song.title}` : undefined}
        title={t.notFound ?? undefined}
        className={cn(
          "inline-flex min-h-11 items-center gap-2 rounded-full border border-border text-sm font-medium hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]",
          compact ? "min-w-11 justify-center px-3" : "px-4",
        )}
      >
        <Icons.Open size={16} />
        {!compact && t.label}
      </a>
    </span>
  );
}
