// 第 9 章 模型：1024 个真实数字。位置是真实向量的主成分，不是摆出来的。
const sceneVector = (() => {
  const N = 32, CS = 11.4, BG = '#101214', AMBER = '#e2ab52', CYAN = '#8cc4c8', GRAY = '#8b8f94', FG = '#e9e6df';
  const FEED = new Set(['给孩子喂饭', '喂饭', '喂奶', '喂狗粮', '喂猫', '饲料', '吃饭']);
  const CALL = new Set(['喂，听得见吗', '喂，你好', '喂，你在吗', '哈喽', '你好', '在吗']);
  let data, cells = [], points = [], maxV = 0;
  // 点的位置是真实的，只有标签为了可读手动摆放。
  const LABEL = { '给孩子喂饭': [232, 530, 'right'], '喂饭': [296, 438, 'right'], '喂奶': [386, 484, 'left'], '喂狗粮': [392, 528, 'left'], '喂猫': [400, 432, 'left'],
    '喂，你好': [1226, 204, 'right'], '喂，你在吗': [1304, 216, 'left'], '喂，听得见吗': [1205, 318, 'right'], '光纤': [1628, 664, 'left'], '电报': [1630, 708, 'left'] };

  const screen = ([x, y]) => [960 + (x + .06) * 1720, 470 + y * 640];
  const colorOf = w => FEED.has(w) ? AMBER : CALL.has(w) ? CYAN : GRAY;

  return {
    async init() {
      data = await (await fetch('数据/pca.json')).json();
      points = data.words.map((w, i) => { const [x, y] = screen(data.pts[i]); return { w, x, y, color: colorOf(w) }; });
      maxV = Math.max(...data.vec0.map(Math.abs));
      const n = N * 12, c = offscreen(n, n), p = c.getContext('2d', { willReadFrequently: true });
      p.font = `600 ${n * .97}px ${SERIF}`; p.textAlign = 'center'; p.textBaseline = 'middle'; p.fillStyle = '#000';
      p.fillText('喂', n / 2, n / 2 + n * .03);
      const src = p.getImageData(0, 0, n, n).data, r = rng(21);
      for (let row = 0; row < N; row++) for (let col = 0; col < N; col++) {
        let s = 0;
        for (let y = 0; y < 12; y++) for (let x = 0; x < 12; x++) s += src[((row * 12 + y) * n + col * 12 + x) * 4 + 3];
        const i = row * N + col, v = data.vec0[i];
        cells.push({ i, ink: s / (144 * 255), v, x: GLYPH.x + (col - N / 2 + .5) * CS, y: GLYPH.y + (row - N / 2 + .5) * CS,
          target: i % points.length, ang: r() * 6.283, rad: 6 + r() * 34, delay: r() * .35, phase: r() * 6.283 });
      }
    },
    draw(t) {
      ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
      ctx.fillStyle = BG; ctx.fillRect(0, 0, W, H);

      // 字先散成 1024 格，再显出每一格的真实数值。
      const show = ss(.55, 1.5, t), fly = t => easeInOut((t - 2.15) / 1.15);
      for (const c of cells) {
        const local = fly(t - c.delay), tp = points[c.target];
        const tx = tp.x + Math.cos(c.ang + t * .25) * c.rad * (1 - ss(3.3, 4.2, t) * .75);
        const ty = tp.y + Math.sin(c.ang + t * .25) * c.rad * (1 - ss(3.3, 4.2, t) * .75);
        const x = lerp(c.x, tx, local), y = lerp(c.y, ty, local);
        const mag = Math.abs(c.v) / maxV;
        const lum = lerp(c.ink, .16 + Math.pow(mag, .55) * .84, show);
        const col = local > .5 ? tp.color : (c.v >= 0 ? FG : CYAN);
        const size = lerp(CS - 1.4, 2.6, local);
        ctx.globalAlpha = lerp(lum, .34, local);
        ctx.fillStyle = show < .02 ? FG : col;
        ctx.fillRect(x - size / 2, y - size / 2, size, size);
      }
      ctx.globalAlpha = 1;
      const ghost = ss(3.2, 3.8, t) * .09;
      if (ghost > 0) { ctx.globalAlpha = ghost; ctx.fillStyle = FG; ctx.font = `600 ${GLYPH.size}px ${SERIF}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('喂', GLYPH.x, GLYPH.y); ctx.globalAlpha = 1; }

      // 前几位真实数值。
      const list = ss(.9, 1.3, t) * (1 - ss(2.0, 2.35, t));
      if (list > 0) {
        ctx.font = `400 19px ${MONO}`; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; ctx.fillStyle = FG; ctx.globalAlpha = list * .7;
        const first = Math.floor(Math.max(0, t - .9) * 34);
        for (let i = 0; i < 26; i++) {
          const idx = (first + i) % 1024, v = data.vec0[idx];
          ctx.fillText(`${String(idx).padStart(4, ' ')}  ${v >= 0 ? ' ' : ''}${v.toFixed(5)}`, 1250, 150 + i * 24);
        }
        ctx.globalAlpha = 1;
      }

      // 真实相似度的连线。
      const links = [['喂，你在吗', '喂，你好', '0.82', 4.1, CYAN], ['喂猫', '喂饭', '0.79', 4.55, AMBER]];
      for (const [a, b, s, at, col] of links) {
        const k = easeOut((t - at) / .4); if (k <= 0) continue;
        const A = points.find(p => p.w === a), B = points.find(p => p.w === b);
        ctx.strokeStyle = col; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.moveTo(A.x, A.y); ctx.lineTo(lerp(A.x, B.x, k), lerp(A.y, B.y, k)); ctx.stroke();
      }

      // 点和标签按拍子落下。
      const order = [...points].sort((a, b) => a.x - b.x);
      order.forEach((p, i) => {
        const a = ss(3.25 + i * .045, 3.5 + i * .045, t); if (a <= 0) return;
        ctx.globalAlpha = a; ctx.fillStyle = p.color;
        ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, 7); ctx.fill();
        const [lx, ly, align] = LABEL[p.w] || [p.x + 20, p.y, 'left'];
        ctx.font = `500 29px ${SERIF}`; ctx.textAlign = align; ctx.textBaseline = 'middle'; ctx.fillStyle = FG;
        ctx.fillText(p.w, lx, ly);
      });
      ctx.globalAlpha = 1;

      // 字从中间分叉，连到两团。
      const fork = easeOut((t - 4.6) / .5);
      if (fork > 0) for (const [tx, ty, col] of [[430, 480, AMBER], [1225, 314, CYAN]]) {
        ctx.strokeStyle = col; ctx.globalAlpha = .55 * (1 - ss(5.8, 6, t)); ctx.lineWidth = 1.4; ctx.beginPath(); ctx.moveTo(GLYPH.x, GLYPH.y); ctx.lineTo(lerp(GLYPH.x, tx, fork), lerp(GLYPH.y, ty, fork)); ctx.stroke();
      }
      ctx.globalAlpha = 1;
      // 两团的名字。
      const name = ss(5.0, 5.4, t) * (1 - ss(5.8, 6, t) * .75);
      if (name > 0) {
        ctx.font = `600 72px ${SERIF}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.globalAlpha = name;
        ctx.fillStyle = AMBER; ctx.fillText('喂养', 300, 330);
        ctx.fillStyle = CYAN; ctx.fillText('叫你', 1390, 120);
        ctx.font = `500 28px ${SERIF}`; ctx.fillStyle = GRAY; ctx.fillText('它走过的路', 1590, 860);
        ctx.globalAlpha = 1;
      }

      // 反转：1955 年，这两个意思才合进同一个字。
      const dark = ss(5.8, 6, t);
      if (dark > 0) {
        ctx.globalAlpha = dark * .8; ctx.fillStyle = BG; ctx.fillRect(0, 0, W, 900); ctx.globalAlpha = 1;
        ctx.textBaseline = 'middle'; ctx.textAlign = 'center'; ctx.fillStyle = FG;
        ctx.font = `600 ${GLYPH.size}px ${SERIF}`; ctx.globalAlpha = dark; ctx.fillText('喂', GLYPH.x, GLYPH.y);
        const r = ss(6, 6.25, t);
        ctx.globalAlpha = r; ctx.fillStyle = AMBER; ctx.font = `500 120px ${SERIF}`; ctx.textAlign = 'left';
        ctx.fillText('〔餵餧〕', GLYPH.x + 210 + (1 - easeOut((t - 6) / .25)) * 40, GLYPH.y + 6);
        ctx.globalAlpha = 1;
      }
      const year = t < 5.8 ? 2026 : Math.round(lerp(2026, 1955, easeOut((t - 5.8) / .35)));
      hud({ year, form: dark > .5 ? '三个字并成一个' : t > 3.3 ? '一个位置' : '1024 个数', ink: FG, soft: 'rgba(233,230,223,.55)',
        caption: t < 3.8 ? '' : t < 5.8 ? '同一个字，落在两团' : '《第一批异体字整理表》',
        captionAlpha: t < 5.8 ? ss(3.8, 4.1, t) * (1 - ss(5.6, 5.8, t)) : ss(5.9, 6.15, t) });
      ctx.font = `400 16px ${MONO}`; ctx.textAlign = 'left'; ctx.fillStyle = 'rgba(233,230,223,.4)'; ctx.fillText('text-embedding-v3 · 1024d · PCA', 96, 948);
    },
  };
})();
