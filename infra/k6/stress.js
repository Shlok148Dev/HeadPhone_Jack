// Stress / capacity test for the laptop pilot (QA campaign 2026-10). Reads AND writes, ramping
// 50 → 150 → 300 virtual users to find where p95 leaves the NFR-PERF budgets on this machine.
// Run: docker run --rm -i --network jingle_default -v "$PWD/infra/k6:/k6" grafana/k6 run /k6/stress.js
// Registration is rate-limited (AUTH_REGISTER_RATE), so users are created once in setup.
import http from "k6/http";
import { check, sleep } from "k6";
import { API, authed, get, registerUsers } from "./lib.js";

export const options = {
  setupTimeout: "180s",
  // VUS=n runs a constant load instead of the ramp (to find the highest load inside budget).
  scenarios: __ENV.VUS ? { flat: { executor: "constant-vus", vus: Number(__ENV.VUS), duration: "75s" } } : {
    ramp: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 50 },
        { duration: "60s", target: 50 },
        { duration: "30s", target: 150 },
        { duration: "60s", target: 150 },
        { duration: "30s", target: 300 },
        { duration: "60s", target: 300 },
        { duration: "20s", target: 0 },
      ],
    },
  },
  // Not pass/fail gates for the laptop: recorded to find the knee. NFR targets for reference.
  thresholds: {
    "http_req_duration{kind:read}": ["p(95)<300", "p(99)<800"],
    "http_req_duration{kind:write}": ["p(95)<500"],
    "http_req_duration{name:feed}": ["p(95)<500"],
    http_req_failed: ["rate<0.005"],
  },
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "p(99)", "max"],
};

const SONGS = [
  ["Kasoor", "Prateek Kuhad"],
  ["Baarishein", "Anuv Jain"],
  ["Blinding Lights", "The Weeknd"],
  ["Kesariya", "Arijit Singh"],
  ["Yellow", "Coldplay"],
];

export function setup() {
  return { users: registerUsers(40, "st") };
}

function read(path, token, name) {
  const p = authed(token);
  p.tags = { name, kind: "read" };
  return http.get(`${API}${path}`, p);
}

function write(method, path, token, body, name) {
  const p = authed(token);
  p.tags = { name, kind: "write" };
  p.headers["Idempotency-Key"] = `${__VU}-${__ITER}-${name}-${Math.random()}`;
  return http.request(method, `${API}${path}`, JSON.stringify(body), p);
}

export default function (data) {
  const u = data.users[__VU % data.users.length];
  if (!u) return;
  const t = u.token;
  check(read("/feed", t, "feed"), { "feed 200": (r) => r.status === 200 });
  check(read("/me", t, "me"), { "me 200": (r) => r.status === 200 });
  read("/drops/today", t, "drops_today");
  read("/notifications", t, "notifications");
  read("/inbox/unread", t, "inbox_unread");
  read("/friends", t, "friends");
  read("/rituals", t, "rituals");
  read("/circles", t, "circles");
  read(`/songs/search?q=${encodeURIComponent(["kas", "arij", "weekn", "cold"][__ITER % 4])}`, t, "song_search");
  // Writes: a drop (one per user per day; 409 after the first is expected and still exercises the path)
  // and a privacy toggle round-trip.
  const s = SONGS[__ITER % SONGS.length];
  const d = write("POST", "/drops", t, { title: s[0], artist: s[1] }, "drop");
  check(d, { "drop 201/409": (r) => r.status === 201 || r.status === 409 });
  const pr = write("PATCH", "/me", t, { city: ["Mumbai", "Pune"][__ITER % 2] }, "me_patch");
  check(pr, { "me patch 200": (r) => r.status === 200 });
  sleep(1 + Math.random());
}
