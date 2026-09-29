"use client";

import { Children, useCallback, useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { IconButton } from "./Button";
import { ChevronLeft, ChevronRight } from "./icons";
import { cn } from "./utils";

export interface ShelfProps {
  title: string;
  /** Live shelf only: prefixes the title with the coral dot. */
  live?: boolean;
  /** Optional count shown after the title (mono). */
  count?: number;
  /** Width of each item, CSS length (UX_SPEC §3 shelf card widths). */
  itemWidth?: string;
  children: ReactNode;
  className?: string;
}

/**
 * Horizontal scroll-snap row with prev/next buttons (UX_SPEC §4.5).
 * Keyboard: roving tabindex — one item is in the tab order; ←/→ move between items and scroll
 * them into view, Home/End jump to the ends, Tab leaves the shelf. The arrow buttons are a
 * pointer affordance (tabindex -1) because the keys already cover keyboard users.
 */
export function Shelf({ title, live = false, count, itemWidth = "clamp(136px, 38vw, 200px)", children, className }: ShelfProps) {
  const track = useRef<HTMLUListElement>(null);
  const headingId = useId();
  const trackId = useId();
  const items = Children.toArray(children);
  const [active, setActive] = useState(0);
  const [canPrev, setCanPrev] = useState(false);
  const [canNext, setCanNext] = useState(false);

  const update = useCallback(() => {
    const el = track.current;
    if (!el) return;
    setCanPrev(el.scrollLeft > 4);
    setCanNext(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
  }, []);

  useEffect(() => {
    update();
    const el = track.current;
    if (!el) return;
    el.addEventListener("scroll", update, { passive: true });
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(update) : null;
    ro?.observe(el);
    return () => {
      el.removeEventListener("scroll", update);
      ro?.disconnect();
    };
  }, [update]);

  const reduce = () => typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  const page = (dir: 1 | -1) => {
    const el = track.current;
    if (!el) return;
    const first = el.querySelector("li");
    const step = first ? first.getBoundingClientRect().width + 16 : el.clientWidth * 0.9;
    const visible = Math.max(1, Math.floor(el.clientWidth / step));
    el.scrollBy({ left: dir * visible * step, behavior: reduce() ? "auto" : "smooth" });
  };

  const focusItem = (i: number) => {
    const li = track.current?.children[i] as HTMLElement | undefined;
    if (!li) return;
    setActive(i);
    li.focus({ preventScroll: true });
    li.scrollIntoView({ behavior: reduce() ? "auto" : "smooth", inline: "nearest", block: "nearest" });
  };

  const onKeyDown = (e: KeyboardEvent<HTMLUListElement>) => {
    const target = e.target as HTMLElement;
    if (target.parentElement !== track.current) return; // let inner controls handle their own keys
    const n = items.length;
    const map: Record<string, number> = { ArrowRight: Math.min(n - 1, active + 1), ArrowLeft: Math.max(0, active - 1), Home: 0, End: n - 1 };
    const next = map[e.key];
    if (next !== undefined) {
      e.preventDefault();
      focusItem(next);
    }
  };

  const arrowClass = (enabled: boolean) => cn("hidden [@media(pointer:fine)]:inline-flex", !enabled && "pointer-events-none opacity-0");

  return (
    <section aria-labelledby={headingId} className={cn("flex flex-col gap-3", className)}>
      <div className="flex h-10 items-center justify-between gap-2">
        <h2 id={headingId} className="flex items-center gap-2 font-display text-xl font-semibold text-text lg:text-[22px]">
          {live && <span aria-hidden="true" className="h-2 w-2 rounded-pill bg-live" />}
          {title}
          {count !== undefined && <span className="font-mono text-[13px] font-medium text-text-muted">{count}</span>}
        </h2>
        <div className="flex gap-1">
          <IconButton
            label={`Scroll ${title} left`}
            tabIndex={-1}
            aria-controls={trackId}
            aria-disabled={!canPrev}
            onClick={() => canPrev && page(-1)}
            className={arrowClass(canPrev)}
          >
            <ChevronLeft />
          </IconButton>
          <IconButton
            label={`Scroll ${title} right`}
            tabIndex={-1}
            aria-controls={trackId}
            aria-disabled={!canNext}
            onClick={() => canNext && page(1)}
            className={arrowClass(canNext)}
          >
            <ChevronRight />
          </IconButton>
        </div>
      </div>
      <ul
        id={trackId}
        ref={track}
        role="list"
        aria-label={title}
        onKeyDown={onKeyDown}
        className="ds-scrollbar-none -mx-2 flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-px-2 px-2 py-2"
      >
        {items.map((child, i) => (
          <li
            key={i}
            role="listitem"
            tabIndex={i === active ? 0 : -1}
            onFocus={(e) => {
              if (e.target === e.currentTarget) setActive(i);
            }}
            className="ds-focus shrink-0 snap-start rounded-lg"
            style={{ width: itemWidth }}
          >
            {child}
          </li>
        ))}
      </ul>
    </section>
  );
}
