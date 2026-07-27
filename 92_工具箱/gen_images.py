#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量生图 —— Gemini / Nano Banana

两种模式:
  sheet : 生成角色定妆照(三视图),一次出 N 张候选供人工挑选
  shots : 读 02_分镜脚本.md, 批量生成全片分镜, 带"滚动锚定"保持风格连续

滚动锚定(rolling anchor): 每出一张满意的分镜就加入参考图池、替换掉最早的一张,
让画风沿着片子自然演进而不是突变。这是跨镜一致性的关键技巧。

依赖:
    pip install -U google-genai
    export GEMINI_API_KEY=xxx        # Windows: set GEMINI_API_KEY=xxx

用法:
    # 定妆照(用最贵档位,一次投入全片受益)
    python gen_images.py --mode sheet --character ../00_账号定位/角色资产库/C001_xxx.md \
        --out ../00_账号定位/角色资产库/C001_素材/ --n 4 --model pro --size 4K --ratio 16:9

    # 批量分镜
    python gen_images.py --mode shots --script ../02_制作中/xxx/02_分镜脚本.md \
        --refs ../00_账号定位/角色资产库/C001_素材/ \
        --out ../02_制作中/xxx/素材/img/ --model flash --size 2K --ratio 9:16

    # 重出第 5 镜(会自动带上已通过的邻近镜作参考)
    python gen_images.py --mode shots --script ... --out ... --redo 5

    # 只打印将要发送的提示词,不真的调 API
    python gen_images.py --mode shots --script ... --out ... --dry-run
