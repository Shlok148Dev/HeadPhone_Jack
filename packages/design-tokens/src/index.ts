/** Jingle design tokens — single source for web (and mobile later). See .claude/skills/jingle-design-system. */
export const brand = {
  violet: "#8B6BFF",
  cyan: "#3FE7D8",
  live: "#FF6B5E",
} as const;

export const fonts = {
  display: "Bricolage Grotesque",
  ui: "Inter",
  mono: "JetBrains Mono",
} as const;

export const radius = { sm: 8, md: 12, lg: 20, pill: 999 } as const;
export const space = (n: number): number => n * 4;
