#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline-only Qwen3-TTS CustomVoice runner for shadow A/B candidates.

This tool never downloads weights. ``synthesize`` accepts an existing local
model directory, sets the common model hubs to offline mode, and refuses to
run unless the operator explicitly confirms the local GPU job. Dry-run is the
default and writes a reproducible plan without importing torch/qwen-tts.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any


MODEL_NAME = "Qwen3-TTS-12Hz-1.7B-CustomVoice"
MODEL_SOURCE = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
LICENSE_CHECKED = "2026-07-28"
DEFAULT_MIN_FREE_VRAM_MB = 7000
MIN_EXPECTED_WEIGHT_BYTES = 4_000_000_000


class QwenLocalError(RuntimeError):
    pass


def portable_path(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.name


def read_segments(path: Path) -> list[tuple[str, str]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    segments = [(f"{index:02d}", text) for index, text in enumerate(
        (line for line in lines if line), 1
    )]
    if not segments:
        raise QwenLocalError(f"No non-empty segments in {path}")
    return segments


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_inventory(model_dir: Path) -> dict[str, Any]:
    if not model_dir.is_dir():
        return {
            "ready": False,
            "path": portable_path(model_dir),
            "reason": "local model directory does not exist",
        }
    config = model_dir / "config.json"
    speech_tokenizer = model_dir / "speech_tokenizer"
    speech_tokenizer_config = speech_tokenizer / "config.json"
    speech_tokenizer_weights = speech_tokenizer / "model.safetensors"
    weights = sorted(model_dir.rglob("*.safetensors"))
    entries = [
        {
            "path": path.relative_to(model_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in weights
    ]
    fingerprint = hashlib.sha256(
        json.dumps(entries, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    try:
        config_data = json.loads(config.read_text(encoding="utf-8")) if config.is_file() else {}
    except (OSError, json.JSONDecodeError):
        config_data = {}
    architecture_ok = (
        config_data.get("model_type") == "qwen3_tts"
        and config_data.get("tts_model_size") == "1b7"
        and config_data.get("tts_model_type") == "custom_voice"
        and "Qwen3TTSForConditionalGeneration" in config_data.get("architectures", [])
    )
    weight_bytes = sum(item["bytes"] for item in entries)
    root_weight_bytes = sum(
        item["bytes"] for item in entries
        if not item["path"].startswith("speech_tokenizer/")
    )
    missing_components = []
    if not config.is_file():
        missing_components.append("config.json")
    elif not architecture_ok:
        missing_components.append("official 1.7B CustomVoice architecture metadata")
    if not speech_tokenizer_config.is_file():
        missing_components.append("speech_tokenizer/config.json")
    if (
        not speech_tokenizer_weights.is_file()
        or speech_tokenizer_weights.stat().st_size < 600_000_000
    ):
        missing_components.append("complete bundled speech_tokenizer/model.safetensors")
    if not weights:
        missing_components.append("model weight files")
    if weight_bytes < MIN_EXPECTED_WEIGHT_BYTES:
        missing_components.append(
            f"at least {MIN_EXPECTED_WEIGHT_BYTES} bytes of official 1.7B weights"
        )
    if root_weight_bytes < 3_000_000_000:
        missing_components.append("at least 3000000000 bytes of root model weights")
    ready = not missing_components
    return {
        "ready": ready,
        "path": portable_path(model_dir),
        "config_sha256": sha256_file(config) if config.is_file() else None,
        "weight_file_count": len(weights),
        "weight_bytes": weight_bytes,
        "weight_inventory_sha256": fingerprint,
        "required_components": {
            "root_config": config.is_file(),
            "architecture_metadata": architecture_ok,
            "bundled_speech_tokenizer_config": speech_tokenizer_config.is_file(),
            "bundled_speech_tokenizer_weights": (
                speech_tokenizer_weights.is_file()
                and speech_tokenizer_weights.stat().st_size >= 600_000_000
            ),
            "minimum_expected_weight_bytes": MIN_EXPECTED_WEIGHT_BYTES,
            "minimum_expected_root_weight_bytes": 3_000_000_000,
            "safetensors_only": True,
        },
        "reason": None if ready else "missing/incomplete: " + ", ".join(missing_components),
    }


def gpu_status() -> dict[str, Any]:
    try:
        result = subprocess.run([
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.free,driver_version",
            "--format=csv,noheader,nounits",
        ], check=True, capture_output=True, text=True)
        line = result.stdout.strip().splitlines()[0]
        name, total, free, driver = [part.strip() for part in line.split(",", 3)]
        return {
            "available": True,
            "name": name,
            "memory_total_mb": int(total),
            "memory_free_mb": int(free),
            "driver_version": driver,
        }
    except (FileNotFoundError, subprocess.CalledProcessError, IndexError, ValueError):
        return {"available": False, "reason": "nvidia-smi did not return a usable GPU"}


def dependency_status() -> dict[str, bool]:
    return {
        name: importlib.util.find_spec(module) is not None
        for name, module in {
            "qwen-tts": "qwen_tts",
            "torch": "torch",
            "soundfile": "soundfile",
        }.items()
    }


def offline_environment() -> dict[str, str]:
    values = {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "MODELSCOPE_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
    }
    os.environ.update(values)
    return values


def require_media_tools() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        raise QwenLocalError(
            "Execution requires ffmpeg and ffprobe on PATH before loading the model; "
            f"missing: {', '.join(missing)}"
        )


def reusable_segment(out_dir: Path, name: str, text: str, seed: int,
                     args: argparse.Namespace, model_revision: str
                     ) -> tuple[Path, dict[str, Any]] | None:
    sidecar_path = out_dir / f"{name}.json"
    if not sidecar_path.exists():
        collisions = [
            path for path in out_dir.glob(f"{name}.*")
            if path.name != f"{name}.json"
        ]
        if collisions and not args.overwrite:
            raise QwenLocalError(
                f"Orphaned output for segment {name}; inspect it before retrying or "
                "use --overwrite to authorize replacement"
            )
        return None
    if args.overwrite:
        return None
    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QwenLocalError(f"Invalid partial sidecar {sidecar_path}: {exc}") from exc
    filename = sidecar.get("file")
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise QwenLocalError(f"Unsafe or missing file name in {sidecar_path}")
    audio_path = out_dir / filename
    expected = {
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "voice": args.speaker,
        "model": MODEL_NAME,
        "model_revision": model_revision,
        "language": args.language,
        "instruction": args.instruction,
        "seed": seed,
        "dtype": args.dtype,
    }
    if any(sidecar.get(key) != value for key, value in expected.items()):
        raise QwenLocalError(
            f"Existing segment {name} does not match this request; use a new output "
            "directory or explicitly authorize --overwrite"
        )
    if not audio_path.is_file() or audio_path.stat().st_size == 0:
        raise QwenLocalError(f"Partial segment {name} has no valid audio file: {audio_path}")
    return audio_path, sidecar


def make_plan(args: argparse.Namespace) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    source = Path(args.text_file).resolve()
    segments = read_segments(source)
    model_dir = Path(args.model_dir).expanduser().resolve()
    inventory = model_inventory(model_dir)
    gpu = gpu_status()
    dependencies = dependency_status()
    enough_vram = bool(
        gpu.get("available")
        and gpu.get("memory_free_mb", 0) >= args.minimum_free_vram_mb
    )
    status = "planned_ready" if (
        inventory["ready"] and enough_vram and all(dependencies.values())
    ) else "planned_not_ready"
    plan = {
        "schema_version": 1,
        "status": status,
        "provider": "local:qwen3-tts",
        "model": MODEL_NAME,
        "model_source": MODEL_SOURCE,
        "model_revision": (
            f"local-inventory-sha256:{inventory.get('weight_inventory_sha256')}"
            if inventory.get("ready") else None
        ),
        "model_inventory": inventory,
        "source": {
            "path": portable_path(Path(args.text_file)),
            "sha256": sha256_file(source),
            "segment_count": len(segments),
        },
        "voice": {
            "speaker": args.speaker,
            "language": args.language,
            "instruction": args.instruction,
            "seed": args.seed,
        },
        "runtime": {
            "gpu": gpu,
            "minimum_free_vram_mb": args.minimum_free_vram_mb,
            "enough_free_vram": enough_vram,
            "dependencies": dependencies,
            "attention": args.attention,
            "dtype": args.dtype,
            "offline_environment": offline_environment(),
        },
        "guards": {
            "dry_run_default": True,
            "requires_execute": True,
            "requires_confirm_local_run": True,
            "remote_model_ids_rejected": True,
            "automatic_downloads_disabled": True,
        },
    }
    return plan, segments


def concat_wav(files: list[Path], out_dir: Path, pause_ms: int,
               sample_rate: int) -> tuple[str | None, list[dict[str, Any]]]:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return None, []
    silence = out_dir / f"_silence_{pause_ms}ms.wav"
    if pause_ms > 0:
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
            "-i", f"anullsrc=r={sample_rate}:cl=mono", "-t", str(pause_ms / 1000),
            "-c:a", "pcm_s16le", str(silence),
        ], check=True)
    concat_lines: list[str] = []
    timeline: list[dict[str, Any]] = []
    cursor = 0.0
    for index, path in enumerate(files):
        duration = float(subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ], check=True, capture_output=True, text=True).stdout.strip())
        concat_lines.append(f"file '{path.name}'")
        timeline.append({
            "name": path.stem,
            "file": path.name,
            "start_s": round(cursor, 3),
            "end_s": round(cursor + duration, 3),
        })
        cursor += duration
        if pause_ms > 0 and index < len(files) - 1:
            concat_lines.append(f"file '{silence.name}'")
            cursor += pause_ms / 1000
    list_file = out_dir / "_concat_qwen.txt"
    list_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    narration = out_dir / "narration.wav"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
        "-i", list_file.name, "-c:a", "pcm_s16le", "-ar", str(sample_rate),
        "-ac", "1", narration.name,
    ], check=True, cwd=str(out_dir))
    return narration.name, timeline


