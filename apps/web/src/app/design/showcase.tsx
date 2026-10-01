"use client";

import { useState, type ReactNode } from "react";
import { brandContrastPairs, contrastPairs, contrastRatio, radius, themes, type ThemeColors } from "@jingle/design-tokens";
import {
  Avatar,
  Pulse,
  AvatarStack,
  Blip,
  Button,
  Chip,
  CompatibilityMeter,
  Dialog,
  EmptyState,
  EqualiserBars,
  ErrorState,
  FeedCard,
  FeedCardSkeleton,
  FilterChips,
  GenerativeCover,
  IconButton,
  Icons,
  LiveBadge,
  NowPlayingBar,
  PlatformBadge,
  Sheet,
  Shelf,
  Skeleton,
  SuggestionCard,
  Tabs,
  ThemeToggle,
  ToastProvider,
  useToast,
  type BlipPose,
  type Platform,
} from "@/components/ds";
import { useTheme } from "@/lib/theme";
import { coverSeeds, sampleCards } from "./samples";

function Section({ id, title, children, note }: { id: string; title: string; note?: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="flex flex-col gap-4 border-t border-border py-10">
      <div>
        <h2 id={`${id}-h`} className="font-display text-2xl font-semibold text-text">
          {title}
        </h2>
        {note && <p className="mt-1 max-w-2xl text-sm text-text-muted">{note}</p>}
      </div>
      {children}
    </section>
  );
}

const SWATCHES: Array<keyof ThemeColors> = [
  "bg",
  "surface-1",
  "surface-2",
  "surface-3",
  "border",
  "border-strong",
  "text",
  "text-muted",
  "text-subtle",
  "accent-text",
  "live",
  "live-soft",
  "live-text",
  "danger",
  "danger-soft",
  "warning",
  "warning-soft",
  "success",
  "success-soft",
  "focus-ring",
];

