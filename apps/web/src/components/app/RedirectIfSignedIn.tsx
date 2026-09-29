"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

export function RedirectIfSignedIn({ to = "/home" }: { to?: string }) {
  const { status } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (status === "signed-in") router.replace(to);
  }, [status, router, to]);
  return null;
}
