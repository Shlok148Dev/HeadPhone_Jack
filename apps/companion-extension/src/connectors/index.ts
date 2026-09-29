import type { Connector } from "./common";
import { youtubeMusic } from "./youtube-music";
import { spotify } from "./spotify";
import { appleMusic } from "./apple-music";
import { amazonMusic } from "./amazon-music";

export const CONNECTORS: readonly Connector[] = [youtubeMusic, spotify, appleMusic, amazonMusic];

export function connectorForHost(hostname: string): Connector | undefined {
  return CONNECTORS.find((c) => c.hosts.includes(hostname));
}

export { youtubeMusic, spotify, appleMusic, amazonMusic };
