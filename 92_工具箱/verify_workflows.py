#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仓库级离线验证入口。

默认检查所有 Python CLI 的语法与 --help、内建 self-test，以及首条故事的
字幕/时轴/运镜/漫画画格合同。不读 API Key、不联网、不调用付费接口，
也不写生产素材。
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parent
ROOT = TOOL_DIR.parent
STORY = ROOT / "02_制作中" / "2026-07-26_故事线_最后一位图书管理员"

CLI_NAMES = (
    "align_subtitles.py",
    "build_video.py",
    "gen_images.py",
    "make_jy_draft.py",
    "matrix_tracker.py",
    "tts_batch.py",
    "tts_dashscope.py",
    "tts_minimax.py",
    "tts_qwen_local.py",
)

SELF_TESTS = (
    ("build_video.py", "--self-test"),
    ("matrix_tracker.py", "--self-test"),
    ("test_tts_timing_contracts.py",),
    ("tts_dashscope.py", "self-test"),
    ("tts_minimax.py", "self-test"),
    ("tts_qwen_local.py", "self-test"),
)


class CheckFailure(RuntimeError):
    pass


def _pass(label: str) -> None:
    print(f"[PASS] {label}")


def _run(script: str, *args: str, timeout: int = 60) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / script), *args],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise CheckFailure(f"{script} {' '.join(args)} 失败:\n{detail}")


def _load(name: str, filename: str):
    path = TOOL_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CheckFailure(f"无法加载 {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_syntax_and_help() -> None:
    actual = tuple(sorted(path.name for path in TOOL_DIR.glob("*.py")))
    missing = sorted(set(CLI_NAMES) - set(actual))
    if missing:
        raise CheckFailure(f"缺少声明的 CLI: {', '.join(missing)}")

    for name in CLI_NAMES:
        path = TOOL_DIR / name
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        _run(name, "--help")
        _pass(f"{name}: AST + --help")


def check_self_tests() -> None:
    for command in SELF_TESTS:
        _run(*command)
        _pass(" ".join(command))


def check_story_contracts() -> None:
    timeline_path = STORY / "素材" / "image_timeline.json"
    motion_path = STORY / "素材" / "motion_plan.json"
    comic_layout_path = STORY / "素材" / "comic_layout_plan.json"
    manifest_path = STORY / "素材" / "audio" / "manifest.json"
    image_dir = STORY / "素材" / "img"

    for path in (timeline_path, motion_path, comic_layout_path, manifest_path):
        if not path.is_file():
            raise CheckFailure(f"缺少故事合同文件: {path.relative_to(ROOT)}")

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    names = [item["image"] for item in timeline.get("segments", [])]
    if not names or len(names) != len(set(names)):
        raise CheckFailure("图片时轴为空或含重复图片")
    images = [str(image_dir / name) for name in names]
    absent = [name for name, path in zip(names, images) if not Path(path).is_file()]
    if absent:
        raise CheckFailure(f"时轴引用的图片不存在: {', '.join(absent)}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audio_duration = float(manifest["total_duration_s"])
    build = _load("verify_build_video", "build_video.py")
    ordered_images, slots = build.slots_from_timeline(
        timeline_path, images, audio_duration
    )
    motions = build.load_motion_plan(motion_path, ordered_images)
    comic_layouts = build.load_comic_layout_plan(comic_layout_path, ordered_images)
    if len(slots) != len(motions) or len(slots) != len(images):
        raise CheckFailure("时轴、图片和运镜计划数量不一致")
    if len(comic_layouts) != len(images):
        raise CheckFailure("漫画布局计划与图片数量不一致")

    for style in ("full", "comic"):
        layout_arg = comic_layouts if style == "comic" else None
        graph, label, durations = build.build_filter(
            ordered_images,
            slots,
            0.35,
            None,
            None,
            42,
            motions,
            style,
            layout_arg,
        )
        if not graph or not label or len(durations) != len(images):
            raise CheckFailure(f"{style} 滤镜合同生成不完整")
        if style == "comic" and not all(
            marker in graph for marker in ("[cp0_main]", "[cp3_focus]", "[cp6_main]")
        ):
            raise CheckFailure("comic 滤镜合同未产生全格/细节格/冲击格节点")
        _pass(f"故事时轴 + {style} 滤镜合同 ({len(slots)} 镜)")

    align = _load("verify_align_subtitles", "align_subtitles.py")
    cues, total = align.from_manifest(manifest_path)
    if not cues or abs(float(total) - audio_duration) > 0.001:
        raise CheckFailure("字幕 manifest 未完整覆盖旁白时长")
    for _, _, text in cues:
        align.wrap(align.strip_punct_tail(text))
    _pass(f"真实词时间字幕合同 ({len(cues)} 条)")


def main() -> int:
    parser = argparse.ArgumentParser(description="AI 自媒体仓库离线合同检查")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="只跑 AST 与 --help，跳过 self-test 和故事合同",
    )
    args = parser.parse_args()

    try:
        check_syntax_and_help()
        if not args.quick:
            check_self_tests()
            check_story_contracts()
    except (CheckFailure, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    print("[PASS] 全部离线检查通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
