import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CompatibilityMeter } from "./CompatibilityMeter";
import { FeedCard } from "./FeedCard";
import { FilterChips } from "./Chip";
import { GenerativeCover, generateCover } from "./GenerativeCover";
import { PlatformBadge } from "./Badges";
import { SuggestionCard } from "./SuggestionCard";
import type { CardState, FeedCardData, Platform } from "./types";

function card(state: CardState, over: Partial<FeedCardData> = {}): FeedCardData {
  return {
    friend: { id: "u1", username: "aanya", display_name: "Aanya", avatar_url: null },
    state,
    platform: "SPOTIFY",
    recording:
      state === "HIDDEN"
        ? null
        : { id: "r1", title: "Kesariya", artist: "Arijit Singh", artwork_url: null, links: { SPOTIFY: "https://open.spotify.com/x" } },
    observed_at: "2026-09-29T10:15:20Z",
    freshness_label: state === "LIVE" ? "Live on Spotify" : state === "TOP" ? "Top this month" : state === "HIDDEN" ? "Hidden" : "20 min ago on Spotify",
    degraded: false,
    attribution: null,
    ...over,
  };
}

const ROUTE_WORDS = /listenbrainz|last\.fm|lastfm|scrobbl|bridge|companion|\bvia\b|extension/i;

describe("FeedCard", () => {
  it("shows the Live badge when state is LIVE", () => {
    render(<FeedCard card={card("LIVE")} />);
    expect(screen.getByLabelText("Live")).toBeTruthy();
    expect(document.querySelector(".ds-eq-bar")).not.toBeNull();
  });

  it.each<CardState>(["RECENT", "TOP", "HIDDEN"])("never shows Live styling for %s", (state) => {
    // Even a mislabelled or degraded payload must not render Live when state isn't LIVE.
    const { container } = render(<FeedCard card={card(state, { freshness_label: "Live on Spotify", degraded: true })} />);
    expect(screen.queryByLabelText("Live")).toBeNull();
    expect(container.querySelector(".ds-eq-bar")).toBeNull();
    expect(container.innerHTML).not.toMatch(/ring-live|bg-live\b/);
  });

  it("renders freshness_label verbatim and the delayed tag when degraded", () => {
    render(<FeedCard card={card("RECENT", { freshness_label: "2 h ago on YouTube Music", platform: "YOUTUBE_MUSIC", degraded: true })} />);
    expect(screen.getByTestId("freshness-label").textContent).toBe("2 h ago on YouTube Music");
    expect(screen.getByText("delayed")).toBeTruthy();
  });

  it("never shows Live while degraded, even if state is LIVE", () => {
    const { container } = render(<FeedCard card={card("LIVE", { degraded: true })} />);
    expect(screen.queryByLabelText("Live")).toBeNull();
    expect(container.querySelector(".ds-eq-bar")).toBeNull();
  });

  it("shows 'Open Spotify' and 'Data from Spotify' only for SPOTIFY attribution", () => {
    const { unmount } = render(<FeedCard card={card("RECENT", { attribution: "SPOTIFY" })} myPlatform="APPLE_MUSIC" />);
    expect(screen.getByRole("link", { name: "Data from Spotify" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Open Spotify/ }).getAttribute("href")).toBe("https://open.spotify.com/x");
    unmount();
    render(<FeedCard card={card("RECENT")} />);
    expect(screen.queryByText("Data from Spotify")).toBeNull();
    expect(screen.getByRole("link", { name: /Open in my app/ })).toBeTruthy();
  });

  it("unresolved recordings offer a platform search", () => {
    const c = card("RECENT");
    render(<FeedCard card={{ ...c, recording: { ...c.recording!, id: null } }} />);
    expect(screen.getByRole("link", { name: /Search in Spotify/ })).toBeTruthy();
  });

  it("has Open in my app and Send actions and no route words", () => {
    const onSend = vi.fn();
    const { container } = render(<FeedCard card={card("LIVE")} onSend={onSend} />);
    expect(screen.getByRole("link", { name: /Open in my app/ }).getAttribute("href")).toBe("https://open.spotify.com/x");
    fireEvent.click(screen.getByRole("button", { name: /Send/ }));
    expect(onSend).toHaveBeenCalledOnce();
    expect(container.textContent).not.toMatch(ROUTE_WORDS);
  });

  it("HIDDEN shows name and label but no track", () => {
    render(<FeedCard card={card("HIDDEN")} />);
    expect(screen.getByText("Aanya")).toBeTruthy();
    expect(screen.getByText("Hidden")).toBeTruthy();
    expect(screen.queryByText("Kesariya")).toBeNull();
  });
});

