import { api } from "./api";

/** Invite code remembered across sign-up (sessionStorage; JNG-02-07). */
export const INVITE_KEY = "jingle.invite";

/** After sign-up/sign-in, send the pending invite's friend request once. Never throws. */
export async function redeemPendingInvite(): Promise<void> {
  let code: string | null = null;
  try {
    code = sessionStorage.getItem(INVITE_KEY);
    sessionStorage.removeItem(INVITE_KEY);
  } catch {
    return;
  }
  if (!code) return;
  try {
    await api(`/invites/${encodeURIComponent(code)}`, { method: "POST" });
  } catch {
    /* an expired link just doesn't send a request */
  }
}
