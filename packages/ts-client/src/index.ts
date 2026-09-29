import createClient from "openapi-fetch";
import type { paths } from "./schema";

export type { paths };

/** Create a typed Jingle API client. `getToken` returns the in-memory access JWT. */
export function createJingleClient(baseUrl: string, getToken: () => string | null) {
  const client = createClient<paths>({ baseUrl, credentials: "include" });
  client.use({
    onRequest({ request }) {
      const token = getToken();
      if (token) request.headers.set("Authorization", `Bearer ${token}`);
      return request;
    },
  });
  return client;
}
