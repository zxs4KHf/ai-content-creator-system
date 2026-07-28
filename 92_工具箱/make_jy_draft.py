#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成剪映草稿工程 —— 用于爆款候选的人工精修

定位: **不是主流水线**。主流水线是 build_video.py 全自动出片。
      只有数据回流后的前 5% 爆款候选才走这条, 用剪映独占的花字/气泡/官方特效包做精包装。

三条必须知道的版本限制:
  ┌──────────────────────┬────────────────────────┐
  │ 草稿生成(我们用的)    │ 剪映 5 及以上全版本 ✅  │  ← 没被封
  │ 模板模式(读已有草稿)  │ 仅 ≤5.9  ❌ 6+ 已加密   │
  │ 批量自动导出          │ 仅 ≤6    ❌ 7+ 封了 UI  │
  └──────────────────────┴────────────────────────┘

  **不要尝试自动导出。** 剪映主流版本已到 10.x, 硬做会一直碎。
  手动点导出正好是 G3 人工门, 反而契合流程设计。

三个坑:
  1. **音频必须用 WAV 不用 MP3** —— 已知 issue: VBR MP3 读时长会少于实际并报错
  2. **锁定版本 0.2.7** —— v0.3.0 有破坏性变更 (add_track -> append_track)
  3. **中文枚举成员名各版本在变** —— 用 --list-enums 先打印本机实际可用的, 不要照抄

依赖:
    pip install "pyJianYingDraft==0.2.7"

用法:
    # 先看看本机剪映支持哪些转场/动画名
    python make_jy_draft.py --list-enums

    python make_jy_draft.py \
        --images "../02_制作中/xxx/素材/img/*.png" \
        --audio  "../02_制作中/xxx/素材/audio/narration.wav" \
        --srt    "../02_制作中/xxx/素材/narration.srt" \
        --name   "最后一位图书管理员" \
        --draft-folder "C:/Users/你的用户名/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft"

