import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, refreshSession, setAccessToken } from "./api";

function res(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}

describe("api client", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken(null);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("sends the in-memory access token and never puts it in the URL", async () => {
    setAccessToken("acc-1");
    fetchMock.mockResolvedValueOnce(res(200, { ok: true }));
    await api("/me");
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/v1/me");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer acc-1");
  });

  it("refreshes once on 401 and retries", async () => {
    setAccessToken("stale");
    fetchMock
      .mockResolvedValueOnce(res(401, { error: { code: "UNAUTHENTICATED", message: "x" } }))
      .mockResolvedValueOnce(res(200, { access: "fresh", user: { id: "u" } }))
      .mockResolvedValueOnce(res(200, { state: "LIVE" }));
    await expect(api("/me/card")).resolves.toEqual({ state: "LIVE" });
    expect(fetchMock.mock.calls[1]![0]).toBe("/api/v1/auth/refresh");
    expect(new Headers(fetchMock.mock.calls[2]![1].headers).get("Authorization")).toBe("Bearer fresh");
  });

  it("shares one in-flight refresh between parallel callers (refresh tokens rotate)", async () => {
    let resolve!: (r: Response) => void;
    fetchMock.mockReturnValueOnce(new Promise<Response>((r) => (resolve = r)));
    const a = refreshSession();
    const b = refreshSession();
    resolve(res(200, { access: "t", user: { id: "u" } }));
    await Promise.all([a, b]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("maps the error envelope to ApiError", async () => {
    fetchMock.mockResolvedValueOnce(res(409, { error: { code: "CONSENT_REQUIRED", message: "Allow sharing", details: { purpose: "activity_sharing" } } }));
    const err = await api("/sources/companion/token", { method: "POST" }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).code).toBe("CONSENT_REQUIRED");
    expect((err as ApiError).status).toBe(409);
  });

  it("reports network failures with friendly copy", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("fetch failed"));
    const err = (await api("/me").catch((e: unknown) => e)) as ApiError;
    expect(err.code).toBe("NETWORK");
    expect(err.message).toMatch(/couldn't reach Jingle/);
  });
});
