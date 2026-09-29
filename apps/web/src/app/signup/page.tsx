"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState, type FormEvent } from "react";
import { Blip, Button } from "@/components/ds";
import { FocusShell } from "@/components/app/FocusShell";
import { GoogleButton } from "@/components/app/GoogleButton";
import { FormAlert, SelectField, TextField, birthYearOptions, fieldErrors } from "@/components/app/forms";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** JNG-01-01 sign-up with the 18+ gate (NFR-PRIV-02, UX_SPEC §5.2). */
export default function SignUpPage() {
  const { signUp } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "", username: "", birth_year: "" });
  const [agreed, setAgreed] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [alert, setAlert] = useState<string | null>(null);
  const [blocked, setBlocked] = useState(false);
  const [busy, setBusy] = useState(false);
  const onGoogle = useCallback(() => undefined, []);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (!/^\S+@\S+\.\S+$/.test(form.email)) local.email = "Enter an email like name@example.com";
    if (form.password.length < 10) local.password = "Use at least 10 characters";
    if (!/^[a-z0-9_.]{3,20}$/.test(form.username)) local.username = "3–20 characters: a–z, 0–9, _ and .";
    if (!form.birth_year) local.birth_year = "Pick your birth year";
    if (!agreed) local.terms = "Please agree to continue";
    setErrors(local);
    setAlert(null);
    if (Object.keys(local).length) return;
    setBusy(true);
    try {
      await signUp({ ...form, birth_year: Number(form.birth_year), display_name: form.username });
      router.replace("/onboarding/sources");
    } catch (err) {
      if (err instanceof ApiError && err.code === "AGE_RESTRICTED") setBlocked(true);
      else if (err instanceof ApiError && err.code === "VALIDATION_ERROR") setErrors(fieldErrors(err.details));
      else setAlert(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  if (blocked) {
    return (
      <FocusShell>
        <div className="flex flex-col items-center gap-4 text-center">
          <Blip pose="sleepy" size={96} decorative />
          <h1 className="font-display text-2xl font-semibold">Jingle is for people 18 and over for now.</h1>
          <p className="text-text-muted">Thanks for your interest.</p>
        </div>
      </FocusShell>
    );
  }

  return (
    <FocusShell>
      <h1 className="font-display text-3xl font-semibold tracking-tight">Create your Jingle account</h1>
      <p className="mt-1 text-sm text-text-muted">See what your friends are playing, on any app.</p>
      <div className="mt-6 flex flex-col gap-4">
        <GoogleButton onSignedIn={onGoogle} />
        <form onSubmit={submit} noValidate className="flex flex-col gap-4">
          {alert && <FormAlert>{alert}</FormAlert>}
          <TextField label="Email" type="email" autoComplete="email" value={form.email} onChange={set("email")} error={errors.email} readOnly={busy} />
          <TextField
            label="Password"
            type="password"
            autoComplete="new-password"
            value={form.password}
            onChange={set("password")}
            error={errors.password}
            hint="At least 10 characters."
            readOnly={busy}
          />
          <TextField
            label="Username"
            autoComplete="username"
            value={form.username}
            onChange={(e) => setForm((f) => ({ ...f, username: e.target.value.toLowerCase() }))}
            error={errors.username}
            hint={<span className="font-mono">jingle.app/u/{form.username || "you"}</span>}
            readOnly={busy}
          />
          <SelectField
            label="Birth year"
            value={form.birth_year}
            onChange={set("birth_year")}
            options={birthYearOptions()}
            placeholder="Choose a year"
            hint="You need to be 18 or over to use Jingle."
            error={errors.birth_year}
          />
          <label className="flex min-h-11 items-start gap-3 text-sm text-text-muted">
            <input type="checkbox" className="mt-1 h-4 w-4 accent-[var(--brand-violet)]" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
            <span>
              I agree to the Terms and Privacy Policy.
              {errors.terms && <span role="alert" className="block text-xs font-medium text-danger">{errors.terms}</span>}
            </span>
          </label>
          <Button type="submit" size="lg" loading={busy} loadingLabel="Creating your account">
            Create account
          </Button>
        </form>
        <p className="text-center text-sm text-text-muted">
          Already have an account?{" "}
          <Link href="/signin" className="font-medium text-accent-text underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </FocusShell>
  );
}
