import { describe, expect, it, vi } from "vitest";
import type { SendResult } from "../src/background/client";
import { buildSubmission, type LbSubmission } from "../src/background/payload";
import { backoffMs, ListenQueue, QUEUE_MAX } from "../src/background/queue";
import { memoryKV } from "../src/shared/settings";

const single = (n: number): LbSubmission =>
  buildSubmission("single", { platform: "SPOTIFY", artist: "A", title: `T${n}`, isPlaying: true }, 1790000000 + n);

function setup() {
  let now = 1_000_000;
  const clock = { now: () => now, advance: (ms: number) => (now += ms) };
  const kv = memoryKV();
  return { clock, kv, q: new ListenQueue(kv, clock.now) };
}

const ok: SendResult = { ok: true };
const down: SendResult = { ok: false, retryable: true, unauthorized: false, status: 0 };
const bad: SendResult = { ok: false, retryable: false, unauthorized: false, status: 400 };

describe("ListenQueue", () => {
  it("never queues playing_now", async () => {
    const { q } = setup();
    await q.enqueue(buildSubmission("playing_now", { platform: "SPOTIFY", artist: "A", title: "T", isPlaying: true }));
    expect(await q.size()).toBe(0);
  });

  it("caps at 500, dropping the oldest", async () => {
    const { q } = setup();
    for (let i = 0; i < QUEUE_MAX + 3; i++) await q.enqueue(single(i));
    const items = await q.items();
    expect(items).toHaveLength(QUEUE_MAX);
    expect(items[0]!.body.payload[0].listened_at).toBe(1790000000 + 3);
  });

  it("waits for backoff, then retries with growing delays until success", async () => {
    const { q, clock } = setup();
    await q.enqueue(single(1));
    const send = vi.fn<(b: LbSubmission) => Promise<SendResult>>().mockResolvedValue(down);

    expect((await q.flush(send)).sent).toBe(0);
    expect(send).not.toHaveBeenCalled(); // not due yet

    clock.advance(backoffMs(1));
    await q.flush(send);
    expect(send).toHaveBeenCalledTimes(1);
    const [item] = await q.items();
    expect(item!.attempts).toBe(2);
    expect(item!.nextAttemptAt).toBe(clock.now() + backoffMs(2));

    clock.advance(backoffMs(2));
    send.mockResolvedValue(ok);
    expect((await q.flush(send)).sent).toBe(1);
    expect(await q.size()).toBe(0);
  });

  it("stops at the first retryable failure, keeping order", async () => {
    const { q, clock } = setup();
    for (let i = 0; i < 3; i++) await q.enqueue(single(i));
    clock.advance(backoffMs(1));
    const send = vi.fn<(b: LbSubmission) => Promise<SendResult>>().mockResolvedValueOnce(ok).mockResolvedValueOnce(down);
    await q.flush(send);
    expect(send).toHaveBeenCalledTimes(2);
    expect((await q.items()).map((i) => i.body.payload[0].listened_at)).toEqual([1790000001, 1790000002]);
  });

  it("drops listens the server rejects as malformed", async () => {
    const { q } = setup();
    await q.enqueue(single(1));
    await q.flush(async () => bad, true);
    expect(await q.size()).toBe(0);
  });

  it("reports an unauthorized token and keeps the listen", async () => {
    const { q } = setup();
    await q.enqueue(single(1));
    const r = await q.flush(async () => ({ ok: false, retryable: true, unauthorized: true, status: 401 }), true);
    expect(r.unauthorized).toBe(true);
    expect(await q.size()).toBe(1);
  });

  it("backoff grows to a 1 h ceiling", () => {
    expect(backoffMs(1)).toBe(30_000);
    expect(backoffMs(2)).toBe(60_000);
    expect(backoffMs(30)).toBe(3_600_000);
  });
});
