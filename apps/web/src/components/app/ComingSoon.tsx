import { Blip } from "@/components/ds";

/** Honest placeholder for sections scheduled in later sprints (no dead links in the nav). */
export function ComingSoon({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-3xl font-semibold tracking-tight">{title}</h1>
      <div className="flex flex-col items-center gap-3 rounded-lg border border-border bg-surface-1 px-6 py-12 text-center">
        <Blip pose="sleepy" size={96} decorative />
        <p className="font-display text-xl font-semibold">Coming soon</p>
        <p className="max-w-md text-sm text-text-muted">{body}</p>
      </div>
    </div>
  );
}
