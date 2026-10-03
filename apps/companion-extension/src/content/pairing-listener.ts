import type { PairResult } from "../shared/types";

/** window.postMessage contract with the Jingle web page `/connect/companion`. */
export const MSG = {
  /** page → extension: the scrobble token to store. */
  token: "JINGLE_COMPANION_TOKEN",
  /** page → extension: "are you installed?" (answered with READY). */
  ping: "JINGLE_COMPANION_PING",
  /** extension → page: installed and listening. */
  ready: "JINGLE_COMPANION_READY",
  /** extension → page: pairing outcome. */
  paired: "JINGLE_COMPANION_PAIRED",
} as const;

/** Printable ASCII, no spaces, sane length. */
export function isPlausibleToken(t: unknown): t is string {
  return typeof t === "string" && t.length >= 8 && t.length <= 512 && /^[\x21-\x7e]+$/.test(t);
}

export interface PairingDeps {
  win: Window;
  /** Whether this extension is already connected to this Jingle origin. */
  status?: () => Promise<{ paired: boolean }>;
  /** Forwards the token to the service worker, which validates it with the Jingle server. */
  pair: (token: string) => Promise<PairResult>;
  version: string;
}

/**
 * Accepts a token only from the page's own window, from the page's own origin,
 * with exactly `{type: "JINGLE_COMPANION_TOKEN", token: string}`. Everything else is ignored.
 * The token is never logged.
 */
export function installPairingListener({ win, pair, version, status }: PairingDeps): () => void {
  const origin = win.location.origin;
  const reply = (data: Record<string, unknown>): void => win.postMessage(data, origin);
  const ready = (): void => {
    if (!status) return reply({ type: MSG.ready, version });
    status()
      .then((s) => reply({ type: MSG.ready, version, paired: s.paired }))
      .catch(() => reply({ type: MSG.ready, version }));
  };
  let busy = false;

  const onMessage = (ev: MessageEvent): void => {
    if (ev.source !== win || ev.origin !== origin) return;
    const data: unknown = ev.data;
    if (typeof data !== "object" || data === null) return;
    const type = (data as { type?: unknown }).type;
    if (type === MSG.ping) {
      ready();
      return;
    }
    if (type !== MSG.token) return;
    const token = (data as { token?: unknown }).token;
    if (!isPlausibleToken(token)) {
      reply({ type: MSG.paired, ok: false, error: "invalid_token" });
      return;
    }
    if (busy) return;
    busy = true;
    pair(token)
      .then((r) => reply({ type: MSG.paired, ok: r.ok, ...(r.userName ? { userName: r.userName } : {}), ...(r.error ? { error: r.error } : {}) }))
      .catch(() => reply({ type: MSG.paired, ok: false, error: "extension_error" }))
      .finally(() => {
        busy = false;
      });
  };

  win.addEventListener("message", onMessage);
  ready();
  return () => win.removeEventListener("message", onMessage);
}
