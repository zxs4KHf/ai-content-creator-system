#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片轮播时长按配音分段自动对齐 -> 生成并执行 ffmpeg 命令
输入: 图片列表 + 每段字幕的起止时间 (srt/ass 文件或直接给 list)
输出: 1080x1920 竖版短视频, 每张图正好覆盖对应旁白段落, 带 Ken Burns + xfade + 烧录字幕

只依赖 Python 标准库 + ffmpeg/ffprobe。
用法:
    python3 build_video.py --images img/*.png --srt sub.srt --audio narration.mp3 --out final.mp4
"""

import argparse
import glob
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

W, H = 1080, 1920
FPS = 25
UPSCALE = 4            # zoompan 抗抖动: 先放大 4 倍
XFADE_TRANSITIONS = [
    "fade", "dissolve", "smoothleft", "smoothright",
    "circleopen", "fadeblack", "wipeleft", "slideup",
]


# ---------------------------------------------------------------- 工具

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def probe_duration(path):
    """用 ffprobe 取媒体时长(秒)"""
    out = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ]).stdout.strip()
    return float(out)


def slots_from_manifest(path, audio_duration):
    """用 TTS manifest 的原始分段作为图片时轴，字幕拆细后仍保持一镜一段。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    segments = data.get("segments", [])
    if not segments:
        raise ValueError(f"manifest 没有 segments: {path}")
    slots = []
    for i, seg in enumerate(segments):
        start = float(seg["start_s"])
        end = (float(segments[i + 1]["start_s"])
               if i + 1 < len(segments) else float(audio_duration))
        slots.append((start, max(start + 0.05, end)))
    return slots


def slots_from_timeline(path, images, audio_duration):
    """读取显式图片时轴，并按时轴顺序返回图片与时间槽。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    segments = data.get("segments", [])
    if not segments:
        raise ValueError(f"timeline 没有 segments: {path}")

    by_name = {}
    for image in images:
        name = os.path.basename(image)
        if name in by_name:
            raise ValueError(f"图片文件名重复，无法按 timeline 匹配: {name}")
        by_name[name] = image

    ordered_images = []
    slots = []
    previous_end = None
    for i, seg in enumerate(segments):
        name = seg["image"]
        if name not in by_name:
            raise ValueError(f"timeline 引用了未提供的图片: {name}")
        start = float(seg["start_s"])
        end = float(seg["end_s"])
        if start < 0 or end <= start:
            raise ValueError(f"timeline 时间无效: {name} {start} -> {end}")
        if previous_end is not None and abs(start - previous_end) > 0.002:
            raise ValueError(
                f"timeline 不连续: {segments[i - 1]['image']} 结束于 {previous_end}, "
                f"{name} 开始于 {start}"
            )
        ordered_images.append(by_name[name])
        slots.append((start, end))
        previous_end = end

    if abs(slots[0][0]) > 0.002:
        raise ValueError(f"timeline 必须从 0 开始，实际为 {slots[0][0]}")
    if abs(slots[-1][1] - audio_duration) > 0.05:
        raise ValueError(
            f"timeline 结束时间 {slots[-1][1]:.3f}s 与音频 {audio_duration:.3f}s 不一致"
        )
    slots[-1] = (slots[-1][0], audio_duration)
    return ordered_images, slots


# ---------------------------------------------------------------- SRT 解析

_TS = re.compile(
    r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{1,3})"
)


def _hms(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def parse_srt(path):
    """返回 [(start_sec, end_sec, text), ...]"""
    with open(path, "r", encoding="utf-8-sig") as f:
        raw = f.read()
    cues = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        m = None
        ti = 0
        for i, l in enumerate(lines):
            m = _TS.search(l)
            if m:
                ti = i
                break
        if not m:
            continue
        start = _hms(m.group(1), m.group(2), m.group(3), m.group(4))
        end = _hms(m.group(5), m.group(6), m.group(7), m.group(8))
        text = "\n".join(lines[ti + 1:])
        cues.append((start, end, text))
    cues.sort(key=lambda c: c[0])
    return cues


def parse_ass(path):
    """从 ASS 的 [Events] 里取 Dialogue 时间"""
    cues = []
    fmt = None
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line.lower().startswith("format:") and fmt is None and "start" in line.lower():
                fmt = [x.strip().lower() for x in line.split(":", 1)[1].split(",")]
            elif line.startswith("Dialogue:") and fmt:
                vals = line.split(":", 1)[1].split(",", len(fmt) - 1)
                d = dict(zip(fmt, [v.strip() for v in vals]))
                cues.append((_ass_t(d["start"]), _ass_t(d["end"]), d.get("text", "")))
    cues.sort(key=lambda c: c[0])
    return cues


def _ass_t(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


# ------------------------------------------------- 字幕分段 -> 图片时长分配

def group_cues_to_images(cues, n_images, audio_dur, lead_in=0.0):
    """
    把 M 条字幕分配到 N 张图上, 返回每张图的 [start, end] 时间槽。
    - M >= N: 连续的字幕合并成一组, 尽量让每组总时长接近
    - M <  N: 图片数多于字幕数, 多余的图平分最后一段(或直接截断图片列表)
    结果保证: 槽首尾相接、覆盖 [0, audio_dur]、无空隙。
    """
    if not cues:
        # 没有字幕就按均分
        step = audio_dur / n_images
        return [(i * step, (i + 1) * step) for i in range(n_images)]

    m = len(cues)
    if m < n_images:
        n_images = m  # 图片比字幕多时, 只用前 m 张

    # 均衡分组: 先算出理想等分切点, 再把每个切点吸附到最近的"字幕间隙"上。
    # 这样既保证每张图时长接近, 又保证绝不在一句话中间换图。
    t0, t1 = cues[0][0], cues[-1][1]
    span = max(1e-6, t1 - t0)
    cut_idx = []                      # 分界处的 cue 下标 (该 cue 作为下一组的第一条)
    for k in range(1, n_images):
        ideal = t0 + span * k / n_images
        lo = len(cut_idx) + 1                       # 前面每组至少留 1 条
        hi = m - (n_images - k)                     # 后面每组至少留 1 条
        if lo > hi:
            cut_idx.append(lo)
            continue
        best = min(range(lo, hi + 1), key=lambda j: abs(cues[j][0] - ideal))
        cut_idx.append(best)

    groups, prev = [], 0
    for j in cut_idx:
        groups.append(list(range(prev, j)))
        prev = j
    groups.append(list(range(prev, m)))

    # 组 -> 时间槽, 并把边界拉齐成首尾相接
    slots = []
    for g in groups:
        slots.append([cues[g[0]][0], cues[g[-1]][1]])
    slots[0][0] = 0.0
    for i in range(len(slots) - 1):
        mid = (slots[i][1] + slots[i + 1][0]) / 2.0
        slots[i][1] = mid
        slots[i + 1][0] = mid
    slots[-1][1] = audio_dur
    return [(a, b) for a, b in slots]


# ---------------------------------------------------------------- 滤镜构建

def ken_burns(idx, dur_sec, seed_rng, motion=None):
    """
    单张图的 Ken Burns 滤镜串。
    抗抖动关键: crop 到 1080x1920 后先 scale 到 UPSCALE 倍, zoompan 在大图上走,
    最后 s=1080x1920 输出 —— 平移步进变成亚像素, 消除逐帧整数跳变。
    """
    frames = max(2, int(round(dur_sec * FPS)))
    motion = motion or {}

    # --no-kenburns 或 method=static: 跳过运镜, 只做静态铺满。
    if UPSCALE <= 1 or motion.get("method") == "static":
        return (
            f"[{idx}:v]"
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},"
            f"trim=duration={dur_sec:.4f},"
            f"setpts=PTS-STARTPTS,fps={FPS},setsar=1,format=yuv420p"
            f"[v{idx}]"
        )

    bw, bh = W * UPSCALE, H * UPSCALE
    valid_modes = {"in", "out", "left", "right", "up", "down"}
    mode = motion.get("mode") or seed_rng.choice(sorted(valid_modes))
    if mode not in valid_modes:
        raise ValueError(f"未知运镜模式: {mode}")
    zmax = min(1.30, max(1.01, float(motion.get("amount", 1.18))))
    settle = min(0.98, max(0.50, float(motion.get("settle", 0.85))))
    active_frames = max(1, int(round((frames - 1) * settle)))
    raw = f"min(on/{active_frames},1)"
    prog = f"({raw})*({raw})*(3-2*({raw}))"  # smoothstep 缓动，末段稳定
    if mode == "in":
        z = f"1+{zmax - 1.0:.6f}*{prog}"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mode == "out":
        z = f"{zmax}-{zmax - 1.0:.6f}*{prog}"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:
        z = f"{zmax}"
        cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
        if mode == "left":
            x, y = f"(iw-iw/zoom)*(1-{prog})", cy
        elif mode == "right":
            x, y = f"(iw-iw/zoom)*{prog}", cy
        elif mode == "up":
            x, y = cx, f"(ih-ih/zoom)*(1-{prog})"
        else:
            x, y = cx, f"(ih-ih/zoom)*{prog}"

    return (
        f"[{idx}:v]"
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        f"scale={bw}:{bh}:flags=lanczos,"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},"
        f"trim=duration={dur_sec:.4f},"
        f"setpts=PTS-STARTPTS,fps={FPS},setsar=1,format=yuv420p"
        f"[v{idx}]"
    )


def _merge_motion_config(base, override):
    """Shallow merge, while preserving nested motion-channel defaults."""
    if not isinstance(base, dict) or not isinstance(override, dict):
        raise ValueError("motion plan 的 default 和逐镜配置必须是对象")
    merged = dict(base)
    for key, value in override.items():
        if key in {"subject_motion", "environment_motion", "camera_motion"}:
            nested = dict(merged.get(key) or {})
            nested.update(value or {})
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def _normalize_motion_config(cfg, image_name):
    """Validate v2 shot metadata and flatten camera fields for Ken Burns."""
    cfg = dict(cfg)
    camera = dict(cfg.get("camera_motion") or {})
    if camera:
        cfg["mode"] = camera.get("mode", cfg.get("mode"))
        cfg["amount"] = camera.get("amount", cfg.get("amount"))
        cfg["settle"] = camera.get("settle_ratio", camera.get("settle", cfg.get("settle")))
        ease = camera.get("ease", "smoothstep")
        if ease != "smoothstep":
            raise ValueError(f"{image_name}: build_video 当前只支持 ease=smoothstep")

    method = cfg.get("method", "ken_burns")
    if method not in {"static", "ken_burns"}:
        raise ValueError(
            f"{image_name}: build_video 只渲染 static/ken_burns 基线，{method} 应先离线生成视频后再进入剪辑"
        )

    endpoint = cfg.get("endpoint_binding", "not_applicable")
    if endpoint not in {"not_applicable", "actual_last_frame", "prompt_only"}:
        raise ValueError(f"{image_name}: 未知 endpoint_binding={endpoint}")
    if method in {"static", "ken_burns"} and endpoint != "not_applicable":
        raise ValueError(
            f"{image_name}: {method} 不使用 I2V 末帧槽，endpoint_binding 必须为 not_applicable"
        )
    if "hero_candidate" in cfg and not isinstance(cfg["hero_candidate"], bool):
        raise ValueError(f"{image_name}: hero_candidate 必须是 true/false")

    channel_levels = {}
    for channel in ("subject_motion", "environment_motion", "camera_motion"):
        value = cfg.get(channel)
        if value is None:
            continue
        if not isinstance(value, dict):
            raise ValueError(f"{image_name}: {channel} 必须是对象")
        level = value.get("level", 0)
        if not isinstance(level, int) or isinstance(level, bool) or not 0 <= level <= 3:
            raise ValueError(f"{image_name}: {channel}.level 必须是 0..3 的整数")
        channel_levels[channel] = level
    if sum(level == 3 for level in channel_levels.values()) > 1:
        raise ValueError(f"{image_name}: 每镜最多一个强运动通道(level=3)")
    if channel_levels.get("subject_motion") == 3 and channel_levels.get("camera_motion", 0) > 1:
        raise ValueError(f"{image_name}: 主体强运动时摄影机必须 <=1")
    return cfg


def load_motion_plan(path, images):
    """读取按图片文件名配置的 v1/v2 运镜计划。"""
    if not path:
        return [{} for _ in images]
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("motion plan 顶层必须是对象")
    if "schema_version" in data and data["schema_version"] != 2:
        raise ValueError(f"不支持 motion plan schema_version={data['schema_version']}")
    default = data.get("default", {})
    if not isinstance(default, dict):
        raise ValueError("motion plan.default 必须是对象")
    image_names = [os.path.basename(image) for image in images]
    if len(set(image_names)) != len(image_names):
        raise ValueError("motion plan 无法匹配重名图片")
    reserved = {"schema_version", "hero_shot_budget", "default"}
    unknown = sorted(key for key in data if key not in reserved and key not in image_names)
    if unknown:
        raise ValueError(f"motion plan 含未匹配的逐镜键: {', '.join(unknown)}")
    plans = []
    for image in images:
        image_name = os.path.basename(image)
        shot_config = data.get(image_name, {})
        if not isinstance(shot_config, dict):
            raise ValueError(f"{image_name}: 逐镜配置必须是对象")
        cfg = _merge_motion_config(default, shot_config)
        plans.append(_normalize_motion_config(cfg, image_name))

    budget = data.get("hero_shot_budget")
    if budget is not None:
        if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
            raise ValueError("hero_shot_budget 必须是非负整数")
        candidates = sum(bool(plan.get("hero_candidate")) for plan in plans)
        if candidates > budget:
            raise ValueError(f"英雄镜候选 {candidates} 个，超过预算 {budget}")
    return plans


def build_filter(images, slots, xfade_dur, subtitle_path, fontsdir, seed, motions=None,
                 frame_style="full"):
    """
    返回 (filter_complex 字符串, 最终视频标签, 每个输入的 -t 时长列表)

    时长/offset 推导 (这是本脚本的核心):
      设第 i 张图的目标可见槽 slot_i = e_i - s_i
      xfade 每次会让总长缩短 T, 所以给前 N-1 段各多加 T:
          d_i = slot_i + T   (i < N-1)
          d_last = slot_last
      则总长 = sum(d) - (N-1)*T = sum(slot) = 音频长度  ✓
      第 i 次 xfade 的 offset:
          offset_i = sum(d_0..d_{i-1}) - i*T
                   = sum(slot_0..slot_{i-1}) + i*T - i*T
                   = s_i                                    ✓
      即: 转场恰好在第 i 段旁白开始的瞬间启动。
    """
    rng = random.Random(seed)
    n = len(images)
    slot_durs = [b - a for a, b in slots]
    in_durs = [d + xfade_dur for d in slot_durs[:-1]] + [slot_durs[-1]]

    motions = motions or [{} for _ in images]
    parts = [ken_burns(i, in_durs[i], rng, motions[i]) for i in range(n)]

    if n == 1:
        last = "v0"
    else:
        prev = "v0"
        for i in range(1, n):
            offset = slots[i][0]                     # == 第 i 段旁白起点
            tr = rng.choice(XFADE_TRANSITIONS)
            out = f"x{i}" if i < n - 1 else "vmix"
            parts.append(
                f"[{prev}][v{i}]xfade=transition={tr}:"
                f"duration={xfade_dur:.4f}:offset={offset:.4f}[{out}]"
            )
            prev = out
        last = "vmix"

    if frame_style == "comic":
        # Deterministic comic-explainer layout: the animated shot remains the
        # content source, while a dark blurred duplicate fills the vertical
        # canvas behind a white, hard-edged panel. This avoids inventing new
        # frames and keeps the existing motion/timeline contract intact.
        parts.append(
            f"[{last}]split=2[comic_bg_src][comic_panel_src];"
            f"[comic_bg_src]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},boxblur=18:1,eq=brightness=-0.30:saturation=0.55[comic_bg];"
            # 864x1536 is exactly 9:16. Fit and pad instead of `increase+crop`
            # so future shots with edge-critical details are not silently cut.
            f"[comic_panel_src]scale=864:1536:force_original_aspect_ratio=decrease,"
            f"pad=864:1536:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"pad=892:1564:14:14:color=white,"
            f"drawbox=x=0:y=0:w=iw:h=ih:color=black:t=5[comic_panel];"
            f"[comic_bg][comic_panel]overlay=94:94,"
            f"drawbox=x=36:y=38:w=210:h=16:color=white@0.92:t=fill,"
            f"drawbox=x=258:y=38:w=70:h=16:color=white@0.48:t=fill,"
            f"drawbox=x=0:y=1730:w={W}:h=190:color=black@0.28:t=fill[comic]"
        )
        last = "comic"
    elif frame_style != "full":
        raise ValueError(f"未知 frame_style={frame_style}")

    if subtitle_path:
        esc = escape_for_filter(subtitle_path)
        font_esc = escape_for_filter(fontsdir) if fontsdir else None
        font_opt = f":fontsdir='{font_esc}'" if font_esc else ""
        if subtitle_path.lower().endswith(".ass"):
            parts.append(f"[{last}]ass=filename='{esc}'{font_opt}[vout]")
        else:
            # 注意: subtitles 滤镜把 SRT 转成 ASS 时用的是默认 PlayRes 384x288,
            # 所有尺寸数值必须按 288/1920 = 0.15 缩放。
            # 目标(1920 坐标系): FontSize=104 Outline=5 Shadow=3 MarginV=380 MarginL/R=80
            k = 288.0 / H
            style = (
                f"FontName=Noto Sans CJK SC,FontSize={104 * k:.4g},"
                "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                "BackColour=&H80000000,BorderStyle=1,"
                f"Outline={5 * k:.4g},Shadow={3 * k:.4g},Alignment=2,"
                f"MarginL={int(80 * k)},MarginR={int(80 * k)},"
                f"MarginV={int(380 * k)},Bold=-1,Spacing={1 * k:.4g}"
            )
            parts.append(
                f"[{last}]subtitles=filename='{esc}'"
                f"{font_opt}"
                f":force_style='{style}'[vout]"
            )
        last = "vout"
    return ";".join(parts), last, in_durs


def escape_for_filter(p):
    """filter_complex 里的文件路径转义: \\ -> \\\\, : -> \\:, ' -> \\'"""
    return p.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", nargs="+", required=True, help="图片列表(支持通配符)")
    ap.add_argument("--audio", required=True, help="旁白 mp3")
    ap.add_argument("--bgm", default=None, help="背景音乐(可选)")
    ap.add_argument("--srt", default=None, help="字幕 srt/ass, 用于分段+烧录")
    ap.add_argument("--manifest", default=None,
                    help="TTS manifest.json；提供时按原始 segments 对齐图片，字幕只负责显示")
    ap.add_argument("--timeline", default=None,
                    help="显式图片时轴 JSON；用于一个旁白分段拆成多个画面时覆盖 manifest")
    ap.add_argument("--burn-subs", action="store_true", default=True)
    ap.add_argument("--no-burn-subs", dest="burn_subs", action="store_false")
    ap.add_argument("--fontsdir", default=None)
    ap.add_argument("--xfade", type=float, default=0.8, help="转场时长(秒)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--motion-plan", default=None,
                    help="逐镜运镜 JSON；兼容 v1 mode/amount/settle 与 v2 三运动通道")
    ap.add_argument("--frame-style", choices=("full", "comic"), default="full",
                    help="full=全幅画面；comic=漫画解说白边画格影子版")
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--out", default="final.mp4")
    ap.add_argument("--print-only", action="store_true", help="只打印命令不执行")
    ap.add_argument("--upscale", type=int, default=4,
                    help="Ken Burns 抗抖动预放大倍数。4=画质优先(默认) 2=批量生产 1=关闭运镜。"
                         "8 比 4 慢 3.5 倍收益极小, 不要用")
    ap.add_argument("--no-kenburns", action="store_true",
                    help="关闭运镜, 等价于 --upscale 1。快约 20 倍, 用于快速预览")
    args = ap.parse_args()

    global UPSCALE
    UPSCALE = 1 if args.no_kenburns else max(1, args.upscale)

    images = []
    for pat in args.images:
        hit = sorted(glob.glob(pat))
        images.extend(hit if hit else [pat])
    images = [p for p in images if os.path.isfile(p)]
    if not images:
        sys.exit("没有找到任何图片")

    audio_dur = probe_duration(args.audio)

    cues = []
    if args.srt:
        cues = parse_ass(args.srt) if args.srt.lower().endswith(".ass") else parse_srt(args.srt)

    if args.timeline:
        images, slots = slots_from_timeline(args.timeline, images, audio_dur)
    elif args.manifest:
        slots = slots_from_manifest(args.manifest, audio_dur)
        if len(slots) != len(images):
            sys.exit(f"manifest 分段数 {len(slots)} != 图片数 {len(images)}")
    else:
        slots = group_cues_to_images(cues, len(images), audio_dur)
    images = images[:len(slots)]
    motions = load_motion_plan(args.motion_plan, images)

    # 转场不能长过最短的槽
    xfade = min(args.xfade, max(0.05, min(b - a for a, b in slots) * 0.5))

    sub_path = args.srt if (args.burn_subs and args.srt) else None
    fc, vlabel, in_durs = build_filter(
        images, slots, xfade, sub_path, args.fontsdir, args.seed, motions,
        args.frame_style,
    )

    # ---- 音频链 ----
    ai = len(images)                     # 旁白的输入序号
    inputs = []
    for p, d in zip(images, in_durs):
        inputs += ["-loop", "1", "-t", f"{d:.4f}", "-i", p]
    inputs += ["-i", args.audio]
    if args.bgm:
        inputs += ["-stream_loop", "-1", "-i", args.bgm]
        afc = (
            f"[{ai}:a]aformat=channel_layouts=stereo,asplit=2[voice][sc];"
            f"[{ai + 1}:a]aformat=channel_layouts=stereo,volume=0.45,"
            f"afade=t=in:st=0:d=1.5[music];"
            f"[music][sc]sidechaincompress=threshold=0.02:ratio=12:attack=15:"
            f"release=350:makeup=1:level_sc=1[ducked];"
            f"[voice][ducked]amix=inputs=2:duration=first:normalize=0,"
            f"afade=t=out:st={max(0.0, audio_dur - 2.0):.3f}:d=2,"
            f"loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
        )
        fc = fc + ";" + afc
        amap = "[aout]"
    else:
        fc = fc + f";[{ai}:a]aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
        amap = "[aout]"

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", fc,
        "-map", f"[{vlabel}]", "-map", amap,
        "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
        "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-g", str(FPS * 2), "-keyint_min", str(FPS),
        "-sc_threshold", "0",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        "-shortest",
        args.out,
    ]

    print("=" * 70)
    print(
        f"图片 {len(images)} 张 | 音频 {audio_dur:.2f}s | 字幕 {len(cues)} 条 | "
        f"转场 {xfade:.2f}s | 画框 {args.frame_style}"
    )
    for i, ((a, b), p, motion) in enumerate(zip(slots, images, motions)):
        motion_desc = motion.get("mode", "random")
        method = motion.get("method", "ken_burns")
        levels = "/".join(
            str((motion.get(name) or {}).get("level", 0))
            for name in ("subject_motion", "environment_motion", "camera_motion")
        )
        print(
            f"  #{i:02d} {a:7.2f} -> {b:7.2f}  ({b - a:5.2f}s, 输入时长 {in_durs[i]:5.2f}s)  "
            f"{os.path.basename(p)}  method={method} motion={motion_desc} S/E/C={levels}"
        )
    print("=" * 70)

    # 同时导出一份 concat demuxer 文件(不带转场的简易方案备用)
    concat_path = os.path.splitext(args.out)[0] + "_concat.txt"
    with open(concat_path, "w", encoding="utf-8") as f:
        for (a, b), p in zip(slots, images):
            f.write(f"file '{os.path.abspath(p)}'\n")
            f.write(f"duration {b - a:.4f}\n")
        f.write(f"file '{os.path.abspath(images[-1])}'\n")   # concat demuxer 要求重复最后一帧
    print(f"[concat demuxer 备用方案已写出] {concat_path}")

    if args.print_only:
        print("\n" + " ".join(_q(c) for c in cmd))
        return

    print("\n开始渲染 ...")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f"ffmpeg 失败, 退出码 {r.returncode}")
    print(f"完成: {args.out}  ({probe_duration(args.out):.2f}s)")


def _q(s):
    return f"'{s}'" if (" " in s or ";" in s or "[" in s) else s


if __name__ == "__main__":
    main()
