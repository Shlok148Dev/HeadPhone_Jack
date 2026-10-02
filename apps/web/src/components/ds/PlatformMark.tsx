import { AMAZON_WORDMARK, MARKS } from "./platformMarks";
import type { Platform } from "./types";
import { PLATFORM_NAMES } from "./types";
import { cn } from "./utils";

/**
 * A platform's official mark at text size (D-BRAND-02). Decorative by default: the platform's
 * name is always present as text nearby (or, for Amazon Music's wordmark, as an sr-only label).
 */
/** `mono`: currentColor (white on a coloured button), which the brand guidelines allow. */
export function PlatformMark({ platform, size = 14, className, mono = false }: { platform: Platform; size?: number; className?: string; mono?: boolean }) {
  if (platform === "UNKNOWN") return null;
  if (platform === "AMAZON_MUSIC") {
    const h = size * 0.9;
    return (
      <svg
        viewBox={`0 0 ${AMAZON_WORDMARK.w} ${AMAZON_WORDMARK.h}`}
        height={h}
        width={(h * AMAZON_WORDMARK.w) / AMAZON_WORDMARK.h}
        aria-hidden="true"
        focusable="false"
        className={cn("inline-block shrink-0 align-[-0.1em]", className)}
      >
        <path fill={mono ? "currentColor" : AMAZON_WORDMARK.hex} fillRule="evenodd" d={AMAZON_WORDMARK.d} />
      </svg>
    );
  }
  const m = (MARKS as Record<string, { hex: string; d: string } | undefined>)[platform];
  if (!m) return null; // a platform without an official mark here renders nothing (its name still shows)
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false" className={cn("inline-block shrink-0 align-[-0.125em]", className)}>
      <path fill={mono ? "currentColor" : m.hex} d={m.d} />
    </svg>
  );
}

/** Mark + name. Amazon Music's wordmark already spells the name, so the text goes to screen readers only. */
export function PlatformLabel({ platform, size = 14, className }: { platform: Platform; size?: number; className?: string }) {
  if (platform === "UNKNOWN") return null;
  const name = PLATFORM_NAMES[platform];
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <PlatformMark platform={platform} size={size} />
      {platform === "AMAZON_MUSIC" ? <span className="sr-only">{name}</span> : <span>{name}</span>}
    </span>
  );
}
