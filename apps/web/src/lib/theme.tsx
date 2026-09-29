"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Theme = "dark" | "light";
export const THEME_STORAGE_KEY = "jingle-theme";
export const DEFAULT_THEME: Theme = "dark";

/**
 * Inline script for <head>: applies the stored theme before first paint (no flash).
 * Dark is the default; storage access is wrapped in try/catch.
 */
export const themeInitScript = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t!=="light"&&t!=="dark"){t="${DEFAULT_THEME}"}document.documentElement.setAttribute("data-theme",t)}catch(e){document.documentElement.setAttribute("data-theme","${DEFAULT_THEME}")}})();`;

function readTheme(): Theme {
  if (typeof document === "undefined") return DEFAULT_THEME;
  const attr = document.documentElement.getAttribute("data-theme");
  return attr === "light" ? "light" : "dark";
}

interface ThemeContextValue {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(DEFAULT_THEME);

  useEffect(() => {
    setThemeState(readTheme());
  }, []);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    document.documentElement.setAttribute("data-theme", t);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, t);
    } catch {
      /* storage unavailable: theme still applies for this page view */
    }
  }, []);

  const toggleTheme = useCallback(() => setTheme(readTheme() === "dark" ? "light" : "dark"), [setTheme]);

  const value = useMemo(() => ({ theme, setTheme, toggleTheme }), [theme, setTheme, toggleTheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/** Works without a provider too (falls back to reading/writing the <html> attribute). */
export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  const [local, setLocal] = useState<Theme>(DEFAULT_THEME);
  useEffect(() => {
    if (!ctx) setLocal(readTheme());
  }, [ctx]);
  if (ctx) return ctx;
  const setTheme = (t: Theme) => {
    setLocal(t);
    if (typeof document !== "undefined") document.documentElement.setAttribute("data-theme", t);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, t);
    } catch {
      /* ignore */
    }
  };
  return { theme: local, setTheme, toggleTheme: () => setTheme(local === "dark" ? "light" : "dark") };
}
