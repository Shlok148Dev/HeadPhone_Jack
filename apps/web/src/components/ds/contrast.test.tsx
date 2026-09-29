import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { describe, expect, it } from "vitest";
import { brandContrastPairs, contrastPairs, contrastRatio, themes, type ThemeName } from "@jingle/design-tokens";

const require = createRequire(import.meta.url);

/** Parse `--name: value;` declarations from a CSS block selected by a header regex. */
function readBlock(css: string, header: RegExp): Record<string, string> {
  const m = header.exec(css);
  if (!m) throw new Error(`block not found: ${header}`);
  const start = css.indexOf("{", m.index) + 1;
  const end = css.indexOf("}", start);
  const out: Record<string, string> = {};
  for (const d of css.slice(start, end).matchAll(/--([a-z0-9-]+):\s*([^;]+);/g)) out[d[1]!] = d[2]!.trim().toLowerCase();
  return out;
}

describe("design tokens: contrast", () => {
  for (const theme of ["dark", "light"] as ThemeName[]) {
    for (const [fg, bg] of contrastPairs) {
      it(`${theme}: ${fg} on ${bg} >= 4.5`, () => {
        const ratio = contrastRatio(themes[theme][fg], themes[theme][bg]);
        expect(ratio, `${fg}/${bg} = ${ratio.toFixed(2)}`).toBeGreaterThanOrEqual(4.5);
      });
    }
  }
  for (const [fg, bg] of brandContrastPairs) {
    it(`on-brand ${fg} on ${bg} >= 4.5`, () => {
      expect(contrastRatio(fg, bg)).toBeGreaterThanOrEqual(4.5);
    });
  }

  it("computes known reference ratios", () => {
    expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21, 1);
    expect(contrastRatio("#777777", "#FFFFFF")).toBeCloseTo(4.48, 1);
  });
});

describe("design tokens: tokens.css mirrors the TS source", () => {
  const css = readFileSync(require.resolve("@jingle/design-tokens/tokens.css"), "utf8");
  const blocks: Record<ThemeName, Record<string, string>> = {
    dark: readBlock(css, /:root,\s*\[data-theme="dark"\]/),
    light: readBlock(css, /\[data-theme="light"\]\s*\{/),
  };
  for (const theme of ["dark", "light"] as ThemeName[]) {
    it(`${theme} colour variables match`, () => {
      for (const [k, v] of Object.entries(themes[theme])) {
        expect(blocks[theme][k], `--${k}`).toBe(v.toLowerCase());
      }
    });
  }
});
