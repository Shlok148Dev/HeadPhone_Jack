"use client";

import { useRef, useState } from "react";
import { Avatar, Button, useToast } from "@/components/ds";
import { api, ApiError, type Me } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const ACCEPT = "image/jpeg,image/png,image/webp,image/gif";
const MAX_BYTES = 5 * 1024 * 1024;

/**
 * Profile photo (JNG-01-15). The server validates and re-encodes (square, no location data);
 * the client only pre-checks type and size so mistakes are caught before an upload.
 */
export function AvatarUploader({ size = 88 }: { size?: number }) {
  const { me, setMe } = useAuth();
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  if (!me) return null;

  async function upload(file: File) {
    if (!ACCEPT.split(",").includes(file.type)) {
      toast.toast({ title: "Use a JPEG, PNG, WebP or GIF photo.", tone: "danger" });
      return;
    }
    if (file.size > MAX_BYTES) {
      toast.toast({ title: "Photos can be up to 5 MB.", tone: "danger" });
      return;
    }
    const local = URL.createObjectURL(file);
    setPreview(local);
    setBusy(true);
    try {
      const body = new FormData();
      body.append("file", file);
      const updated = await api<Me>("/me/avatar", { method: "POST", body });
      setMe(updated);
      toast.toast({ title: "Profile photo updated", tone: "success" });
    } catch (err) {
      toast.toast({ title: err instanceof ApiError ? err.message : "Couldn't upload that photo.", tone: "danger" });
    } finally {
      setBusy(false);
      setPreview(null);
      URL.revokeObjectURL(local);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      setMe(await api<Me>("/me/avatar", { method: "DELETE" }));
      toast.toast({ title: "Profile photo removed", tone: "success" });
    } catch {
      toast.toast({ title: "Couldn't remove the photo.", tone: "danger" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-5">
      <div className={busy ? "opacity-60 motion-safe:animate-pulse" : ""}>
        <Avatar name={me.display_name || me.username} url={preview ?? me.avatar_url ?? null} seed={me.id} size={size} />
      </div>
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" loading={busy} loadingLabel="Uploading" onClick={() => input.current?.click()}>
            {me.avatar_url ? "Change photo" : "Add a photo"}
          </Button>
          {me.avatar_url && !busy && (
            <Button variant="ghost" onClick={() => void remove()}>
              Remove
            </Button>
          )}
        </div>
        <p className="text-xs text-text-muted">JPEG, PNG, WebP or GIF, up to 5 MB. Friends and people who can find you see it.</p>
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          aria-label="Choose a profile photo"
          tabIndex={-1}
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = "";
            if (f) void upload(f);
          }}
        />
      </div>
    </div>
  );
}
