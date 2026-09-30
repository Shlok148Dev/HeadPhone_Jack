"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type { Socket } from "socket.io-client";
import type { FeedCardData } from "@/components/ds";
import { api, getAccessToken, refreshSession } from "./api";
import { sortFeed, type Feed } from "./feed";

type Status = "connecting" | "live" | "reconnecting";
const RealtimeContext = createContext<Status>("connecting");

/**
 * Socket.IO client for `/rt` (Technical Bible 4.3, ADR-0018). The server only sends hints; this
 * hook refetches the affected card over REST, where core-api applies privacy and blocks.
 */
export function RealtimeProvider({
  userId,
  children,
}: {
  userId: string;
  children: ReactNode;
}) {
  const qc = useQueryClient();
  const [status, setStatus] = useState<Status>("connecting");

  useEffect(() => {
    let socket: Socket | null = null;
    let cancelled = false;
    // Loaded after first paint to keep the home route within its JS budget (Stack 2.2).
    void import("socket.io-client").then(({ io }) => {
      if (cancelled) return;
      socket = io({
        path: "/rt/socket.io",
        transports: ["websocket"],
        auth: (cb) => cb({ token: getAccessToken() }),
        reconnectionDelayMax: 10_000,
      });

      const patchCard = async (friendId: string) => {
        try {
          const card = await api<FeedCardData>(`/feed/${friendId}`);
          qc.setQueryData<Feed>(["feed"], (prev) => {
            if (!prev) return prev;
            const results = prev.results.some((c) => c.friend.id === friendId)
              ? prev.results.map((c) => (c.friend.id === friendId ? card : c))
              : [...prev.results, card];
            const sorted = sortFeed(results);
            return {
              ...prev,
              results: sorted,
              live_count: sorted.filter((c) => c.state === "LIVE").length,
            };
          });
        } catch {
          void qc.invalidateQueries({ queryKey: ["feed"] }); // e.g. no longer friends: refetch the list
        }
      };

      const s = socket;
      s.on("connect", () => {
        setStatus("live");
        void qc.invalidateQueries({ queryKey: ["feed"] }); // catch up on anything missed while away
      });
      s.on("disconnect", () => setStatus("reconnecting"));
      s.on("connect_error", async (err) => {
        setStatus("reconnecting");
        if (err.message === "unauthorized") await refreshSession(); // token expired: next retry uses the new one
      });
      s.on(
        "feed:update",
        ({ user_id }: { user_id: string }) => void patchCard(user_id),
      );
      s.on(
        "me:update",
        () => void qc.invalidateQueries({ queryKey: ["me", "card"] }),
      );
      s.on("friends:changed", () => {
        void qc.invalidateQueries({ queryKey: ["friends"] });
        void qc.invalidateQueries({ queryKey: ["feed"] });
      });
      s.on(
        "notify",
        () => void qc.invalidateQueries({ queryKey: ["friends", "requests"] }),
      );
    });
    return () => {
      cancelled = true;
      socket?.close();
    };
  }, [userId, qc]);

  return (
    <RealtimeContext.Provider value={status}>
      {children}
    </RealtimeContext.Provider>
  );
}

export const useRealtimeStatus = () => useContext(RealtimeContext);
