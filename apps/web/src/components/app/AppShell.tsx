"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ComponentType, type ReactNode } from "react";
import {
  Avatar,
  IconButton,
  Icons,
  NowPlayingBar,
  Skeleton,
  ThemeToggle,
  cn,
} from "@/components/ds";
import { useAuth } from "@/lib/auth";
import { toNowPlaying, useMyCard } from "@/lib/queries";
import { RealtimeProvider, useRealtimeStatus } from "@/lib/realtime";
import { Logo } from "./Logo";

interface NavItem {
  href: string;
  label: string;
  icon: ComponentType<{ size?: number }>;
  mobile: boolean;
}

const NAV: NavItem[] = [
  { href: "/home", label: "Home", icon: Icons.Home, mobile: true },
  { href: "/friends", label: "Friends", icon: Icons.Friends, mobile: true },
  { href: "/circles", label: "Circles", icon: Icons.Circles, mobile: true },
  { href: "/blends", label: "Blends", icon: Icons.Blend, mobile: false },
  { href: "/rituals", label: "Rituals", icon: Icons.Trophy, mobile: true },
];

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Signed-in layout: sidebar (≥768 px, rail until 1024), top bar, mobile tabs, my now-playing bar. */
export function AppShell({ children }: { children: ReactNode }) {
  const { status, me, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const card = useMyCard(status === "signed-in" && !me?.needs_onboarding);

  useEffect(() => {
    if (status === "signed-out")
      router.replace(`/signin?next=${encodeURIComponent(pathname)}`);
    else if (status === "signed-in" && me?.needs_onboarding)
      router.replace("/onboarding/profile");
  }, [status, me, router, pathname]);

  if (status !== "signed-in" || !me || me.needs_onboarding) {
    return (
      <div
        className="flex min-h-dvh items-center justify-center bg-bg"
        aria-busy="true"
      >
        <Skeleton className="h-10 w-40" />
      </div>
    );
  }

  const profileHref = `/u/${me.username}`;
  return (
    <RealtimeProvider userId={me.id}>
      <div className="min-h-dvh bg-bg text-text">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface-2 focus:px-4 focus:py-2"
        >
          Skip to content
        </a>
        <aside
          aria-label="Main"
          className="fixed inset-y-0 left-0 hidden w-[72px] flex-col border-r border-border bg-surface-1 px-2 py-4 md:flex lg:w-60 lg:px-4 xl:w-[280px]"
        >
          <div className="mb-6 hidden px-2 lg:block">
            <Logo href="/home" />
          </div>
          <nav className="flex flex-col gap-1">
            {[
              ...NAV,
              {
                href: profileHref,
                label: "Profile",
                icon: Icons.User,
                mobile: false,
              },
            ].map((item) => {
              const active = isActive(pathname, item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex min-h-11 flex-col items-center justify-center gap-1 rounded-md px-2 py-2 text-[11px] font-medium text-text-muted transition-colors hover:bg-surface-2 hover:text-text lg:flex-row lg:justify-start lg:gap-3 lg:px-3 lg:text-sm",
                    active && "bg-surface-2 text-text",
                  )}
                >
                  <Icon size={22} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
          <div className="mt-auto flex flex-col gap-1">
            <Link
              href="/settings/connections"
              aria-current={
                pathname.startsWith("/settings") ? "page" : undefined
              }
              className={cn(
                "flex min-h-11 flex-col items-center justify-center gap-1 rounded-md px-2 py-2 text-[11px] text-text-muted hover:bg-surface-2 hover:text-text lg:flex-row lg:justify-start lg:gap-3 lg:px-3 lg:text-sm",
                pathname.startsWith("/settings") && "bg-surface-2 text-text",
              )}
            >
              <Icons.Settings size={22} />
              <span>Settings</span>
            </Link>
          </div>
        </aside>

        <div className="md:pl-[72px] lg:pl-60 xl:pl-[280px]">
          <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-transparent bg-[var(--surface-glass)] px-4 backdrop-blur-xl md:h-16 md:px-6">
            <div className="md:hidden">
              <Logo href="/home" className="text-lg" />
            </div>
            <div className="flex-1" />
            <ThemeToggle />
            <Link
              href="/settings/connections"
              className="hidden rounded-full md:inline-flex"
              aria-label="Your account and settings"
            >
              <Avatar name={me.display_name || me.username} size={36} />
            </Link>
            <IconButton
              label="Sign out"
              variant="ghost"
              onClick={() => void signOut().then(() => router.replace("/"))}
            >
              <Icons.LogOut />
            </IconButton>
          </header>
          <ReconnectingBanner />
          <main
            id="main"
            tabIndex={-1}
            className="mx-auto w-full max-w-[1600px] px-4 pb-44 pt-4 outline-none md:px-6 md:pb-32 xl:px-8"
          >
            {children}
          </main>
        </div>

        <NowPlayingBar
          track={toNowPlaying(card.data)}
          className="bottom-[calc(64px+env(safe-area-inset-bottom))] md:bottom-0 md:left-[72px] lg:left-60 xl:left-[280px]"
        />

        <nav
          aria-label="Main"
          className="fixed inset-x-0 bottom-0 z-40 grid h-16 grid-cols-5 border-t border-border bg-surface-1 pb-[env(safe-area-inset-bottom)] md:hidden"
        >
          {[
            ...NAV.filter((n) => n.mobile),
            { href: profileHref, label: "You", icon: Icons.User, mobile: true },
          ].map((item) => {
            const active = isActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex flex-col items-center justify-center gap-0.5 text-[11px] text-text-muted",
                  active && "text-text",
                )}
              >
                <Icon size={22} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </RealtimeProvider>
  );
}

/** UX_SPEC §5.4 degraded: cards keep their last state while the live connection recovers. */
function ReconnectingBanner() {
  const status = useRealtimeStatus();
  if (status !== "reconnecting") return null;
  return (
    <p
      role="status"
      className="bg-surface-2 px-4 py-2 text-center font-mono text-xs text-text-muted"
    >
      Reconnecting… Showing the latest we have.
    </p>
  );
}
