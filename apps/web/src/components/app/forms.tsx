"use client";

import { useId, useState, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { IconButton, Icons, cn } from "@/components/ds";

const fieldBase =
  "h-11 w-full rounded-md border bg-surface-2 px-3 text-sm text-text placeholder:text-text-subtle transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)] disabled:opacity-60";

interface FieldShellProps {
  label: string;
  hint?: ReactNode;
  error?: string;
  children: (ids: { inputId: string; describedBy?: string }) => ReactNode;
}

function FieldShell({ label, hint, error, children }: FieldShellProps) {
  const inputId = useId();
  const hintId = `${inputId}-hint`;
  const errId = `${inputId}-err`;
  const describedBy = [hint ? hintId : null, error ? errId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="text-sm font-medium text-text">
        {label}
      </label>
      {children({ inputId, describedBy })}
      {hint && !error && (
        <p id={hintId} className="text-xs text-text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errId} role="alert" className="text-xs font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: ReactNode; error?: string };

export function TextField({ label, hint, error, className, type = "text", ...rest }: TextFieldProps) {
  const [shown, setShown] = useState(false);
  const isPassword = type === "password";
  return (
    <FieldShell label={label} hint={hint} error={error}>
      {({ inputId, describedBy }) => (
        <div className="relative">
          <input
            id={inputId}
            type={isPassword && shown ? "text" : type}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            className={cn(fieldBase, error ? "border-danger" : "border-border", isPassword && "pr-12", className)}
            {...rest}
          />
          {isPassword && (
            <IconButton
              type="button"
              variant="ghost"
              label={shown ? "Hide password" : "Show password"}
              className="absolute right-0 top-0"
              onClick={() => setShown((s) => !s)}
            >
              <Icons.Eye size={18} />
            </IconButton>
          )}
        </div>
      )}
    </FieldShell>
  );
}

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  hint?: ReactNode;
  error?: string;
  options: { value: string; label: string }[];
  placeholder?: string;
};

export function SelectField({ label, hint, error, options, placeholder, className, ...rest }: SelectFieldProps) {
  return (
    <FieldShell label={label} hint={hint} error={error}>
      {({ inputId, describedBy }) => (
        <select
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(fieldBase, error ? "border-danger" : "border-border", className)}
          {...rest}
        >
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )}
    </FieldShell>
  );
}

export function FormAlert({ children }: { children: ReactNode }) {
  return (
    <div role="alert" className="rounded-md border border-danger/40 bg-danger-soft px-3 py-2 text-sm text-text">
      {children}
    </div>
  );
}

/** Birth-year options for the 18+ gate (UX_SPEC §5.2): current year − 13 … − 100. */
export function birthYearOptions(now = new Date()) {
  const y = now.getFullYear();
  return Array.from({ length: 88 }, (_, i) => {
    const v = String(y - 13 - i);
    return { value: v, label: v };
  });
}

/** Map a DRF field-error payload (`details`) to the first message per field. */
export function fieldErrors(details: Record<string, unknown>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(details)) {
    const first = Array.isArray(v) ? v[0] : v;
    if (typeof first === "string") out[k] = first;
  }
  return out;
}
