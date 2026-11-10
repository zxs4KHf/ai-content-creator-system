// 第 5 章 电报：活版电码本。页面内容来自 Unihan，不是编的。
const sceneTelegraph = (() => {
  const CELL = 78, PAGE = CELL * 10, PITCH = PAGE + 170, TARGET = { col: 8, row: 0 };
  const HOME = { x: W * .5, y: 452, zoom: .93 };
  const MORSE = { 0: '-----', 8: '---..' };
  const UNIT = .038, KEY_START = 3.75;
  let paper, wear, layer, codes, tape = [], digitAt = [];

  function buildTape() {
    let u = 0;
    for (const [i, dg] of [...'0808'].entries()) {
      digitAt[i] = KEY_START + u * UNIT;
      for (const m of MORSE[dg]) { const len = m === '-' ? 3 : 1; tape.push({ u, len }); u += len + 1; }
      u += 2;
    }
  }

  return {
    async init() {
      paper = paperTexture(236, 228, 208, 8);
      codes = await (await fetch('数据/电码页.json')).json();
      wear = offscreen(1400, 1400);
      const w = wear.getContext('2d'), img = w.createImageData(1400, 1400), r = rng(5);
      for (let i = 0; i < img.data.length; i += 4) {
        const x = (i / 4) % 1400, y = Math.floor(i / 4 / 1400);
        const a = ss(.56, .8, fbm(x * .05, y * .05, 3)) * .55 + (r() > .988 ? .7 : 0);
        img.data[i + 3] = a * 255;
      }
      w.putImageData(img, 0, 0);
      layer = offscreen(W, H);
      buildTape();
    },
    draw(t) {
      // 整本电码本横着走，停在第 08 页。每一页都是真实电码。
      const pos = 8 * easeOut(t / 1.0);
      const k = easeInOut((t - 2.65) / 1.0);
      const zoom = lerp(HOME.zoom, GLYPH.size / 58, k);
      const fx = lerp(pos * PITCH + PAGE / 2, 8 * PITCH + (TARGET.col + .5) * CELL, k), fy = lerp(PAGE / 2, (TARGET.row + .5) * CELL, k);
      const ax = lerp(HOME.x, GLYPH.x, k), ay = lerp(HOME.y, GLYPH.y, k);
      const hit = [['14', 1.1], ['15', 1.35], ['34', 1.6], ['37', 1.85]];

      const p = layer.getContext('2d');
      p.setTransform(1, 0, 0, 1, 0, 0); p.clearRect(0, 0, W, H);
      const settle = ss(.9, 1.1, t);
      for (let n = 0; n <= 9; n++) {
        const ox = n * PITCH - fx, on = n === 8;
        if (Math.abs(ox * zoom + ax - 960) > 1500 + PAGE * zoom) continue;
        p.setTransform(zoom, 0, 0, zoom, ax + ox * zoom, ay - fy * zoom);
        const pageNo = String(n).padStart(2, '0'), side = on ? 1 : lerp(1, .22, settle);
        p.globalAlpha = side; p.fillStyle = '#17171a'; p.strokeStyle = 'rgba(23,23,26,.55)'; p.lineWidth = 1;
        p.textAlign = 'center'; p.textBaseline = 'middle';
        p.font = `500 16px ${MONO}`;
        for (let i = 0; i < 10; i++) { p.fillText(i, (i + .5) * CELL, -20); p.fillText(i, -22, (i + .5) * CELL); }
        p.textAlign = 'left'; p.font = `600 30px ${SERIF}`; p.fillText(`第 ${pageNo} 页`, 0, -58); p.textAlign = 'center';
        for (let i = 0; i <= 10; i++) { p.beginPath(); p.moveTo(0, i * CELL); p.lineTo(PAGE, i * CELL); p.moveTo(i * CELL, 0); p.lineTo(i * CELL, PAGE); p.stroke(); }
        if (on) {
          const band = ss(2.2, 2.6, t) * .13 * (1 - ss(2.8, 3.3, t));
          p.globalAlpha = band; p.fillStyle = VERMILION;
          p.fillRect(0, TARGET.row * CELL, PAGE, CELL); p.fillRect(TARGET.col * CELL, 0, CELL, PAGE);
        }
        const dim = 1 - .72 * ss(1.0, 1.2, t);
        for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) {
          const ch = codes[`${pageNo}${r}${c}`];
          if (!ch) continue;
          const h = on && hit.find(([s]) => s === `${r}${c}`);
          const isTarget = on && r === TARGET.row && c === TARGET.col;
          let color = '#17171a', alpha = side;
          if (on) {
            alpha = dim;
            if (h && t >= h[1]) { alpha = 1; color = VERMILION; }
            if (isTarget) { alpha = 1; if (t >= 2.25) color = VERMILION; }
          }
          p.globalAlpha = alpha; p.fillStyle = color;
          p.font = `500 58px ${SERIF}`;
          const j = Math.sin(r * 12.9 + c * 78.2) * .8;
          p.fillText(ch, (c + .5) * CELL + j * .6, (r + .5) * CELL + 2 + j * .4);
        }
        p.globalAlpha = 1;
      }
      p.setTransform(zoom, 0, 0, zoom, ax - fx * zoom + 8 * PITCH * zoom, ay - fy * zoom);
      p.globalCompositeOperation = 'destination-out';
      p.drawImage(wear, -200, -200, 1400, 1400);
      p.globalCompositeOperation = 'source-over';
      p.setTransform(1, 0, 0, 1, 0, 0);

      ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
      ctx.drawImage(paper, 0, 0);
      ctx.globalCompositeOperation = 'multiply';
      ctx.drawImage(layer, 0, 0);
      ctx.globalCompositeOperation = 'source-over';

      // 四位数字随摩尔斯落下。
      ctx.globalAlpha = ss(2.8, 3.15, t);
      ctx.drawImage(paper, 0, 668, W, H - 668, 0, 668, W, H - 668);
      ctx.globalAlpha = 1;
      if (t > KEY_START - .1) {
        ctx.font = `500 76px ${MONO}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = '#17171a';
        [...'0808'].forEach((d, i) => {
          const a = t - digitAt[i];
          if (a < 0) return;
          const drop = (1 - easeOut(a / .09)) * -16;
          ctx.fillText(d, GLYPH.x + (i - 1.5) * 92, 722 + drop);
        });

        // 纸带：打点头固定，纸往左走。每个点划都是 0808 的真实摩尔斯。
        const HEAD = 1360, TOP = 786, TH = 78, SCALE = 15;
        const u = (t - KEY_START) / UNIT;
        ctx.fillStyle = '#d9cdb0'; ctx.fillRect(0, TOP, W, TH);
        ctx.fillStyle = 'rgba(23,23,26,.22)'; ctx.fillRect(0, TOP, W, 1); ctx.fillRect(0, TOP + TH, W, 1);
        const off = u * SCALE % 30;
        for (let x = -off; x < W; x += 30) { ctx.fillStyle = '#ece4d0'; ctx.beginPath(); ctx.arc(x, TOP + 11, 4, 0, 7); ctx.fill(); ctx.beginPath(); ctx.arc(x, TOP + TH - 11, 4, 0, 7); ctx.fill(); }
        ctx.fillStyle = '#17171a';
        for (const m of tape) {
          if (u < m.u) break;
          const done = Math.min(m.len, u - m.u);
          ctx.fillRect(HEAD - (u - m.u) * SCALE, TOP + 30, done * SCALE, 18);
        }
        const keyed = tape.some(m => u >= m.u && u < m.u + m.len);
        ctx.fillStyle = keyed ? VERMILION : '#17171a';
        ctx.fillRect(HEAD - 2, TOP - 16, 5, keyed ? 42 : 30);
      }

      const cap = t < 2.1 ? '这一页全是嘴：喉、喊、吗、嗓' : '第 08 页，第 0 行，第 8 列';
      hud({ year: 1871, form: t > 3.7 ? '电码' : '一个编号', ink: '#17171a', soft: 'rgba(23,23,26,.6)', caption: t > 1 ? cap : '',
        captionAlpha: t < 2.1 ? ss(1, 1.25, t) * (1 - ss(1.95, 2.1, t)) : ss(2.1, 2.35, t) });
    },
  };
})();
