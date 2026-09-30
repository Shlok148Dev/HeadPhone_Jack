"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { cn } from "@/components/ds";

const ITEMS = [
  { href: "/settings/connections", label: "Music apps" },
  { href: "/settings/privacy", label: "Privacy" },
];

/** Settings sub-navigation (UX_SPEC §5.14). */
export default function SettingsLayout({ children }: { children: ReactNode }) {
  const path = usePathname();
  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:gap-10">
      <nav aria-label="Settings" className="flex gap-2 overflow-x-auto lg:w-48 lg:shrink-0 lg:flex-col">
        {ITEMS.map((i) => (
          <Link
            key={i.href}
            href={i.href}
            aria-current={path === i.href ? "page" : undefined}
            className={cn(
              "flex min-h-11 items-center whitespace-nowrap rounded-md px-3 text-sm text-text-muted hover:bg-surface-2 hover:text-text",
              path === i.href && "bg-surface-2 text-text",
            )}
          >
            {i.label}
          </Link>
        ))}
      </nav>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
