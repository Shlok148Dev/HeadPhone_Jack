"use client";

import { EqualiserBars } from "./Badges";
import { Blip } from "./Blip";
import { Button } from "./Button";
import { Artwork } from "./GenerativeCover";
import { Send } from "./icons";
import type { CardState, Platform } from "./types";
import { cn } from "./utils";

export interface NowPlayingTrack {
  id: string | null;
  title: string;
  artist: string;
  artwork_url: string | null;
  platform: Platform;
  state: CardState;
  /** Server-built label, verbatim. */
  freshness_label: string;
}

export interface NowPlayingBarProps {
  track: NowPlayingTrack | null;
  onSend?: () => void;
  /** "fixed" pins to the viewport bottom; "static" is for previews. */
  position?: "fixed" | "static";
  className?: string;
}

/** Bottom bar with my own now-playing card and a quick Send. */
export function NowPlayingBar({ track, onSend, position = "fixed", className }: NowPlayingBarProps) {
  const isLive = track?.state === "LIVE";
  return (
    <aside
      aria-label="Now playing"
      className={cn(
        "border border-border bg-surface-glass backdrop-blur-glass",
        position === "fixed" ? "fixed inset-x-0 bottom-0 border-x-0 border-b-0 pb-[env(safe-area-inset-bottom)]" : "rounded-lg",
        className,
      )}
      style={position === "fixed" ? { zIndex: "var(--z-now-playing)" } : undefined}
    >
      <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-2.5">
        {track ? (
          <>
            <div className={cn("w-12 shrink-0 rounded-sm", isLive && "ring-2 ring-live ring-offset-2 ring-offset-surface-1")}>
              <Artwork url={track.artwork_url} seed={track.id ?? `${track.title}|${track.artist}`} alt="" rounded="sm" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 truncate text-sm font-semibold text-text">
                {isLive && <EqualiserBars decorative size={12} />}
                <span className="truncate">{track.title}</span>
              </p>
              <p className="truncate text-xs text-text-muted">
                {track.artist} <span aria-hidden="true">·</span>{" "}
                <span className={cn("font-mono", isLive ? "text-live-text" : "text-text-muted")}>{track.freshness_label}</span>
              </p>
            </div>
            <Button onClick={onSend} leadingIcon={<Send size={16} />}>
              Send
            </Button>
          </>
        ) : (
          <>
            <Blip pose="sleepy" size={44} decorative />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-text">Nothing playing</p>
              <p className="text-xs text-text-muted">Play something on any app and it shows up here.</p>
            </div>
            <Button disabled leadingIcon={<Send size={16} />}>
              Send
            </Button>
          </>
        )}
      </div>
    </aside>
  );
}
