// 全片共用：版式、缓动、噪声。任何章节都不改这里的版式位置。
const W = 1920, H = 1080, BEAT = 0.5;
const GLYPH = { x: 960, y: 470, size: 380 };
const SERIF = '"Noto Serif SC"', MONO = '"JetBrains Mono"';
const VERMILION = '#b5392b';
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');

const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const lerp = (a, b, k) => a + (b - a) * k;
const ss = (a, b, v) => { const k = clamp((v - a) / (b - a)); return k * k * (3 - 2 * k); };
const easeOut = k => 1 - Math.pow(1 - clamp(k), 3);
const easeInOut = k => { k = clamp(k); return k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; };

function offscreen(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function rng(seed) { return () => { seed = (seed + 0x6D2B79F5) | 0; let k = Math.imul(seed ^ (seed >>> 15), 1 | seed); k = (k + Math.imul(k ^ (k >>> 7), 61 | k)) ^ k; return ((k ^ (k >>> 14)) >>> 0) / 4294967296; }; }

const PERM = (() => { const r = rng(7), p = Array.from({ length: 256 }, (_, i) => i); for (let i = 255; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [p[i], p[j]] = [p[j], p[i]]; } return new Uint8Array([...p, ...p]); })();
const VALS = (() => { const r = rng(11); return Float32Array.from({ length: 256 }, () => r()); })();
function noise(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi;
  const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
  const a = xi & 255, b = (xi + 1) & 255, c = yi & 255, d = (yi + 1) & 255;
  const n00 = VALS[PERM[a + PERM[c]]], n10 = VALS[PERM[b + PERM[c]]], n01 = VALS[PERM[a + PERM[d]]], n11 = VALS[PERM[b + PERM[d]]];
  return lerp(lerp(n00, n10, u), lerp(n01, n11, u), v);
}
function fbm(x, y, oct = 4) { let s = 0, a = .5, f = 1, n = 0; for (let i = 0; i < oct; i++) { s += a * noise(x * f, y * f); n += a; a *= .5; f *= 2.03; } return s / n; }

async function loadFonts() {
  const faces = [new FontFace('Noto Serif SC', 'url(/fonts/NotoSerifSC.ttf)', { weight: '200 900' }), new FontFace('JetBrains Mono', 'url(/fonts/JetBrainsMono.ttf)', { weight: '100 800' })];
  for (const f of faces) { await f.load(); document.fonts.add(f); }
}

// 纸：纤维和细小的斑点，预先算好。
function paperTexture(r, g, b, grain = 10) {
  const c = offscreen(W, H), p = c.getContext('2d'), img = p.createImageData(W, H), d = img.data;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = (y * W + x) * 4;
    const v = (fbm(x * .004, y * .004, 3) - .5) * grain * 1.6 + (fbm(x * .35, y * .08, 2) - .5) * grain * .9 + (noise(x * .9, y * .9) - .5) * grain * .5;
    d[i] = r + v; d[i + 1] = g + v; d[i + 2] = b + v * 1.1; d[i + 3] = 255;
  }
  p.putImageData(img, 0, 0);
  return c;
}

// 固定版式：左下年份，中间字幕，右下形态。
function hud({ year, form, caption, ink, soft, captionAlpha = 1 }) {
  ctx.save();
  ctx.textBaseline = 'alphabetic';
  ctx.fillStyle = ink;
  ctx.textAlign = 'left';
  ctx.font = `300 50px ${MONO}`;
  ctx.fillText(String(year), 96, 1006);
  ctx.textAlign = 'right';
  ctx.font = `500 36px ${SERIF}`;
  ctx.fillText(form, 1824, 1006);
  ctx.fillStyle = soft;
  ctx.font = `400 24px ${SERIF}`;
  ctx.fillText('现在它是', 1824, 952);
  ctx.textAlign = 'center';
  ctx.font = `400 36px ${SERIF}`;
  ctx.globalAlpha = captionAlpha;
  ctx.fillStyle = ink;
  if (caption) ctx.fillText(caption, W / 2, 1006);
  ctx.restore();
}
