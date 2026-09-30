"use client";

import { useQueryClient } from "@tanstack/react-query";
import { notFound, useParams, useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Button, Skeleton, cn } from "@/components/ds";
import { ConnectPlatformCard, ConnectSheet, PLATFORMS, type MusicPlatform } from "@/components/app/Connect";
import { FindFriends } from "@/components/app/FindFriends";
import { FocusShell } from "@/components/app/FocusShell";
import { FormAlert, SelectField, TextField, birthYearOptions, fieldErrors } from "@/components/app/forms";
import { ApiError, api, json, type Me } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useConnections } from "@/lib/queries";

const STEPS = ["profile", "sources", "privacy", "friends"] as const;
type Step = (typeof STEPS)[number];
const LABELS: Record<Step, string> = { profile: "Profile", sources: "Sources", privacy: "Privacy", friends: "Friends" };

function Stepper({ current }: { current: Step }) {
  const idx = STEPS.indexOf(current);
  return (
    <ol className="mb-6 flex items-center gap-2" aria-label="Onboarding progress">
      {STEPS.map((s, i) => (
        <li key={s} className="flex flex-1 flex-col gap-1.5" aria-current={s === current ? "step" : undefined}>
          <span className={cn("h-1.5 rounded-full", i <= idx ? "bg-gradient-brand" : "bg-surface-3")} />
          <span className={cn("font-mono text-[11px] uppercase tracking-wide", i === idx ? "text-text" : "text-text-subtle")}>
            {i + 1}. {LABELS[s]}
          </span>
        </li>
      ))}
    </ol>
  );
}

