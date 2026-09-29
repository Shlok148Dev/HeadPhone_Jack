// Multi-entry Vite build for an MV3 extension.
// Content scripts and the popup are classic scripts, so each is bundled on its own as an IIFE
// (no shared chunks). The service worker is an ES module. public/ (manifest, popup.html, icons)
// is copied as-is. Output: dist/ — load it with chrome://extensions → Load unpacked.
import { build } from "vite";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { existsSync, readFileSync } from "node:fs";

const root = resolve(fileURLToPath(new URL(".", import.meta.url)), "..");
const watch = process.argv.includes("--watch");

const entries = [
  { name: "background", src: "src/background/index.ts", out: "background.js", format: "es" },
  { name: "popup", src: "src/popup/popup.ts", out: "popup.js", format: "iife" },
  ...["youtube-music", "spotify", "apple-music", "amazon-music", "pairing"].map((n) => ({
    name: n.replace(/-/g, "_"),
    src: `src/content/${n}.ts`,
    out: `content/${n}.js`,
    format: "iife",
  })),
];

let first = true;
for (const e of entries) {
  await build({
    root,
    configFile: false,
    logLevel: "warn",
    publicDir: first ? resolve(root, "public") : false,
    build: {
      outDir: resolve(root, "dist"),
      emptyOutDir: first,
      target: "chrome120",
      minify: false,
      sourcemap: false,
      copyPublicDir: first,
      watch: watch ? {} : null,
      lib: { entry: resolve(root, e.src), formats: [e.format], name: e.name, fileName: () => e.out },
      rollupOptions: { output: { inlineDynamicImports: true } },
    },
  });
  first = false;
}

if (!watch) {
  const manifest = resolve(root, "dist/manifest.json");
  if (!existsSync(manifest)) throw new Error("dist/manifest.json missing");
  const m = JSON.parse(readFileSync(manifest, "utf8"));
  const pkg = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));
  if (m.version !== pkg.version) throw new Error(`manifest version ${m.version} != package.json ${pkg.version}`);
  console.log(`Built Jingle Companion ${m.version} → dist/ (${entries.length} bundles)`);
}
