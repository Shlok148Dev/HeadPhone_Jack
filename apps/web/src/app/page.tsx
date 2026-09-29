import { Blip, ButtonLink, FeedCard, ThemeToggle, type FeedCardData } from "@/components/ds";
import { Logo } from "@/components/app/Logo";
import { RedirectIfSignedIn } from "@/components/app/RedirectIfSignedIn";

const EXAMPLE: FeedCardData[] = [
  {
    friend: { id: "ex-aanya", username: "aanya", display_name: "Aanya", avatar_url: null },
    state: "LIVE",
    platform: "SPOTIFY",
    recording: { id: "ex-1", title: "Kesariya", artist: "Arijit Singh", artwork_url: null, links: {} },
    freshness_label: "Live on Spotify",
    degraded: false,
    attribution: null,
  },
  {
    friend: { id: "ex-meera", username: "meera", display_name: "Meera", avatar_url: null },
    state: "RECENT",
    platform: "APPLE_MUSIC",
    recording: { id: "ex-2", title: "cold/mess", artist: "Prateek Kuhad", artwork_url: null, links: {} },
    freshness_label: "2 h ago on Apple Music",
    degraded: false,
    attribution: null,
  },
  {
    friend: { id: "ex-dev", username: "dev", display_name: "Dev", avatar_url: null },
    state: "RECENT",
    platform: "YOUTUBE_MUSIC",
    recording: { id: "ex-3", title: "Excuses", artist: "AP Dhillon", artwork_url: null, links: {} },
    freshness_label: "20 min ago on YouTube Music",
    degraded: false,
    attribution: null,
  },
];

const FEATURES = [
  { pose: "wave" as const, title: "Live now", body: "See who's playing what right now, on whichever app they use. Never faked." },
  { pose: "cheer" as const, title: "Circles and battles", body: "Your crew, a weekly song battle and a leaderboard reveal every Sunday." },
  { pose: "idle" as const, title: "Blends that explain themselves", body: "A shared playlist where every track says why it's there." },
];

export default function Landing() {
  return (
    <div className="min-h-dvh bg-bg text-text">
      <RedirectIfSignedIn />
      <header className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 md:px-8">
        <Logo />
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <ButtonLink href="/signin" variant="ghost">
            Sign in
          </ButtonLink>
          <ButtonLink href="/signup" className="hidden sm:inline-flex">
            Get started
          </ButtonLink>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-6xl px-4 md:px-8">
        <section className="grid items-center gap-10 py-10 md:grid-cols-12 md:py-20">
          <div className="flex flex-col gap-6 md:col-span-7">
            <h1 className="font-display text-4xl font-bold leading-[1.05] tracking-tight md:text-6xl">
              See what your friends are playing, on any app.
            </h1>
            <p className="max-w-xl text-lg text-text-muted">
              Spotify, Apple Music, YouTube Music, Amazon Music. One feed, honest labels, no switching apps.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <ButtonLink href="/signup" size="lg">
                Connect your music
              </ButtonLink>
              <ButtonLink href="/signin" size="lg" variant="secondary">
                Sign in
              </ButtonLink>
            </div>
          </div>
          <div className="flex flex-col gap-3 md:col-span-5">
            <p className="font-mono text-xs text-text-subtle">Example feed</p>
            {EXAMPLE.map((card, i) => (
              <FeedCard key={card.friend.id} card={card} index={i} sharedLayout={false} />
            ))}
          </div>
        </section>
        <section aria-label="What you get" className="grid gap-6 pb-20 md:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-6">
              <Blip pose={f.pose} size={56} decorative />
              <h2 className="font-display text-xl font-semibold">{f.title}</h2>
              <p className="text-sm text-text-muted">{f.body}</p>
            </div>
          ))}
        </section>
      </main>
      <footer className="border-t border-border py-8 text-center font-mono text-xs text-text-subtle">
        Jingle · pilot · Platform names are trademarks of their owners; Jingle is not affiliated with them.
      </footer>
    </div>
  );
}
