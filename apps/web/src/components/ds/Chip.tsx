"use client";

import { useId, useRef, useState, type ButtonHTMLAttributes, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "./utils";

const chipBase =
  "ds-focus inline-flex min-h-11 items-center gap-1.5 rounded-pill px-4 text-sm font-medium whitespace-nowrap " +
  "motion-safe:transition-[transform,background-color,color] motion-safe:duration-150 motion-safe:active:scale-[0.96]";
const chipOff = "bg-surface-2 text-text-muted border border-border hover:text-text hover:bg-surface-3";
// Selected is a solid, inverted chip: the brand gradient is kept for the three moments per screen.
const chipOn = "bg-text text-bg border border-transparent";

export interface ChipProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onChange"> {
  selected?: boolean;
  onSelectedChange?: (selected: boolean) => void;
  icon?: ReactNode;
}

/** Toggle chip (aria-pressed). For single-choice filters use <FilterChips>. */
export function Chip({ selected = false, onSelectedChange, icon, className, children, onClick, ...rest }: ChipProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={cn(chipBase, selected ? chipOn : chipOff, className)}
      onClick={(e) => {
        onClick?.(e);
        onSelectedChange?.(!selected);
      }}
      {...rest}
    >
      {icon}
      {children}
    </button>
  );
}

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterChipsProps {
  options: FilterOption[];
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  /** Accessible name for the group. */
  label: string;
  className?: string;
}

/** Single-select chip row with radio-group semantics: roving tabindex, arrows/Home/End select. */
export function FilterChips({ options, value, defaultValue, onChange, label, className }: FilterChipsProps) {
  const [inner, setInner] = useState(defaultValue ?? options[0]?.value ?? "");
  const current = value ?? inner;
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const groupId = useId();

  const select = (i: number) => {
    const opt = options[i];
    if (!opt) return;
    if (value === undefined) setInner(opt.value);
    onChange?.(opt.value);
    refs.current[i]?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    const n = options.length;
    let next: number | null = null;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (i + 1) % n;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = (i - 1 + n) % n;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = n - 1;
    if (next !== null) {
      e.preventDefault();
      select(next);
    }
  };

  const selectedIndex = Math.max(0, options.findIndex((o) => o.value === current));

  return (
    // Phones: one row that scrolls sideways (padding keeps focus rings unclipped); wider: wraps.
    <div role="radiogroup" aria-label={label} className={cn("ds-scrollbar-none -mx-1 flex gap-2 overflow-x-auto px-1 py-1 md:flex-wrap md:overflow-visible [&>button]:shrink-0", className)}>
      {options.map((opt, i) => {
        const checked = opt.value === current;
        return (
          <button
            key={opt.value}
            id={`${groupId}-${opt.value}`}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={checked}
            tabIndex={i === selectedIndex ? 0 : -1}
            className={cn(chipBase, checked ? chipOn : chipOff)}
            onClick={() => select(i)}
            onKeyDown={(e) => onKeyDown(e, i)}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
