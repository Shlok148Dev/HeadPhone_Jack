// Generates the Jingle-original extension icons (public/icons/icon-{16,32,48,128}.png)
// with no native dependencies: a rounded square with the violet #8B6BFF → cyan #3FE7D8 diagonal
// gradient and a white eighth-note glyph, rasterised with 4×4 supersampling and encoded with zlib.
// Mirrors public/icons/icon.svg. Run: pnpm --filter @jingle/companion-extension icons
import { deflateSync } from "node:zlib";
import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const outDir = resolve(fileURLToPath(new URL(".", import.meta.url)), "../public/icons");
mkdirSync(outDir, { recursive: true });

const VIOLET = [0x8b, 0x6b, 0xff];
const CYAN = [0x3f, 0xe7, 0xd8];

// Geometry in unit space (0..1), matching icon.svg's 128-unit viewBox.
const RADIUS = 28 / 128;
function inRoundedSquare(x, y) {
  const r = RADIUS;
  const cx = Math.min(Math.max(x, r), 1 - r);
  const cy = Math.min(Math.max(y, r), 1 - r);
  return (x - cx) ** 2 + (y - cy) ** 2 <= r * r && x >= 0 && x <= 1 && y >= 0 && y <= 1;
}
function inNote(x, y) {
  // Note head: ellipse centred (50,86) rx 17 ry 13 rotated -20°.
  const hx = x * 128 - 50, hy = y * 128 - 86, a = (-20 * Math.PI) / 180;
  const u = hx * Math.cos(a) + hy * Math.sin(a), v = -hx * Math.sin(a) + hy * Math.cos(a);
  if ((u / 17) ** 2 + (v / 13) ** 2 <= 1) return true;
  const px = x * 128, py = y * 128;
  // Stem: x 58..66, y 28..84.
  if (px >= 58 && px <= 66 && py >= 28 && py <= 84) return true;
  // Flag: quadrilateral (66,28) (92,44) (92,58) (66,44).
  if (px >= 66 && px <= 92) {
    const t = (px - 66) / 26;
    const top = 28 + 16 * t, bottom = 44 + 14 * t;
    if (py >= top && py <= bottom) return true;
  }
  return false;
}

function crc32(buf) {
  let c, crc = 0xffffffff;
  for (let n = 0; n < buf.length; n++) {
    c = (crc ^ buf[n]) & 0xff;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    crc = (crc >>> 8) ^ c;
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type, "ascii"), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, crc]);
}

function render(size) {
  const SS = 4;
  const raw = Buffer.alloc(size * (size * 4 + 1));
  for (let py = 0; py < size; py++) {
    raw[py * (size * 4 + 1)] = 0; // filter: none
    for (let px = 0; px < size; px++) {
      let r = 0, g = 0, b = 0, a = 0;
      for (let sy = 0; sy < SS; sy++) {
        for (let sx = 0; sx < SS; sx++) {
          const x = (px + (sx + 0.5) / SS) / size;
          const y = (py + (sy + 0.5) / SS) / size;
          if (!inRoundedSquare(x, y)) continue;
          let col;
          if (inNote(x, y)) col = [255, 255, 255];
          else {
            const t = Math.min(1, Math.max(0, (x + y) / 2));
            col = VIOLET.map((c, i) => c + (CYAN[i] - c) * t);
          }
          r += col[0]; g += col[1]; b += col[2]; a += 1;
        }
      }
      const o = py * (size * 4 + 1) + 1 + px * 4;
      const n = SS * SS;
      raw[o] = a ? Math.round(r / a) : 0;
      raw[o + 1] = a ? Math.round(g / a) : 0;
      raw[o + 2] = a ? Math.round(b / a) : 0;
      raw[o + 3] = Math.round((a / n) * 255);
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // RGBA
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(raw, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

for (const size of [16, 32, 48, 128]) {
  writeFileSync(resolve(outDir, `icon-${size}.png`), render(size));
  console.log(`icon-${size}.png`);
}
