"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialog, ErrorState, Skeleton, useToast } from "@/components/ds";
import { AvatarUploader } from "@/components/app/AvatarUploader";
import { TextField } from "@/components/app/forms";
import { ApiError, type Me } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { api, json } from "@/lib/api";
import { useMyModeration, type MyAction } from "@/lib/trust";

const KIND: Record<MyAction["kind"], string> = { warn: "Warning", mute: "Muted", suspend: "Suspended", ban: "Banned" };

function AppealForm({ action }: { action: MyAction }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const qc = useQueryClient();
  const toast = useToast();
  async function submit() {
    setBusy(true);
    try {
      await api(`/me/moderation/${action.id}/appeal`, { method: "POST", ...json({ text }) });
      toast.toast({ title: "Appeal sent. A moderator will review it.", tone: "success" });
      await qc.invalidateQueries({ queryKey: ["my-moderation"] });
    } catch (e) {
      toast.toast({ title: e instanceof Error ? e.message : "That didn't work.", tone: "danger" });
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="flex flex-col gap-2">
      <label className="flex flex-col gap-1 text-sm font-medium">
        Why should we look again?
        <textarea value={text} maxLength={1000} rows={3} onChange={(e) => setText(e.target.value)} className="rounded-md border border-border bg-surface-2 px-3 py-2 font-normal" />
      </label>
      <Button disabled={!text.trim()} loading={busy} loadingLabel="Sending" onClick={() => void submit()}>Appeal</Button>
    </div>
  );
}

/** JNG-13-04 download everything; JNG-01-10 delete (hidden now, purged within 30 days). */
function YourData() {
  const toast = useToast();
  const { me, signOut } = useAuth();
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setBusy(true);
    try {
      const data = await api<unknown>("/me/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "jingle-export.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.toast({ title: e instanceof Error ? e.message : "Couldn't prepare your data.", tone: "danger" });
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setError(null);
    try {
      await api("/me", { method: "DELETE", ...json({ password: confirm, confirm }) });
      await signOut();
      window.location.replace("/"); // full navigation: beats the signed-out redirect to /signin
    } catch (e) {
      setError(e instanceof Error ? e.message : "That didn't work.");
    }
  }

  return (
    <section aria-labelledby="data-h" className="flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-4">
      <h2 id="data-h" className="font-medium">Your data</h2>
      <p className="text-sm text-text-muted">Everything Jingle holds about you, as one JSON file: profile, privacy, listening, friends, circles, songs sent and received, Blends, battles, recaps and notifications.</p>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" loading={busy} loadingLabel="Preparing" onClick={() => void download()}>Download my data</Button>
        <Button variant="danger" onClick={() => setOpen(true)}>Delete my account</Button>
      </div>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Delete your account?"
        description="You disappear from Jingle straight away. Everything is erased within 30 days. Circles you own pass to another member."
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button variant="danger" disabled={!confirm} onClick={() => void remove()}>Delete my account</Button>
          </>
        }
      >
        <div className="flex flex-col gap-2">
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <TextField
            label={`Your password (or type ${me?.username ?? "your username"} if you sign in with Google)`}
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="current-password"
          />
        </div>
      </Dialog>
    </section>
  );
}

/** Account standing and appeals (JNG-12-03, 12-08), plus data rights. */
/** Your profile as friends see it: photo, name, college, city (JNG-01-12, JNG-01-15). */
function ProfileEditor() {
  const { me, setMe } = useAuth();
  const toast = useToast();
  const [name, setName] = useState(me?.display_name ?? "");
  const [college, setCollege] = useState(me?.college ?? "");
  const [city, setCity] = useState(me?.city ?? "");
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  if (!me) return null;
  const dirty = name !== me.display_name || college !== (me.college ?? "") || city !== (me.city ?? "");

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      setMe(await api<Me>("/me", { method: "PATCH", ...json({ display_name: name.trim(), college: college.trim(), city: city.trim() }) }));
      toast.toast({ title: "Profile saved", tone: "success" });
    } catch (err) {
      if (err instanceof ApiError && err.code === "VALIDATION_ERROR") {
        const d = (err.details ?? {}) as Record<string, string[] | string>;
        setErrors(Object.fromEntries(Object.entries(d).map(([k, v]) => [k, Array.isArray(v) ? v[0]! : String(v)])));
      } else toast.toast({ title: "Couldn't save your profile.", tone: "danger" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="profile-h" className="flex flex-col gap-5 rounded-lg border border-border bg-surface-1 p-5">
      <h2 id="profile-h" className="font-medium">Your profile</h2>
      <AvatarUploader />
      <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <TextField label="Display name" value={name} maxLength={60} onChange={(e) => setName(e.target.value)} error={errors.display_name} required />
        </div>
        <TextField label="College (optional)" value={college} maxLength={80} onChange={(e) => setCollege(e.target.value)} error={errors.college} />
        <TextField label="City (optional)" value={city} maxLength={60} onChange={(e) => setCity(e.target.value)} error={errors.city} />
        <div className="sm:col-span-2">
          <Button type="submit" variant="secondary" loading={busy} loadingLabel="Saving" disabled={!dirty || !name.trim()}>
            Save profile
          </Button>
        </div>
      </form>
    </section>
  );
}

export default function AccountPage() {
  const q = useMyModeration();
  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Account</h1>
      <ProfileEditor />
      <YourData />
      <h2 className="font-display text-xl font-semibold">Standing</h2>
      {q.isLoading ? (
        <Skeleton className="h-32" rounded="lg" />
      ) : q.isError || !q.data ? (
        <ErrorState message="Couldn't load your account standing." onRetry={() => void q.refetch()} />
      ) : !q.data.actions.length ? (
        <p className="rounded-lg border border-border bg-surface-1 p-4 text-sm">Your account is in good standing.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {q.data.actions.map((a) => (
            <li key={a.id} className="flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-4">
              <p className="font-medium">
                {KIND[a.kind]}
                {a.expires_at && !a.lifted ? ` until ${new Date(a.expires_at).toLocaleString()}` : ""}
                {a.lifted ? " (lifted)" : ""}
              </p>
              <p className="text-sm text-text-muted">Reason: {a.reason}</p>
              {a.appeal ? (
                <p className="text-sm">
                  Appeal: {a.appeal.status === "open" ? "under review" : a.appeal.status}
                  {a.appeal.note ? ` · ${a.appeal.note}` : ""}
                </p>
              ) : (
                !a.lifted && <AppealForm action={a} />
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
