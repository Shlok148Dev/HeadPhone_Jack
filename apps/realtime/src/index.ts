import { createServer } from "node:http";
import express from "express";
import { pino } from "pino";
import { Server } from "socket.io";

const log = pino({ base: { service: "realtime" } });
const app = express();
app.get("/healthz", (_req, res) => {
  res.json({ status: "ok" });
});

const http = createServer(app);
// Full auth, rooms and fan-out land in Sprint 4 (realtime-engineer).
export const io = new Server(http, { path: "/rt/socket.io", cors: { origin: false } });

const port = Number(process.env.PORT ?? 4000);
http.listen(port, () => log.info({ port }, "realtime listening"));
