"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { WallCover } from "@/components/landing/data";

/** Cover-wall data rendered on the server for auth pages (LCP: no client fetch before images). */
const WallContext = createContext<WallCover[] | null>(null);

export function WallProvider({ covers, children }: { covers: WallCover[]; children: ReactNode }) {
  return <WallContext.Provider value={covers}>{children}</WallContext.Provider>;
}

export const useServerWall = () => useContext(WallContext);
