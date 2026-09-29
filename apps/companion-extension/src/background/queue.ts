import type { KV } from "../shared/settings";
import { STORAGE_KEYS } from "../shared/settings";
import type { LbSubmission } from "./payload";
import type { SendResult } from "./client";

export const QUEUE_MAX = 500;
export const BACKOFF_BASE_MS = 30_000;
export const BACKOFF_MAX_MS = 60 * 60_000;

export interface QueuedListen {
  body: LbSubmission;
  attempts: number;
  nextAttemptAt: number;
}

export function backoffMs(attempts: number): number {
  return Math.min(BACKOFF_BASE_MS * 2 ** Math.max(0, attempts - 1), BACKOFF_MAX_MS);
}

/**
 * Offline queue for `single` listens only (playing_now is never queued: stale Live is worse than none).
 * Persisted in chrome.storage.local, capped at 500 (oldest dropped), exponential backoff 30 s → 1 h.
 */
export class ListenQueue {
  private flushing = false;

  constructor(private readonly kv: KV, private readonly now: () => number) {}

  async items(): Promise<QueuedListen[]> {
    return (await this.kv.get<QueuedListen[]>(STORAGE_KEYS.queue)) ?? [];
  }

  async size(): Promise<number> {
    return (await this.items()).length;
  }

  async enqueue(body: LbSubmission, attempts = 1): Promise<void> {
    if (body.listen_type !== "single") return;
    const q = await this.items();
    q.push({ body, attempts, nextAttemptAt: this.now() + backoffMs(attempts) });
    while (q.length > QUEUE_MAX) q.shift();
    await this.kv.set(STORAGE_KEYS.queue, q);
  }

  /**
   * Send every due item in order. Stops at the first retryable failure (server down or token
   * rejected) and pushes back that item; drops items the server rejects as malformed (4xx).
   */
  async flush(send: (body: LbSubmission) => Promise<SendResult>, force = false): Promise<{ sent: number; unauthorized: boolean }> {
    if (this.flushing) return { sent: 0, unauthorized: false };
    this.flushing = true;
    let sent = 0;
    let unauthorized = false;
    try {
      const q = await this.items();
      const t = this.now();
      const keep: QueuedListen[] = [];
      let stop = false;
      for (const item of q) {
        if (stop || (!force && item.nextAttemptAt > t)) {
          keep.push(item);
          continue;
        }
        const r = await send(item.body);
        if (r.ok) {
          sent++;
        } else if (r.retryable) {
          const attempts = item.attempts + 1;
          keep.push({ body: item.body, attempts, nextAttemptAt: t + backoffMs(attempts) });
          unauthorized = r.unauthorized;
          stop = true;
        }
        // non-retryable (400 etc.): drop
      }
      await this.kv.set(STORAGE_KEYS.queue, keep);
    } finally {
      this.flushing = false;
    }
    return { sent, unauthorized };
  }

  async clear(): Promise<void> {
    await this.kv.remove(STORAGE_KEYS.queue);
  }
}
