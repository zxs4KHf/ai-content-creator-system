# 程序合成音效。全黑段（17.6-19.6 秒）必须完全无声，这是全片的落差所在。
import numpy as np, wave
SR = 44100; DUR = 34; N = SR * DUR; rng = np.random.default_rng(31)
X = np.zeros(N)
def add(at, sig, g=1.0):
    i = int(at * SR)
    if i >= N: return
    e = min(N, i + len(sig)); X[i:e] += sig[:e - i] * g
def lp(x, k):
    from numpy import convolve
    n = max(1, int(1 / k)); return np.convolve(x, np.ones(n) / n, 'same')
def tone(f, d, a=.003, dec=.1):
    n = int(d * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t) * np.minimum(t / a, 1) * np.exp(-t / dec)
def drum(f=62, d=.7):
    n = int(d * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (f * t + 34 * (1 - np.exp(-t * 26)) / 26)) * np.exp(-t / .2)
    hit = lp(rng.normal(0, 1, n), .04) * np.exp(-t / .012) * 3
    return body + hit
def fire(a, b, g):
    n = int((b - a) * SR); r = lp(rng.normal(0, 1, n), .004) * 6
    fade = np.minimum(np.arange(n) / (.6 * SR), 1) * np.minimum((n - np.arange(n)) / (.3 * SR), 1)
    add(a, r * fade, g)
    for _ in range(int((b - a) * 11)):
        m = int(.03 * SR); t = np.arange(m) / SR
        add(rng.uniform(a, b - .05), rng.normal(0, 1, m) * np.exp(-t / rng.uniform(.002, .008)), g * rng.uniform(.12, .5))
fire(0, 5.4, .5)
for at, f in ((5.05, 58), (6.55, 62), (9.35, 66), (11.95, 70)): add(at, drum(f, 1.2), .9)
# 持续低音：从拉远开始累积到骤停
n = int((17.56 - 5) * SR); t = np.arange(n) / SR; k = t / t[-1]
bed = (np.sin(2 * np.pi * (44 * t + 9 * t * t / 12.56)) + .55 * np.sin(2 * np.pi * (66.4 * t + 21 * t * t / 12.56))) * (.12 + .88 * k ** 3)
add(5, bed, .34)
# 鼓点加速：间隔从 0.8 秒压到 0.07 秒，17.56 秒硬切
at = 13.0; gap = .8
while at < 17.5:
    add(at, drum(70, .32), .75); at += gap; gap = max(.07, gap * .84)
for i in range(420):  # 话语涌入：细碎的人声质感噪点
    b = 14.3 + 2.75 * np.sqrt(rng.uniform()); m = int(.05 * SR); w = np.arange(m) / SR
    add(b, np.sin(2 * np.pi * rng.uniform(300, 2200) * w) * np.exp(-w / .018), .035)
X[int(17.56 * SR):] = 0  # 硬切
s = np.array(X)
X[:] = 0; 
for a, b, f in ((19.6, 19.95, 3), (20.9, 22.5, 12), (23.4, 25.5, 13)):  # 敲字，极轻
    for i in range(f):
        m = int(.02 * SR); w = np.arange(m) / SR
        add(a + (b - a) * i / f, rng.normal(0, 1, m) * np.exp(-w / .004), .09)
add(20.3, tone(38, 6, .8, 3.2), .16)  # 极低的压迫音，几乎听不到
# 冲进光标
n = int(.46 * SR); w = np.arange(n) / SR
add(26.55, np.sin(2 * np.pi * (40 * w + 340 * w * w)) * (w / w[-1]) ** 2, .6); add(26.55, lp(rng.normal(0, 1, n), .02) * 5 * (w / w[-1]) ** 3, .5)
s2 = np.array(X); X[:] = 0
fire(27, 33, .5)
add(30.4, tone(46, 2.6, .9, 1.2), .55)  # 转头对视时的压迫
add(33, np.zeros(10))
s3 = np.array(X); s3[int(33 * SR):] = 0
mix = s + s2 + s3; mix = mix / np.abs(mix).max() * .9
R = np.zeros(N); d = int(.009 * SR); R[d:] = mix[:-d]; R = mix * .8 + R * .5
st = np.stack([mix, R], 1); st = st / np.abs(st).max() * .9
with wave.open('sfx.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype('<i2').tobytes())
print('ok')
