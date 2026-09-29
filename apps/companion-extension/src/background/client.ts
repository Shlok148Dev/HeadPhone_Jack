import type { LbSubmission } from "./payload";

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export type SendResult =
  | { ok: true }
  | { ok: false; retryable: boolean; unauthorized: boolean; status: number };

/** POST {origin}/ingest/1/submit-listens with `Authorization: Token <token>`. Never logs the token. */
export async function submitListens(fetchImpl: FetchLike, origin: string, token: string, body: LbSubmission): Promise<SendResult> {
  let res: Response;
  try {
    res = await fetchImpl(`${origin}/ingest/1/submit-listens`, {
      method: "POST",
      headers: { Authorization: `Token ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "omit",
    });
  } catch {
    return { ok: false, retryable: true, unauthorized: false, status: 0 };
  }
  if (res.ok) return { ok: true };
  const unauthorized = res.status === 401 || res.status === 403;
  const retryable = unauthorized || res.status === 408 || res.status === 429 || res.status >= 500;
  return { ok: false, retryable, unauthorized, status: res.status };
}

export interface ValidateResult {
  valid: boolean;
  userName?: string;
  /** true when the server could not be reached. */
  networkError?: boolean;
}

/** GET {origin}/ingest/1/validate-token (ListenBrainz response: {valid, user_name}). */
export async function validateToken(fetchImpl: FetchLike, origin: string, token: string): Promise<ValidateResult> {
  let res: Response;
  try {
    res = await fetchImpl(`${origin}/ingest/1/validate-token`, {
      method: "GET",
      headers: { Authorization: `Token ${token}` },
      credentials: "omit",
    });
  } catch {
    return { valid: false, networkError: true };
  }
  if (!res.ok) return { valid: false };
  let data: unknown;
  try {
    data = await res.json();
  } catch {
    return { valid: false };
  }
  const d = data as { valid?: unknown; user_name?: unknown };
  if (d.valid !== true) return { valid: false };
  return { valid: true, ...(typeof d.user_name === "string" ? { userName: d.user_name } : {}) };
}
