import type { ChartSong } from "@/lib/charts";

/**
 * The chart share card (JNG-15-04): a 1080×1920 story image of your people's top 5, drawn on the
 * device (no third-party service). Covers go through our own image cache (same origin), so the
 * canvas can be exported; covers are drawn whole, never cropped or covered.
 */
const W = 1080;
const H = 1920;

function proxied(url: string): string {
  return `/_next/image?url=${encodeURIComponent(url)}&w=384&q=85`;
}

function load(src: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

function fontOf(selector: string, fallback: string): string {
  const el = document.querySelector(selector);
  return (el && getComputedStyle(el).fontFamily) || fallback;
}

function fit(ctx: CanvasRenderingContext2D, text: string, max: number): string {
  if (ctx.measureText(text).width <= max) return text;
  let t = text;
  while (t.length > 1 && ctx.measureText(`${t}…`).width > max) t = t.slice(0, -1);
  return `${t}…`;
}

// The Jingle mark (white), as in components/app/LogoMark.tsx.
const MARK = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" stroke="#fff" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="20" width="40" height="27" rx="4.5" stroke-width="3.2"/><rect x="11" y="25.5" width="28" height="10.5" rx="2.6" stroke-width="2.4"/><circle cx="18.5" cy="30.75" r="2.6" stroke-width="2.2"/><circle cx="31.5" cy="30.75" r="2.6" stroke-width="2.2"/><path d="M21.6 30.75h6.8" stroke-width="2.2"/><path d="M14.5 47l2.8-5.6h15.4l2.8 5.6" stroke-width="2.4"/><circle cx="49.5" cy="9.6" r="3.4" fill="#fff" stroke-width="1.4"/><path d="M49.5 13v2.2" stroke-width="3.4"/><circle cx="57.6" cy="12.4" r="3.4" fill="#fff" stroke-width="1.4"/><path d="M57.4 15.8v2" stroke-width="3.4"/><path d="M49.5 15v15.5c0 2.6 2 4.2 4.4 4.2" stroke-width="2.6"/><path d="M57.3 17.6v8.8c0 4.4-3.4 4.2-3.4 8.3v12.8c0 7.7-5.8 12.2-12.4 12.2-5.3 0-9.4-3.3-10.6-8" stroke-width="2.9"/></svg>`;

export async function renderChartCard(songs: ChartSong[], range: string): Promise<Blob | null> {
  const c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const ctx = c.getContext("2d");
  if (!ctx) return null;
  const display = fontOf(".font-display", "sans-serif");
  const ui = fontOf("body", "sans-serif");
  const mono = fontOf(".font-mono", "monospace");
  await document.fonts?.ready;

  // Background: the #1 cover's own ambient colour, deepening to near black.
  const amb = songs[0]?.artwork_colors?.ambient_dark ?? "#1B181F";
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, amb);
  g.addColorStop(1, "#0A090C");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);

  ctx.fillStyle = "rgba(246,243,239,0.7)";
  ctx.font = `600 34px ${mono}`;
  ctx.fillText("SONG OF THE WEEK", 90, 190);
  ctx.fillStyle = "#F6F3EF";
  ctx.font = `700 92px ${display}`;
  ctx.fillText("My people's top 5", 90, 300);
  ctx.fillStyle = "rgba(246,243,239,0.7)";
  ctx.font = `500 36px ${mono}`;
  ctx.fillText(range, 90, 370);

  const covers = await Promise.all(songs.slice(0, 5).map((s) => (s.artwork_url ? load(proxied(s.artwork_url)) : Promise.resolve(null))));
  const rowH = 236;
  songs.slice(0, 5).forEach((s, i) => {
    const y = 450 + i * rowH;
    ctx.fillStyle = i === 0 ? "#F6F3EF" : "rgba(246,243,239,0.55)";
    ctx.font = `700 ${i === 0 ? 96 : 72}px ${mono}`;
    ctx.fillText(String(i + 1), 90, y + 140);
    const size = 200;
    const x = 220;
    const img = covers[i];
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(x, y + 10, size, size, 16);
    ctx.clip();
    if (img) ctx.drawImage(img, x, y + 10, size, size);
    else {
      ctx.fillStyle = "#252129";
      ctx.fillRect(x, y + 10, size, size);
    }
    ctx.restore();
    const tx = x + size + 44;
    const max = W - tx - 80;
    ctx.fillStyle = "#F6F3EF";
    ctx.font = `700 ${i === 0 ? 56 : 48}px ${display}`;
    ctx.fillText(fit(ctx, s.title, max), tx, y + 100);
    ctx.fillStyle = "rgba(246,243,239,0.7)";
    ctx.font = `500 38px ${ui}`;
    ctx.fillText(fit(ctx, s.artist, max), tx, y + 156);
    ctx.font = `500 30px ${mono}`;
    ctx.fillText(`${s.listeners} ${s.listeners === 1 ? "friend" : "friends"}`, tx, y + 204);
  });

  const mark = await load(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(MARK)}`);
  if (mark) ctx.drawImage(mark, 90, H - 220, 120, 120);
  ctx.fillStyle = "#F6F3EF";
  ctx.font = `700 64px ${display}`;
  ctx.fillText("jingle", 230, H - 140);
  ctx.fillStyle = "rgba(246,243,239,0.6)";
  ctx.font = `500 32px ${ui}`;
  ctx.fillText("what your people are really listening to", 232, H - 92);

  return new Promise((resolve) => c.toBlob((b) => resolve(b), "image/png"));
}

/** Share through the phone's share sheet when available, else download. */
export async function shareChartCard(songs: ChartSong[], range: string): Promise<"shared" | "downloaded" | "failed"> {
  const blob = await renderChartCard(songs, range);
  if (!blob) return "failed";
  const file = new File([blob], "jingle-song-of-the-week.png", { type: "image/png" });
  const nav = navigator as Navigator & { canShare?: (d: ShareData) => boolean };
  // Phones get the share sheet (straight to Instagram/WhatsApp); desktops get a download.
  const touch = typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;
  if (touch && nav.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: "My people's Song of the Week" });
      return "shared";
    } catch {
      /* cancelled: fall through to download */
    }
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = file.name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  return "downloaded";
}
