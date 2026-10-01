// Local smoke at 50 concurrent users (Tech Bible 9.x; SRS JNG-13-01, NFR-PERF p95 ≤ 300 ms).
// Run: docker run --rm -i --network jingle_default -v "$PWD/infra/k6:/k6" grafana/k6 run /k6/smoke.js
import { check, sleep } from "k6";
import { get, registerUsers } from "./lib.js";

export const options = {
  setupTimeout: "120s",
  scenarios: {
    browse: { executor: "ramping-vus", startVUs: 0, stages: [{ duration: "30s", target: 50 }, { duration: "90s", target: 50 }, { duration: "15s", target: 0 }] },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{name:feed}": ["p(95)<300"],
    "http_req_duration{name:me}": ["p(95)<300"],
    "http_req_duration{name:notifications}": ["p(95)<300"],
    "http_req_duration{name:inbox_unread}": ["p(95)<300"],
    "http_req_duration{name:friends}": ["p(95)<300"],
    "http_req_duration{name:rituals}": ["p(95)<300"],
    "http_req_duration{name:suggestions}": ["p(95)<300"],
    http_req_duration: ["p(95)<300"],
  },
};

export function setup() {
  return { users: registerUsers(50, "ks") };
}

// A pilot user's loop: home feed, notifications, inbox badge, friends, rituals, profile.
export default function (data) {
  const u = data.users[(__VU - 1) % data.users.length];
  const r = get("/feed", u.token, "feed");
  check(r, { "feed 200": (x) => x.status === 200 });
  check(get("/me", u.token, "me"), { "me 200": (x) => x.status === 200 });
  get("/notifications", u.token, "notifications");
  get("/inbox/unread", u.token, "inbox_unread");
  get("/friends", u.token, "friends");
  get("/rituals", u.token, "rituals");
  get("/suggestions", u.token, "suggestions");
  // Realistic browsing: a page change every 5–10 s (the socket keeps the feed live in between).
  // STRESS=1 drops the think time to 1–3 s to find the throughput ceiling instead.
  sleep(__ENV.STRESS ? 1 + Math.random() * 2 : 5 + Math.random() * 5);
}
