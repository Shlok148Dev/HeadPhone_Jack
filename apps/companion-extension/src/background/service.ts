import { connectorForHost } from "../connectors";
import { mergeSettings, normaliseOrigin, STORAGE_KEYS, type Auth, type KV, type Settings } from "../shared/settings";
import type { PairResult, TrackState } from "../shared/types";
import { submitListens, validateToken, type FetchLike } from "./client";
import { buildSubmission, type LbSubmission } from "./payload";
import { ListenQueue } from "./queue";
import { Scrobbler, type Emission, type ScrobblerState } from "./scrobbler";

export interface Status {
  settings: Settings;
  userName: string | null;
  queueSize: number;
  lastError: string | null;
  nowPlaying: { platform: string; artist: string; title: string } | null;
}

export interface CompanionDeps {
  local: KV;
  /** Survives worker restarts but not browser restarts (chrome.storage.session). */
  session: KV;
  fetch: FetchLike;
  now: () => number;
}

/**
 * Service-worker core: settings, auth, the scrobbler and the offline queue.
 * All entry points are serialised so MV3 events cannot interleave state writes.
 */
export class Companion {
  private chain: Promise<unknown> = Promise.resolve();
  private scrobbler: Scrobbler | undefined;
  private readonly queue: ListenQueue;
  private nowPlaying: TrackState | null = null;

  constructor(private readonly deps: CompanionDeps) {
    this.queue = new ListenQueue(deps.local, deps.now);
  }

  private run<T>(fn: () => Promise<T>): Promise<T> {
    const p = this.chain.then(fn, fn);
    this.chain = p.catch(() => undefined);
    return p;
  }

  async settings(): Promise<Settings> {
    return mergeSettings(await this.deps.local.get<Partial<Settings>>(STORAGE_KEYS.settings));
  }

  private async auth(): Promise<Auth | undefined> {
    return this.deps.local.get<Auth>(STORAGE_KEYS.auth);
  }

  private async engine(): Promise<Scrobbler> {
    if (!this.scrobbler) {
      const saved = await this.deps.session.get<ScrobblerState>(STORAGE_KEYS.scrobbler);
      this.scrobbler = new Scrobbler(this.deps.now, saved);
    }
    return this.scrobbler;
  }

  private async persist(): Promise<void> {
    if (this.scrobbler) await this.deps.session.set(STORAGE_KEYS.scrobbler, this.scrobbler.snapshot());
  }

  /** A player content script reported its state. `senderUrl` is the tab URL Chrome attests. */
  onTrack(tabId: number, senderUrl: string | undefined, state: TrackState | null): Promise<void> {
    return this.run(async () => {
      const eng = await this.engine();
      const id = String(tabId);
      let accepted = state;
      if (state) {
        const host = senderUrl ? safeHost(senderUrl) : undefined;
        const conn = host ? connectorForHost(host) : undefined;
        const settings = await this.settings();
        const authed = (await this.auth()) !== undefined;
        if (!conn || conn.platform !== state.platform || settings.paused || !settings.platforms[state.platform] || !authed) {
          accepted = null;
        }
      }
      const emissions = eng.update(id, accepted);
      if (accepted?.isPlaying) this.nowPlaying = accepted;
      else if (!eng.isActive()) this.nowPlaying = null;
      await this.persist();
      await this.emit(emissions);
    });
  }

  onTabClosed(tabId: number): Promise<void> {
    return this.run(async () => {
      (await this.engine()).end(String(tabId));
      await this.persist();
    });
  }

  /** Alarm / keepalive: heartbeat playing_now and retry the queue. */
  onTick(): Promise<void> {
    return this.run(async () => {
      const emissions = (await this.engine()).tick();
      await this.persist();
      await this.emit(emissions);
      await this.flushQueue(false);
    });
  }

