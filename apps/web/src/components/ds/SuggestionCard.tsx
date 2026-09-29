"use client";

import { Avatar } from "./Avatar";
import { Button, IconButton } from "./Button";
import { Close } from "./icons";
import { cn } from "./utils";

export interface SuggestionCardProps {
  person: { id: string; name: string; username: string; avatar_url?: string | null };
  /** Plain-language reasons; at most 3 are shown. */
  reasons: string[];
  actionLabel?: string;
  onAction?: () => void;
  onDismiss?: () => void;
  className?: string;
}

/** A friend suggestion with up to three honest reasons. */
export function SuggestionCard({ person, reasons, actionLabel = "Add", onAction, onDismiss, className }: SuggestionCardProps) {
  const shown = reasons.filter(Boolean).slice(0, 3);
  // No unexplained suggestions: without a reason the card is not rendered.
  if (shown.length === 0) return null;
  return (
    <article aria-label={`Suggestion: ${person.name}`} className={cn("flex flex-col gap-4 rounded-lg border border-border bg-surface-1 p-4", className)}>
      <div className="flex items-center gap-3">
        <Avatar name={person.name} url={person.avatar_url} seed={person.id} size={48} decorative />
        <div className="min-w-0">
          <p className="truncate font-semibold text-text">{person.name}</p>
          <p className="truncate font-mono text-xs text-text-muted">@{person.username}</p>
        </div>
      </div>
      {shown.length > 0 && (
        <ul className="flex flex-col gap-1.5" aria-label="Why we suggest them">
          {shown.map((r) => (
            <li key={r} className="flex gap-2 text-sm text-text-muted">
              <span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 rounded-pill bg-gradient-brand" />
              <span>{r}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <Button variant="secondary" onClick={onAction} className="flex-1">
          {actionLabel}
        </Button>
        {onDismiss && (
          <IconButton label={`Dismiss ${person.name}`} onClick={onDismiss}>
            <Close />
          </IconButton>
        )}
      </div>
    </article>
  );
}
