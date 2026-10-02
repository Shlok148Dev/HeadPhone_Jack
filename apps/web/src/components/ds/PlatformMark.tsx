import { AMAZON_WORDMARK, MARKS } from "./platformMarks";
import type { Platform } from "./types";
import { PLATFORM_NAMES } from "./types";
import { cn } from "./utils";

/**
 * A platform's official mark at text size (D-BRAND-02). Decorative by default: the platform's
 * name is always present as text nearby (or, for Amazon Music's wordmark, as an sr-only label).
 */
export function PlatformMark({ platform, size = 14, className }: { platform: Platform; size?: number; className?: string }) {
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
        <path fill={AMAZON_WORDMARK.hex} fillRule="evenodd" d={AMAZON_WORDMARK.d} />
      </svg>
    );
  }
  const m = MARKS[platform];
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false" className={cn("inline-block shrink-0 align-[-0.125em]", className)}>
      <path fill={m.hex} d={m.d} />
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
