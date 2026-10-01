import { Artwork, ButtonLink, ThemeToggle } from "@/components/ds";
import { Logo } from "@/components/app/Logo";
import { RedirectIfSignedIn } from "@/components/app/RedirectIfSignedIn";
import { loadWall } from "@/components/landing/data";
import { ConnectDemo, ConstellationDemo, CoverWall, FinalBlip, LiveFeedDemo, PodiumDemo, Reveal } from "@/components/landing/Landing";

export const revalidate = 3600;

const PLATFORMS = ["Spotify", "Apple Music", "YouTube Music", "Amazon Music"];

function Chapter({ kicker, title, body, children, id }: { kicker: string; title: string; body: string; children: React.ReactNode; id: string }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-8 border-t border-border py-20 md:py-28">
      <Reveal className="flex max-w-2xl flex-col gap-3">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-text-muted">{kicker}</p>
        <h2 id={id} className="font-display text-4xl font-semibold leading-[1.02] tracking-tight md:text-5xl">
          {title}
        </h2>
        <p className="text-lg text-text-muted">{body}</p>
      </Reveal>
      {children}
    </section>
  );
}

/**
 * Logged-out homepage (docs/ux UX_SPEC §5.1, DECISIONS D-LAND-*): a scroll story with real covers.
 * Server-rendered hero (LCP), motion only below the fold and only on transform/opacity.
 */
export default async function Landing() {
  const covers = await loadWall();
  return (
    <div className="min-h-dvh overflow-x-clip bg-bg text-text">
      <RedirectIfSignedIn />
      <header className="sticky top-0 z-30 border-b border-transparent bg-[var(--surface-glass)] backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 md:px-8">
          <Logo />
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <ButtonLink href="/signin" variant="ghost">
              Sign in
            </ButtonLink>
            <ButtonLink href="/signup" variant="primary" className="hidden sm:inline-flex">
              Get started
            </ButtonLink>
          </div>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-6xl px-4 md:px-8">
        {/* Opening: headline beside (never over) a wall of real covers. */}
        <section className="grid items-center gap-10 pb-10 pt-8 md:grid-cols-12 md:pb-16 md:pt-12">
          <div className="flex flex-col gap-6 md:col-span-5">
            <h1 className="font-display text-5xl font-semibold leading-[0.98] tracking-tight md:text-7xl">
              See what your friends are playing.
              <span className="block text-text-muted">On every app.</span>
            </h1>
            <p className="max-w-md text-lg text-text-muted">
              One feed for Spotify, Apple Music, YouTube Music and Amazon Music. Live is never faked: if it says Live, it&rsquo;s playing now.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <ButtonLink href="/signup" size="lg" variant="primary">
                Get started, it&rsquo;s free
              </ButtonLink>
              <ButtonLink href="/signin" size="lg" variant="secondary">
                Sign in
              </ButtonLink>
            </div>
            <ul className="flex flex-wrap gap-2" aria-label="Works with">
              {PLATFORMS.map((p) => (
                <li key={p} className="rounded-pill border border-border px-3 py-1.5 text-xs font-medium text-text-muted">
                  {p}
                </li>
              ))}
            </ul>
          </div>
          <div className="md:col-span-7">
            <CoverWall covers={covers} />
          </div>
        </section>

        <Chapter id="ch-live" kicker="Your friends, live" title="Who's playing what, right now." body="A breathing coral ring means Live, this second. A still ring and an honest time mean recently. You can tell at a glance, without reading a word.">
          <LiveFeedDemo covers={covers} />
        </Chapter>

        <Chapter id="ch-connect" kicker="One button per app" title="Connect once. Jingle handles the rest." body="Press Connect for your app. No settings to learn, no plugins to configure; Jingle quietly picks the best way to hear what you play.">
          <ConnectDemo />
        </Chapter>

        <Chapter id="ch-taste" kicker="Taste, explained" title="A score that shows its working." body="Where your favourite artists overlap with a friend's, and three plain reasons why. Never a bare number.">
          <ConstellationDemo covers={covers} />
        </Chapter>

        <Chapter id="ch-rituals" kicker="Rituals" title="Sunday is battle night." body="Each circle nominates a song a week, votes three times, and watches the podium rise. Then, every month, a recap of your listening worth sharing.">
          <PodiumDemo covers={covers} />
        </Chapter>

        <Chapter id="ch-circle" kicker="Your circle" title="Your crew, your feed, your Blend." body="Circles get their own feed, a weekly battle and a Blend where every track says why it's there. Start a room and listen together, each on your own app.">
          <Reveal className="grid grid-cols-4 gap-2 sm:grid-cols-8">
            {covers.slice(12, 28).map((c) => (
              <div key={c.url} className="jg-art-glow aspect-square overflow-hidden rounded-[4px]" style={{ ["--art" as string]: c.color ?? "#000" }}>
                <Artwork url={c.url_small} seed={c.label} alt="" rounded="none" />
              </div>
            ))}
          </Reveal>
        </Chapter>

        <section aria-labelledby="ch-privacy" className="grid gap-6 border-t border-border py-20 md:grid-cols-3">
          <Reveal className="md:col-span-1">
            <h2 id="ch-privacy" className="font-display text-4xl font-semibold tracking-tight">You&rsquo;re in control.</h2>
          </Reveal>
          {[
            ["You choose who sees what", "Friends, only the circles you pick, or nobody. Private mode hides you for an hour, a day, or until you turn it off."],
            ["Honest about Live", "Live means a signal from the last 90 seconds. Otherwise we show how long ago, and from which app."],
          ].map(([t, b], i) => (
            <Reveal key={t} delay={i * 0.04} className="rounded-[12px] bg-surface-1 p-6">
              <h3 className="font-semibold">{t}</h3>
              <p className="mt-2 text-sm text-text-muted">{b}</p>
            </Reveal>
          ))}
        </section>

        <section className="flex flex-col items-center gap-6 border-t border-border py-24 text-center">
          <FinalBlip />
          <h2 className="font-display text-4xl font-semibold tracking-tight md:text-5xl">Your friends are already listening.</h2>
          <ButtonLink href="/signup" size="lg" variant="primary">
            Get started
          </ButtonLink>
        </section>
      </main>

      <footer className="border-t border-border py-8 text-center font-mono text-xs text-text-subtle">
        Jingle · pilot · Album artwork via Apple Music. Platform names are trademarks of their owners; Jingle is not affiliated with them.
      </footer>
    </div>
  );
}
