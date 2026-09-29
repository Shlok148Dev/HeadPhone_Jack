import type { ReactNode } from "react";
import { ThemeToggle } from "@/components/ds";
import { Logo } from "./Logo";

/** Centred single-task layout for sign-in, sign-up, onboarding and pairing (UX_SPEC §2.1). */
export function FocusShell({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <header className="flex h-16 items-center justify-between px-4 md:px-8">
        <Logo />
        <ThemeToggle />
      </header>
      <main id="main" className="flex flex-1 items-start justify-center px-4 pb-16 pt-4 md:items-center md:pt-0">
        <div
          className={`w-full ${wide ? "max-w-3xl" : "max-w-[480px]"} rounded-lg border border-border bg-surface-1 p-6 shadow-1 md:p-8`}
        >
          {children}
        </div>
      </main>
    </div>
  );
}
