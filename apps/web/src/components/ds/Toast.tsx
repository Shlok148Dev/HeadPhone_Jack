"use client";

import { AnimatePresence, motion } from "motion/react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useMotionSafe } from "@/lib/motion";
import { IconButton } from "./Button";
import { Alert, Check, Close, Sparkle } from "./icons";
import { cn } from "./utils";

export type ToastTone = "neutral" | "success" | "danger";

export interface ToastInput {
  title: string;
  description?: string;
  tone?: ToastTone;
  /** ms; 0 keeps it until dismissed. Defaults: 4000, or persistent for danger. */
  duration?: number;
}

interface ToastItem extends Required<Omit<ToastInput, "description">> {
  id: number;
  description?: string;
}

interface ToastApi {
  toast: (t: ToastInput) => number;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}

const toneIcon: Record<ToastTone, ReactNode> = {
  neutral: <Sparkle size={18} />,
  success: <Check size={18} />,
  danger: <Alert size={18} />,
};
const toneClass: Record<ToastTone, string> = {
  neutral: "bg-surface-3 text-accent-text",
  success: "bg-success-soft text-success",
  danger: "bg-danger-soft text-danger",
};

function ToastView({ item, onDismiss }: { item: ToastItem; onDismiss: () => void }) {
  const m = useMotionSafe();
  const [paused, setPaused] = useState(false);
  const dismissRef = useRef(onDismiss);
  dismissRef.current = onDismiss;
  useEffect(() => {
    if (!item.duration || paused) return;
    const t = setTimeout(() => dismissRef.current(), item.duration);
    return () => clearTimeout(t);
  }, [item.duration, paused]);
  return (
    <motion.div
      role={item.tone === "danger" ? "alert" : "status"}
      initial={m.reduced ? { opacity: 0 } : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0, transition: m.spring.snappy }}
      exit={{ opacity: 0, transition: { duration: 0.15 } }}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      className="pointer-events-auto flex w-full items-start gap-3 rounded-md border border-border bg-surface-2 p-3 pl-4 shadow-2 sm:w-96"
    >
      <span aria-hidden="true" className={cn("mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-pill", toneClass[item.tone])}>
        {toneIcon[item.tone]}
      </span>
      <div className="min-w-0 flex-1 py-1">
        <p className="text-sm font-semibold text-text">{item.title}</p>
        {item.description && <p className="mt-0.5 text-sm text-text-muted">{item.description}</p>}
      </div>
      <IconButton label="Dismiss" onClick={onDismiss} className="-my-1">
        <Close size={16} />
      </IconButton>
    </motion.div>
  );
}

/** One toast visible at a time with up to 3 queued (UX_SPEC §4.16). Hover/focus pauses the timer. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const next = useRef(1);

  const dismiss = useCallback((id: number) => setItems((xs) => xs.filter((x) => x.id !== id)), []);
  const toast = useCallback((t: ToastInput) => {
    const id = next.current++;
    const tone = t.tone ?? "neutral";
    const duration = t.duration ?? (tone === "danger" ? 0 : 4000);
    setItems((xs) => [...xs, { id, title: t.title, description: t.description, tone, duration }].slice(-4));
    return id;
  }, []);
  const api = useMemo(() => ({ toast, dismiss }), [toast, dismiss]);
  const current = items[0];

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        role="region"
        aria-label="Notifications"
        className="pointer-events-none fixed inset-x-0 bottom-0 flex justify-center p-4 pb-24"
        style={{ zIndex: "var(--z-toast)" }}
      >
        <AnimatePresence mode="wait" initial={false}>
          {current && <ToastView key={current.id} item={current} onDismiss={() => dismiss(current.id)} />}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
