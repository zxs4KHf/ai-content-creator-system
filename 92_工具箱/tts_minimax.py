#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Budget-guarded MiniMax Speech adapter.

The command is dry-run by default. Network access requires both ``--execute``
and ``--confirm-billable``; synthesis additionally requires a positive
``--max-cost-cny``. API keys are read from an environment variable and are
never written to plans or manifests.

This adapter intentionally uses only Python's standard library so it can be
audited before an account or paid API call is authorized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any


API_BASE = "https://api.minimaxi.com/v1"
ALLOWED_API_BASES = {
    API_BASE,
    "https://api-bj.minimaxi.com/v1",
}
PRICING_CHECKED = "2026-07-28"
PRICING_MAX_AGE_DAYS = 30
MODEL_PRICE_CNY_PER_10K = {
    "speech-2.8-hd": 3.5,
    "speech-2.8-turbo": 2.0,
}
VOICE_DESIGN_PREVIEW_PRICE_CNY_PER_10K = 2.0
MODELS = tuple(MODEL_PRICE_CNY_PER_10K)
EMOTIONS = (
    "auto", "happy", "sad", "angry", "fearful", "disgusted",
    "surprised", "calm", "fluent", "whisper",
)


class MiniMaxError(RuntimeError):
    pass


TIMING_CONTRACT_VERSION = 1
MINIMAX_T2A_DOC_URL = (
    "https://platform.minimaxi.com/docs/api-reference/speech-t2a-http"
)


def timing_text(value: str) -> str:
    """Normalize only characters that cannot require an audible word slot."""
    return "".join(
        char
        for char in unicodedata.normalize("NFKC", value)
        if not char.isspace() and not unicodedata.category(char).startswith("P")
    )


def validate_word_timings(
    source_text: str,
    words: Any,
    *,
    complete: bool,
    audio_duration_ms: int | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """Validate already-normalized word timings before publishing them.

    Provider-specific fields must be mapped to ``text/start_ms/end_ms`` only
    after that provider schema has been verified. This function deliberately
    does not guess provider aliases.
    """
    if not complete:
        return [], "provider_result_incomplete"
    if not isinstance(source_text, str) or not timing_text(source_text):
        return [], "source_text_empty_after_normalization"
    if not isinstance(words, list) or not words:
        return [], "word_timings_missing"
    if audio_duration_ms is not None and (
        type(audio_duration_ms) is not int or audio_duration_ms <= 0
    ):
        return [], "audio_duration_invalid"

    normalized: list[dict[str, Any]] = []
    previous_end = 0
    for index, item in enumerate(words):
        if not isinstance(item, dict):
            return [], f"word_{index}_not_object"
        text = item.get("text")
        start_ms = item.get("start_ms")
        end_ms = item.get("end_ms")
        if not isinstance(text, str) or not timing_text(text):
            return [], f"word_{index}_text_invalid"
        if type(start_ms) is not int or type(end_ms) is not int:
            return [], f"word_{index}_time_not_integer_ms"
        if start_ms < 0 or end_ms <= start_ms:
            return [], f"word_{index}_time_range_invalid"
        if start_ms < previous_end:
            return [], f"word_{index}_time_not_monotonic"
        if audio_duration_ms is not None and end_ms > audio_duration_ms:
            return [], f"word_{index}_exceeds_audio_duration"
        normalized.append({
            "text": text,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "confidence": item.get("confidence"),
        })
        previous_end = end_ms

    if timing_text("".join(item["text"] for item in normalized)) != timing_text(
        source_text
    ):
        return [], "word_text_does_not_cover_source"
    return normalized, None


def minimax_timing_contract(result: Any, source_text: str) -> dict[str, Any]:
    """Normalize documented MiniMax timing evidence without guessing its file schema.

    The official synchronous T2A reference documents ``data.subtitle_file``
    as a JSON download URL with millisecond timestamps, but does not document
    the JSON item's field names. Until a real response fixture and its schema
    are verified, the URL is evidence only and cannot populate ``words``.
    """
    data = dict(result.get("data") or {}) if isinstance(result, dict) else {}
    base = dict(result.get("base_resp") or {}) if isinstance(result, dict) else {}
    response_status = data.get("status")
    subtitle_available = isinstance(data.get("subtitle_file"), str) and bool(
        data.get("subtitle_file", "").strip()
    )
    complete = base.get("status_code") in (None, 0) and response_status == 2
    if not complete:
        reason = "provider_result_incomplete"
    elif not subtitle_available:
        reason = "provider_subtitle_missing"
    else:
        reason = "provider_subtitle_item_schema_not_documented"
    words, validation_error = validate_word_timings(
        source_text,
        [],
        complete=complete,
        audio_duration_ms=(result.get("extra_info") or {}).get("audio_length")
        if isinstance(result, dict)
        else None,
    )
    return {
        "schema_version": TIMING_CONTRACT_VERSION,
        "status": "forced_alignment_required",
        "mode": "listening_only",
        "words": words,
        "timestamps_source": "forced_alignment_required",
        "reason": reason,
        "validator_reason": validation_error,
        "provider_evidence": {
            "response_complete": complete,
            "response_status": response_status,
            "subtitle_file_available": subtitle_available,
            "subtitle_requested": True,
            "subtitle_type_requested": "word",
            "documentation": MINIMAX_T2A_DOC_URL,
        },
    }


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
        raise MiniMaxError(f"No non-empty segments in {path}")
    too_long = [name for name, text in segments if len(text) >= 10_000]
    if too_long:
        raise MiniMaxError(
            "MiniMax synchronous T2A requires every segment to be under "
            f"10000 characters; too long: {', '.join(too_long)}"
        )
    return segments


def billable_characters(text: str) -> int:
    """Estimate the mainland MiniMax billing rule.

    Han ideographs count as two; English letters, punctuation, whitespace and
    other symbols count as one. The estimate is intentionally conservative for
    CJK extension/compatibility blocks.
    """
    return sum(
        2 if (
            "\u3400" <= char <= "\u4dbf"
            or "\u4e00" <= char <= "\u9fff"
            or "\uf900" <= char <= "\ufaff"
        ) else 1
        for char in text
    )


def estimate_cost(segments: list[tuple[str, str]], price: float,
                  activation_cost: float = 0.0) -> dict[str, Any]:
    units = sum(billable_characters(text) for _, text in segments)
    synthesis_cost = round(units * price / 10_000, 6)
    return {
        "billing_characters_estimate": units,
        "price_cny_per_10000_characters": price,
        "synthesis_cost_cny": synthesis_cost,
        "possible_voice_activation_cost_cny": activation_cost,
        "estimated_cost_cny": round(synthesis_cost + activation_cost, 6),
        "pricing_checked": PRICING_CHECKED,
    }


def source_metadata(path: Path, segments: list[tuple[str, str]]) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": portable_path(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "segment_count": len(segments),
    }


