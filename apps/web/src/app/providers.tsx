"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LazyMotion } from "motion/react";
import { useState, type ReactNode } from "react";
import { ToastProvider } from "@/components/ds";
import { ApiError } from "@/lib/api";
import { AuthProvider } from "@/lib/auth";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 10_000,
            refetchOnWindowFocus: true,
            // 4xx are answers, not outages: don't retry them.
            retry: (count, err) => !(err instanceof ApiError && err.status >= 400 && err.status < 500) && count < 2,
          },
        },
      }),
  );
  return (
    <LazyMotion features={loadMotionFeatures} strict>
      <QueryClientProvider client={client}>
        <AuthProvider>
          <ToastProvider>{children}</ToastProvider>
        </AuthProvider>
      </QueryClientProvider>
    </LazyMotion>
  );
}

/** Animation features load after first paint (D-PERF-01): keeps Home under its 180 kB budget. */
const loadMotionFeatures = () => import("@/lib/motion-features").then((r) => r.default);
