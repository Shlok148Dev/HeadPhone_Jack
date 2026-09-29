"use client";

import { forwardRef, type AnchorHTMLAttributes, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "./utils";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "md" | "lg";

const base =
  "ds-focus relative inline-flex select-none items-center justify-center gap-2 font-semibold whitespace-nowrap rounded-pill " +
  "min-h-11 min-w-11 motion-safe:transition-[transform,background-color,color,box-shadow,opacity] motion-safe:duration-150 " +
  "motion-safe:active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50 aria-disabled:cursor-not-allowed aria-disabled:opacity-50";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-gradient-brand text-on-brand shadow-1 hover:bg-[position:100%_50%]",
  secondary: "bg-surface-2 text-text border border-border hover:bg-surface-3 hover:border-border-strong",
  ghost: "bg-transparent text-text hover:bg-surface-2",
  danger: "bg-danger-bg text-on-danger hover:brightness-110",
};

const sizes: Record<ButtonSize, string> = {
  md: "h-11 px-5 text-sm",
  lg: "h-13 px-6 text-base",
};

export function buttonClasses(variant: ButtonVariant = "primary", size: ButtonSize = "md", className?: string) {
  return cn(base, variants[variant], sizes[size], className);
}

function Spinner() {
  return (
    <svg className="ds-spin" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.3" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  /** Label announced while loading (defaults to children). */
  loadingLabel?: string;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading = false, loadingLabel, leadingIcon, trailingIcon, className, children, disabled, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      className={buttonClasses(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Spinner /> : leadingIcon}
      <span>{loading && loadingLabel ? loadingLabel : children}</span>
      {!loading && trailingIcon}
    </button>
  );
});

export interface ButtonLinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leadingIcon?: ReactNode;
}

/** A link styled as a button (e.g. "Open in my app"). */
export function ButtonLink({ variant = "secondary", size = "md", leadingIcon, className, children, ...rest }: ButtonLinkProps) {
  return (
    <a className={buttonClasses(variant, size, className)} {...rest}>
      {leadingIcon}
      <span>{children}</span>
    </a>
  );
}

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Required accessible name. */
  label: string;
  variant?: Exclude<ButtonVariant, "danger">;
  children: ReactNode;
}

/** 44×44 icon-only button. */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, variant = "ghost", className, children, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      aria-label={label}
      title={label}
      className={cn(base, variants[variant], "h-11 w-11 p-0", className)}
      {...rest}
    >
      {children}
    </button>
  );
});
