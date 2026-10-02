// 45 s at 300 users, reads only: used while sampling container CPU (QA campaign).
import { sleep } from "k6";
import { get, registerUsers } from "./lib.js";
export const options = { setupTimeout: "120s", scenarios: { b: { executor: "constant-vus", vus: 300, duration: "45s" } } };
export function setup() { return { users: registerUsers(30, "bu") }; }
export default function (d) { const u = d.users[__VU % d.users.length]; get("/feed", u.token, "feed"); get("/me", u.token, "me"); sleep(0.5); }
