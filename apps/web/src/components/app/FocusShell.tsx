import type { ReactNode } from "react";
import { ThemeToggle } from "@/components/ds";
import { ArtPanel } from "./ArtPanel";
import { Logo } from "./Logo";

/**
 * Single-task layout for sign-in, sign-up, invites and pairing (UX_SPEC §2.1, D-ONB-02).
 * Narrow pages are a viewport-locked split: the form, vertically centred, on the left, always
 * visible without scrolling; the live cover wall fills the right from lg up. Phones get the form only.
 * `wide` (onboarding steps) keeps a centred card on a scrolling page.
 */
export function FocusShell({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  if (wide) {
    return (
      <div className="flex min-h-dvh flex-col bg-bg">
        <header className="flex h-16 items-center justify-between px-4 md:px-8">
          <Logo />
          <ThemeToggle />
        </header>
        <main id="main" className="flex flex-1 items-start justify-center px-4 pb-16 pt-4 md:items-center md:pt-0">
          <div className="jg-enter w-full max-w-3xl rounded-[20px] border border-border bg-surface-1 p-6 shadow-1 md:p-8">{children}</div>
        </main>
      </div>
    );
  }
  return (
    <div className="grid h-dvh overflow-hidden bg-bg lg:grid-cols-[minmax(440px,5fr)_7fr]">
      {/* Scrolls only if the form itself is taller than a very short window. */}
      <div className="flex min-h-0 flex-col overflow-y-auto px-6 md:px-12">
        <header className="flex h-16 shrink-0 items-center justify-between">
          <Logo />
          <ThemeToggle />
        </header>
        <main id="main" className="flex flex-1 items-center justify-center py-6">
          <div className="jg-enter w-full max-w-[400px]">{children}</div>
        </main>
      </div>
      <ArtPanel />
    </div>
  );
}
