// Shared helpers for Jingle k6 scripts (JNG-13-01).
import http from "k6/http";
import { check } from "k6";

export const BASE = __ENV.BASE || "http://edge:8080";
export const API = `${BASE}/api/v1`;
const json = { headers: { "Content-Type": "application/json" } };

/** Register `n` throwaway users (k6 setup runs once). Each VU later picks one by index. */
export function registerUsers(n, prefix) {
  const run = Date.now().toString(36);
  const users = [];
  for (let i = 0; i < n; i++) {
    const username = `${prefix}${run}${i}`.slice(0, 20);
    const res = http.post(
      `${API}/auth/register`,
      JSON.stringify({ email: `${username}@load.jingle.local`, password: "load-test-pass-123", username, display_name: `Load ${i}`, birth_year: 1999 }),
      json,
    );
    check(res, { "register 201": (r) => r.status === 201 });
    if (res.status === 201) users.push({ token: res.json("access"), id: res.json("user.id"), username });
  }
  return users;
}

export function authed(token) {
  return { headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, tags: {} };
}

export function get(path, token, name) {
  const p = authed(token);
  p.tags.name = name || path;
  return http.get(`${API}${path}`, p);
}
