"use client";

import { Button, Skeleton, useToast } from "@/components/ds";
import { useInvite } from "@/lib/social";

/** JNG-02-07: my invite link + QR. The SVG comes from our own API (never user input). */
export function InviteCard() {
  const invite = useInvite();
  const toast = useToast();
  if (invite.isLoading) return <Skeleton className="h-40" rounded="lg" />;
  if (!invite.data) return null;
  const { url, qr_svg } = invite.data;
  return (
    <div className="flex flex-col items-center gap-4 rounded-lg border border-border bg-surface-1 p-4 sm:flex-row">
      <div
        className="h-32 w-32 shrink-0 rounded-md bg-white p-2 [&_svg]:h-full [&_svg]:w-full"
        role="img"
        aria-label="QR code for your invite link"
        dangerouslySetInnerHTML={{ __html: qr_svg }}
      />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <p className="font-display text-lg font-semibold">Invite friends</p>
        <p className="text-sm text-text-muted">Anyone who opens this link sends you a friend request.</p>
        <code className="truncate rounded-md bg-surface-2 px-3 py-2 font-mono text-xs">{url}</code>
        <Button
          variant="secondary"
          onClick={() =>
            navigator.clipboard
              .writeText(url)
              .then(() => toast.toast({ title: "Invite link copied", tone: "success" }))
              .catch(() => toast.toast({ title: "Couldn't copy. Select the link instead.", tone: "danger" }))
          }
        >
          Copy invite link
        </Button>
      </div>
    </div>
  );
}
