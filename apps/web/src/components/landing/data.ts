/** Server-side data for the logged-out homepage: real covers from the Artwork service. */

export interface WallCover {
  url: string;
  url_small: string;
  color: string | null;
  label: string;
}

export async function loadWall(): Promise<WallCover[]> {
  const base = process.env.CORE_API_INTERNAL_URL;
  if (!base) return [];
  try {
    const res = await fetch(`${base.replace(/\/$/, "")}/api/v1/artwork/wall`, {
      next: { revalidate: 3600 },
      headers: { "X-Forwarded-For": "127.0.0.1" },
    });
    if (!res.ok) return [];
    const body = (await res.json()) as { covers: WallCover[] };
    return body.covers ?? [];
  } catch {
    return []; // the page still renders (generative covers) if the API is down
  }
}
