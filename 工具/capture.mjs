// 本地回环服务 + 无头 Chrome + CDP 逐帧取画布。无需安装依赖。
// 在作品文件夹里运行，页面入口是当前目录的 render.html：
// node ../../工具/capture.mjs stills 6,8
// node ../../工具/capture.mjs video out.mp4 --seconds 34 --from 60 --size 1920x1080 --fps 30 --page render.html
// stills 默认写到 ./stills，可用 --out 换目录，避免覆盖已有截帧。
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, extname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const tools = dirname(fileURLToPath(import.meta.url));
const here = process.cwd();
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FFMPEG = resolve(tools, '../.tools/ffmpeg/ffmpeg-n8.1-latest-win64-gpl-8.1/bin/ffmpeg.exe');
const [mode, arg, ...rest] = process.argv.slice(2);
const opt = (name, fallback) => { const i = rest.indexOf(`--${name}`); return i < 0 ? fallback : rest[i + 1]; };
const PAGE = opt('page', 'render.html'), OUT = resolve(here, opt('out', 'stills')), FPS = +opt('fps', 30), DURATION = +opt('seconds', 10), FROM = +opt('from', 0), [W, H] = opt('size', '1920x1080').split('x');
const MIME = { '.html': 'text/html; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.ttf': 'font/ttf' };
const server = createServer((req, res) => {
  const url = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const root = url.startsWith('/fonts/') ? tools : here;
  const p = join(root, url);
  if (!p.startsWith(root) || !existsSync(p)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': MIME[extname(p)] || 'application/octet-stream' }); createReadStream(p).pipe(res);
});
for (const [name, p] of [['Chrome', CHROME], ['ffmpeg', FFMPEG]]) if (!existsSync(p)) { console.error(`${name} 不存在：${p}`); process.exit(1); }
if (!['stills', 'video'].includes(mode) || !arg) { console.error('用法见文件开头：stills <秒,秒> 或 video <输出.mp4>'); process.exit(1); }
await new Promise(r => server.listen(0, '127.0.0.1', r));
// Chrome 子进程退出慢，临时目录常要等本进程退出后才能删。所有临时目录放在一处，
// 每次启动先删掉主人进程已经不在的旧目录；并行运行的目录主人还活着，不会被碰。
const PROFILES = join(tmpdir(), 'capture-profiles');
mkdirSync(PROFILES, { recursive: true });
const alive = pid => { try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; } };
for (const d of readdirSync(PROFILES)) {
  const dir = join(PROFILES, d);
  let owner = 0; try { owner = +readFileSync(join(dir, 'owner.pid'), 'utf8'); } catch {}
  if (owner && owner !== process.pid && !alive(owner)) try { rmSync(dir, { recursive: true, force: true }); } catch {}
}
const profile = mkdtempSync(join(PROFILES, 'cap-'));
writeFileSync(join(profile, 'owner.pid'), String(process.pid));
const chrome = spawn(CHROME, ['--headless=new', '--use-angle=d3d11', '--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
  `--user-data-dir=${profile}`, '--remote-debugging-port=0', `--window-size=${W},${H}`, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
const exited = new Promise(r => { chrome.once('exit', r); chrome.once('error', r); });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ws, devPort, id = 0; const pending = new Map();
const send = (method, params = {}) => new Promise((ok, no) => { const i = ++id; pending.set(i, { ok, no }); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async expr => {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 700));
  return r.result.value;
};
const frame = t => evaluate(`renderAsync(${t}).then(()=>document.getElementById('c').toDataURL('image/jpeg',.96).split(',')[1])`);

async function main() {
  const portFile = join(profile, 'DevToolsActivePort');
  for (let i = 0; i < 600 && !existsSync(portFile); i++) await sleep(100);
  const port = readFileSync(portFile, 'utf8').split('\n')[0];
  const page = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(x => x.type === 'page');
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = no; });
  ws.onmessage = e => { const m = JSON.parse(e.data), p = pending.get(m.id); if (p) { pending.delete(m.id); m.error ? p.no(new Error(m.error.message)) : p.ok(m.result); } };
  await send('Page.enable'); await send('Runtime.enable');
  await send('Page.navigate', { url: `http://127.0.0.1:${server.address().port}/${PAGE}` });
  for (let i = 0; i < 100; i++) { if (await evaluate(`typeof window.ready==='object'`).catch(() => false)) break; await sleep(100); }
  await evaluate('window.ready');
  if (mode === 'stills') {
    mkdirSync(OUT, { recursive: true });
    for (const t of arg.split(',')) writeFileSync(join(OUT, `t${t}.jpg`), Buffer.from(await frame(+t), 'base64'));
    return;
  }
  const ff = spawn(FFMPEG, ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', 'pipe:0',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', resolve(arg)], { windowsHide: true, stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((ok, no) => { ff.on('error', no); ff.on('close', code => code === 0 ? ok() : no(new Error(`ffmpeg ${code}`))); });
  let ffDead = null; ff.stdin.on('error', e => { ffDead = e; }); ff.on('close', () => { ffDead ??= new Error('ffmpeg 提前退出'); });
  const total = FPS * DURATION;
  for (let i = 0; i < total; i++) {
    if (ffDead) throw ffDead;
    const buf = Buffer.from(await frame(FROM + i / FPS), 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${total}`);
  }
  ff.stdin.end(); await done;
}
try { await main(); }
catch (e) { console.error(e); process.exitCode = 1; }
finally {
  try { ws?.close(); } catch {}
  // 先让 Chrome 自己关（带走 GPU/渲染子进程），5 秒没关再按 PID 结束我们自己启动的整棵进程树。
  if (chrome.exitCode === null && devPort) {
    try {
      const { webSocketDebuggerUrl } = await (await fetch(`http://127.0.0.1:${devPort}/json/version`, { signal: AbortSignal.timeout(2000) })).json();
      const b = new WebSocket(webSocketDebuggerUrl);
      await Promise.race([new Promise(r => { b.onopen = r; b.onerror = r; }), sleep(2000)]);
      if (b.readyState === 1) b.send(JSON.stringify({ id: 1, method: 'Browser.close' }));
    } catch {}
  }
  const closed = await Promise.race([exited.then(() => true), sleep(5000).then(() => false)]);
  if (!closed && chrome.exitCode === null && chrome.pid) {
    if (process.platform === 'win32') spawn('taskkill', ['/PID', String(chrome.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
    else chrome.kill('SIGKILL');
    await Promise.race([exited, sleep(5000)]);
  }
  // 浏览器主进程退了，GPU/渲染子进程有时还挂着并锁住临时目录。临时目录名每次唯一，按它认领并结束。
  if (process.platform === 'win32') {
    const ps = `Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -like '*${profile}*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $_.ProcessId }`;
    const killer = spawn('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', ps], { windowsHide: true, stdio: ['ignore', 'pipe', 'ignore'] });
    let out = ''; killer.stdout.on('data', d => { out += d; });
    await Promise.race([new Promise(r => killer.once('close', r)), sleep(15000)]);
    if (out.trim()) console.error(`回收了残留的 Chrome 子进程：${out.trim().split(/\s+/).join(', ')}`);
  }
  server.close();
  await sleep(300);
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 }); } catch { console.error(`临时目录暂时被占用，下次运行时清理：${profile}`); }
}