def fallback_timeline(results: list[dict[str, Any]], pause_ms: int) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    cursor = 0.0
    for index, item in enumerate(results):
        duration = float(item["duration_s"])
        timeline.append({
            "name": item["name"],
            "file": item["file"],
            "start_s": round(cursor, 3),
            "end_s": round(cursor + duration, 3),
            "text": item["text"],
        })
        cursor += duration
        if pause_ms > 0 and index < len(results) - 1:
            cursor += pause_ms / 1000
    return timeline


def require_execution(args: argparse.Namespace, plan: dict[str, Any], need_model: bool) -> None:
    if not args.confirm_local_run:
        raise QwenLocalError("Execution requires --confirm-local-run")
    if not need_model:
        return
    inventory = plan["model_inventory"]
    if not inventory["ready"]:
        raise QwenLocalError(inventory["reason"])
    missing = [name for name, ready in plan["runtime"]["dependencies"].items() if not ready]
    if missing:
        raise QwenLocalError(f"Missing isolated-environment dependencies: {', '.join(missing)}")
    if not plan["runtime"]["gpu"].get("available"):
        raise QwenLocalError("A CUDA GPU visible to nvidia-smi is required")
    if not plan["runtime"]["enough_free_vram"]:
        free = plan["runtime"]["gpu"].get("memory_free_mb", 0)
        raise QwenLocalError(
            f"Only {free} MiB GPU memory is free; require at least "
            f"{args.minimum_free_vram_mb} MiB. Close other GPU applications first."
        )