function ColourTokens() {
  const { theme } = useTheme();
  const t = themes[theme];
  return (
    <>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
        <div className="flex flex-col overflow-hidden rounded-md border border-border bg-surface-1">
          <span className="h-16 bg-gradient-brand" />
          <span className="p-2 font-mono text-xs text-text">--gradient-brand</span>
        </div>
        {SWATCHES.map((k) => (
          <div key={k} className="flex flex-col overflow-hidden rounded-md border border-border bg-surface-1">
            <span className="h-16" style={{ background: `var(--${k})` }} />
            <span className="flex flex-col p-2">
              <span className="font-mono text-xs text-text">--{k}</span>
              <span className="font-mono text-xs text-text-muted">{t[k]}</span>
            </span>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full min-w-[520px] text-left text-sm">
          <caption className="p-3 text-left text-sm text-text-muted">
            Text pairs, WCAG contrast (AA needs 4.5). Current theme: <span className="font-mono">{theme}</span>
          </caption>
          <thead className="bg-surface-2 text-text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">Sample</th>
              <th className="px-3 py-2 font-medium">Pair</th>
              <th className="px-3 py-2 font-medium">Dark</th>
              <th className="px-3 py-2 font-medium">Light</th>
            </tr>
          </thead>
          <tbody>
            {contrastPairs.map(([fg, bg]) => {
              const d = contrastRatio(themes.dark[fg], themes.dark[bg]);
              const l = contrastRatio(themes.light[fg], themes.light[bg]);
              return (
                <tr key={`${fg}/${bg}`} className="border-t border-border">
                  <td className="px-3 py-2">
                    <span className="inline-block rounded-sm px-2 py-1" style={{ color: `var(--${fg})`, background: `var(--${bg})` }}>
                      Aa Kesariya
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-text">
                    {fg} / {bg}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-text">{d.toFixed(2)}</td>
                  <td className="px-3 py-2 font-mono text-xs text-text">{l.toFixed(2)}</td>
                </tr>
              );
            })}
            {brandContrastPairs.map(([fg, bg]) => (
              <tr key={bg} className="border-t border-border">
                <td className="px-3 py-2">
                  <span className="inline-block rounded-sm px-2 py-1" style={{ color: fg, background: bg }}>
                    Aa Send
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-xs text-text">on-brand / {bg}</td>
                <td className="px-3 py-2 font-mono text-xs text-text" colSpan={2}>
                  {contrastRatio(fg, bg).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function TypeScale() {
  return (
    <div className="flex flex-col gap-4">
      <p className="font-display text-5xl font-semibold leading-tight text-text">Display 48 — Bricolage</p>
      <p className="font-display text-3xl font-semibold text-text">Title 30 — What your friends are playing</p>
      <p className="font-display text-xl font-semibold text-text">Heading 20 — Live now</p>
      <p className="text-base text-text">Body 16 — Inter. Aanya is listening to Kesariya by Arijit Singh.</p>
      <p className="text-sm text-text-muted">Small 14 — secondary text, muted.</p>
      <p className="font-mono text-xs text-text-muted">Mono 12 — 20 min ago on Apple Music · 87 / 100</p>
    </div>
  );
}

function SpacingRadius() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end gap-4">
        {[1, 2, 3, 4, 6, 8, 12, 16].map((n) => (
          <div key={n} className="flex flex-col items-center gap-2">
            <span className="block bg-gradient-brand" style={{ width: n * 4, height: n * 4 }} />
            <span className="font-mono text-xs text-text-muted">{n * 4}</span>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-4">
        {(Object.keys(radius) as Array<keyof typeof radius>).map((k) => (
          <div key={k} className="flex flex-col items-center gap-2">
            <span className="block h-16 w-16 border border-border-strong bg-surface-2" style={{ borderRadius: `var(--r-${k})` }} />
            <span className="font-mono text-xs text-text-muted">
              r-{k} {radius[k]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

const PLATFORMS: Platform[] = ["SPOTIFY", "APPLE_MUSIC", "YOUTUBE_MUSIC", "AMAZON_MUSIC"];
const POSES: BlipPose[] = ["idle", "wave", "cheer", "sleepy", "listening", "thinking", "oops"];

function Showcase() {
  const { toast } = useToast();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [chip, setChip] = useState(true);
  const [filter, setFilter] = useState("all");
  const [npEmpty, setNpEmpty] = useState(false);
  const [replay, setReplay] = useState(0);

  const fakeLoad = () => {
    setLoading(true);
    setTimeout(() => setLoading(false), 1500);
  };

  return (
    <div className="mx-auto max-w-6xl overflow-x-clip px-4 pb-40 sm:px-6">
      <header className="sticky top-0 flex items-center justify-between gap-4 border-b border-border bg-bg/85 py-4 backdrop-blur-md" style={{ zIndex: "var(--z-sticky)" }}>
        <div className="flex items-center gap-3">
          <Blip pose="idle" size={40} decorative />
          <div>
            <h1 className="font-display text-2xl font-semibold text-text">Jingle design system</h1>
            <p className="text-sm text-text-muted">Tokens, components and card states. The reference for every screen.</p>
          </div>
        </div>
        <ThemeToggle />
      </header>

      <Section id="colour" title="Colour tokens" note="Coral means Live and nothing else. The brand gradient is for the one primary action per view.">
        <ColourTokens />
      </Section>

      <Section id="type" title="Type scale">
        <TypeScale />
      </Section>

      <Section id="spacing" title="Spacing and radius" note="4 px grid. Touch targets are at least 44 × 44.">
        <SpacingRadius />
      </Section>

      <Section id="buttons" title="Buttons">
        <div className="flex flex-wrap items-center gap-3">
          <Button leadingIcon={<Icons.Send size={16} />}>Send to a friend</Button>
          <Button variant="secondary">Open in my app</Button>
          <Button variant="ghost">Not now</Button>
          <Button variant="danger">Remove friend</Button>
          <Button loading={loading} loadingLabel="Connecting…" onClick={fakeLoad}>
            Connect
          </Button>
          <Button disabled>Disabled</Button>
          <IconButton label="Send">
            <Icons.Send />
          </IconButton>
          <IconButton label="Refresh" variant="secondary">
            <Icons.Refresh />
          </IconButton>
        </div>
      </Section>

      <Section id="chips" title="Chips">
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap gap-2">
            <Chip selected={chip} onSelectedChange={setChip}>
              Friends only
            </Chip>
            <Chip>Toggle chip</Chip>
          </div>
          <FilterChips
            label="Filter feed"
            value={filter}
            onChange={setFilter}
            options={[
              { value: "all", label: "All" },
              { value: "live", label: "Live now" },
              { value: "recent", label: "Recent" },
              { value: "top", label: "Top" },
            ]}
          />
          <p className="font-mono text-xs text-text-muted">selected: {filter}</p>
        </div>
      </Section>

      <Section id="badges" title="Platform badges and Live" note="Platform names are plain text on neutral surfaces. No logos, icons or brand colours.">
        <div className="flex flex-wrap items-center gap-3">
          {PLATFORMS.map((p) => (
            <PlatformBadge key={p} platform={p} />
          ))}
          <LiveBadge />
          <EqualiserBars />
          <EqualiserBars size={24} seed="demo" />
        </div>
      </Section>

      <Section id="cards" title="Feed cards" note="Labels come verbatim from the server (freshness_label). Live styling only when state is LIVE.">
        <div className="flex items-center gap-3">
          <Button variant="secondary" onClick={() => setReplay((n) => n + 1)} leadingIcon={<Icons.Refresh size={16} />}>
            Replay entry
          </Button>
          <span className="font-mono text-xs text-text-muted">card.enter · spring.soft · 40 ms stagger</span>
        </div>
        <div key={replay} className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(184px,1fr))]">
          {sampleCards.map((s, i) => (
            <div key={s.title} className="flex flex-col gap-1">
              <span className="px-2 font-mono text-xs text-text-subtle">{s.title}</span>
              <FeedCard
                card={s.card}
                index={i}
                topRecordings={s.top}
                myPlatform="SPOTIFY"
                onSend={(c) => toast({ title: "Ready to send", description: `${c.recording?.title ?? ""}: pick a friend.` })}
              />
            </div>
          ))}
        </div>
      </Section>

      <Section id="loading" title="Skeletons" note="Shaped like the real content.">
        <div className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(184px,1fr))]">
          <FeedCardSkeleton />
          <FeedCardSkeleton />
          <div className="flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-4">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-3.5 w-full" />
            <Skeleton className="h-3.5 w-5/6" />
            <Skeleton rounded="pill" className="h-11 w-32" />
          </div>
        </div>
      </Section>

      <Section id="states" title="Empty and error states">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-border bg-surface-1">
            <EmptyState
              pose="wave"
              title="No friends here yet"
              description="Add a friend to see what they're playing, on any app."
              action={{ label: "Find friends", onClick: () => toast({ title: "Find friends", tone: "neutral" }) }}
            />
          </div>
          <div className="rounded-lg border border-border bg-surface-1">
            <ErrorState message="We couldn't load your feed. Check your connection and try again." onRetry={fakeLoad} retrying={loading} />
          </div>
        </div>
      </Section>

      <Section id="blip" title="Blip" note="Empty states (wave, sleepy), success (cheer), long jobs (idle). Never decoration on busy screens.">
        <div className="flex flex-wrap gap-8">
          {POSES.map((p) => (
            <figure key={p} className="flex flex-col items-center gap-2">
              <Blip pose={p} size={112} />
              <figcaption className="font-mono text-xs text-text-muted">{p}</figcaption>
            </figure>
          ))}
        </div>
      </Section>

      <Section id="covers" title="Generative covers" note="Deterministic per seed. The fallback for missing artwork; never a grey square.">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {coverSeeds.map((s) => (
            <figure key={s} className="flex flex-col gap-2">
              <GenerativeCover seed={s} label={`Generated cover for ${s}`} />
              <figcaption className="truncate font-mono text-xs text-text-muted">{s}</figcaption>
            </figure>
          ))}
        </div>
        <div className="flex items-center gap-4">
          <Pulse state="live" name="Aanya Sharma" seed="u-aanya" size={48} decorative={false} />
          <Pulse state="recent" name="Meera Iyer" seed="u-meera" size={48} decorative={false} />
          <Avatar name="Aanya Sharma" seed="u-aanya" size={48} />
          <Avatar name="Kabir Mehta" seed="u-kabir" size={48} />
          <AvatarStack
            people={[
              { id: "u-aanya", name: "Aanya" },
              { id: "u-kabir", name: "Kabir" },
              { id: "u-meera", name: "Meera" },
              { id: "u-rohan", name: "Rohan" },
              { id: "u-isha", name: "Isha" },
              { id: "u-dev", name: "Dev" },
            ]}
          />
        </div>
      </Section>

      <Section id="shelf" title="Shelf" note="Scroll-snap row. Arrow buttons for pointers; ← → Home End move between cards for keyboards.">
        <Shelf title="Live now" live count={2}>
          {sampleCards.slice(0, 2).map((s) => (
            <FeedCard key={s.title} card={s.card} myPlatform="SPOTIFY" sharedLayout={false} />
          ))}
        </Shelf>
        <Shelf title="Friends' recent plays">
          {sampleCards.slice(2).map((s) => (
            <FeedCard key={s.title} card={s.card} topRecordings={s.top} myPlatform="SPOTIFY" sharedLayout={false} />
          ))}
        </Shelf>
        <Shelf title="New for you">
          {coverSeeds.map((s) => (
            <div key={s} className="flex flex-col gap-2">
              <GenerativeCover seed={s} />
              <span className="truncate text-sm text-text">{s.replace("rec-", "").replace(/-/g, " ")}</span>
            </div>
          ))}
        </Shelf>
      </Section>

      <Section id="compat" title="Compatibility and suggestions">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-border bg-surface-1 p-5">
            <CompatibilityMeter
              score={82}
              breakdown={[
                { label: "Shared artists", value: 90, detail: "Arijit Singh, Prateek Kuhad, AP Dhillon" },
                { label: "Genre overlap", value: 76, detail: "Indie, Bollywood, hip-hop" },
                { label: "Listening times", value: 64, detail: "Both late-night listeners" },
              ]}
            />
          </div>
          <SuggestionCard
            person={{ id: "u-tara", name: "Tara Nair", username: "tara" }}
            reasons={["3 friends in common", "You both play Prateek Kuhad a lot", "Same late-night listening"]}
            onAction={() => toast({ title: "Request sent", tone: "success" })}
            onDismiss={() => undefined}
          />
        </div>
      </Section>

      <Section id="overlays" title="Dialogs, sheets and toasts">
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={() => setDialogOpen(true)}>
            Open dialog
          </Button>
          <Button variant="secondary" onClick={() => setSheetOpen(true)}>
            Open sheet
          </Button>
          <Button variant="secondary" onClick={() => toast({ title: "Sent to Aanya", description: "Kesariya · Arijit Singh", tone: "success" })}>
            Success toast
          </Button>
          <Button variant="secondary" onClick={() => toast({ title: "Couldn't send", description: "Try again in a moment.", tone: "danger" })}>
            Error toast
          </Button>
        </div>
        <Tabs
          label="Profile sections"
          items={[
            { id: "recent", label: "Recent", content: <p className="text-sm text-text-muted">Recent plays appear here.</p> },
            { id: "top", label: "Top", content: <p className="text-sm text-text-muted">Top this month appears here.</p> },
            { id: "blends", label: "Blends", content: <p className="text-sm text-text-muted">Shared playlists appear here.</p> },
          ]}
        />
      </Section>

      <Section id="nowplaying" title="Now playing bar">
        <div className="flex flex-col gap-3">
          <Chip selected={npEmpty} onSelectedChange={setNpEmpty} className="w-fit">
            Show empty state
          </Chip>
          <NowPlayingBar
            position="static"
            track={
              npEmpty
                ? null
                : {
                    id: "rec-kesariya",
                    title: "Kesariya",
                    artist: "Arijit Singh",
                    artwork_url: null,
                    platform: "SPOTIFY",
                    state: "LIVE",
                    freshness_label: "Live on Spotify",
                  }
            }
            onSend={() => toast({ title: "Pick a friend to send Kesariya" })}
          />
        </div>
      </Section>

      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title="Send Kesariya"
        description="Pick who gets it. They can open it in their own app."
        footer={
          <>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                setDialogOpen(false);
                toast({ title: "Sent to Aanya", tone: "success" });
              }}
            >
              Send
            </Button>
          </>
        }
      >
        <FilterChips
          label="Recipient"
          options={[
            { value: "aanya", label: "Aanya" },
            { value: "kabir", label: "Kabir" },
            { value: "meera", label: "Meera" },
          ]}
        />
      </Dialog>

      <Sheet open={sheetOpen} onClose={() => setSheetOpen(false)} title="Share to a circle" description="Circles see it in their feed.">
        <div className="flex flex-col gap-2">
          {["College friends", "Road trip", "Late night"].map((c) => (
            <Button key={c} variant="secondary" className="justify-start" onClick={() => setSheetOpen(false)}>
              {c}
            </Button>
          ))}
        </div>
      </Sheet>
    </div>
  );
}

export function DesignShowcase() {
  return (
    <ToastProvider>
      <Showcase />
    </ToastProvider>
  );
}
