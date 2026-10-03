"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  api,
  json,
  onSessionEnded,
  refreshSession,
  setAccessToken,
  type AuthPayload,
  type Me,
} from "./api";

type Status = "loading" | "signed-in" | "signed-out";

interface AuthValue {
  status: Status;
  me: Me | null;
  signIn: (email: string, password: string) => Promise<Me>;
  signUp: (input: SignUpInput) => Promise<Me>;
  signOut: () => Promise<void>;
  setMe: (me: Me) => void;
}

export interface SignUpInput {
  email: string;
  password: string;
  username: string;
  display_name?: string;
  birth_year: number;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [me, setMeState] = useState<Me | null>(null);
  const qc = useQueryClient();
  // Whose data the query cache holds. Every cached response belongs to one person: when that
  // person changes (sign out, sign in as someone else, new account), nothing of theirs may stay.
  const owner = useRef<string | null>(null);

  const accept = useCallback(
    (payload: AuthPayload) => {
      if (owner.current !== payload.user.id) {
        qc.cancelQueries();
        qc.clear();
        owner.current = payload.user.id;
      }
      setAccessToken(payload.access);
      setMeState(payload.user);
      setStatus("signed-in");
      return payload.user;
    },
    [qc],
  );

  const clear = useCallback(() => {
    qc.cancelQueries();
    qc.clear();
    owner.current = null;
    setAccessToken(null);
    setMeState(null);
    setStatus("signed-out");
  }, [qc]);

  useEffect(() => {
    onSessionEnded(clear);
    let alive = true;
    refreshSession()
      .then((p) => {
        if (!alive) return;
        if (p) accept(p);
        else clear();
      })
      .catch(() => alive && clear());
    return () => {
      alive = false;
    };
  }, [accept, clear]);

  const value = useMemo<AuthValue>(
    () => ({
      status,
      me,
      signIn: async (email, password) =>
        accept(
          await api<AuthPayload>("/auth/login", {
            method: "POST",
            ...json({ email, password }),
          }),
        ),
      signUp: async (input) =>
        accept(
          await api<AuthPayload>("/auth/register", {
            method: "POST",
            ...json(input),
          }),
        ),
      signOut: async () => {
        try {
          await api("/auth/logout", { method: "POST" });
        } finally {
          clear();
        }
      },
      setMe: setMeState,
    }),
    [status, me, accept, clear],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
