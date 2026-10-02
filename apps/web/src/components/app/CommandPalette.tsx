"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Artwork, Avatar, Icons, cn } from "@/components/ds";
import { api } from "@/lib/api";
import { useCircles } from "@/lib/circles";
import { useOpenSend } from "@/lib/send";
import { useSongSearch } from "@/lib/sends";
import type { Person } from "@/lib/social";

interface Item {
  id: string;
  group: "Go to" | "People" | "Songs" | "Circles" | "Actions";
  label: string;
  hint?: string;
  icon: ReactNode;
  run: () => void;
}

const PAGES: [string, string][] = [
  ["Home", "/home"],
  ["Friends", "/friends"],
  ["Circles", "/circles"],
  ["Blends", "/blends"],
  ["Rituals", "/rituals"],
  ["Inbox", "/inbox"],
  ["Notifications", "/notifications"],
  ["Settings", "/settings/connections"],
];

/** ⌘K / Ctrl+K: people, songs, circles and actions from anywhere (keyboard-first, D-SHELL-03). */
export function CommandPalette({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const openSend = useOpenSend();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const needle = q.trim().toLowerCase();
  const people = useQuery({
    queryKey: ["palette-people", needle],
    queryFn: () => api<Person[]>(`/users/search?q=${encodeURIComponent(needle)}`),
    enabled: needle.length >= 2,
    staleTime: 30_000,
  });
  const songs = useSongSearch(needle);
  const circles = useCircles();

  useEffect(() => input.current?.focus(), []);

  const go = (href: string) => () => {
    onClose();
    router.push(href);
  };
  const items: Item[] = useMemo(() => {
    const out: Item[] = [];
    for (const [label, href] of PAGES)
      if (!needle || label.toLowerCase().includes(needle)) out.push({ id: `p-${href}`, group: "Go to", label, icon: <Icons.Home size={16} />, run: go(href) });
    if (!needle || "send a song".includes(needle))
      out.push({ id: "a-send", group: "Actions", label: "Send a song", icon: <Icons.Send size={16} />, run: () => { onClose(); openSend(); } });
    if (!needle || "listen together".includes(needle))
      out.push({ id: "a-room", group: "Actions", label: "Listen together", hint: "Start a room", icon: <Icons.Blend size={16} />, run: go("/blends") });
    for (const p of (people.data ?? []).slice(0, 5))
      out.push({ id: `u-${p.id}`, group: "People", label: p.display_name, hint: `@${p.username}`, icon: <Avatar name={p.display_name} url={p.avatar_url} seed={p.id} size={22} decorative />, run: go(`/u/${p.username}`) });
    for (const c of (circles.data ?? []).filter((c) => !needle || c.name.toLowerCase().includes(needle)).slice(0, 5))
      out.push({ id: `c-${c.id}`, group: "Circles", label: c.name, hint: `${c.member_count} members`, icon: <Icons.Circles size={16} />, run: go(`/circles/${c.id}`) });
    for (const s of (songs.data ?? []).slice(0, 6))
      out.push({
        id: `s-${s.artist}|${s.title}`,
        group: "Songs",
        label: s.title,
        hint: s.artist,
        icon: (
          <span className="block h-7 w-7 overflow-hidden rounded-[4px]">
            <Artwork url={s.artwork_small ?? s.artwork_url} seed={`${s.artist}|${s.title}`} alt="" rounded="none" />
          </span>
        ),
        run: () => { onClose(); openSend({ song: s }); },
      });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [needle, people.data, songs.data, circles.data]);

  useEffect(() => setActive(0), [needle]);

  function onKey(e: React.KeyboardEvent) {
    if (e.key === "Escape") onClose();
    else if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(items.length - 1, a + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    else if (e.key === "Enter") { e.preventDefault(); items[active]?.run(); }
  }

  let lastGroup = "";
  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center bg-scrim px-4 pt-[12vh]" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Search and commands"
        className="w-full max-w-xl overflow-hidden rounded-[20px] border border-border bg-[var(--surface-glass)] shadow-2 backdrop-blur-xl"
        onMouseDown={(e) => e.stopPropagation()}
        onKeyDown={onKey}
      >
        <div className="flex items-center gap-3 border-b border-border px-4">
          <Icons.Sparkle size={18} />
          <input
            ref={input}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            role="combobox"
            aria-expanded="true"
            aria-controls="palette-list"
            aria-activedescendant={items[active] ? `pi-${items[active].id}` : undefined}
            aria-label="Search people, songs, circles and actions"
            placeholder="Search people, songs, circles…"
            className="h-14 flex-1 bg-transparent text-[15px] outline-none placeholder:text-text-subtle"
          />
          <kbd className="rounded-sm border border-border px-1.5 font-mono text-[11px] text-text-muted">Esc</kbd>
        </div>
        <ul id="palette-list" role="listbox" aria-label="Results" className="max-h-[56vh] overflow-y-auto p-2">
          {items.map((it, i) => {
            const head = it.group !== lastGroup ? it.group : null;
            lastGroup = it.group;
            return (
              <li key={it.id} role="presentation">
                {head && <p className="px-3 pb-1 pt-3 font-mono text-[11px] uppercase tracking-wider text-text-muted">{head}</p>}
                <div
                  id={`pi-${it.id}`}
                  role="option"
                  aria-selected={i === active}
                  onMouseEnter={() => setActive(i)}
                  onClick={it.run}
                  className={cn("flex min-h-11 cursor-pointer items-center gap-3 rounded-md px-3 py-1.5 text-sm", i === active && "bg-surface-3")}
                >
                  <span className="flex w-7 shrink-0 justify-center text-text-muted">{it.icon}</span>
                  <span className="min-w-0 flex-1 truncate">{it.label}</span>
                  {it.hint && <span className="truncate text-xs text-text-muted">{it.hint}</span>}
                </div>
              </li>
            );
          })}
          {!items.length && <li className="px-3 py-6 text-center text-sm text-text-muted">Nothing matches &ldquo;{q}&rdquo;.</li>}
        </ul>
      </div>
    </div>
  );
}