describe("PlatformBadge", () => {
  const names: Array<[Platform, string]> = [
    ["SPOTIFY", "Spotify"],
    ["APPLE_MUSIC", "Apple Music"],
    ["YOUTUBE_MUSIC", "YouTube Music"],
    ["AMAZON_MUSIC", "Amazon Music"],
  ];
  it.each(names)("%s renders text only", (p, text) => {
    const { container } = render(<PlatformBadge platform={p} />);
    expect(container.textContent).toBe(text);
    expect(container.querySelector("svg, img, picture, [style*='background-image']")).toBeNull();
  });
  it("renders nothing for UNKNOWN", () => {
    const { container } = render(<PlatformBadge platform="UNKNOWN" />);
    expect(container.innerHTML).toBe("");
  });
});

describe("GenerativeCover", () => {
  it("is deterministic per seed", () => {
    expect(generateCover("rec-kesariya")).toEqual(generateCover("rec-kesariya"));
    const a = render(<GenerativeCover seed="rec-kesariya" />).container.innerHTML.replace(/gc-[\w-]+/g, "ID");
    const b = render(<GenerativeCover seed="rec-kesariya" />).container.innerHTML.replace(/gc-[\w-]+/g, "ID");
    expect(a).toBe(b);
  });
  it("differs across seeds", () => {
    const seeds = Array.from({ length: 12 }, (_, i) => `seed-${i}`);
    const specs = new Set(seeds.map((s) => JSON.stringify(generateCover(s))));
    expect(specs.size).toBe(seeds.length);
    const palettes = new Set(seeds.map((s) => generateCover(s).colors[0]));
    expect(palettes.size).toBeGreaterThan(6);
  });
  it("is never a grey placeholder and never Live-coral", () => {
    for (let i = 0; i < 200; i++) {
      for (const c of generateCover(`s${i}`).colors) {
        const [, hue, sat] = /hsl\((\d+) (\d+)%/.exec(c)!.map(Number);
        expect(sat).toBeGreaterThanOrEqual(50);
        expect(hue! > 20).toBe(true);
      }
    }
  });
});

describe("CompatibilityMeter", () => {
  it("refuses to render a score without a breakdown", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    for (const breakdown of [[], undefined as unknown as []]) {
      const { container, unmount } = render(<CompatibilityMeter score={82} breakdown={breakdown} />);
      expect(container.textContent).not.toMatch(/82/);
      expect(screen.queryByRole("img", { name: /82/ })).toBeNull();
      expect(screen.getByTestId("compat-limited")).toBeTruthy();
      unmount();
    }
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });
  it("renders the score with its breakdown", () => {
    render(<CompatibilityMeter score={82} breakdown={[{ label: "Shared artists", value: 90 }]} />);
    expect(screen.getByRole("img", { name: "Taste match 82 out of 100" })).toBeTruthy();
    expect(screen.getByText("Shared artists")).toBeTruthy();
  });
});

describe("SuggestionCard", () => {
  const person = { id: "u9", name: "Tara", username: "tara" };
  it("shows at most 3 reasons", () => {
    render(<SuggestionCard person={person} reasons={["a", "b", "c", "d"]} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });
  it("is not rendered without reasons", () => {
    const { container } = render(<SuggestionCard person={person} reasons={[]} />);
    expect(container.innerHTML).toBe("");
  });
});

describe("FilterChips", () => {
  const options = [
    { value: "all", label: "All" },
    { value: "live", label: "Live now" },
    { value: "recent", label: "Recent" },
  ];

  it("has radio-group semantics with a single tab stop", () => {
    render(<FilterChips label="Filter" options={options} />);
    const group = screen.getByRole("radiogroup", { name: "Filter" });
    const radios = within(group).getAllByRole("radio");
    expect(radios.map((r) => r.getAttribute("aria-checked"))).toEqual(["true", "false", "false"]);
    expect(radios.map((r) => r.tabIndex)).toEqual([0, -1, -1]);
  });

  it("selects with arrow keys, Home and End, and moves focus", () => {
    const onChange = vi.fn();
    render(<FilterChips label="Filter" options={options} onChange={onChange} />);
    const radios = screen.getAllByRole("radio");
    radios[0]!.focus();
    fireEvent.keyDown(radios[0]!, { key: "ArrowRight" });
    expect(onChange).toHaveBeenLastCalledWith("live");
    expect(screen.getAllByRole("radio")[1]!.getAttribute("aria-checked")).toBe("true");
    expect(document.activeElement).toBe(screen.getAllByRole("radio")[1]);

    fireEvent.keyDown(screen.getAllByRole("radio")[1]!, { key: "End" });
    expect(onChange).toHaveBeenLastCalledWith("recent");
    fireEvent.keyDown(screen.getAllByRole("radio")[2]!, { key: "ArrowRight" });
    expect(onChange).toHaveBeenLastCalledWith("all"); // wraps
    fireEvent.keyDown(screen.getAllByRole("radio")[0]!, { key: "ArrowLeft" });
    expect(onChange).toHaveBeenLastCalledWith("recent");
    fireEvent.keyDown(screen.getAllByRole("radio")[2]!, { key: "Home" });
    expect(onChange).toHaveBeenLastCalledWith("all");
  });
});
