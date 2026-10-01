// 5,000 concurrent users (SRS JNG-13-01; Tech Bible 9.3 scale test). Written for the scale
// environment, NOT the laptop pilot: run against a staging stack sized per docs/runbooks/scale-test.md.
// Users are pre-created by scripts/seed_load_users (USERS_FILE) because registration is rate-limited.
import { check, sleep } from "k6";
import { SharedArray } from "k6/data";
import { get } from "./lib.js";

const users = new SharedArray("users", () => JSON.parse(open(__ENV.USERS_FILE || "./users.json")));

export const options = {
  scenarios: {
    steady: { executor: "ramping-vus", startVUs: 0, stages: [{ duration: "10m", target: 5000 }, { duration: "20m", target: 5000 }, { duration: "5m", target: 0 }] },
  },
  thresholds: {
    http_req_failed: ["rate<0.005"],
    http_req_duration: ["p(95)<300"],
    "http_req_duration{name:feed}": ["p(95)<300"],
  },
};

export default function () {
  const u = users[(__VU - 1) % users.length];
  check(get("/feed", u.token, "feed"), { "feed 200": (r) => r.status === 200 });
  get("/inbox/unread", u.token, "inbox_unread");
  get("/notifications", u.token, "notifications");
  sleep(5 + Math.random() * 10); // realistic think time: feed is mostly kept live by the socket
}
