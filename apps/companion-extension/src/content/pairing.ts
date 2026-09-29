import type { ContentMessage, PairResult } from "../shared/types";
import { VERSION } from "../shared/version";
import { installPairingListener } from "./pairing-listener";

// Runs only on `{jingle origin}/connect/companion*`.
installPairingListener({
  win: window,
  version: VERSION,
  pair: async (token) => {
    const msg: ContentMessage = { type: "jingle:pair", token };
    const res = (await chrome.runtime.sendMessage(msg)) as PairResult | undefined;
    return res ?? { ok: false, error: "extension_error" };
  },
});
