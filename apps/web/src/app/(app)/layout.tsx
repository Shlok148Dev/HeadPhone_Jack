import type { ReactNode } from "react";
import { AppShell } from "@/components/app/AppShell";

export default function SignedInLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
