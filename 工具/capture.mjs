// 本地回环服务 + 无头 Chrome + CDP 逐帧取画布。无需安装依赖。
// 在作品文件夹里运行，页面入口是当前目录的 render.html：
// node ../../工具/capture.mjs stills 6,8
// node ../../工具/capture.mjs video out.mp4 --seconds 34 --size 1920x1080 --fps 30
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, extname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const tools = dirname(fileURLToPath(import.meta.url));
const here = process.cwd();
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FFMPEG = resolve(tools, '../.tools/ffmpeg/ffmpeg-n8.1-latest-win64-gpl-8.1/bin/ffmpeg.exe');
const [mode, arg, ...rest] = process.argv.slice(2);
const opt = (name, fallback) => { const i = rest.indexOf(`--${name}`); return i < 0 ? fallback : rest[i + 1]; };
const FPS = +opt('fps', 30), DURATION = +opt('seconds', 10), [W, H] = opt('size', '1920x1080').split('x');
const MIME = { '.html': 'text/html; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.ttf': 'font/ttf' };
const server = createServer((req, res) => {
  const url = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const root = url.startsWith('/fonts/') ? tools : here;
  const p = join(root, url);
  if (!p.startsWith(root) || !existsSync(p)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': MIME[extname(p)] || 'application/octet-stream' }); createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const profile = mkdtempSync(join(tmpdir(), 'cap-'));
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
  `--user-data-dir=${profile}`, '--remote-debugging-port=0', `--window-size=${W},${H}`, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
const exited = new Promise(r => chrome.once('exit', r));
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ws, id = 0; const pending = new Map();
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
  await send('Page.navigate', { url: `http://127.0.0.1:${server.address().port}/render.html` });
  for (let i = 0; i < 100; i++) { if (await evaluate(`typeof window.ready==='object'`).catch(() => false)) break; await sleep(100); }
  await evaluate('window.ready');
  if (mode === 'stills') {
    mkdirSync(join(here, 'stills'), { recursive: true });
    for (const t of arg.split(',')) writeFileSync(join(here, 'stills', `t${t}.jpg`), Buffer.from(await frame(+t), 'base64'));
    return;
  }
  const ff = spawn(FFMPEG, ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', 'pipe:0',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', resolve(arg)], { windowsHide: true, stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((ok, no) => ff.on('close', code => code === 0 ? ok() : no(new Error(`ffmpeg ${code}`))));
  const total = FPS * DURATION;
  for (let i = 0; i < total; i++) {
    const buf = Buffer.from(await frame(i / FPS), 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${total}`);
  }
  ff.stdin.end(); await done;
}
try { await main(); }
catch (e) { console.error(e); process.exitCode = 1; }
finally {
  try { ws?.close(); } catch {}
  chrome.kill();
  await Promise.race([exited, sleep(5000)]);
  server.close();
  await sleep(300);
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }); } catch {}
}