def cmd_preflight(args: argparse.Namespace) -> None:
    model_dir = Path(args.model_dir).expanduser().resolve()
    result = {
        "provider": "local:qwen3-tts",
        "model_name": MODEL_NAME,
        "model": model_inventory(model_dir),
        "gpu": gpu_status(),
        "dependencies": dependency_status(),
        "offline_only": True,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_synthesize(args: argparse.Namespace) -> None:
    plan, segments = make_plan(args)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "request_plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        print(f"DRY RUN: no model load; plan written to {plan_path}")
        return
    require_media_tools()
    collisions = [
        path for path in (out_dir / "manifest.json", out_dir / "narration.wav")
        if path.exists()
    ]
    if collisions and not args.overwrite:
        raise QwenLocalError(
            "Completed/combined output already exists; use a new directory or pass "
            f"--overwrite explicitly: {', '.join(path.name for path in collisions)}"
        )
    model_revision = plan.get("model_revision") or "unverified-local-model"
    prepared: list[tuple[str, str, int, tuple[Path, dict[str, Any]] | None]] = []
    for index, (name, text) in enumerate(segments):
        seed = args.seed + index
        prepared.append((
            name, text, seed,
            reusable_segment(out_dir, name, text, seed, args, model_revision),
        ))
    need_model = any(existing is None for _, _, _, existing in prepared)
    require_execution(args, plan, need_model)
    offline_environment()

    model = None
    sf = None
    torch = None
    if need_model:
        import soundfile as sf_module
        import torch as torch_module
        from qwen_tts import Qwen3TTSModel

        sf = sf_module
        torch = torch_module
        if not torch.cuda.is_available():
            raise QwenLocalError("torch cannot access CUDA in this environment")
        model_dir = Path(args.model_dir).expanduser().resolve()
        try:
            model = Qwen3TTSModel.from_pretrained(
                str(model_dir),
                device_map="cuda:0",
                dtype=getattr(torch, args.dtype),
                attn_implementation=args.attention,
                local_files_only=True,
            )
        except Exception as exc:
            raise QwenLocalError(f"Local model load failed without downloads: {exc}") from exc

    outputs: list[Path] = []
    results: list[dict[str, Any]] = []
    sample_rate = 0
    reused = 0
    started = time.perf_counter()
    for name, text, seed, existing in prepared:
        if existing:
            path, result = existing
            outputs.append(path)
            results.append(result)
            sample_rate = sample_rate or int(result.get("sample_rate", 0))
            reused += 1
            continue
        if model is None or torch is None or sf is None:
            raise QwenLocalError("Internal error: model runtime was not initialized")
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.cuda.reset_peak_memory_stats()
        segment_started = time.perf_counter()
        try:
            wavs, sample_rate = model.generate_custom_voice(
                text=text,
                language=args.language,
                speaker=args.speaker,
                instruct=args.instruction or None,
            )
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower():
                raise QwenLocalError(
                    "Qwen3-TTS 1.7B ran out of GPU memory. Do not enable swap tricks; "
                    "close GPU applications, retry once, then explicitly test 0.6B."
                ) from exc
            raise
        wav = wavs[0]
        path = out_dir / f"{name}.wav"
        sf.write(str(path), wav, sample_rate, subtype="PCM_16")
        duration = len(wav) / float(sample_rate)
        elapsed = time.perf_counter() - segment_started
        result = {
            "name": name,
            "text": text,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "file": path.name,
            "duration_s": round(duration, 3),
            "voice": args.speaker,
            "model": MODEL_NAME,
            "model_revision": model_revision,
            "language": args.language,
            "instruction": args.instruction,
            "dtype": args.dtype,
            "seed": seed,
            "sample_rate": sample_rate,
            "elapsed_s": round(elapsed, 3),
            "rtf": round(elapsed / duration, 3) if duration else None,
            "peak_vram_mb": round(torch.cuda.max_memory_allocated() / 1024 / 1024, 1),
            "words": [],
            "timestamps_source": "alignment_required",
        }
        (out_dir / f"{name}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        outputs.append(path)
        results.append(result)

    if sample_rate <= 0:
        raise QwenLocalError("No valid sample rate was recorded for the generated segments")
    try:
        narration, timeline = concat_wav(outputs, out_dir, args.pause_ms, sample_rate)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        raise QwenLocalError(
            "Audio concatenation failed. Generated segment sidecars were preserved; "
            "fix ffmpeg/input files and rerun in the same directory to resume."
        ) from exc
    if not timeline:
        timeline = fallback_timeline(results, args.pause_ms)
    else:
        raw_by_name = {item["name"]: item for item in results}
        for item in timeline:
            item["text"] = raw_by_name[item["name"]]["text"]
    total_duration = round(float(timeline[-1]["end_s"]), 3) if timeline else 0.0
    if not narration:
        raise QwenLocalError("Audio concatenation did not produce narration")
    manifest = {
        **plan,
        "status": "synthesized_shadow_candidate",
        "generated_on": date.today().isoformat(),
        "narration": narration,
        "audio_path": narration,
        "pause_ms": args.pause_ms,
        "sample_rate": sample_rate,
        "total_duration_s": total_duration,
        "duration_sec": total_duration,
        "consent_record": None,
        "license_checked_at": LICENSE_CHECKED,
        "cost": {"currency": "CNY", "amount": 0.0, "billable_units": 0},
        "resume": {"reused_segments": reused, "new_segments": len(results) - reused},
        "elapsed_s": round(time.perf_counter() - started, 3),
        "segments": timeline,
        "raw": results,
        "note": "Local shadow candidate; align word timestamps and pass blind/stability gates before G3 use.",
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Generated {len(outputs)} local segments in {out_dir}")
    print(f"Manifest: {out_dir / 'manifest.json'}")


def cmd_self_test(_: argparse.Namespace) -> None:
    def check(condition: bool, message: str) -> None:
        if not condition:
            raise QwenLocalError(f"self-test failed: {message}")

    results = [
        {"name": "01", "file": "01.wav", "text": "第一段", "duration_s": 1.0},
        {"name": "02", "file": "02.wav", "text": "Second", "duration_s": 2.0},
    ]
    timeline = fallback_timeline(results, 350)
    check(timeline[0]["start_s"] == 0.0, "first segment start")
    check(timeline[1]["start_s"] == 1.35, "pause boundary")
    check(timeline[1]["end_s"] == 3.35, "final boundary")
    check(offline_environment()["HF_HUB_OFFLINE"] == "1", "offline environment")
    print("self-test passed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline-only Qwen3-TTS 1.7B CustomVoice runner"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight", help="check local weights, GPU, and dependencies")
    preflight.add_argument("--model-dir", required=True)
    preflight.set_defaults(func=cmd_preflight)

    synth = sub.add_parser("synthesize", help="plan or run local synthesis")
    synth.add_argument("--model-dir", required=True)
    synth.add_argument("--text-file", required=True)
    synth.add_argument("--out", required=True)
    synth.add_argument("--speaker", choices=("Serena", "Vivian"), default="Serena")
    synth.add_argument("--language", choices=("Chinese", "English", "Auto"), default="Chinese")
    synth.add_argument("--instruction", default="")
    synth.add_argument("--seed", type=int, default=42)
    synth.add_argument("--pause-ms", type=int, default=350)
    synth.add_argument("--attention", choices=("sdpa", "flash_attention_2"), default="sdpa")
    synth.add_argument(
        "--dtype", choices=("bfloat16", "float16"), default="bfloat16",
        help="bfloat16 matches the official example; float16 is an explicit compatibility fallback",
    )
    synth.add_argument("--minimum-free-vram-mb", type=int, default=DEFAULT_MIN_FREE_VRAM_MB)
    synth.add_argument("--execute", action="store_true")
    synth.add_argument("--confirm-local-run", action="store_true")
    synth.add_argument(
        "--overwrite", action="store_true",
        help="explicitly allow replacing existing output files",
    )
    synth.set_defaults(func=cmd_synthesize)

    test = sub.add_parser("self-test", help="run offline contract tests")
    test.set_defaults(func=cmd_self_test)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if getattr(args, "pause_ms", 0) < 0:
        raise QwenLocalError("--pause-ms must be non-negative")
    if getattr(args, "minimum_free_vram_mb", 1) <= 0:
        raise QwenLocalError("--minimum-free-vram-mb must be positive")
    if hasattr(args, "model_dir") and "://" in args.model_dir:
        raise QwenLocalError("--model-dir must be a local filesystem directory, not a URL")
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except QwenLocalError as exc:
        sys.exit(f"error: {exc}")
