"use client";

import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { motion } from "motion/react";
import { useMotionSafe } from "@/lib/motion";
import { cn } from "./utils";

export interface TabItem {
  id: string;
  label: string;
  content: ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  value?: string;
  defaultValue?: string;
  onChange?: (id: string) => void;
  label: string;
  className?: string;
}

/** WAI-ARIA tabs with automatic activation and roving focus. */
export function Tabs({ items, value, defaultValue, onChange, label, className }: TabsProps) {
  const [inner, setInner] = useState(defaultValue ?? items[0]?.id ?? "");
  const current = value ?? inner;
  const base = useId();
  const m = useMotionSafe();
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  const activate = (i: number) => {
    const t = items[i];
    if (!t) return;
    if (value === undefined) setInner(t.id);
    onChange?.(t.id);
    refs.current[i]?.focus();
  };

  const onKeyDown = (e: KeyboardEvent, i: number) => {
    const n = items.length;
    const map: Record<string, number> = { ArrowRight: (i + 1) % n, ArrowLeft: (i - 1 + n) % n, Home: 0, End: n - 1 };
    const next = map[e.key];
    if (next !== undefined) {
      e.preventDefault();
      activate(next);
    }
  };

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <div role="tablist" aria-label={label} className="ds-scrollbar-none flex max-w-full gap-2 overflow-x-auto border-b border-border px-1 pt-1">
        {items.map((t, i) => {
          const selected = t.id === current;
          return (
            <button
              key={t.id}
              ref={(el) => {
                refs.current[i] = el;
              }}
              id={`${base}-tab-${t.id}`}
              role="tab"
              type="button"
              aria-selected={selected}
              aria-controls={`${base}-panel-${t.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => activate(i)}
              onKeyDown={(e) => onKeyDown(e, i)}
              className={cn(
                "ds-focus relative h-11 shrink-0 rounded-sm px-3 text-[15px] font-semibold motion-safe:transition-colors",
                selected ? "text-text" : "text-text-muted hover:text-text",
              )}
            >
              {t.label}
              {selected && (
                <motion.span
                  layoutId={`${base}-underline`}
                  transition={m.spring.snappy}
                  aria-hidden="true"
                  className="absolute inset-x-2 bottom-0 h-[3px] rounded-pill bg-gradient-brand"
                />
              )}
            </button>
          );
        })}
      </div>
      {items.map((t) => (
        <div
          key={t.id}
          role="tabpanel"
          id={`${base}-panel-${t.id}`}
          aria-labelledby={`${base}-tab-${t.id}`}
          hidden={t.id !== current}
          tabIndex={0}
          className="ds-focus rounded-md"
        >
          {t.id === current && t.content}
        </div>
      ))}
    </div>
  );
}