"""

import argparse
import base64
import concurrent.futures
import os
import re
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------- 模型档位

MODELS = {
    # 别名        模型 ID                      说明
    "pro":   "gemini-3-pro-image",       # 最多 5 个角色参考 + 3 个风格参考, $0.134/张(1K/2K)
    "flash": "gemini-3.1-flash-image",   # 最多 4 个角色参考, 便宜, 批量分镜用这个
    "lite":  "gemini-3.1-flash-lite-image",
    "25":    "gemini-2.5-flash-image",   # 旧款, $0.039/张, 最便宜
}

# 注意: image_size 必须大写 K, 小写会被 API 拒绝
VALID_SIZES = {"0.5K", "1K", "2K", "4K"}
VALID_RATIOS = {"1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}

MAX_REFS = 4          # 参考图池上限(flash 档角色参考上限是 4)
CONCURRENCY = 3       # API 并发, 不要调高, 会触发速率限制
RETRY = 3


# ---------------------------------------------------------------- API 调用

def _client():
    try:
        from google import genai
    except ImportError:
        sys.exit("缺少依赖: pip install -U google-genai")
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        sys.exit("未设置 GEMINI_API_KEY 环境变量。\n"
                 "  Linux/Mac: export GEMINI_API_KEY=xxx\n"
                 "  Windows  : set GEMINI_API_KEY=xxx\n"
                 "注意: 图像生成没有免费额度, 需要绑定计费账户。")
    return genai.Client()


def _extract_image_bytes(resp):
    """从各种可能的响应结构里把图片 bytes 抠出来。

    SDK 的响应结构在不同版本间有差异, 这里做兼容处理:
    不要假设某一种结构, 逐个尝试。
    """
    # 形态 1: resp.output_image.data (base64 str 或 bytes)
    img = getattr(resp, "output_image", None)
    if img is not None:
        data = getattr(img, "data", None)
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        if isinstance(data, str):
            return base64.b64decode(data)

    # 形态 2: candidates[].content.parts[].inline_data.data
    for cand in (getattr(resp, "candidates", None) or []):
        content = getattr(cand, "content", None)
        for part in (getattr(content, "parts", None) or []):
            inline = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
            if inline is not None:
                data = getattr(inline, "data", None)
                if isinstance(data, (bytes, bytearray)):
                    return bytes(data)
                if isinstance(data, str):
                    return base64.b64decode(data)

    # 形态 3: resp.generated_images[].image.image_bytes
    for gi in (getattr(resp, "generated_images", None) or []):
        image = getattr(gi, "image", None)
        data = getattr(image, "image_bytes", None)
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)

    raise RuntimeError("响应里没找到图片数据。请打印 resp 检查 SDK 版本的响应结构。")


def generate(client, model_id, prompt, ref_paths=(), size="2K", ratio="9:16"):
    """调 API 出一张图, 返回 bytes。

    SDK 的图像生成接口在不同版本有两种调用形态, 这里都试一遍。
    """
    refs = []
    for p in ref_paths:
        refs.append({
            "type": "image",
            "data": base64.b64encode(Path(p).read_bytes()).decode(),
            "mime_type": "image/png",
        })

    last_err = None

    # 形态 A: client.interactions.create(...)
    try:
        payload = [{"type": "text", "text": prompt}] + refs if refs else prompt
        resp = client.interactions.create(
            model=model_id,
            input=payload,
            response_format={
                "type": "image",
                "mime_type": "image/png",
                "aspect_ratio": ratio,
                "image_size": size,          # 必须大写 K
            },
        )
        return _extract_image_bytes(resp)
    except AttributeError as e:
        last_err = e
    except TypeError as e:
        last_err = e

    # 形态 B: client.models.generate_content(...)
    try:
        from google.genai import types
        parts = [prompt]
        for p in ref_paths:
            parts.append(types.Part.from_bytes(
                data=Path(p).read_bytes(), mime_type="image/png"))
        resp = client.models.generate_content(
            model=model_id,
            contents=parts,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=ratio),
            ),
        )
        return _extract_image_bytes(resp)
    except Exception as e:
        raise RuntimeError(
            f"两种调用形态都失败。\n形态A: {last_err}\n形态B: {e}\n"
            f"请检查 google-genai 版本 (pip install -U google-genai) 与模型 ID: {model_id}"
        )


def generate_with_retry(client, model_id, prompt, ref_paths, size, ratio, label=""):
    for attempt in range(1, RETRY + 1):
        try:
            return generate(client, model_id, prompt, ref_paths, size, ratio)
        except Exception as e:
            if attempt == RETRY:
                print(f"  [FAIL] {label} 重试 {RETRY} 次仍失败: {e}", file=sys.stderr)
                return None
            wait = 2 ** attempt
            print(f"  [retry {attempt}/{RETRY}] {label}: {e} — {wait}s 后重试", file=sys.stderr)
            time.sleep(wait)


# ---------------------------------------------------------------- 分镜脚本解析

def clean_prompt(s):
    """清洗从 markdown 表格里抠出来的提示词。

    表格里的提示词常带着排版噪音: 反引号、<br> 换行、中文注记(如 "(拼 LIN)")。
    这些直接发给 API 会污染生成结果, 必须去掉。
    """
    s = s.strip()
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)     # 表格内换行
    s = s.replace("\\|", "|")                         # 表格转义的竖线
    s = re.sub(r"`{1,3}", "", s)                      # 反引号
    # 去掉纯中文的括号注记(英文提示词里不该有中文)
    s = re.sub(r"[（(][^）)]*[一-鿿][^）)]*[)）]", "", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip(" *_")


def parse_shots(md_path):
    """从 02_分镜脚本.md 抽取每镜的生图提示词。

    支持两种写法:
      1) markdown 表格, 表头含"生图提示词", 取该列
      2) 独立段落, 形如  ### 镜 3 ... ```prompt ... ```
    返回 [(镜号, 提示词), ...]
    """
    text = Path(md_path).read_text(encoding="utf-8")
    shots = []

    # --- 写法 1: 表格 ---
    lines = text.splitlines()
    header_idx = None
    prompt_col = None
    shot_col = None
    for i, line in enumerate(lines):
        if "|" not in line or "生图提示词" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        for j, c in enumerate(cells):
            if "生图提示词" in c:
                prompt_col = j
            if "镜号" in c or c in ("镜", "#"):
                shot_col = j
        if prompt_col is not None:
            header_idx = i
            break

    if header_idx is not None:
        for line in lines[header_idx + 1:]:
            s = line.strip()
            if not s.startswith("|"):
                if shots:
                    break
                continue
            if re.fullmatch(r"\|[\s\-:|]+\|", s):     # 分隔行
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if prompt_col >= len(cells):
                continue
            prompt = clean_prompt(cells[prompt_col])
            if not prompt or prompt in ("-", "—"):
                continue
            num = None
            if shot_col is not None and shot_col < len(cells):
                m = re.search(r"\d+", cells[shot_col])
                if m:
                    num = int(m.group())
            shots.append((num if num is not None else len(shots) + 1, prompt))

    # --- 写法 2: 代码块 ---
    if not shots:
        pattern = re.compile(
            r"###\s*镜\s*(\d+).*?```(?:prompt|text)?\s*\n(.*?)```",
            re.S,
        )
        for m in pattern.finditer(text):
            shots.append((int(m.group(1)), clean_prompt(m.group(2))))

    if not shots:
        sys.exit(f"没能从 {md_path} 解析出任何生图提示词。\n"
                 f"请确认分镜表里有'生图提示词'列, 或用 ### 镜 N + ``` 代码块的写法。")
    return shots


def parse_block(md_path, block_name):
    """抽取 STYLE LOCK / CHARACTER LOCK 等全局块(在 【】 或 ## 标题之后的段落)"""
    text = Path(md_path).read_text(encoding="utf-8")
    m = re.search(
        rf"(?:【\s*{block_name}[^】]*】|#+\s*{block_name}[^\n]*)\n+(.*?)(?=\n【|\n#+\s|\Z)",
        text, re.S | re.I,
    )
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------- 模式实现

def mode_sheet(args, client, model_id):
    """生成角色定妆照(三视图), 出 N 张候选"""
    char_md = Path(args.character)
    if not char_md.exists():
        sys.exit(f"角色卡不存在: {char_md}")

    char_lock = parse_block(char_md, "CHARACTER LOCK") or char_md.read_text(encoding="utf-8")
    style_lock = parse_block(char_md, "STYLE LOCK")

    prompt = (
        "A character reference sheet of a single character, on a plain neutral grey background.\n"
        f"The character: {char_lock}\n"
        "Show three views side by side: front view, three-quarter view, and side profile. "
        "Same height, same lighting, neutral expression, arms relaxed.\n"
        f"{style_lock}"
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"生成定妆照候选 ×{args.n}  模型={model_id}  {args.size} {args.ratio}")
    if args.dry_run:
        print("\n--- 提示词 ---\n" + prompt)
        return

    def one(i):
        data = generate_with_retry(client, model_id, prompt, [], args.size, args.ratio,
                                   label=f"sheet_{i}")
        if data:
            p = out / f"sheet_cand_{i:02d}.png"
            p.write_bytes(data)
            print(f"  [OK] {p}")
            return p
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        list(ex.map(one, range(1, args.n + 1)))

    print(f"\n完成。请人工挑 1 张最符合的, 然后裁成 front/three_quarter/profile 三张独立图,")
    print(f"存回 {out}, 再用 --mode shots 批量出分镜。")


def mode_shots(args, client, model_id):
    """批量生成分镜, 带滚动锚定"""
    shots = parse_shots(args.script)
    if args.redo:
        shots = [s for s in shots if s[0] in args.redo]
        if not shots:
            sys.exit(f"--redo {args.redo} 在分镜脚本里找不到对应镜号")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # 初始参考图池: 角色资产包
    ref_pool = []
    if args.refs:
        refs_dir = Path(args.refs)
        if refs_dir.is_dir():
            ref_pool = sorted(
                [p for p in refs_dir.iterdir()
                 if p.suffix.lower() in (".png", ".jpg", ".jpeg")
                 and "cand" not in p.name],
            )[:MAX_REFS]
        elif refs_dir.is_file():
            ref_pool = [refs_dir]

    print(f"共 {len(shots)} 镜  模型={model_id}  {args.size} {args.ratio}")
    print(f"参考图池({len(ref_pool)}): {[p.name for p in ref_pool]}")
    if not ref_pool:
        print("  ⚠️ 没有参考图! 角色跨镜一致性会很差。建议先跑 --mode sheet 出定妆照。")

    if args.dry_run:
        for num, prompt in shots:
            print(f"\n--- 镜 {num} ---\n{prompt}")
        return

    # 滚动锚定 => 必须串行(后一镜依赖前一镜的产物)
    # 想要速度可以关掉锚定用 --no-anchor, 但一致性会下降
    done = []
    for num, prompt in shots:
        label = f"镜{num}"
        data = generate_with_retry(client, model_id, prompt, [str(p) for p in ref_pool],
                                   args.size, args.ratio, label=label)
        if not data:
            continue
        p = out / f"shot_{num:02d}.png"
        p.write_bytes(data)
        done.append(p)
        print(f"  [OK] {label} -> {p.name}  (参考 {len(ref_pool)} 张)")

        if not args.no_anchor:
            # 滚动锚定: 新图入池, 挤掉最早的一张
            ref_pool.append(p)
            if len(ref_pool) > MAX_REFS:
                ref_pool.pop(0)

    print(f"\n完成 {len(done)}/{len(shots)} 张 -> {out}")
    print("请人工过一遍: 手指 / 文字乱码 / 角色漂移 / 构图越界。")
    print("单张不满意用 --redo N 重出; 反复出不好的关键镜转 GPT 网页手动补。")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="批量生图 (Gemini / Nano Banana)")
    ap.add_argument("--mode", choices=["sheet", "shots"], required=True)
    ap.add_argument("--character", help="[sheet] 角色卡 md 路径")
    ap.add_argument("--script", help="[shots] 02_分镜脚本.md 路径")
    ap.add_argument("--refs", help="[shots] 参考图目录(角色资产包)")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--n", type=int, default=4, help="[sheet] 候选张数")
    ap.add_argument("--redo", type=int, nargs="+", help="[shots] 只重出这几个镜号")
    ap.add_argument("--model", default="flash", choices=list(MODELS),
                    help="pro=最强一致性(贵) flash=批量分镜(默认) 25=最便宜")
    ap.add_argument("--size", default="2K", help="0.5K / 1K / 2K / 4K (必须大写 K)")
    ap.add_argument("--ratio", default="9:16", help="9:16 竖版视频 / 3:4 小红书 / 21:9 公众号头图")
    ap.add_argument("--no-anchor", action="store_true", help="关闭滚动锚定(更快但一致性下降)")
    ap.add_argument("--dry-run", action="store_true", help="只打印提示词, 不调 API")
    args = ap.parse_args()

    if args.size not in VALID_SIZES:
        sys.exit(f"--size 必须是 {VALID_SIZES} 之一(注意 K 要大写)")
    if args.ratio not in VALID_RATIOS:
        sys.exit(f"--ratio 必须是 {VALID_RATIOS} 之一")

    model_id = MODELS[args.model]
    client = None if args.dry_run else _client()

    if args.mode == "sheet":
        if not args.character:
            sys.exit("--mode sheet 需要 --character")
        mode_sheet(args, client, model_id)
    else:
        if not args.script:
            sys.exit("--mode shots 需要 --script")
        mode_shots(args, client, model_id)


if __name__ == "__main__":
    main()
