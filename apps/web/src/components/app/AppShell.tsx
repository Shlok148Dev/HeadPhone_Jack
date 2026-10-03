"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { lazy, Suspense, useEffect, useState, type ComponentType, type ReactNode } from "react";
import {
  Avatar,
  IconButton,
  Icons,
  NowPlayingBar,
  Skeleton,
  ThemeToggle,
  cn,
} from "@/components/ds";
import { CompanionAutoPair } from "@/components/app/CompanionAutoPair";
import { useAuth } from "@/lib/auth";
import { toNowPlaying, useMyCard } from "@/lib/queries";
import { RealtimeProvider, useRealtimeStatus } from "@/lib/realtime";
import { SendProvider, songFromCard, useOpenSend } from "@/lib/send";
import { useUnread } from "@/lib/sends";
import { useNotifications } from "@/lib/trust";
import { Logo } from "./Logo";
// Presence lives in wide-screen chrome (lg/xl) and fills from live data anyway: keep it out of first load.
const SidebarLive = lazy(() => import("./Presence").then((m) => ({ default: m.SidebarLive })));
const ActivityPanel = lazy(() => import("./Presence").then((m) => ({ default: m.ActivityPanel })));

// Loaded on first ⌘K / tap so the shell stays inside Home's JS budget.
const CommandPalette = lazy(() => import("./CommandPalette").then((m) => ({ default: m.CommandPalette })));

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
  const [palette, setPalette] = useState(false);
  // Friend activity is a panel you open, not chrome you must live with (D-SHELL-04). Remembered per device.
  const [activity, setActivity] = useState(false);
  useEffect(() => {
    try {
      setActivity(localStorage.getItem("jingle-activity") === "open");
    } catch {
      /* storage unavailable: stays closed */
    }
  }, []);
  const toggleActivity = (open: boolean) => {
    setActivity(open);
    try {
      localStorage.setItem("jingle-activity", open ? "open" : "closed");
    } catch {
      /* ignore */
    }
  };

  // ⌘K / Ctrl+K opens search and commands anywhere (D-SHELL-03).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette((p) => !p);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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
      <SendProvider>
        <CompanionAutoPair />
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
                    "relative flex min-h-11 flex-col items-center justify-center gap-1 rounded-md px-2 py-2 text-[11px] font-medium text-text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-text lg:flex-row lg:justify-start lg:gap-3 lg:px-3 lg:text-sm",
                    active && "bg-surface-2 text-text",
                  )}
                >
                  {active && <span aria-hidden className="bg-gradient-brand absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-pill" />}
                  <Icon size={22} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
          {!activity && (
            <Suspense fallback={null}>
              <SidebarLive />
            </Suspense>
          )}
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

        {activity && (
          <Suspense fallback={null}>
            <ActivityPanel onClose={() => toggleActivity(false)} />
          </Suspense>
        )}
        <div className={cn("md:pl-[72px] lg:pl-60 xl:pl-[280px]", activity && "xl:pr-[320px]")}>
          <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-transparent bg-[var(--surface-glass)] px-4 backdrop-blur-xl md:h-16 md:px-6">
            <div className="md:hidden">
              <Logo href="/home" className="text-lg" />
            </div>
            <div className="flex flex-1 justify-center">
              <SearchButton onOpen={() => setPalette(true)} />
            </div>
            <InboxButton active={isActive(pathname, "/inbox")} />
            <BellButton active={isActive(pathname, "/notifications")} />
            <IconButton
              label="Friend activity"
              aria-pressed={activity}
              className={cn("hidden lg:inline-flex", activity && "bg-surface-2 text-text")}
              onClick={() => toggleActivity(!activity)}
            >
              <Icons.Friends size={20} />
            </IconButton>
            {me.is_staff && (
              <Link href="/staff" className="hidden rounded-full px-3 py-2 text-sm text-text-muted hover:bg-surface-2 hover:text-text md:inline-flex">
                Staff
              </Link>
            )}
            <ThemeToggle />
            <Link
              href="/settings/connections"
              className="hidden rounded-full md:inline-flex"
              aria-label="Your account and settings"
            >
              <Avatar name={me.display_name || me.username} url={me.avatar_url} seed={me.id} size={36} />
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

        {palette && (
          <Suspense fallback={null}>
            <CommandPalette onClose={() => setPalette(false)} />
          </Suspense>
        )}
        <MySendBar
          card={card.data}
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
      </SendProvider>
    </RealtimeProvider>
  );
}

/** Top bar search: opens the command palette (⌘K). */
function SearchButton({ onOpen }: { onOpen: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label="Search people, songs and circles"
      aria-keyshortcuts="Control+K Meta+K"
      className="flex h-10 w-11 items-center justify-center gap-2 rounded-pill border border-border bg-surface-2 text-sm text-text-muted transition-colors duration-150 hover:border-border-strong hover:text-text focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)] sm:w-full sm:max-w-[420px] sm:justify-start sm:px-4"
    >
      <Icons.Search size={17} />
      <span className="hidden flex-1 text-left sm:inline">Search people, songs, circles</span>
      <kbd className="hidden rounded-sm border border-border px-1.5 font-mono text-[11px] lg:inline">Ctrl K</kbd>
    </button>
  );
}

/** TopBar Inbox with the unviewed-sends badge (UX_SPEC TopBar; JNG-06-07). */
function InboxButton({ active }: { active: boolean }) {
  const unread = useUnread().data?.count ?? 0;
  const label = unread ? `Inbox, ${unread} new` : "Inbox";
  return (
    <Link
      href="/inbox"
      aria-label={label}
      aria-current={active ? "page" : undefined}
      className="relative inline-flex h-11 w-11 items-center justify-center rounded-full text-text-muted hover:bg-surface-2 hover:text-text focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]"
    >
      <Icons.Inbox size={22} />
      {unread > 0 && (
        <span aria-hidden className="absolute right-1 top-1 min-w-[18px] rounded-full bg-text px-1 text-center font-mono text-[11px] leading-[18px] text-bg">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}

/** TopBar bell: unread notifications (JNG-11-01). */
function BellButton({ active }: { active: boolean }) {
  const unread = useNotifications().data?.unread ?? 0;
  return (
    <Link
      href="/notifications"
      aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
      aria-current={active ? "page" : undefined}
      className="relative inline-flex h-11 w-11 items-center justify-center rounded-full text-text-muted hover:bg-surface-2 hover:text-text focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]"
    >
      <Icons.Bell size={22} />
      {unread > 0 && (
        <span aria-hidden className="absolute right-1 top-1 min-w-[18px] rounded-full bg-text px-1 text-center font-mono text-[11px] leading-[18px] text-bg">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}

function MySendBar({ card, className }: { card: Parameters<typeof toNowPlaying>[0]; className?: string }) {
  const openSend = useOpenSend();
  const track = toNowPlaying(card);
  const song = card ? songFromCard(card) : undefined;
  return <NowPlayingBar track={track} onSend={song ? () => openSend({ song }) : undefined} className={className} />;
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
