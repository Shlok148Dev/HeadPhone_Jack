"use client";

import type { ReactNode } from "react";
import { Blip, type BlipPose } from "./Blip";
import { Button } from "./Button";
import { Refresh } from "./icons";
import { cn } from "./utils";

export interface SkeletonProps {
  className?: string;
  rounded?: "sm" | "md" | "lg" | "pill";
}

/** Shimmering block. Static under reduced motion. Never grey artwork: skeletons are loading-only. */
export function Skeleton({ className, rounded = "sm" }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "ds-shimmer relative block overflow-hidden bg-skeleton",
        rounded === "sm" && "rounded-sm",
        rounded === "md" && "rounded-md",
        rounded === "lg" && "rounded-lg",
        rounded === "pill" && "rounded-pill",
        className,
      )}
    />
  );
}

/** Matches FeedCard's shape so nothing jumps when content arrives. */
export function FeedCardSkeleton({ className }: { className?: string }) {
  return (
    <div role="status" aria-busy="true" className={cn("flex flex-col gap-2 p-2", className)}>
      <span className="ds-visually-hidden">Loading</span>
      <Skeleton rounded="md" className="aspect-square w-full" />
      <div className="flex items-center gap-2 pt-1">
        <Skeleton rounded="pill" className="h-5 w-5 shrink-0" />
        <Skeleton className="h-3 w-[70%]" />
      </div>
      <Skeleton className="h-4 w-[90%]" />
      <Skeleton className="h-3 w-[50%]" />
      <Skeleton className="mt-1 h-3 w-[40%]" />
      <div className="flex gap-1">
        <Skeleton rounded="pill" className="h-11 flex-1" />
        <Skeleton rounded="pill" className="h-11 w-11" />
      </div>
    </div>
  );
}

export interface EmptyStateProps {
  title: string;
  description?: string;
  pose?: Extract<BlipPose, "wave" | "sleepy" | "idle">;
  /** One clear action. */
  action?: { label: string; onClick: () => void };
  className?: string;
}

export function EmptyState({ title, description, pose = "wave", action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center gap-3 px-6 py-10 text-center", className)}>
      <Blip pose={pose} size={96} decorative />
      <h3 className="font-display text-xl font-semibold text-text">{title}</h3>
      {description && <p className="max-w-sm text-sm text-text-muted">{description}</p>}
      {action && (
        <Button className="mt-2" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}

export interface ErrorStateProps {
  title?: string;
  /** Plain words: what happened and what to do. */
  message: ReactNode;
  onRetry?: () => void;
  retrying?: boolean;
  className?: string;
}

export function ErrorState({ title = "Something went wrong", message, onRetry, retrying, className }: ErrorStateProps) {
  return (
    <div role="alert" className={cn("flex flex-col items-center gap-3 px-6 py-10 text-center", className)}>
      <span aria-hidden="true" className="inline-flex h-12 w-12 items-center justify-center rounded-pill bg-danger-soft text-danger">
        <Refresh size={22} />
      </span>
      <h3 className="font-display text-xl font-semibold text-text">{title}</h3>
      <p className="max-w-sm text-sm text-text-muted">{message}</p>
      {onRetry && (
        <Button variant="secondary" className="mt-2" onClick={onRetry} loading={retrying} leadingIcon={<Refresh size={16} />}>
          Try again
        </Button>
      )}
    </div>
  );
}
