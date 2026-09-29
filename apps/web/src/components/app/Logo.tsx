import Link from "next/link";
import { cn } from "@/components/ds";

/** Jingle's own mark: a gradient note-dot plus the wordmark in Bricolage. */
export function Logo({ href = "/", className }: { href?: string; className?: string }) {
  return (
    <Link
      href={href}
      className={cn("inline-flex items-center gap-2 rounded-md font-display text-xl font-bold tracking-tight text-text", className)}
      aria-label="Jingle home"
    >
      <span aria-hidden="true" className="relative inline-block h-6 w-6 rounded-full bg-gradient-brand">
        <span className="absolute left-[9px] top-[5px] h-[11px] w-[3px] rounded-full bg-bg" />
        <span className="absolute left-[5px] top-[13px] h-[6px] w-[7px] rounded-full bg-bg" />
      </span>
      Jingle
    </Link>
  );
}
