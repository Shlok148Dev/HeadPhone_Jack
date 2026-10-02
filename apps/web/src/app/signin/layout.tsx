import type { ReactNode } from "react";
import { WallProvider } from "@/components/app/WallContext";
import { loadWall } from "@/components/landing/data";

export const revalidate = 3600;

/** Server layout: the cover wall arrives with the HTML, so its images start loading at once. */
export default async function AuthLayout({ children }: { children: ReactNode }) {
  return <WallProvider covers={await loadWall()}>{children}</WallProvider>;
}
