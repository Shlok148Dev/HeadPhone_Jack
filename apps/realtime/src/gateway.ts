/**
 * Jingle realtime gateway logic (Technical Bible 7.3; ADR-0005, ADR-0018).
 *
 * The gateway authenticates sockets, keeps room membership and fans out *hints*. It never decides
 * privacy: a `feed:update {user_id}` only tells friends to refetch that card over REST, where
 * core-api applies blocks, visibility and Private mode (BR-06/07).
 */
import { jwtVerify } from "jose";

export interface Config {
  jwtKey: Uint8Array;
  coreApiUrl: string;
  serviceToken: string;
  coalesceMs: number;
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const key = env.JWT_SIGNING_KEY ?? "";
  if (!key) throw new Error("JWT_SIGNING_KEY is required");
  return {
    jwtKey: new TextEncoder().encode(key),
    coreApiUrl: (env.CORE_API_INTERNAL_URL ?? "http://core-api:8000").replace(/\/$/, ""),
    serviceToken: env.SERVICE_TOKEN ?? "",
    coalesceMs: Number(env.RT_COALESCE_MS ?? 2000),
  };
}

/** Verify an access JWT from core-api (HS256, iss=jingle-core, typ=access). Returns the user id. */
export async function verifyAccess(token: unknown, cfg: Pick<Config, "jwtKey">): Promise<string> {
  if (typeof token !== "string" || token.length > 4096) throw new Error("missing token");
  const { payload } = await jwtVerify(token, cfg.jwtKey, { algorithms: ["HS256"], issuer: "jingle-core" });
  if (payload.typ !== "access" || typeof payload.sub !== "string") throw new Error("not an access token");
  return payload.sub;
}

export type Fetcher = (url: string, init: RequestInit) => Promise<Response>;

export async function fetchFriendIds(userId: string, cfg: Config, fetcher: Fetcher = fetch): Promise<string[]> {
  const res = await fetcher(`${cfg.coreApiUrl}/internal/users/${encodeURIComponent(userId)}/friends`, {
    headers: { "X-Service-Token": cfg.serviceToken },
  });
  if (!res.ok) throw new Error(`friends lookup failed: ${res.status}`);
  const ids = (await res.json()) as unknown;
  return Array.isArray(ids) ? ids.filter((x): x is string => typeof x === "string") : [];
}

/** Rooms: `user:{id}` (me), `friends:{id}` (joined by each online friend of id). */
export const userRoom = (id: string) => `user:${id}`;
export const friendsRoom = (id: string) => `friends:${id}`;

/** Collapse bursts: at most one emit per key per window (Technical Bible 7.3 back-pressure). */
export class Coalescer {
  private pending = new Map<string, ReturnType<typeof setTimeout>>();
  constructor(private readonly windowMs: number) {}
  schedule(key: string, fire: () => void): void {
    if (this.pending.has(key)) return;
    this.pending.set(
      key,
      setTimeout(() => {
        this.pending.delete(key);
        fire();
      }, this.windowMs),
    );
  }
  clear(): void {
    for (const t of this.pending.values()) clearTimeout(t);
    this.pending.clear();
  }
}

export interface Emitter {
  toRoom(room: string, event: string, payload: unknown): void;
  resyncUser(userId: string): Promise<void>;
}

/**
 * Route one stream entry to rooms. `events:listen` fields: {data: ListenEvent JSON};
 * `events:domain` fields: {type, data: payload JSON}. Returns a short description for logs/tests.
 */
export function routeEvent(
  stream: string,
  fields: Record<string, string>,
  emitter: Emitter,
  coalescer: Coalescer,
): string {
  let ev: Record<string, unknown>;
  try {
    ev = JSON.parse(fields.data ?? "") as Record<string, unknown>;
  } catch {
    return "ignored:bad-json";
  }
  if (stream === "events:listen") {
    const uid = typeof ev.user_id === "string" ? ev.user_id : null;
    if (!uid) return "ignored:no-user";
    coalescer.schedule(`listen:${uid}`, () => {
      emitter.toRoom(friendsRoom(uid), "feed:update", { user_id: uid });
      emitter.toRoom(userRoom(uid), "me:update", {});
    });
    return `listen:${uid}`;
  }
  const type = String(fields.type ?? "");
  const payload = ev;
  if (type === "friendship.changed" || type === "block.created") {
    const ids = Array.isArray(payload.user_ids) ? payload.user_ids.filter((x): x is string => typeof x === "string") : [];
    for (const id of ids) {
      void emitter.resyncUser(id);
      emitter.toRoom(userRoom(id), "friends:changed", {});
    }
    return `${type}:${ids.length}`;
  }
  if (type === "feed.invalidate" && typeof payload.user_id === "string") {
    emitter.toRoom(friendsRoom(payload.user_id), "feed:update", { user_id: payload.user_id });
    return "feed.invalidate";
  }
  if (type === "notify" && typeof payload.user_id === "string") {
    emitter.toRoom(userRoom(payload.user_id), "notify", { type: payload.type, id: payload.id });
    return "notify";
  }
  return `ignored:${type || "unknown"}`;
}
