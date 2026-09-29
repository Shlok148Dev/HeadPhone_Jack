import { chromeKV, isBuiltinOrigin, type Settings } from "../shared/settings";
import type { ContentMessage, PopupMessage } from "../shared/types";
import { Companion } from "./service";

const TICK_ALARM = "jingle-tick";
const PAIRING_SCRIPT_ID = "jingle-pairing-custom-origin";

const companion = new Companion({
  local: chromeKV(chrome.storage.local),
  session: chromeKV(chrome.storage.session),
  fetch: (input, init) => fetch(input, init),
  now: () => Date.now(),
});

async function ensureAlarm(): Promise<void> {
  const existing = await chrome.alarms.get(TICK_ALARM);
  if (!existing) await chrome.alarms.create(TICK_ALARM, { periodInMinutes: 0.5 });
}

/**
 * Built-in origins get the pairing script from the manifest. A custom (https) origin gets it
 * registered at runtime, only after the user granted that origin + `scripting` in the popup.
 */
async function syncPairingScript(): Promise<void> {
  if (!chrome.scripting) return; // optional permission not granted
  const { origin } = await companion.settings();
  const registered = await chrome.scripting.getRegisteredContentScripts({ ids: [PAIRING_SCRIPT_ID] });
  if (registered.length > 0) await chrome.scripting.unregisterContentScripts({ ids: [PAIRING_SCRIPT_ID] });
  if (isBuiltinOrigin(origin)) return;
  const granted = await chrome.permissions.contains({ origins: [`${origin}/*`] });
  if (!granted) return;
  await chrome.scripting.registerContentScripts([
    { id: PAIRING_SCRIPT_ID, matches: [`${origin}/connect/companion*`], js: ["content/pairing.js"], runAt: "document_idle" },
  ]);
}

/**
 * Leaving a custom origin gives its runtime host permission back; returning to a built-in
 * origin also gives back `scripting`. Grants never accumulate.
 */
async function revokeOldOrigin(oldOrigin: string, newOrigin: string): Promise<void> {
  if (!isBuiltinOrigin(oldOrigin)) await chrome.permissions.remove({ origins: [`${oldOrigin}/*`] });
  if (isBuiltinOrigin(newOrigin) && (await chrome.permissions.contains({ permissions: ["scripting"] }))) {
    if (chrome.scripting) {
      const ids = (await chrome.scripting.getRegisteredContentScripts({ ids: [PAIRING_SCRIPT_ID] })).map((s) => s.id);
      if (ids.length > 0) await chrome.scripting.unregisterContentScripts({ ids });
    }
    await chrome.permissions.remove({ permissions: ["scripting"] });
  }
}

chrome.runtime.onInstalled.addListener(() => void ensureAlarm().then(syncPairingScript));
chrome.runtime.onStartup.addListener(() => void ensureAlarm());
void ensureAlarm();

chrome.alarms.onAlarm.addListener((a) => {
  if (a.name === TICK_ALARM) void companion.onTick();
});

chrome.tabs.onRemoved.addListener((tabId) => void companion.onTabClosed(tabId));

function senderOrigin(sender: chrome.runtime.MessageSender): string | null {
  const url = sender.url ?? sender.tab?.url;
  if (!url) return null;
  try {
    return new URL(url).origin;
  } catch {
    return null;
  }
}

chrome.runtime.onMessage.addListener((raw: unknown, sender, sendResponse) => {
  if (sender.id !== chrome.runtime.id || typeof raw !== "object" || raw === null) return false;
  const msg = raw as ContentMessage | PopupMessage;
  const fromTab = sender.tab?.id !== undefined;

  switch (msg.type) {
    case "jingle:track":
      if (sender.tab?.id === undefined) return false;
      void companion.onTrack(sender.tab.id, sender.url ?? sender.tab.url, msg.state).then(() => companion.onTick());
      return false;
    case "jingle:pair": {
      const origin = senderOrigin(sender);
      if (!fromTab || origin === null) return false;
      void companion.pair(msg.token, origin).then(sendResponse);
      return true;
    }
    default:
      break;
  }

  // Popup-only messages: reject anything coming from a web page's content script.
  if (fromTab) return false;
  switch (msg.type) {
    case "popup:status":
      void companion.status().then(sendResponse);
      return true;
    case "popup:settings":
      void (async () => {
        const before = (await companion.settings()).origin;
        const r = await companion.updateSettings(msg.patch as Partial<Settings>);
        if (!("error" in r) && r.origin !== before) await revokeOldOrigin(before, r.origin).catch(() => undefined);
        await syncPairingScript().catch(() => undefined);
        sendResponse(r);
      })();
      return true;
    case "popup:pair":
      void companion.pair(msg.token, null).then(sendResponse);
      return true;
    case "popup:signOut":
      void companion.signOut().then(() => sendResponse({ ok: true }));
      return true;
    case "popup:originChanged":
      void syncPairingScript()
        .catch(() => undefined)
        .then(() => sendResponse({ ok: true }));
      return true;
    default:
      return false;
  }
});
