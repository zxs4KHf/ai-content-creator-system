// 第 4 章 烽火：水墨。山是算出来的，烟的根数就是信息。
const sceneInk = (() => {
  const SPEED = 210, TOWER_GAP = 500, FIRST = 620;
  const LAYERS = [
    { base: 430, amp: 300, freq: .0013, ink: .24, fade: 120, par: .22, seed: 3, scale: 2 },
    { base: 560, amp: 330, freq: .0018, ink: .40, fade: 125, par: .45, seed: 9, scale: 2 },
    { base: 690, amp: 230, freq: .0023, ink: .68, fade: 135, par: 1, seed: 17, scale: 1 },
    { base: 900, amp: 240, freq: .0030, ink: .92, fade: 110, par: 1.45, seed: 29, scale: 1 },
  ];
  const WORLD = 4600;
  let paper, built = [], sprites = [], glyphAlpha, glyphField, glyphTmp, smoke;

  const ridge = (L, wx) => {
    const n = fbm(wx * L.freq + L.seed * 13.1, L.seed, 5);
    const sharp = 1 - Math.abs(2 * fbm(wx * L.freq * 1.7 + L.seed, L.seed * 2.3, 4) - 1);
    return L.base + L.amp * (1 - (n * .62 + sharp * .38) * 1.45);
  };

  function buildLayer(L) {
    const w = Math.ceil(WORLD / L.scale), h = Math.ceil(H / L.scale), c = offscreen(w, h), p = c.getContext('2d');
    const img = p.createImageData(w, h), d = img.data, S = L.scale;
    for (let px = 0; px < w; px++) {
      const wx = px * S, r = ridge(L, wx);
      for (let py = 0; py < h; py++) {
        const y = py * S, dist = y - r;
        if (dist < -2) continue;
        const edgeSoft = ss(-2, 1.5, dist);
        const wash = Math.exp(-dist / L.fade) * (.78 + .3 * fbm(wx * .006, y * .004, 2));
        const edge = Math.exp(-dist / 15) * (.45 + .75 * fbm(wx * .028, y * .05, 3));
        const crease = fbm(wx * .05 + dist * .012, y * .007, 3);
        const strokes = ss(.5, .66, crease) * Math.exp(-dist / (L.fade * .8)) * .5;
        const fall = 1 - ss(H * .7, H * 1.02, y) * .85;
        const a = clamp(wash * .72 + edge * .72 + strokes) * L.ink * edgeSoft * fall;
        const i = (py * w + px) * 4;
        d[i] = 28; d[i + 1] = 30; d[i + 2] = 32; d[i + 3] = a * 255;
      }
    }
    p.putImageData(img, 0, 0);
    return c;
  }

  function buildSprites() {
    for (let s = 0; s < 7; s++) {
      const n = 150, c = offscreen(n, n), p = c.getContext('2d'), img = p.createImageData(n, n), d = img.data;
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const dx = (x - n / 2) / (n / 2), dy = (y - n / 2) / (n / 2), r = Math.hypot(dx, dy);
        const f = fbm(x * .035 + s * 9.7, y * .035 + s * 4.1, 4);
        const a = ss(1, .15, r + (f - .5) * 1.25) * (.35 + f * .9);
        const i = (y * n + x) * 4;
        d[i] = 30; d[i + 1] = 32; d[i + 2] = 36; d[i + 3] = clamp(a) * 255;
      }
      p.putImageData(img, 0, 0);
      sprites.push(c);
    }
  }

  function buildGlyph() {
    const n = 500, c = offscreen(n, n), p = c.getContext('2d', { willReadFrequently: true });
    p.font = `600 ${GLYPH.size}px ${SERIF}`; p.textAlign = 'center'; p.textBaseline = 'middle';
    p.filter = 'blur(2px)';
    p.fillText('喂', n / 2, n / 2 + 10);
    const src = p.getImageData(0, 0, n, n).data;
    glyphAlpha = new Float32Array(n * n); glyphField = new Float32Array(n * n);
    for (let i = 0; i < n * n; i++) {
      const x = i % n, y = Math.floor(i / n);
      glyphAlpha[i] = src[i * 4 + 3] / 255 * (.8 + .32 * fbm(x * .05, y * .05, 3));
      glyphField[i] = fbm(x * .012 + 3, y * .012, 4) * .75 + (1 - y / n) * .25;
    }
    glyphTmp = offscreen(n, n);
  }

  const towers = [];
  for (let i = 0; i < 7; i++) towers.push({ wx: FIRST + i * TOWER_GAP, at: .2 + i * 2 * BEAT, smokes: i < 3 ? 1 : 2 });

  function column(p, x0, y0, age, seed, t) {
    const reach = Math.min(660, age * 270), count = 170;
    for (let k = 0; k < count; k++) {
      const u = k / count, s = u * reach;
      const drift = Math.pow(s / 640, 1.7) * 330;
      const sway = (noise(s * .0065 - t * .32, seed) - .5) * (20 + s * .2) + (noise(s * .021 - t * .6, seed + 4) - .5) * (6 + s * .07);
      const x = x0 + drift + sway, y = y0 - s * .92;
      const r = 7 + s * .115;
      const tail = 1 - ss(.72, 1, u);
      p.globalAlpha = (.2 - u * .13) * tail * ss(0, .12, age);
      const sp = sprites[(k + seed) % sprites.length];
      p.save(); p.translate(x, y); p.rotate((k * 1.7 + seed) + t * .12);
      p.drawImage(sp, -r, -r, r * 2, r * 2);
      p.restore();
    }
    p.globalAlpha = 1;
  }

  return {
    async init() {
      paper = paperTexture(233, 225, 207, 9);
      built = LAYERS.map(buildLayer);
      buildSprites(); buildGlyph();
      smoke = offscreen(W, H);
    },
    draw(t) {
      const cam = 120 + t * SPEED;
      ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
      ctx.drawImage(paper, 0, 0);
      LAYERS.forEach((L, i) => {
        if (i > 2) return;
        ctx.drawImage(built[i], -cam * L.par, 0, WORLD, H);
      });

      // 长城沿中景山脊走，城垛是一格一格算的。
      const WL = LAYERS[2];
      ctx.strokeStyle = 'rgba(26,28,30,.82)'; ctx.lineWidth = 2.4; ctx.beginPath();
      for (let sx = -10; sx <= W + 10; sx += 6) { const y = ridge(WL, sx + cam) - 9; sx === -10 ? ctx.moveTo(sx, y) : ctx.lineTo(sx, y); }
      ctx.stroke();
      ctx.fillStyle = 'rgba(26,28,30,.8)';
      for (let wx = Math.floor((cam - 20) / 13) * 13; wx < cam + W + 20; wx += 13) ctx.fillRect(wx - cam, ridge(WL, wx) - 15, 5, 6);

      const sp = smoke.getContext('2d');
      sp.clearRect(0, 0, W, H);
      for (const [i, tw] of towers.entries()) {
        const sx = tw.wx - cam, gy = ridge(WL, tw.wx) - 9;
        if (sx < -260 || sx > W + 120) continue;
        ctx.fillStyle = '#1b1d1f';
        ctx.beginPath(); ctx.moveTo(sx - 21, gy + 3); ctx.lineTo(sx - 15, gy - 38); ctx.lineTo(sx + 15, gy - 38); ctx.lineTo(sx + 21, gy + 3); ctx.closePath(); ctx.fill();
        for (let k = -1; k <= 1; k++) ctx.fillRect(sx + k * 11 - 3, gy - 45, 6, 8);
        const age = t - tw.at;
        if (age > 0) {
          for (let n = 0; n < tw.smokes; n++) {
            const ox = tw.smokes === 2 ? (n ? 13 : -13) : 0;
            column(sp, sx + ox, gy - 44, age - n * .14, i * 31 + n * 7 + 5, t);
            ctx.fillStyle = VERMILION; ctx.globalAlpha = ss(0, .1, age);
            ctx.beginPath(); ctx.arc(sx + ox, gy - 47, 5.5, 0, 7); ctx.fill(); ctx.globalAlpha = 1;
          }
        }
      }
      ctx.globalCompositeOperation = 'multiply';
      ctx.drawImage(smoke, 0, 0);
      ctx.globalCompositeOperation = 'source-over';

      // 烟走到版心，凝成这个字。
      const k = ss(3.9, 6.4, t), n = 500, gp = glyphTmp.getContext('2d'), img = gp.createImageData(n, n), d = img.data;
      if (k > 0) {
        ctx.save();
        const mist = ctx.createRadialGradient(GLYPH.x, GLYPH.y, 40, GLYPH.x, GLYPH.y, 400);
        mist.addColorStop(0, `rgba(233,225,207,${.82 * k})`); mist.addColorStop(.6, `rgba(233,225,207,${.5 * k})`); mist.addColorStop(1, 'rgba(233,225,207,0)');
        ctx.fillStyle = mist; ctx.fillRect(GLYPH.x - 420, GLYPH.y - 420, 840, 840); ctx.restore();
        const th = k * 1.25 - .15;
        for (let i = 0; i < n * n; i++) {
          const a = glyphAlpha[i]; if (a <= .004) continue;
          const j = i * 4; d[j] = 24; d[j + 1] = 26; d[j + 2] = 28;
          d[j + 3] = 255 * clamp(a * ss(glyphField[i] - .08, glyphField[i] + .08, th));
        }
        gp.putImageData(img, 0, 0);
        ctx.globalCompositeOperation = 'multiply';
        ctx.drawImage(glyphTmp, GLYPH.x - n / 2, GLYPH.y - n / 2);
        ctx.globalCompositeOperation = 'source-over';
      }

      ctx.drawImage(built[3], -cam * LAYERS[3].par, 0, WORLD, H);
      const shade = ctx.createLinearGradient(0, 860, 0, 1080);
      shade.addColorStop(0, 'rgba(233,225,207,0)'); shade.addColorStop(.36, 'rgba(233,225,207,.94)'); shade.addColorStop(1, 'rgba(233,225,207,.96)');
      ctx.fillStyle = shade; ctx.fillRect(0, 860, W, 220);
      hud({ year: 1466, form: '烟', ink: '#1c1e20', soft: 'rgba(28,30,32,.6)',
        caption: t < 2.6 ? '百人，一烟一炮' : '五百人，二烟二炮',
        captionAlpha: ss(.2, .5, t) * (t < 2.6 ? 1 - ss(2.4, 2.6, t) : ss(2.6, 2.85, t)) });
    },
  };
})();
