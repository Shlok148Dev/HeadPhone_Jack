import type { ReactNode } from "react";
import { ThemeToggle } from "@/components/ds";
import { ArtPanel } from "./ArtPanel";
import { Logo } from "./Logo";

/**
 * Single-task layout for sign-in, sign-up, onboarding and pairing (UX_SPEC §2.1). On large screens
 * the narrow variant becomes a split screen with live real artwork beside the form (D-ONB-01).
 */
export function FocusShell({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <header className="flex h-16 items-center justify-between px-4 md:px-8">
        <Logo />
        <ThemeToggle />
      </header>
      <main
        id="main"
        className={`flex flex-1 items-start justify-center gap-8 px-4 pb-16 pt-4 md:items-center md:pt-0 ${wide ? "" : "lg:grid lg:grid-cols-2 lg:items-stretch lg:px-8 lg:pb-8"}`}
      >
        <div className={wide ? "w-full max-w-3xl" : "flex w-full items-center justify-center"}>
          <div className={`jg-enter w-full ${wide ? "" : "max-w-[480px]"} rounded-[20px] border border-border bg-surface-1 p-6 shadow-1 md:p-8`}>{children}</div>
        </div>
        {!wide && <ArtPanel />}
      </main>
    </div>
  );
}
