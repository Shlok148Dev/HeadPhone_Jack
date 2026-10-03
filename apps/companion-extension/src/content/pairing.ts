import type { ContentMessage, PairResult } from "../shared/types";
import { VERSION } from "../shared/version";
import { installPairingListener } from "./pairing-listener";

// Runs on every page of the Jingle origin (D-EXT-02): the signed-in app connects us on sight.
// Guard against double install (manifest script + post-install injection).
const w = window as Window & { __jinglePairing?: boolean };
if (!w.__jinglePairing) {
  w.__jinglePairing = true;
  installPairingListener({
    win: window,
    version: VERSION,
    status: async () => {
      const msg: ContentMessage = { type: "jingle:status" };
      const res = (await chrome.runtime.sendMessage(msg)) as
        { paired: boolean } | undefined;
      return { paired: !!res?.paired };
    },
    pair: async (token) => {
      const msg: ContentMessage = { type: "jingle:pair", token };
      const res = (await chrome.runtime.sendMessage(msg)) as
        PairResult | undefined;
      return res ?? { ok: false, error: "extension_error" };
    },
  });
}
