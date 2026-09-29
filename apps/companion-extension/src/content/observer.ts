import type { Connector, ReadEnv } from "../connectors/common";
import { trackKey, type TrackState } from "../shared/types";

export interface ObserverOptions {
  connector: Connector;
  env: () => ReadEnv;
  send: (state: TrackState | null) => void;
  now?: () => number;
  /** Poll period (ms). */
  intervalMs?: number;
  /** Re-send the unchanged state this often while playing, so the worker can heartbeat. */
  keepaliveMs?: number;
  /** Position drift (ms) treated as a seek / restart. */
  seekToleranceMs?: number;
  target?: EventTarget;
}

const MEDIA_EVENTS = ["play", "playing", "pause", "ended", "seeked", "loadedmetadata", "durationchange", "emptied"] as const;

/** Identity fields whose change always triggers a message. */
function signature(s: TrackState | null): string {
  if (!s) return "null";
  return [trackKey(s), s.isPlaying ? "1" : "0", s.durationMs ?? "", s.originUrl ?? ""].join("|");
}

/**
 * Polls the connector every 2 s and on media element events, and sends a message only when
 * something meaningful changed: track identity, play/pause, duration, a seek, or a keepalive
 * while playing. Never throws into the page.
 */
export function createObserver(opts: ObserverOptions) {
  const now = opts.now ?? Date.now;
  const intervalMs = opts.intervalMs ?? 2000;
  const keepaliveMs = opts.keepaliveMs ?? 15000;
  const tolerance = opts.seekToleranceMs ?? 3000;
  const target = opts.target ?? document;

  let last: TrackState | null = null;
  let lastSig = "null";
  let lastSentAt = 0;
  let timer: ReturnType<typeof setInterval> | undefined;
  let pending: ReturnType<typeof setTimeout> | undefined;

  function shouldSend(s: TrackState | null, t: number): boolean {
    if (signature(s) !== lastSig) return true;
    if (!s || !last) return false;
    if (s.positionMs !== undefined && last.positionMs !== undefined) {
      const expected = last.positionMs + (last.isPlaying ? t - lastSentAt : 0);
      if (Math.abs(s.positionMs - expected) > tolerance) return true;
    }
    return s.isPlaying && t - lastSentAt >= keepaliveMs;
  }

  function check(): void {
    let s: TrackState | null;
    try {
      s = opts.connector.read(opts.env());
    } catch {
      s = null;
    }
    const t = now();
    if (!shouldSend(s, t)) return;
    last = s;
    lastSig = signature(s);
    lastSentAt = t;
    try {
      opts.send(s);
    } catch {
      /* worker unavailable (e.g. extension reloaded); next poll retries */
    }
  }

  function onMediaEvent(): void {
    if (pending !== undefined) return;
    // Let the page update MediaSession metadata before reading.
    pending = setTimeout(() => {
      pending = undefined;
      check();
    }, 250);
  }

  return {
    check,
    start() {
      for (const ev of MEDIA_EVENTS) target.addEventListener(ev, onMediaEvent, true);
      timer = setInterval(check, intervalMs);
      check();
    },
    stop() {
      for (const ev of MEDIA_EVENTS) target.removeEventListener(ev, onMediaEvent, true);
      if (timer !== undefined) clearInterval(timer);
      if (pending !== undefined) clearTimeout(pending);
      timer = pending = undefined;
      if (last) {
        last = null;
        lastSig = "null";
        try {
          opts.send(null);
        } catch {
          /* ignore */
        }
      }
    },
  };
}
