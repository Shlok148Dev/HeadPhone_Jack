import type { Status } from "../background/service";
import { BUILTIN_ORIGINS, normaliseOrigin, type Settings } from "../shared/settings";
import { PLATFORM_NAMES, PLATFORMS, type PairResult, type PopupMessage } from "../shared/types";

const $ = <T extends HTMLElement>(id: string): T => {
  const el = document.getElementById(id);
  if (!el) throw new Error(`missing #${id}`);
  return el as T;
};

const ERRORS: Record<string, string> = {
  token_rejected: "Jingle rejected the token. Sign in again.",
  offline: "Can't reach Jingle right now. Plays are saved and will be sent later.",
  invalid_token: "That token wasn't accepted by Jingle.",
  unreachable: "Can't reach Jingle at that address.",
  wrong_origin: "That page isn't your configured Jingle server.",
  invalid_origin: "Use an https:// address (or http://localhost).",
};

function send<T>(msg: PopupMessage): Promise<T> {
  return chrome.runtime.sendMessage(msg) as Promise<T>;
}

/** Joins names as "A, B and C". */
export function humanList(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

function showError(code: string | null): void {
  const el = $("error");
  el.hidden = !code;
  el.textContent = code ? (ERRORS[code] ?? `Something went wrong (${code}).`) : "";
}

async function render(): Promise<void> {
  const s = await send<Status>({ type: "popup:status" });
  const connected = s.userName !== null;
  $("signed-in").hidden = !connected;
  $("signed-out").hidden = connected;
  $<HTMLInputElement>("origin").value = s.settings.origin;
  $<HTMLInputElement>("paused").checked = s.settings.paused;

  const enabled = PLATFORMS.filter((p) => s.settings.platforms[p]).map((p) => PLATFORM_NAMES[p]);
  const who = s.userName ? `@${s.userName}` : "your Jingle account";
  let status: string;
  if (!connected) status = "Not connected. Sign in to share what you play in this browser.";
  else if (s.settings.paused) status = `Connected as ${who} — sharing is paused.`;
  else if (enabled.length === 0) status = `Connected as ${who} — no players selected.`;
  else status = `Connected as ${who} — sharing what you play on ${humanList(enabled)} in this browser.`;
  if (s.queueSize > 0) status += ` ${s.queueSize} play${s.queueSize === 1 ? "" : "s"} waiting to send.`;
  $("status").textContent = status;

  const now = $("now");
  now.hidden = !s.nowPlaying;
  now.textContent = s.nowPlaying ? `Now: ${s.nowPlaying.title} — ${s.nowPlaying.artist}` : "";
  showError(s.lastError);

  const box = $("platforms");
  box.replaceChildren(
    ...PLATFORMS.map((p) => {
      const label = document.createElement("label");
      label.className = "switch-row";
      const name = document.createElement("span");
      name.textContent = PLATFORM_NAMES[p];
      const input = document.createElement("input");
      input.type = "checkbox";
      input.setAttribute("role", "switch");
      input.checked = s.settings.platforms[p];
      input.addEventListener("change", () => {
        void send({ type: "popup:settings", patch: { platforms: { [p]: input.checked } } }).then(render);
      });
      label.append(name, input);
      return label;
    }),
  );
}

/** A custom origin needs its host permission (and `scripting` for auto-pairing), asked for on click. */
async function ensureOriginPermission(origin: string): Promise<boolean> {
  if (BUILTIN_ORIGINS.includes(origin)) return true;
  const granted = await chrome.permissions.request({ origins: [`${origin}/*`], permissions: ["scripting"] });
  if (granted) await send({ type: "popup:originChanged" });
  return granted;
}

/** Validate the origin field, ask for its permission if custom, and save it. Must run in a click handler. */
async function applyOrigin(): Promise<string | null> {
  const origin = normaliseOrigin($<HTMLInputElement>("origin").value);
  if (!origin) {
    showError("invalid_origin");
    return null;
  }
  if (!(await ensureOriginPermission(origin))) return null;
  const r = await send<Settings | { error: string }>({ type: "popup:settings", patch: { origin } });
  if ("error" in r) {
    showError(r.error);
    return null;
  }
  return origin;
}

function init(): void {
  $("sign-in").addEventListener("click", async () => {
    const origin = await applyOrigin();
    if (!origin) return;
    await chrome.tabs.create({ url: `${origin}/connect/companion?ext=1` });
    window.close();
  });

  $("token-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const input = $<HTMLInputElement>("token");
    if (!(await applyOrigin())) return;
    const r = await send<PairResult>({ type: "popup:pair", token: input.value });
    input.value = "";
    if (!r.ok) return showError(r.error ?? "invalid_token");
    await render();
  });

  $("paused").addEventListener("change", (ev) => {
    const paused = (ev.target as HTMLInputElement).checked;
    void send({ type: "popup:settings", patch: { paused } }).then(render);
  });

  $("sign-out").addEventListener("click", () => void send({ type: "popup:signOut" }).then(render));

  $("origin-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (await applyOrigin()) await render();
  });

  void render();
}

init();
