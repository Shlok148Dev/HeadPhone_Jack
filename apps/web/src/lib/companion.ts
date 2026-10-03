import { api } from "@/lib/api";

/**
 * Talking to the Jingle extension from any Jingle page (D-EXT-02). The extension's pairing script
 * runs on every page of this origin and answers `JINGLE_COMPANION_PING` with
 * `JINGLE_COMPANION_READY {version, paired}`; we hand it a short-lived scrobble token with
 * `JINGLE_COMPANION_TOKEN` and it confirms with `JINGLE_COMPANION_PAIRED`. Same-origin only.
 */
export const MSG = {
  token: "JINGLE_COMPANION_TOKEN",
  ping: "JINGLE_COMPANION_PING",
  ready: "JINGLE_COMPANION_READY",
  paired: "JINGLE_COMPANION_PAIRED",
} as const;

export interface ExtensionState {
  installed: boolean;
  /** Already connected to this Jingle (undefined on old extension builds). */
  paired?: boolean;
  version?: string;
}

/** Ask the extension if it's here (and connected). Resolves `installed:false` after `ms`. */
export function detectExtension(ms = 900): Promise<ExtensionState> {
  return new Promise((resolve) => {
    const done = (s: ExtensionState) => {
      window.removeEventListener("message", on);
      clearTimeout(t);
      resolve(s);
    };
    const on = (e: MessageEvent) => {
      if (e.source !== window || e.origin !== window.location.origin) return;
      if (e.data?.type === MSG.ready)
        done({
          installed: true,
          paired: e.data.paired,
          version: e.data.version,
        });
    };
    window.addEventListener("message", on);
    const t = setTimeout(() => done({ installed: false }), ms);
    window.postMessage({ type: MSG.ping }, window.location.origin);
  });
}

/** Watch for the extension appearing (e.g. right after "Add to Chrome"). Returns an unsubscribe. */
export function onExtensionReady(cb: (s: ExtensionState) => void): () => void {
  const on = (e: MessageEvent) => {
    if (e.source !== window || e.origin !== window.location.origin) return;
    if (e.data?.type === MSG.ready)
      cb({ installed: true, paired: e.data.paired, version: e.data.version });
  };
  window.addEventListener("message", on);
  return () => window.removeEventListener("message", on);
}

export type PairOutcome = { ok: true } | { ok: false; error: string };

/**
 * Connect the extension to the signed-in account: mint a scrobble token (requires the "share what
 * you play" consent: the server answers CONSENT_REQUIRED otherwise) and hand it over.
 */
export async function pairExtension(): Promise<PairOutcome> {
  let token: string;
  try {
    token = (
      await api<{ token: string }>("/sources/companion/token", {
        method: "POST",
      })
    ).token;
  } catch (e) {
    const code = (e as { code?: string }).code ?? "error";
    return { ok: false, error: code };
  }
  return new Promise((resolve) => {
    const on = (e: MessageEvent) => {
      if (
        e.source !== window ||
        e.origin !== window.location.origin ||
        e.data?.type !== MSG.paired
      )
        return;
      window.removeEventListener("message", on);
      clearTimeout(t);
      resolve(
        e.data.ok
          ? { ok: true }
          : { ok: false, error: String(e.data.error ?? "error") },
      );
    };
    window.addEventListener("message", on);
    const t = setTimeout(() => {
      window.removeEventListener("message", on);
      resolve({ ok: false, error: "timeout" });
    }, 8000);
    window.postMessage({ type: MSG.token, token }, window.location.origin);
  });
}

/** Desktop Chromium-family browser that can run the extension (not phones, not Safari/Firefox). */
export function canRunExtension(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  const mobile = /Android|iPhone|iPad|iPod|Mobile/i.test(ua);
  const chromium = /Chrome\/|Edg\//.test(ua) && !/OPR\//.test(ua);
  return chromium && !mobile;
}

export function isPhone(): boolean {
  return (
    typeof navigator !== "undefined" &&
    /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)
  );
}

export function isAndroid(): boolean {
  return (
    typeof navigator !== "undefined" && /Android/i.test(navigator.userAgent)
  );
}

/**
 * Inside the Jingle Android app (D-CONNECT-01): `window.JingleAndroid` is offered to this origin only.
 * Any music app on the phone connects the same way: hand over a token, the app opens Android's one
 * notification-access toggle, and it reads the four music apps' media sessions from then on.
 */
type AndroidBridge = {
  postMessage: (s: string) => void;
  addEventListener: (t: "message", cb: (e: { data: string }) => void) => void;
};

export function androidBridge(): AndroidBridge | null {
  if (typeof window === "undefined") return null;
  return (
    (window as unknown as { JingleAndroid?: AndroidBridge }).JingleAndroid ??
    null
  );
}

export async function pairAndroid(): Promise<PairOutcome> {
  const bridge = androidBridge();
  if (!bridge) return { ok: false, error: "no_app" };
  try {
    const { token } = await api<{ token: string }>("/sources/companion/token", {
      method: "POST",
    });
    bridge.postMessage(JSON.stringify({ type: "pair", token }));
    return { ok: true };
  } catch (e) {
    return { ok: false, error: (e as { code?: string }).code ?? "error" };
  }
}
