import { trackKey, type TrackState } from "../shared/types";

/** Scrobble rules (ListenBrainz client guidelines + Jingle Live TTL of 90 s). */
export const RULES = {
  heartbeatMs: 30_000,
  minTrackMs: 30_000,
  maxThresholdMs: 240_000,
  /** Longest gap between updates credited as listening time (covers worker/tab sleeps). */
  maxCreditMs: 60_000,
  /** A jump back to within this of the start, after a counted play, is a repeat. */
  restartWindowMs: 10_000,
} as const;

export type Emission =
  | { kind: "playing_now"; track: TrackState }
  | { kind: "single"; track: TrackState; listenedAt: number };

interface Session {
  key: string;
  track: TrackState;
  /** Epoch ms when this play started (→ listened_at). */
  startedAt: number;
  playedMs: number;
  lastUpdateAt: number;
  lastPositionMs?: number;
  isPlaying: boolean;
  scrobbled: boolean;
  lastNowPlayingAt?: number;
}

export interface ScrobblerState {
  sessions: Record<string, Session>;
  /** Tab whose playback is advertised as playing_now. */
  active?: string;
}

/**
 * Pure scrobble engine. Feed it per-tab track states and clock ticks; it returns what to send.
 * - playing_now on a new track or resume, then every 30 s while playing; nothing while paused.
 * - one `single` per play when played ≥ 50% of duration or ≥ 4 min, never for tracks < 30 s.
 * - played time is wall-clock time while playing, so seeking forward does not count as listening.
 * - a jump back to the start after a counted play (repeat) starts a new play.
 */
export class Scrobbler {
  private state: ScrobblerState;

  constructor(private readonly now: () => number, initial?: ScrobblerState) {
    this.state = initial ? structuredClone(initial) : { sessions: {} };
  }

  snapshot(): ScrobblerState {
    return structuredClone(this.state);
  }

  update(tabId: string, next: TrackState | null): Emission[] {
    const t = this.now();
    const out: Emission[] = [];
    let s = this.state.sessions[tabId];
    if (s) this.accrue(s, t, out);

    if (!next) {
      this.end(tabId);
      return out;
    }

    const key = trackKey(next);
    const repeat =
      s !== undefined &&
      s.key === key &&
      next.positionMs !== undefined &&
      s.lastPositionMs !== undefined &&
      next.positionMs < RULES.restartWindowMs &&
      s.lastPositionMs - next.positionMs > RULES.restartWindowMs &&
      (s.scrobbled || this.reached(s));

    if (!s || s.key !== key || repeat) {
      s = { key, track: next, startedAt: t, playedMs: 0, lastUpdateAt: t, isPlaying: false, scrobbled: false };
      if (next.positionMs !== undefined) s.lastPositionMs = next.positionMs;
      this.state.sessions[tabId] = s;
    }

    const resumed = next.isPlaying && !s.isPlaying;
    s.track = { ...s.track, ...next };
    s.isPlaying = next.isPlaying;
    s.lastUpdateAt = t;
    if (next.positionMs !== undefined) s.lastPositionMs = next.positionMs;

    if (next.isPlaying) {
      if (resumed || this.state.active !== tabId) {
        this.state.active = tabId;
        s.lastNowPlayingAt = t;
        out.push({ kind: "playing_now", track: s.track });
      }
    } else if (this.state.active === tabId) {
      this.state.active = this.otherPlayingTab(tabId);
    }
    this.maybeScrobble(s, out);
    return out;
  }

  /** Call periodically (alarm / keepalive). Credits play time and emits heartbeats. */
  tick(): Emission[] {
    const t = this.now();
    const out: Emission[] = [];
    for (const [tabId, s] of Object.entries(this.state.sessions)) {
      this.accrue(s, t, out);
      s.lastUpdateAt = t;
      if (s.isPlaying && this.state.active === tabId && t - (s.lastNowPlayingAt ?? 0) >= RULES.heartbeatMs) {
        s.lastNowPlayingAt = t;
        out.push({ kind: "playing_now", track: s.track });
      }
    }
    return out;
  }

  /** Tab closed, navigated away, or sharing disabled: drop without scrobbling further. */
  end(tabId: string): void {
    delete this.state.sessions[tabId];
    if (this.state.active === tabId) this.state.active = this.otherPlayingTab(tabId);
  }

  endAll(): void {
    this.state = { sessions: {} };
  }

  isActive(): boolean {
    return Object.values(this.state.sessions).some((s) => s.isPlaying);
  }

  private otherPlayingTab(exclude: string): string | undefined {
    return Object.entries(this.state.sessions).find(([id, s]) => id !== exclude && s.isPlaying)?.[0];
  }

  private accrue(s: Session, t: number, out: Emission[]): void {
    if (s.isPlaying) {
      const dt = Math.max(0, t - s.lastUpdateAt);
      s.playedMs += Math.min(dt, RULES.maxCreditMs);
      if (s.lastPositionMs !== undefined) s.lastPositionMs += dt;
    }
    this.maybeScrobble(s, out);
  }

  private threshold(s: Session): number | null {
    const d = s.track.durationMs;
    if (d === undefined) return RULES.maxThresholdMs; // unknown length: 4 min proves it is ≥ 30 s
    if (d < RULES.minTrackMs) return null;
    return Math.min(d / 2, RULES.maxThresholdMs);
  }

  private reached(s: Session): boolean {
    const th = this.threshold(s);
    return th !== null && s.playedMs >= th;
  }

  private maybeScrobble(s: Session, out: Emission[]): void {
    if (s.scrobbled || !this.reached(s)) return;
    s.scrobbled = true;
    out.push({ kind: "single", track: s.track, listenedAt: Math.floor(s.startedAt / 1000) });
  }
}
