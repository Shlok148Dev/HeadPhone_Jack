/**
 * Jingle API client (CONTRACTS.md §3, §8).
 *
 * The access JWT lives only in memory; the refresh token is an HttpOnly cookie the browser sends
 * to /api/v1/auth. One in-flight refresh is shared so parallel 401s never rotate the cookie twice.
 */

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.code = body.code;
    this.details = body.details ?? {};
  }
}

const NETWORK_ERROR: ApiErrorBody = {
  code: "NETWORK",
  message: "We couldn't reach Jingle. Check your connection and try again.",
};

let accessToken: string | null = null;
let refreshing: Promise<AuthPayload | null> | null = null;
let onSignedOut: (() => void) | null = null;

export interface Me {
  id: string;
  is_staff?: boolean;
  email: string;
  username: string;
  display_name: string;
  college: string;
  city: string;
  discoverable: boolean;
  needs_onboarding: boolean;
  private_mode: { active: boolean; until: string | null } | null;
  created_at: string;
}

export interface AuthPayload {
  access: string;
  user: Me;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function onSessionEnded(cb: () => void): void {
  onSignedOut = cb;
}

async function parse(res: Response): Promise<unknown> {
  if (res.status === 204) return null;
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function toError(status: number, body: unknown): ApiError {
  const env = (body as { error?: ApiErrorBody } | null)?.error;
  if (env) return new ApiError(status, env);
  // Gateway errors mean Jingle itself is restarting or unreachable, not that the user did anything wrong.
  if (status >= 502 && status <= 504) {
    return new ApiError(status, { code: "UNAVAILABLE", message: "Jingle can't be reached right now. Try again in a moment." });
  }
  return new ApiError(status, { code: "ERROR", message: "Something went wrong on our side. Please try again." });
}

async function rawFetch(path: string, init: RequestInit, withAuth: boolean): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (withAuth && accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  try {
    return await fetch(`/api/v1${path}`, { ...init, headers, credentials: "same-origin" });
  } catch {
    throw new ApiError(0, NETWORK_ERROR);
  }
}

/** Exchange the refresh cookie for a new access token. Resolves null when signed out. */
export function refreshSession(): Promise<AuthPayload | null> {
  if (!refreshing) {
    refreshing = (async () => {
      const res = await rawFetch("/auth/refresh", { method: "POST" }, false);
      if (!res.ok) {
        accessToken = null;
        return null;
      }
      const body = (await parse(res)) as AuthPayload;
      accessToken = body.access;
      return body;
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res = await rawFetch(path, init, true);
  if (res.status === 401 && !path.startsWith("/auth/")) {
    const renewed = await refreshSession();
    if (!renewed) {
      onSignedOut?.();
      throw toError(401, await parse(res));
    }
    res = await rawFetch(path, init, true);
  }
  const body = await parse(res);
  if (!res.ok) throw toError(res.status, body);
  return body as T;
}

export const json = (data: unknown): RequestInit => ({ body: JSON.stringify(data) });
