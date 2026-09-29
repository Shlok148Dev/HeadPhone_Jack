import { browserEnv, type Connector } from "../connectors/common";
import type { ContentMessage, TrackState } from "../shared/types";
import { createObserver } from "./observer";

/** Content-script bootstrap shared by the four player scripts. */
export function runPlayer(connector: Connector): void {
  const send = (state: TrackState | null): void => {
    const msg: ContentMessage = { type: "jingle:track", state };
    // Swallow "receiving end does not exist" after the extension is reloaded.
    void chrome.runtime.sendMessage(msg).catch(() => undefined);
  };
  const observer = createObserver({ connector, env: browserEnv, send });
  observer.start();
  window.addEventListener("pagehide", () => observer.stop());
}
