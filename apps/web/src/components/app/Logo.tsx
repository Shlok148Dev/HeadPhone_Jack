import Link from "next/link";
import { cn } from "@/components/ds";
import { LogoMark } from "./LogoMark";

/** Jingle's logo: the cassette-and-earphones mark plus the lowercase wordmark (D-BRAND-03). */
export function Logo({ href = "/", className }: { href?: string; className?: string }) {
  return (
    <Link
      href={href}
      className={cn("inline-flex items-center gap-2 rounded-md font-display text-xl font-bold tracking-tight text-text", className)}
      aria-label="Jingle home"
    >
      <LogoMark size={34} className="-my-1" />
      jingle
    </Link>
  );
}
