import { PLATFORMS, type PlatformId } from "./types";

export const DEFAULT_ORIGIN = "http://localhost:8080";

/** Origins covered by the static host_permissions in manifest.json. */
export const BUILTIN_ORIGINS: readonly string[] = ["http://localhost:8080", "http://127.0.0.1:8080"];

export interface Settings {
  origin: string;
  paused: boolean;
  platforms: Record<PlatformId, boolean>;
}

export interface Auth {
  token: string;
  userName: string;
}

export const DEFAULT_SETTINGS: Settings = {
  origin: DEFAULT_ORIGIN,
  paused: false,
  platforms: Object.fromEntries(PLATFORMS.map((p) => [p, true])) as Record<PlatformId, boolean>,
};

export const STORAGE_KEYS = {
  settings: "settings",
  auth: "auth",
  queue: "queue",
  scrobbler: "scrobblerState",
  lastError: "lastError",
} as const;

/**
 * Normalise a user-entered Jingle origin to `scheme://host[:port]`.
 * Only https, or http on loopback, is accepted. Returns null when invalid.
 */
export function normaliseOrigin(input: string): string | null {
  let url: URL;
  try {
    url = new URL(input.trim());
  } catch {
    return null;
  }
  const loopback = url.hostname === "localhost" || url.hostname === "127.0.0.1" || url.hostname === "[::1]";
  if (url.protocol !== "https:" && !(url.protocol === "http:" && loopback)) return null;
  if (url.username || url.password) return null;
  return url.origin;
}

export function mergeSettings(stored: Partial<Settings> | undefined): Settings {
  return {
    origin: stored?.origin ?? DEFAULT_SETTINGS.origin,
    paused: stored?.paused ?? DEFAULT_SETTINGS.paused,
    platforms: { ...DEFAULT_SETTINGS.platforms, ...(stored?.platforms ?? {}) },
  };
}

/** Minimal async key-value store; chrome.storage.local in the extension, a Map in tests. */
export interface KV {
  get<T>(key: string): Promise<T | undefined>;
  set(key: string, value: unknown): Promise<void>;
  remove(key: string): Promise<void>;
}

export function chromeKV(area: chrome.storage.StorageArea): KV {
  return {
    async get<T>(key: string) {
      const res = await area.get(key);
      return res[key] as T | undefined;
    },
    async set(key, value) {
      await area.set({ [key]: value });
    },
    async remove(key) {
      await area.remove(key);
    },
  };
}

export function memoryKV(): KV & { data: Map<string, unknown> } {
  const data = new Map<string, unknown>();
  return {
    data,
    async get<T>(key: string) {
      const v = data.get(key);
      return v === undefined ? undefined : (structuredClone(v) as T);
    },
    async set(key, value) {
      data.set(key, structuredClone(value));
    },
    async remove(key) {
      data.delete(key);
    },
  };
}