  private async emit(emissions: Emission[]): Promise<void> {
    if (emissions.length === 0) return;
    const auth = await this.auth();
    if (!auth) return;
    const { origin } = await this.settings();
    for (const e of emissions) {
      const body = e.kind === "single" ? buildSubmission("single", e.track, e.listenedAt) : buildSubmission("playing_now", e.track);
      const r = await submitListens(this.deps.fetch, origin, auth.token, body);
      if (r.ok) {
        await this.setError(null);
        if (e.kind === "single") await this.flushQueue(false);
        continue;
      }
      await this.setError(r.unauthorized ? "token_rejected" : r.status === 0 ? "offline" : `http_${r.status}`);
      if (e.kind === "single" && r.retryable) await this.queue.enqueue(body);
    }
  }

  private async flushQueue(force: boolean): Promise<void> {
    const auth = await this.auth();
    if (!auth) return;
    const { origin } = await this.settings();
    const send = (body: LbSubmission) => submitListens(this.deps.fetch, origin, auth.token, body);
    const r = await this.queue.flush(send, force);
    if (r.unauthorized) await this.setError("token_rejected");
    else if (r.sent > 0) await this.setError(null);
  }

  private async setError(code: string | null): Promise<void> {
    if (code === null) await this.deps.local.remove(STORAGE_KEYS.lastError);
    else await this.deps.local.set(STORAGE_KEYS.lastError, code);
  }

  /**
   * Pair with a token. `senderOrigin` is the page origin for the pairing content script
   * (must equal the configured Jingle origin), or null when pasted in the popup.
   */
  pair(token: string, senderOrigin: string | null): Promise<PairResult> {
    return this.run(async () => {
      const { origin } = await this.settings();
      if (senderOrigin !== null && senderOrigin !== origin) return { ok: false, error: "wrong_origin" };
      const v = await validateToken(this.deps.fetch, origin, token.trim());
      if (!v.valid) return { ok: false, error: v.networkError ? "unreachable" : "invalid_token" };
      const auth: Auth = { token: token.trim(), userName: v.userName ?? "" };
      await this.deps.local.set(STORAGE_KEYS.auth, auth);
      await this.setError(null);
      await this.flushQueue(true);
      return { ok: true, ...(v.userName ? { userName: v.userName } : {}) };
    });
  }

  signOut(): Promise<void> {
    return this.run(async () => {
      await this.deps.local.remove(STORAGE_KEYS.auth);
      await this.queue.clear();
      await this.setError(null);
      (await this.engine()).endAll();
      this.nowPlaying = null;
      await this.persist();
    });
  }

  /** Update settings. Changing the origin signs out (tokens are per server). */
  updateSettings(patch: Partial<Settings>): Promise<Settings | { error: string }> {
    return this.run(async () => {
      const cur = await this.settings();
      const next: Settings = { ...cur, ...patch, platforms: { ...cur.platforms, ...(patch.platforms ?? {}) } };
      if (patch.origin !== undefined) {
        const o = normaliseOrigin(patch.origin);
        if (!o) return { error: "invalid_origin" };
        next.origin = o;
      }
      await this.deps.local.set(STORAGE_KEYS.settings, next);
      if (next.origin !== cur.origin) {
        await this.deps.local.remove(STORAGE_KEYS.auth);
        await this.queue.clear();
      }
      if (next.paused) {
        (await this.engine()).endAll();
        this.nowPlaying = null;
        await this.persist();
      }
      return next;
    });
  }

  status(): Promise<Status> {
    return this.run(async () => {
      const auth = await this.auth();
      const np = this.nowPlaying;
      return {
        settings: await this.settings(),
        userName: auth ? auth.userName : null,
        queueSize: await this.queue.size(),
        lastError: (await this.deps.local.get<string>(STORAGE_KEYS.lastError)) ?? null,
        nowPlaying: np ? { platform: np.platform, artist: np.artist, title: np.title } : null,
      };
    });
  }
}

function safeHost(url: string): string | undefined {
  try {
    return new URL(url).hostname;
  } catch {
    return undefined;
  }
}