function ProfileStep({ me, next }: { me: Me; next: () => void }) {
  const { setMe } = useAuth();
  const [displayName, setDisplayName] = useState(me.display_name || me.username);
  const [birthYear, setBirthYear] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [alert, setAlert] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (me.needs_onboarding && !birthYear) return setErrors({ birth_year: "Pick your birth year" });
    setBusy(true);
    setAlert(null);
    try {
      const body: Record<string, unknown> = { display_name: displayName.trim() };
      if (me.needs_onboarding) body.birth_year = Number(birthYear);
      setMe(await api<Me>("/me", { method: "PATCH", ...json(body) }));
      next();
    } catch (err) {
      if (err instanceof ApiError && err.code === "AGE_RESTRICTED") window.location.assign("/signup?blocked=1");
      else if (err instanceof ApiError && err.code === "VALIDATION_ERROR") setErrors(fieldErrors(err.details));
      else setAlert(err instanceof Error ? err.message : "Couldn't save. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <h1 className="font-display text-2xl font-semibold">How should friends see you?</h1>
      {alert && <FormAlert>{alert}</FormAlert>}
      <TextField label="Display name" value={displayName} maxLength={60} onChange={(e) => setDisplayName(e.target.value)} error={errors.display_name} />
      {me.needs_onboarding && (
        <SelectField
          label="Birth year"
          value={birthYear}
          onChange={(e) => setBirthYear(e.target.value)}
          options={birthYearOptions()}
          placeholder="Choose a year"
          hint="You need to be 18 or over to use Jingle."
          error={errors.birth_year}
        />
      )}
      <Button type="submit" size="lg" loading={busy} loadingLabel="Saving">
        Continue
      </Button>
    </form>
  );
}

function SourcesStep({ next }: { next: () => void }) {
  const connections = useConnections();
  const [main, setMain] = useState<MusicPlatform | null>(null);
  const [open, setOpen] = useState<MusicPlatform | null>(null);
  const qc = useQueryClient();
  const anyConnected = connections.data?.some((c) => c.status === "CONNECTED") ?? false;
  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="font-display text-2xl font-semibold">Which app do you use most?</h1>
        <p className="mt-1 text-sm text-text-muted">Pick one to start. You can add the others any time.</p>
      </div>
      {connections.isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {PLATFORMS.map((p) => (
            <Skeleton key={p} className="h-36" rounded="lg" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {PLATFORMS.map((p) => (
            <ConnectPlatformCard
              key={p}
              platform={p}
              primary={main === p}
              connection={connections.data?.find((c) => c.platform === p)}
              onConnect={(pl) => {
                setMain(pl);
                setOpen(pl);
              }}
            />
          ))}
        </div>
      )}
      <ConnectSheet
        platform={open}
        returnTo="/onboarding/sources"
        onClose={() => {
          setOpen(null);
          void qc.invalidateQueries({ queryKey: ["connections"] });
        }}
      />
      <div className="flex justify-end gap-2">
        {!anyConnected && (
          <Button variant="ghost" onClick={next}>
            Skip for now
          </Button>
        )}
        <Button onClick={next} disabled={!anyConnected}>
          Continue
        </Button>
      </div>
    </div>
  );
}

function PrivacyStep({ done }: { done: () => void }) {
  const [visibility, setVisibility] = useState<"friends" | "circles" | "nobody">("friends");
  const [discoverable, setDiscoverable] = useState(true);
  const [exactTime, setExactTime] = useState(true);
  const [busy, setBusy] = useState(false);
  const [alert, setAlert] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setAlert(null);
    try {
      await api("/me/privacy", { method: "PATCH", ...json({ activity_visibility: visibility, show_last_active: exactTime }) });
      await api("/me/consents/suggestions_discoverability", { method: "POST", ...json({ given: discoverable }) });
      done();
    } catch {
      setAlert("Couldn't save your privacy choices. Try again.");
    } finally {
      setBusy(false);
    }
  }

  const options = [
    { v: "friends", l: "Friends" },
    { v: "circles", l: "Only circles I choose" },
    { v: "nobody", l: "No one for now" },
  ] as const;
  return (
    <form onSubmit={submit} className="flex flex-col gap-5">
      <h1 className="font-display text-2xl font-semibold">Your privacy</h1>
      {alert && <FormAlert>{alert}</FormAlert>}
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Who can see what you&rsquo;re playing?</legend>
        {options.map((o) => (
          <label key={o.v} className="flex min-h-11 items-center gap-3 rounded-md border border-border px-3 text-sm has-[:checked]:border-brand-violet">
            <input type="radio" name="visibility" value={o.v} checked={visibility === o.v} onChange={() => setVisibility(o.v)} className="accent-[var(--brand-violet)]" />
            {o.l}
          </label>
        ))}
      </fieldset>
      <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
        Let people find me in suggestions
        <input type="checkbox" role="switch" checked={discoverable} onChange={(e) => setDiscoverable(e.target.checked)} className="h-5 w-5 accent-[var(--brand-violet)]" />
      </label>
      <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
        Show my exact play time
        <input type="checkbox" role="switch" checked={exactTime} onChange={(e) => setExactTime(e.target.checked)} className="h-5 w-5 accent-[var(--brand-violet)]" />
      </label>
      <p className="text-xs text-text-muted">You can change these any time in Settings → Privacy.</p>
      <Button type="submit" size="lg" loading={busy} loadingLabel="Saving">
        Continue
      </Button>
    </form>
  );
}

export default function OnboardingPage() {
  const { step } = useParams<{ step: string }>();
  const { status, me } = useAuth();
  const router = useRouter();
  const valid = (STEPS as readonly string[]).includes(step);

  useEffect(() => {
    if (status === "signed-out") router.replace("/signin");
    else if (me?.needs_onboarding && step !== "profile") router.replace("/onboarding/profile");
  }, [status, me, step, router]);

  if (!valid) notFound();
  const current = step as Step;
  const go = (s: Step | "home") => router.push(s === "home" ? "/home" : `/onboarding/${s}`);

  return (
    <FocusShell wide={current === "sources" || current === "friends"}>
      <Stepper current={current} />
      {status !== "signed-in" || !me ? (
        <Skeleton className="h-64" rounded="lg" />
      ) : current === "profile" ? (
        <ProfileStep me={me} next={() => go("sources")} />
      ) : current === "sources" ? (
        <SourcesStep next={() => go("privacy")} />
      ) : (
        current === "privacy" ? (
          <PrivacyStep done={() => go("friends")} />
        ) : (
          <div className="flex flex-col gap-5">
            <div>
              <h1 className="font-display text-2xl font-semibold">Find your friends</h1>
              <p className="mt-1 text-sm text-text-muted">Search for people you know, or share your invite link.</p>
            </div>
            <FindFriends />
            <Button size="lg" onClick={() => go("home")}>Go to my feed</Button>
          </div>
        )
      )}
    </FocusShell>
  );
}
