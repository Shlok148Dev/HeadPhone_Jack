// Session storm (Tech Bible 9.3): 100 sessions x 50 members voting; vote fan-out p95 ≤ 1 s.
// Scale environment only. Each VU is one member; USERS_FILE holds pre-made sessions + tokens:
// [{session_id, entry_ids: [...], members: [{token}]}]. See docs/runbooks/scale-test.md.
import http from "k6/http";
import { check, sleep } from "k6";
import { SharedArray } from "k6/data";
import { API, authed } from "./lib.js";

const rooms = new SharedArray("rooms", () => JSON.parse(open(__ENV.USERS_FILE || "./rooms.json")));

export const options = {
  scenarios: { vote: { executor: "constant-vus", vus: 5000, duration: "10m" } },
  thresholds: { "http_req_duration{name:vote}": ["p(95)<1000"], http_req_failed: ["rate<0.01"] },
};

export default function () {
  const room = rooms[(__VU - 1) % rooms.length];
  const me = room.members[Math.floor((__VU - 1) / rooms.length) % room.members.length];
  const entry = room.entry_ids[Math.floor(Math.random() * room.entry_ids.length)];
  const p = authed(me.token);
  p.tags.name = "vote";
  const r = http.post(`${API}/queue/${entry}/vote`, JSON.stringify({ value: Math.random() < 0.8 ? 1 : -1 }), p);
  check(r, { "vote ok": (x) => x.status === 200 });
  sleep(2 + Math.random() * 3);
}
