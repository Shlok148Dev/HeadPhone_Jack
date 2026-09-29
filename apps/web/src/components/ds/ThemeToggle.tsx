"use client";

import { useTheme } from "@/lib/theme";
import { IconButton } from "./Button";
import { Moon, Sun } from "./icons";

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const next = theme === "dark" ? "light" : "dark";
  return (
    <IconButton label={`Switch to ${next} theme`} variant="secondary" onClick={toggleTheme} className={className}>
      {theme === "dark" ? <Sun /> : <Moon />}
    </IconButton>
  );
}
