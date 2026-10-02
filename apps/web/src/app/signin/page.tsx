"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ds";
import { FocusShell } from "@/components/app/FocusShell";
import { GoogleButton } from "@/components/app/GoogleButton";
import { FormAlert, TextField } from "@/components/app/forms";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** Only same-site relative paths are allowed as post-sign-in destinations (no open redirect). */
function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/home";
}

function SignInForm() {
  const { signIn, status } = useAuth();
  const router = useRouter();
  // Read ?next= when it's needed, not during render: useSearchParams forced a client-side render
  // bailout, and on a first (ISR) render the streamed and client forms briefly coexisted (QA 2026-10).
  const next = () => safeNext(new URLSearchParams(window.location.search).get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [alert, setAlert] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const onGoogle = useCallback(() => undefined, []);

  useEffect(() => {
    if (status === "signed-in") router.replace(next());
  }, [status, router]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setAlert(null);
    setBusy(true);
    try {
      const me = await signIn(email.trim(), password);
      router.replace(me.needs_onboarding ? "/onboarding/profile" : next());
    } catch (err) {
      if (err instanceof ApiError && (err.status === 400 || err.status === 401)) setAlert("That email and password don't match.");
      else setAlert(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className="font-display text-3xl font-semibold tracking-tight">Welcome back</h1>
      <div className="mt-6 flex flex-col gap-4">
        <GoogleButton onSignedIn={onGoogle} />
        <form onSubmit={submit} className="flex flex-col gap-4">
          {alert && <FormAlert>{alert}</FormAlert>}
          <TextField label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} readOnly={busy} required />
          <TextField
            label="Password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            readOnly={busy}
            required
          />
          <Button type="submit" size="lg" loading={busy} loadingLabel="Signing in">
            Sign in
          </Button>
        </form>
        <p className="text-center text-sm text-text-muted">
          New to Jingle?{" "}
          <Link href="/signup" className="font-medium text-accent-text underline-offset-4 hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </>
  );
}

export default function SignInPage() {
  return (
    <FocusShell>
      <SignInForm />
    </FocusShell>
  );
}
