import { createServer } from "node:http";
import { createAdapter } from "@socket.io/redis-adapter";
import express from "express";
import { Redis } from "ioredis";
import { pino } from "pino";
import { Server, type Socket } from "socket.io";
import {
  Coalescer,
  fetchFriendIds,
  friendsRoom,
  loadConfig,
  mayJoinSession,
  sessionRoom,
  routeEvent,
  userRoom,
  verifyAccess,
  type Emitter,
} from "./gateway.js";

const log = pino({ base: { service: "realtime" } });
const cfg = loadConfig();
const redisUrl = process.env.REDIS_URL ?? "redis://redis:6379/0";
const redis = new Redis(redisUrl);
const pub = new Redis(redisUrl);
const sub = pub.duplicate();
const streams = new Redis(redisUrl, { maxRetriesPerRequest: null });

const PRESENCE_TTL = 120; // Technical Bible 3.4
const HEARTBEAT_MS = 60_000;
const SESSION_TTL = 60; // core-api hands the host role over when this lapses (JNG-07-08)
const SESSION_BEAT_MS = 20_000;

async function markSessions(userId: string, sessions: Set<string>): Promise<void> {
  if (!sessions.size) return;
  const pipe = redis.pipeline();
  for (const sid of sessions) pipe.set(`sesspres:${sid}:${userId}`, "1", "EX", SESSION_TTL);
  await pipe.exec();
}

const app = express();
app.get("/healthz", (_req, res) => {
  res.json({ status: redis.status === "ready" ? "ok" : "degraded" });
});

const http = createServer(app);
export const io = new Server(http, {
  path: "/rt/socket.io",
  cors: { origin: false },
  adapter: createAdapter(pub, sub),
  pingInterval: 25_000,
  pingTimeout: 20_000,
});

/** Presence for adaptive polling: me, plus "someone is watching" for each friend (Tech Bible 2.3). */
async function markPresence(userId: string, friendIds: string[]): Promise<void> {
  const pipe = redis.pipeline();
  pipe.set(`presence:${userId}`, "1", "EX", PRESENCE_TTL);
  for (const f of friendIds) pipe.set(`watched:${f}`, "1", "EX", PRESENCE_TTL);
  await pipe.exec();
}

async function joinFriendRooms(socket: Socket): Promise<void> {
  const uid = socket.data.userId as string;
  const friends = await fetchFriendIds(uid, cfg);
  for (const room of socket.rooms) {
    if (room.startsWith("friends:") && !friends.includes(room.slice(8))) void socket.leave(room);
  }
  await socket.join(friends.map(friendsRoom));
  socket.data.friendIds = friends;
  await markPresence(uid, friends);
}

io.use(async (socket, next) => {
  try {
    socket.data.userId = await verifyAccess(socket.handshake.auth?.token, cfg);
    next();
  } catch {
    next(new Error("unauthorized"));
  }
});

io.on("connection", async (socket) => {
  const uid = socket.data.userId as string;
  await socket.join(userRoom(uid));
  try {
    await joinFriendRooms(socket);
  } catch (err) {
    log.warn({ err: String(err) }, "friend rooms unavailable; client falls back to polling");
  }
  const beat = setInterval(() => {
    void markPresence(uid, (socket.data.friendIds as string[]) ?? []).catch(() => undefined);
  }, HEARTBEAT_MS);
  const sessions = new Set<string>();
  const sessionBeat = setInterval(() => void markSessions(uid, sessions).catch(() => undefined), SESSION_BEAT_MS);

  // Live sessions (Tech Bible 4.3): join the room after core-api confirms membership. State and
  // writes go over REST; the room only carries versioned `queue:delta` broadcasts.
  socket.on("session:join", async (msg: { session_id?: unknown }, ack?: (r: { ok: boolean }) => void) => {
    const sid = msg?.session_id;
    let ok = false;
    try {
      ok = await mayJoinSession(sid, uid, cfg);
    } catch (err) {
      log.warn({ err: String(err) }, "session membership check failed");
    }
    if (ok && typeof sid === "string") {
      await socket.join(sessionRoom(sid));
      sessions.add(sid);
      await markSessions(uid, new Set([sid])).catch(() => undefined);
    }
    if (typeof ack === "function") ack({ ok });
  });
  socket.on("session:leave", (msg: { session_id?: unknown }) => {
    if (typeof msg?.session_id !== "string") return;
    sessions.delete(msg.session_id);
    void socket.leave(sessionRoom(msg.session_id));
    void redis.del(`sesspres:${msg.session_id}:${uid}`).catch(() => undefined);
  });
  socket.on("disconnect", () => {
    clearInterval(beat);
    clearInterval(sessionBeat);
  });
});

// Each pod consumes every entry and emits only to its own sockets (io.local), so the Redis
// adapter never duplicates a hint across pods.
const emitter: Emitter = {
  toRoom: (room, event, payload) => io.local.to(room).emit(event, payload),
  resyncUser: async (userId) => {
    for (const s of await io.local.in(userRoom(userId)).fetchSockets()) {
      const sock = io.sockets.sockets.get(s.id);
      if (sock) await joinFriendRooms(sock).catch(() => undefined);
    }
  },
};
const coalescer = new Coalescer(cfg.coalesceMs);

async function consume(): Promise<void> {
  const cursors: Record<string, string> = { "events:listen": "$", "events:domain": "$" };
  for (;;) {
    try {
      const res = (await streams.xread("COUNT", 200, "BLOCK", 5000, "STREAMS", "events:listen", "events:domain",
        cursors["events:listen"]!, cursors["events:domain"]!)) as [string, [string, string[]][]][] | null;
      for (const [stream, entries] of res ?? []) {
        for (const [id, flat] of entries) {
          cursors[stream] = id;
          const fields: Record<string, string> = {};
          for (let i = 0; i + 1 < flat.length; i += 2) fields[flat[i]!] = flat[i + 1]!;
          routeEvent(stream, fields, emitter, coalescer);
        }
      }
    } catch (err) {
      log.warn({ err: String(err) }, "stream read failed; retrying");
      await new Promise((r) => setTimeout(r, 1000));
    }
  }
}

const port = Number(process.env.PORT ?? 4000);
http.listen(port, () => {
  log.info({ port }, "realtime listening");
  void consume();
});
