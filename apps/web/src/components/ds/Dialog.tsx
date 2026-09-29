"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { ease, spring, useMotionSafe } from "@/lib/motion";
import { IconButton } from "./Button";
import { Close } from "./icons";
import { cn } from "./utils";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: ReactNode;
  /** "dialog" is centred (max 560); "sheet" is a bottom sheet under 768 px and a right panel above. */
  variant?: "dialog" | "sheet";
  footer?: ReactNode;
  className?: string;
}

/** Modal dialog / bottom sheet. Traps focus, closes on Esc and scrim click, restores focus. */
export function Dialog({ open, onClose, title, description, children, variant = "dialog", footer, className }: DialogProps) {
  const [mounted, setMounted] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descId = useId();
  const m = useMotionSafe();
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const [wide, setWide] = useState(false);

  useEffect(() => {
    setMounted(true);
    const mq = window.matchMedia?.("(min-width: 768px)");
    if (!mq) return;
    setWide(mq.matches);
    const on = (e: MediaQueryListEvent) => setWide(e.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const focusFirst = () => {
      const el = panel.current;
      if (!el) return;
      const first = el.querySelector<HTMLElement>("[data-autofocus]") ?? el.querySelector<HTMLElement>(FOCUSABLE);
      (first ?? el).focus();
    };
    const raf = requestAnimationFrame(focusFirst);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (e.key !== "Tab" || !panel.current) return;
      const nodes = Array.from(panel.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (nodes.length === 0) {
        e.preventDefault();
        return;
      }
      const first = nodes[0]!;
      const last = nodes[nodes.length - 1]!;
      const active = document.activeElement;
      if (e.shiftKey && (active === first || !panel.current.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || !panel.current.contains(active))) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey, true);
    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("keydown", onKey, true);
      document.body.style.overflow = prevOverflow;
      previouslyFocused?.focus?.();
    };
  }, [open]);

  if (!mounted) return null;

  const isSheet = variant === "sheet";
  // Sheet: bottom sheet under 768 px, right-side panel (420 px) from 768 px.
  const sideSheet = isSheet && wide;
  const hiddenPose = m.reduced
    ? { opacity: 0 }
    : sideSheet
      ? { x: "100%" }
      : isSheet
        ? { y: "100%" }
        : { opacity: 0, scale: 0.96 };
  const shownPose = m.reduced ? { opacity: 1 } : sideSheet ? { x: 0 } : isSheet ? { y: 0 } : { opacity: 1, scale: 1 };
  const exitTransition = m.reduced ? { duration: 0.15 } : { duration: 0.18, ease: ease.exit };

  return createPortal(
    <AnimatePresence>
      {open && (
        <div
          className={cn(
            "fixed inset-0 flex",
            sideSheet ? "items-stretch justify-end" : isSheet ? "items-end justify-center" : "items-center justify-center",
          )}
          style={{ zIndex: isSheet ? "var(--z-sheet)" : "var(--z-dialog)" }}
        >
          <motion.div
            className="absolute inset-0 bg-scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { duration: m.reduced ? 0.15 : 0.2 } }}
            exit={{ opacity: 0, transition: exitTransition }}
            onClick={onClose}
            aria-hidden="true"
          />
          <motion.div
            ref={panel}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={description ? descId : undefined}
            tabIndex={-1}
            initial={hiddenPose}
            animate={{ ...shownPose, transition: m.reduced ? { duration: 0.15 } : spring.gentle }}
            exit={{ ...hiddenPose, transition: exitTransition }}
            className={cn(
              "relative flex w-full flex-col gap-4 overflow-y-auto border border-border bg-surface-1 p-6 shadow-2 outline-none",
              sideSheet
                ? "h-full max-w-[420px] border-y-0 border-r-0"
                : isSheet
                  ? "max-h-[92vh] rounded-t-lg border-b-0"
                  : "m-4 max-h-[90vh] max-w-[560px] rounded-lg",
              className,
            )}
          >
            {isSheet && !sideSheet && <span aria-hidden="true" className="mx-auto -mt-2 h-1 w-9 rounded-pill bg-border-strong" />}
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id={titleId} className="font-display text-xl font-semibold text-text">
                  {title}
                </h2>
                {description && (
                  <p id={descId} className="mt-1 text-sm text-text-muted">
                    {description}
                  </p>
                )}
              </div>
              <IconButton label="Close" onClick={onClose} className="-mr-2 -mt-2">
                <Close />
              </IconButton>
            </div>
            {children}
            {footer && <div className="flex flex-wrap justify-end gap-2">{footer}</div>}
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

/** Alias: bottom sheet. */
export function Sheet(props: Omit<DialogProps, "variant">) {
  return <Dialog {...props} variant="sheet" />;
}