草稿目录路径从剪映「全局设置 → 草稿位置」复制, **不要猜**。
"""

import argparse
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

W, H = 1080, 1920


def die(msg):
    sys.exit(f"[错误] {msg}")


def load_lib():
    try:
        import pyJianYingDraft as draft
    except ImportError:
        die("缺少依赖: pip install \"pyJianYingDraft==0.2.7\"\n"
            "     注意锁 0.2.7, v0.3.0 有破坏性变更 (add_track -> append_track)")
    return draft


def list_enums():
    """打印本机实际可用的枚举 —— 中文成员名各版本在变, 照抄会 AttributeError"""
    draft = load_lib()
    for name in ("TransitionType", "IntroType", "OutroType", "FontType"):
        enum = getattr(draft, name, None)
        if enum is None:
            print(f"{name}: (本版本没有这个枚举)")
            continue
        members = [m.name for m in enum]
        print(f"\n{name}  共 {len(members)} 项:")
        for i in range(0, len(members), 6):
            print("   " + "  ".join(members[i:i + 6]))


def pick(enum, *candidates):
    """从候选里挑第一个本版本真实存在的枚举成员, 都没有就返回 None"""
    if enum is None:
        return None
    names = {m.name: m for m in enum}
    for c in candidates:
        if c in names:
            return names[c]
    return None


# ---------------------------------------------------------------- SRT

_TS = re.compile(
    r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")


def parse_srt(path):
    raw = Path(path).read_text(encoding="utf-8-sig")
    cues = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        m = None
        body_start = 0
        for i, l in enumerate(lines[:2]):
            m = _TS.search(l)
            if m:
                body_start = i + 1
                break
        if not m:
            continue

        def hms(h, mi, s, ms):
            return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000

        st = hms(*m.groups()[:4])
        en = hms(*m.groups()[4:])
        text = " ".join(lines[body_start:]).strip()
        if text:
            cues.append((st, en, text))
    return cues


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True).stdout.strip()
    return float(out)


def slots_from_cues(cues, n_images, total):
    """把字幕条按图片数均分成 n 段, 返回每张图的 (start, end)"""
    if not cues:
        d = total / n_images
        return [(i * d, (i + 1) * d) for i in range(n_images)]
    per = max(1, round(len(cues) / n_images))
    slots, idx = [], 0
    for i in range(n_images):
        start = cues[idx][0] if idx < len(cues) else total
        idx = min(len(cues), idx + per) if i < n_images - 1 else len(cues)
        end = cues[idx][0] if idx < len(cues) else total
        slots.append((start, max(end, start + 0.5)))
    slots[-1] = (slots[-1][0], total)
    return slots


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="生成剪映草稿工程")
    ap.add_argument("--list-enums", action="store_true",
                    help="打印本机剪映实际可用的转场/动画/字体枚举名")
    ap.add_argument("--images", nargs="+")
    ap.add_argument("--audio", help="[注意] 必须是 WAV, MP3 会触发时长读取 bug")
    ap.add_argument("--srt")
    ap.add_argument("--name", default="ai_draft", help="草稿名")
    ap.add_argument("--draft-folder",
                    help="剪映草稿目录, 从「全局设置 → 草稿位置」复制")
    ap.add_argument("--transition", type=float, default=0.5, help="转场时长(秒)")
    args = ap.parse_args()

    if args.list_enums:
        list_enums()
        return

    for req in ("images", "audio", "draft_folder"):
        if not getattr(args, req):
            die(f"需要 --{req.replace('_', '-')}")

    draft = load_lib()

    images = []
    for pat in args.images:
        hit = sorted(glob.glob(pat))
        images.extend(hit if hit else [pat])
    images = [p for p in images if os.path.isfile(p)]
    if not images:
        die("没有找到任何图片")

    audio = Path(args.audio)
    if not audio.exists():
        die(f"音频不存在: {audio}")
    if audio.suffix.lower() != ".wav":
        print(f"[注意] 音频不是 WAV ({audio.suffix})。已知 issue: VBR MP3 读时长会少于实际并报错。")
        print(f"   建议先转: ffmpeg -i {audio.name} -ar 44100 -ac 2 narration.wav")

    total = probe_duration(audio)
    cues = parse_srt(args.srt) if args.srt else []
    slots = slots_from_cues(cues, len(images), total)

    print(f"图 {len(images)} 张 ｜ 音频 {total:.2f}s ｜ 字幕 {len(cues)} 条")

    # 用绝对路径 —— 剪映不认相对路径
    folder = draft.DraftFolder(str(Path(args.draft_folder).resolve()))
    script = folder.create_draft(args.name, W, H, allow_replace=True)
    script.add_track(draft.TrackType.audio)
    script.add_track(draft.TrackType.video)
    script.add_track(draft.TrackType.text)

    # --- 音频 ---
    a = draft.AudioSegment(str(audio.resolve()),
                           draft.trange("0s", f"{total:.3f}s"), volume=0.9)
    a.add_fade("0.4s", "0.6s")
    script.add_segment(a)

    # --- 图片 ---
    # 枚举成员名各版本在变, 用 pick() 优雅降级而不是硬编码
    intro = pick(getattr(draft, "IntroType", None), "渐显", "淡入", "轻微放大")
    trans = pick(getattr(draft, "TransitionType", None), "叠化", "溶解", "闪黑")

    for i, (img, (st, en)) in enumerate(zip(images, slots)):
        dur = max(en - st, 0.5)
        seg = draft.VideoSegment(str(Path(img).resolve()),
                                 draft.trange(f"{st:.3f}s", f"{dur:.3f}s"))
        if intro:
            seg.add_animation(intro)
        try:
            seg.add_background_filling("blur", 0.0625)   # 非 9:16 素材的背景填充
        except Exception:
            pass
        if trans and i < len(images) - 1:
            try:
                seg.add_transition(trans, duration=draft.tim(f"{args.transition}s"))
            except Exception as e:
                print(f"  转场跳过(镜{i+1}): {e}")
        script.add_segment(seg)

    # --- 字幕 ---
    if cues:
        font = pick(getattr(draft, "FontType", None), "文轩体", "思源黑体", "默认")
        for st, en, text in cues:
            kw = {}
            if font:
                kw["font"] = font
            try:
                script.add_segment(draft.TextSegment(
                    text.replace("\n", " "),
                    draft.trange(f"{st:.3f}s", f"{max(en-st, 0.3):.3f}s"),
                    style=draft.TextStyle(size=8.0, color=(1.0, 1.0, 1.0), align=1,
                                          auto_wrapping=True, max_line_width=0.82),
                    clip_settings=draft.ClipSettings(transform_y=-0.72),
                    **kw))
            except Exception as e:
                die(f"字幕写入失败: {e}\n"
                    f"     TextStyle/ClipSettings 的参数名在版本间有差异, "
                    f"请先跑 --list-enums 并核对本机 pyJianYingDraft 的 API。")

    script.save()
    print(f"\n草稿已生成: {args.name}")
    print(f"位置: {args.draft_folder}")
    print("\n下一步(这就是 G3 人工门):")
    print("  1. 打开剪映, 在草稿列表里找到它")
    print("  2. 加花字/气泡字幕/官方特效包 —— 这是剪映独占、ffmpeg 做不了的部分")
    print("  3. 手动点导出 (剪映 7+ 已封自动导出, 不要尝试脚本化)")


if __name__ == "__main__":
    main()