def optional_file_record(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_file():
        raise MiniMaxError(f"Rights/consent record does not exist: {path}")
    return {
        "path": portable_path(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }


def require_media_tools() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        raise MiniMaxError(
            "Execution requires ffmpeg and ffprobe on PATH before any paid call; "
            f"missing: {', '.join(missing)}"
        )


def post_json(endpoint: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise MiniMaxError(f"MiniMax HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise MiniMaxError(f"MiniMax network error: {exc.reason}") from exc
    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MiniMaxError("MiniMax returned non-JSON data") from exc
    base = result.get("base_resp") or {}
    if base.get("status_code") not in (None, 0):
        raise MiniMaxError(
            f"MiniMax error {base.get('status_code')}: {base.get('status_msg')}"
        )
    return result


def require_execution(args: argparse.Namespace, estimated_cost: float | None = None) -> str:
    if not args.execute:
        return ""
    if not args.confirm_billable:
        raise MiniMaxError("Execution requires --confirm-billable")
    if estimated_cost is not None:
        pricing_age = (date.today() - date.fromisoformat(PRICING_CHECKED)).days
        if pricing_age < 0 or pricing_age > PRICING_MAX_AGE_DAYS:
            raise MiniMaxError(
                f"Built-in pricing snapshot {PRICING_CHECKED} is stale; verify the "
                "official price and update the adapter before a billable call"
            )
        if (
            args.max_cost_cny is None
            or not math.isfinite(args.max_cost_cny)
            or args.max_cost_cny <= 0
        ):
            raise MiniMaxError("Execution requires a positive finite --max-cost-cny")
        if estimated_cost > args.max_cost_cny:
            raise MiniMaxError(
                f"Estimated cost CNY {estimated_cost:.6f} exceeds cap "
                f"{args.max_cost_cny:.6f}"
            )
    if getattr(args, "voice_source", None) == "cloned":
        if not getattr(args, "confirm_voice_rights", False):
            raise MiniMaxError("Cloned voice execution requires --confirm-voice-rights")
        if not getattr(args, "consent_record", None):
            raise MiniMaxError("Cloned voice execution requires --consent-record")
        optional_file_record(args.consent_record)
    key = os.environ.get(args.api_key_env, "")
    if not key:
        raise MiniMaxError(f"Missing API key environment variable: {args.api_key_env}")
    return key


def clean_response(result: dict[str, Any]) -> dict[str, Any]:
    """Keep documented metadata, never audio or an expiring subtitle URL."""
    cleaned = {
        key: result[key]
        for key in ("trace_id", "base_resp", "extra_info")
        if key in result
    }
    raw_data = dict(result.get("data") or {})
    data = {key: raw_data[key] for key in ("status",) if key in raw_data}
    if "subtitle_file" in raw_data:
        data["subtitle_file_available"] = (
            isinstance(raw_data["subtitle_file"], str)
            and bool(raw_data["subtitle_file"].strip())
        )
    if data:
        cleaned["data"] = data
    return cleaned


def reusable_segment(out_dir: Path, name: str, text: str,
                     args: argparse.Namespace) -> tuple[Path, dict[str, Any]] | None:
    sidecar_path = out_dir / f"{name}.json"
    if not sidecar_path.exists():
        collisions = list(out_dir.glob(f"{name}.*"))
        collisions = [path for path in collisions if path.name != f"{name}.json"]
        if collisions and not args.overwrite:
            raise MiniMaxError(
                f"Orphaned output for segment {name}; inspect it before retrying or "
                "use --overwrite to authorize replacement"
            )
        return None
    if args.overwrite:
        return None
    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MiniMaxError(f"Invalid partial sidecar {sidecar_path}: {exc}") from exc
    filename = sidecar.get("file")
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise MiniMaxError(f"Unsafe or missing file name in {sidecar_path}")
    audio_path = out_dir / filename
    expected = {
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "voice": args.voice_id,
        "model": args.model,
    }
    if any(sidecar.get(key) != value for key, value in expected.items()):
        raise MiniMaxError(
            f"Existing segment {name} does not match this request; use a new output "
            "directory or explicitly authorize --overwrite"
        )
    if not audio_path.is_file() or audio_path.stat().st_size == 0:
        raise MiniMaxError(f"Partial segment {name} has no valid audio file: {audio_path}")
    return audio_path, sidecar


def decode_hex_audio(value: Any) -> bytes:
    if not isinstance(value, str) or not value:
        raise MiniMaxError("MiniMax response did not contain hex audio")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise MiniMaxError("MiniMax audio was not valid hex") from exc


def media_extension(audio: bytes, requested: str = "") -> str:
    if audio.startswith(b"RIFF"):
        return "wav"
    if audio.startswith(b"fLaC"):
        return "flac"
    if audio.startswith(b"ID3") or audio[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    return requested or "bin"


def concat_audio(files: list[Path], out_dir: Path, pause_ms: int, audio_format: str,
                 sample_rate: int) -> tuple[str | None, list[dict[str, Any]]]:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return None, []
    timeline: list[dict[str, Any]] = []
    concat_lines: list[str] = []
    cursor = 0.0
    silence = out_dir / f"_silence_{pause_ms}ms.{audio_format}"
    if pause_ms > 0:
        codec = "pcm_s16le" if audio_format == "wav" else (
            "flac" if audio_format == "flac" else "libmp3lame"
        )
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
            "-i", f"anullsrc=r={sample_rate}:cl=mono", "-t", str(pause_ms / 1000),
            "-c:a", codec, str(silence),
        ], check=True)
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
    list_file = out_dir / "_concat_minimax.txt"
    list_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    narration = out_dir / f"narration.{audio_format}"
    codec = "pcm_s16le" if audio_format == "wav" else (
        "flac" if audio_format == "flac" else "libmp3lame"
    )
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
        "-i", list_file.name, "-c:a", codec, "-ar", str(sample_rate), "-ac", "1",
        narration.name,
    ], cwd=str(out_dir), check=True)
    return narration.name, timeline


def synthesis_plan(args: argparse.Namespace) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    source = Path(args.text_file)
    segments = read_segments(source)
    price = args.price_cny_per_10k
    activation_cost = (
        9.9 if args.voice_source in ("designed", "cloned")
        and not args.voice_already_activated else 0.0
    )
    estimate = estimate_cost(segments, price, activation_cost)
    plan = {
        "schema_version": 1,
        "status": "planned_not_synthesized",
        "provider": "minimax-cn",
        "endpoint": f"{args.api_base.rstrip('/')}/t2a_v2",
        "model": args.model,
        "voice_id": args.voice_id,
        "voice_source": args.voice_source,
        "voice_already_activated": args.voice_already_activated,
        "consent_record": optional_file_record(args.consent_record),
        "emotion": args.emotion,
        "language_boost": args.language_boost,
        "audio_format": args.audio_format,
        "sample_rate": args.sample_rate,
        "source": source_metadata(source, segments),
        "estimate": estimate,
        "guards": {
            "dry_run_default": True,
            "requires_execute": True,
            "requires_confirm_billable": True,
            "requires_positive_cost_cap": True,
            "api_key_environment_variable": args.api_key_env,
        },
        "timestamp_contract": {
            "requested": "provider word subtitles",
            "publish_words": "fail closed until the downloaded item schema is verified",
            "fallback": "forced alignment",
            "documentation": MINIMAX_T2A_DOC_URL,
        },
    }
    return plan, segments


def cmd_synthesize(args: argparse.Namespace) -> None:
    plan, segments = synthesis_plan(args)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "request_plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    estimate = plan["estimate"]["estimated_cost_cny"]
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        print(f"DRY RUN: no API call; plan written to {plan_path}")
        return
    require_media_tools()
    complete_outputs = [out_dir / "manifest.json"] + [
        out_dir / f"narration.{extension}" for extension in ("wav", "mp3", "flac")
    ]
    collisions = [path for path in complete_outputs if path.exists()]
    if collisions and not args.overwrite:
        raise MiniMaxError(
            "Completed/combined output already exists; use a new directory or pass "
            f"--overwrite explicitly: {', '.join(path.name for path in collisions)}"
        )
    key = require_execution(args, estimate)
    outputs: list[Path] = []
    results: list[dict[str, Any]] = []
    reused = 0
    for name, text in segments:
        existing = reusable_segment(out_dir, name, text, args)
        if existing:
            path, sidecar = existing
            outputs.append(path)
            results.append(sidecar)
            reused += 1
            continue
        payload: dict[str, Any] = {
            "model": args.model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": args.voice_id,
                "speed": args.speed,
                "vol": args.volume,
                "pitch": args.pitch,
            },
            "audio_setting": {
                "sample_rate": args.sample_rate,
                "format": args.audio_format,
                "channel": 1,
            },
            "language_boost": args.language_boost,
            "subtitle_enable": True,
            "subtitle_type": "word",
            "output_format": "hex",
        }
        if args.emotion != "auto":
            payload["voice_setting"]["emotion"] = args.emotion
        result = post_json(f"{args.api_base.rstrip('/')}/t2a_v2", payload, key)
        audio = decode_hex_audio((result.get("data") or {}).get("audio"))
        extension = media_extension(audio)
        if extension == "bin" or extension != args.audio_format:
            raise MiniMaxError(
                f"MiniMax returned unexpected audio container for segment {name}: "
                f"requested {args.audio_format}, detected {extension}"
            )
        path = out_dir / f"{name}.{extension}"
        path.write_bytes(audio)
        outputs.append(path)
        timing = minimax_timing_contract(result, text)
        sidecar = {
            "name": name,
            "text": text,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "file": path.name,
            "duration_s": round(
                float((result.get("extra_info") or {}).get("audio_length", 0)) / 1000,
                3,
            ),
            "voice": args.voice_id,
            "model": args.model,
            "words": timing["words"],
            "timestamps_source": timing["timestamps_source"],
            "timing_contract": timing,
            "response": clean_response(result),
        }
        (out_dir / f"{name}.json").write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        results.append(sidecar)
    try:
        narration, timeline = concat_audio(
            outputs, out_dir, args.pause_ms, args.audio_format, args.sample_rate
        )
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        raise MiniMaxError(
            "Audio concatenation failed after segment generation. Paid segment sidecars "
            "were preserved; fix ffmpeg/input files and rerun in the same directory to resume."
        ) from exc
    raw_by_name = {item["name"]: item for item in results}
    if not timeline:
        cursor = 0.0
        for index, item in enumerate(results):
            duration = float(item["duration_s"])
            timeline.append({
                "name": item["name"],
                "file": item["file"],
                "start_s": round(cursor, 3),
                "end_s": round(cursor + duration, 3),
            })
            cursor += duration
            if args.pause_ms > 0 and index < len(results) - 1:
                cursor += args.pause_ms / 1000
    for segment in timeline:
        segment["text"] = raw_by_name[segment["name"]]["text"]
    total_duration = round(float(timeline[-1]["end_s"]), 3) if timeline else 0.0
    if not narration:
        raise MiniMaxError("Audio concatenation did not produce narration")
    manifest = {
        **plan,
        "status": "synthesized_shadow_candidate_alignment_required",
        "generated_on": date.today().isoformat(),
        "narration": narration,
        "audio_path": narration,
        "pause_ms": args.pause_ms,
        "total_duration_s": total_duration,
        "duration_sec": total_duration,
        "model_revision": None,
        "model_revision_note": "Provider-managed revision is not exposed by this API.",
        "license_checked_at": PRICING_CHECKED,
        "cost": {
            "currency": "CNY",
            "estimated_amount": plan["estimate"]["estimated_cost_cny"],
            "billable_units_estimate": plan["estimate"]["billing_characters_estimate"],
            "provider_actual_amount": None,
        },
        "resume": {"reused_segments": reused, "new_segments": len(results) - reused},
        "segments": timeline,
        "raw": results,
        "note": (
            "Listening A/B shadow only. Provider subtitle item fields are not "
            "documented, so publish subtitles require forced alignment and human review."
        ),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Generated {len(outputs)} segments in {out_dir}")
    print(f"Manifest: {out_dir / 'manifest.json'}")


def cmd_voices(args: argparse.Namespace) -> None:
    if not args.execute:
        print(json.dumps({
            "status": "planned_not_requested",
            "endpoint": f"{args.api_base.rstrip('/')}/get_voice",
            "voice_type": args.voice_type,
            "billable": False,
            "api_key_environment_variable": args.api_key_env,
        }, ensure_ascii=False, indent=2))
        print("DRY RUN: no API call")
        return
    key = require_execution(args)
    result = post_json(
        f"{args.api_base.rstrip('/')}/get_voice", {"voice_type": args.voice_type}, key
    )
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        output_path = Path(args.out)
        if output_path.exists() and not args.overwrite:
            raise MiniMaxError(
                f"Refusing to overwrite voice catalog: {output_path}; use --overwrite"
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"Voice catalog written to {args.out}")
    else:
        print(output)


def cmd_design(args: argparse.Namespace) -> None:
    preview = Path(args.preview_text_file).read_text(encoding="utf-8").strip()
    prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
    if not prompt or not preview:
        raise MiniMaxError("Voice design prompt and preview text must be non-empty")
    if len(preview) > 500:
        raise MiniMaxError("MiniMax voice-design preview text must be <= 500 characters")
    preview_units = billable_characters(preview)
    preview_cost = round(preview_units * args.preview_price_cny_per_10k / 10_000, 6)
    plan = {
        "schema_version": 1,
        "status": "planned_not_designed",
        "provider": "minimax-cn",
        "endpoint": f"{args.api_base.rstrip('/')}/voice_design",
        "prompt_source": {
            "path": portable_path(Path(args.prompt_file)),
            "sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        },
        "preview_text_source": {
            "path": portable_path(Path(args.preview_text_file)),
            "sha256": hashlib.sha256(preview.encode("utf-8")).hexdigest(),
        },
        "preview_billing_characters_estimate": preview_units,
        "preview_estimated_cost_cny": preview_cost,
        "activation_cost_cny": 9.9,
        "pricing_checked": PRICING_CHECKED,
        "note": "The CNY 9.9 voice-design fee is charged on first formal T2A use, not this preview call.",
    }
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "voice_design_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        print("DRY RUN: no API call")
        return
    collisions = [
        path for path in [out_dir / "voice_design_manifest.json", *out_dir.glob("trial.*")]
        if path.exists()
    ]
    if collisions and not args.overwrite:
        raise MiniMaxError(
            "Voice-design output already exists; use a new directory or pass "
            f"--overwrite explicitly: {', '.join(path.name for path in collisions)}"
        )
    key = require_execution(args, preview_cost)
    payload: dict[str, Any] = {"prompt": prompt, "preview_text": preview}
    if args.voice_id:
        payload["voice_id"] = args.voice_id
    result = post_json(f"{args.api_base.rstrip('/')}/voice_design", payload, key)
    audio = decode_hex_audio(result.get("trial_audio"))
    extension = media_extension(audio)
    if extension == "bin":
        raise MiniMaxError("MiniMax voice design returned an unknown audio container")
    audio_path = out_dir / f"trial.{extension}"
    audio_path.write_bytes(audio)
    manifest = {
        **plan,
        "status": "designed_temporary_not_activated",
        "voice_id": result.get("voice_id"),
        "trial_audio": audio_path.name,
        "response": clean_response(result),
    }
    (out_dir / "voice_design_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Temporary voice design: {result.get('voice_id')}")
    print(f"Trial audio: {audio_path}")


def cmd_self_test(_: argparse.Namespace) -> None:
    def check(condition: bool, message: str) -> None:
        if not condition:
            raise MiniMaxError(f"self-test failed: {message}")

    check(billable_characters("中文 A!") == 7, "billing character rule")
    segments = [("01", "中文"), ("02", "API")]
    estimate = estimate_cost(segments, 3.5)
    check(estimate["billing_characters_estimate"] == 7, "billing estimate")
    check(estimate["estimated_cost_cny"] == 0.00245, "cost estimate")
    check(media_extension(b"RIFFxxxx") == "wav", "WAV detection")
    check(media_extension(b"ID3xxxx") == "mp3", "MP3 detection")
    check(VOICE_DESIGN_PREVIEW_PRICE_CNY_PER_10K == 2.0, "design price floor")
    valid_words, reason = validate_word_timings(
        "你好，API！",
        [
            {"text": "你", "start_ms": 0, "end_ms": 120},
            {"text": "好", "start_ms": 120, "end_ms": 240},
            {"text": "API", "start_ms": 260, "end_ms": 600},
        ],
        complete=True,
        audio_duration_ms=700,
    )
    check(reason is None and len(valid_words) == 3, "strict word timing acceptance")
    invalid_words, reason = validate_word_timings(
        "你好",
        [
            {"text": "你", "start_ms": 0, "end_ms": 200},
            {"text": "好", "start_ms": 150, "end_ms": 300},
        ],
        complete=True,
    )
    check(not invalid_words and reason == "word_1_time_not_monotonic", "overlap rejection")
    mock = {
        "data": {"status": 2, "subtitle_file": "https://example.invalid/temporary"},
        "extra_info": {"audio_length": 700},
        "base_resp": {"status_code": 0},
    }
    timing = minimax_timing_contract(mock, "你好")
    check(not timing["words"], "unverified MiniMax subtitle schema stays empty")
    check(
        timing["reason"] == "provider_subtitle_item_schema_not_documented",
        "MiniMax subtitle evidence classification",
    )
    check(
        "subtitle_file" not in clean_response(mock).get("data", {}),
        "expiring subtitle URL redaction",
    )
    print("self-test passed")


def add_execution_flags(parser: argparse.ArgumentParser, with_budget: bool) -> None:
    parser.add_argument("--execute", action="store_true", help="make the API call")
    parser.add_argument(
        "--confirm-billable", action="store_true",
        help="confirm external API use; required even for non-billable account reads",
    )
    parser.add_argument("--api-key-env", default="MINIMAX_API_KEY")
    parser.add_argument("--api-base", default=API_BASE)
    parser.add_argument(
        "--overwrite", action="store_true",
        help="explicitly allow replacing existing output files (may repeat paid work)",
    )
    if with_budget:
        parser.add_argument("--max-cost-cny", type=float)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MiniMax Speech 2.8 adapter (dry-run and budget guarded by default)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    synth = sub.add_parser("synthesize", help="plan or synthesize one segment per line")
    synth.add_argument("--text-file", required=True)
    synth.add_argument("--out", required=True)
    synth.add_argument("--model", choices=MODELS, default="speech-2.8-hd")
    synth.add_argument("--voice-id", required=True)
    synth.add_argument(
        "--voice-source", choices=("system", "designed", "cloned"), default="system",
        help="designed/cloned first use adds the documented activation fee to the cost guard",
    )
    synth.add_argument(
        "--voice-already-activated", action="store_true",
        help="declare that a designed/cloned voice has already paid its first-use fee",
    )
    synth.add_argument(
        "--consent-record",
        help="local authorization record required when --voice-source cloned",
    )
    synth.add_argument(
        "--confirm-voice-rights", action="store_true",
        help="confirm that the cloned voice input and commercial use are authorized",
    )
    synth.add_argument("--emotion", choices=EMOTIONS, default="auto")
    synth.add_argument("--language-boost", default="auto")
    synth.add_argument("--speed", type=float, default=1.0)
    synth.add_argument("--volume", type=float, default=1.0)
    synth.add_argument("--pitch", type=int, choices=range(-12, 13), default=0)
    synth.add_argument("--sample-rate", type=int, default=32000)
    synth.add_argument("--audio-format", choices=("wav", "mp3", "flac"), default="wav")
    synth.add_argument("--pause-ms", type=int, default=350)
    synth.add_argument("--price-cny-per-10k", type=float)
    add_execution_flags(synth, with_budget=True)
    synth.set_defaults(func=cmd_synthesize)

    voices = sub.add_parser("voices", help="plan or query the account voice catalog")
    voices.add_argument(
        "--voice-type", choices=("system", "voice_cloning", "voice_generation", "all"),
        default="system",
    )
    voices.add_argument("--out")
    add_execution_flags(voices, with_budget=False)
    voices.set_defaults(func=cmd_voices)

    design = sub.add_parser("design", help="plan or create a temporary original voice")
    design.add_argument("--prompt-file", required=True)
    design.add_argument("--preview-text-file", required=True)
    design.add_argument("--voice-id")
    design.add_argument("--out", required=True)
    design.add_argument(
        "--preview-price-cny-per-10k", type=float,
        default=VOICE_DESIGN_PREVIEW_PRICE_CNY_PER_10K,
        help="current verified preview price; values below the built-in safety floor are rejected",
    )
    add_execution_flags(design, with_budget=True)
    design.set_defaults(func=cmd_design)

    test = sub.add_parser("self-test", help="run offline contract tests")
    test.set_defaults(func=cmd_self_test)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if hasattr(args, "api_base") and args.api_base.rstrip("/") not in ALLOWED_API_BASES:
        raise MiniMaxError("--api-base must be an official MiniMax China API endpoint")
    if getattr(args, "price_cny_per_10k", None) is None and hasattr(args, "model"):
        args.price_cny_per_10k = MODEL_PRICE_CNY_PER_10K[args.model]
    if (
        not math.isfinite(getattr(args, "price_cny_per_10k", 1))
        or getattr(args, "price_cny_per_10k", 1) <= 0
    ):
        raise MiniMaxError("--price-cny-per-10k must be positive and finite")
    if hasattr(args, "model") and args.price_cny_per_10k < MODEL_PRICE_CNY_PER_10K[args.model]:
        raise MiniMaxError(
            "--price-cny-per-10k cannot be lower than the built-in verified "
            f"price floor ({MODEL_PRICE_CNY_PER_10K[args.model]} CNY for {args.model})"
        )
    if (
        not math.isfinite(getattr(args, "preview_price_cny_per_10k", 1))
        or getattr(args, "preview_price_cny_per_10k", 1) <= 0
    ):
        raise MiniMaxError("--preview-price-cny-per-10k must be positive and finite")
    if (
        hasattr(args, "preview_price_cny_per_10k")
        and args.preview_price_cny_per_10k < VOICE_DESIGN_PREVIEW_PRICE_CNY_PER_10K
    ):
        raise MiniMaxError(
            "--preview-price-cny-per-10k cannot be lower than the built-in "
            f"verified price floor ({VOICE_DESIGN_PREVIEW_PRICE_CNY_PER_10K} CNY)"
        )
    if hasattr(args, "voice_id") and args.command == "synthesize" and not args.voice_id.strip():
        raise MiniMaxError("--voice-id must be non-empty")
    if hasattr(args, "speed") and (
        not math.isfinite(args.speed) or not 0.5 <= args.speed <= 2.0
    ):
        raise MiniMaxError("--speed must be between 0.5 and 2.0")
    if hasattr(args, "pause_ms") and args.pause_ms < 0:
        raise MiniMaxError("--pause-ms must be non-negative")
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except MiniMaxError as exc:
        sys.exit(f"error: {exc}")
