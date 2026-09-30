"use client";

import { createContext, lazy, Suspense, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { FeedCardData, Platform } from "@/components/ds";
import { useConnections, useMyCard } from "./queries";
import type { Song } from "./sends";

// The sheet (recipient picker, song search) loads only when someone taps Send: Home stays in budget.
const SendSheet = lazy(() => import("@/components/app/SendSheet").then((m) => ({ default: m.SendSheet })));

export interface SendRequest {
  song?: Song;
  replyTo?: { deliveryId: string; name: string };
}

const Ctx = createContext<(req?: SendRequest) => void>(() => {});

export function SendProvider({ children }: { children: ReactNode }) {
  const [req, setReq] = useState<SendRequest | null>(null);
  const open = useCallback((r: SendRequest = {}) => setReq(r), []);
  return (
    <Ctx.Provider value={open}>
      {children}
      {req && (
        <Suspense fallback={null}>
          <SendSheet request={req} onClose={() => setReq(null)} />
        </Suspense>
      )}
    </Ctx.Provider>
  );
}

export const useOpenSend = () => useContext(Ctx);

export function songFromCard(card: Pick<FeedCardData, "recording">): Song | undefined {
  const r = card.recording;
  if (!r || !r.title) return undefined;
  return { recording_id: r.id, title: r.title, artist: r.artist, links: r.links, search_links: r.search_links };
}

/** My platform for "Open in my app": the one I'm playing on, else my first connected app. */
export function useMyPlatform(): Platform | undefined {
  const mine = useMyCard();
  const connections = useConnections();
  return useMemo(() => {
    if (mine.data?.platform && mine.data.platform !== "UNKNOWN") return mine.data.platform;
    return connections.data?.find((c) => c.status === "CONNECTED")?.platform;
  }, [mine.data, connections.data]);
}
