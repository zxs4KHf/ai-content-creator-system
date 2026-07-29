#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Budget-guarded DashScope Qwen-Audio/CosyVoice shadow adapter.

The command is dry-run by default and imports the DashScope SDK only after all
local guards pass. It targets the official Beijing workspace WebSocket endpoint
through ``dashscope.audio.tts_v2.SpeechSynthesizer``. Keys and Workspace IDs are
read from environment variables and are never written to output files.

Non-streaming synthesis is deliberate for the first listening A/B. The module
also validates documented streaming event envelopes offline, but it does not
guess undocumented provider word-item fields. Manifests therefore keep
``words=[]`` and require forced alignment until a real schema fixture is
verified.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any


PRICING_CHECKED = "2026-07-29"
PRICING_MAX_AGE_DAYS = 30
MIN_DASHSCOPE_VERSION = (1, 26, 4)
MODEL_PRICE_CNY_PER_10K = {
    "qwen-audio-3.0-tts-plus": 1.4,
    "cosyvoice-v3.5-plus": 1.5,
    "cosyvoice-v3.5-flash": 0.8,
}
MODELS = tuple(MODEL_PRICE_CNY_PER_10K)
LANGUAGE_HINTS = (
    "zh", "en", "fr", "de", "ja", "ko", "ru", "pt", "th", "id",
    "vi", "es", "it", "ms", "fil", "ar",
)


class DashScopeError(RuntimeError):
    pass


TIMING_CONTRACT_VERSION = 1
DASHSCOPE_TTS_DOC_URL = (
    "https://help.aliyun.com/zh/model-studio/cosyvoice-python-sdk"
)
TIMESTAMP_UNSUPPORTED_MODELS = {"qwen-audio-3.0-tts-plus"}
DOCUMENTED_EVENT_TYPES = {
    "sentence-begin",
    "sentence-synthesis",
    "sentence-end",
}


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
    """Validate canonical word timing records; provider aliases are not guessed."""
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


def normalize_dashscope_event(message: Any) -> dict[str, Any]:
    """Normalize only fields documented for ``ResultCallback.on_event``.

    Current official documentation lists ``sentence.words`` but does not define
    the fields of each item. Raw word objects therefore remain evidence and are
    never mapped into publishable ``words`` here.
    """
    if isinstance(message, str):
        try:
            event = json.loads(message)
        except json.JSONDecodeError as exc:
            raise DashScopeError("DashScope timing event is not valid JSON") from exc
    elif isinstance(message, dict):
        event = message
    else:
        raise DashScopeError("DashScope timing event must be JSON text or an object")

    header = event.get("header")
    payload = event.get("payload")
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise DashScopeError("DashScope timing event lacks header/payload objects")
    if header.get("event") != "result-generated":
        raise DashScopeError("DashScope timing event is not result-generated")
    output = payload.get("output")
    if not isinstance(output, dict):
        raise DashScopeError("DashScope timing event lacks payload.output")
    event_type = output.get("type")
    if event_type not in DOCUMENTED_EVENT_TYPES:
        raise DashScopeError("DashScope timing event has an undocumented output.type")
    sentence = output.get("sentence")
    if not isinstance(sentence, dict):
        raise DashScopeError("DashScope timing event lacks output.sentence")
    index = sentence.get("index")
    if type(index) is not int or index < 0:
        raise DashScopeError("DashScope timing event has an invalid sentence index")
    original_text = output.get("original_text")
    if event_type in ("sentence-begin", "sentence-end") and not isinstance(
        original_text, str
    ):
        raise DashScopeError("DashScope boundary event lacks original_text")
    raw_words = sentence.get("words")
    if raw_words is not None and not isinstance(raw_words, list):
        raise DashScopeError("DashScope timing event sentence.words is not a list")
    return {
        "type": event_type,
        "sentence_index": index,
        "original_text": original_text if isinstance(original_text, str) else None,
        "word_items_present": bool(raw_words),
        "word_item_count": len(raw_words or []),
    }


def dashscope_timing_contract(
    messages: list[Any],
    source_text: str,
    *,
    model: str,
    voice_source: str,
    completed: bool,
    streaming: bool,
) -> dict[str, Any]:
    """Classify provider timing evidence and fail closed when it is insufficient."""
    normalized_events: list[dict[str, Any]] = []
    event_error: str | None = None
    try:
        normalized_events = [normalize_dashscope_event(item) for item in messages]
    except DashScopeError as exc:
        event_error = str(exc)

    end_events = [
        item for item in normalized_events if item["type"] == "sentence-end"
    ]
    indexes = [item["sentence_index"] for item in end_events]
    contiguous = indexes == list(range(len(indexes)))
    event_text = "".join(item.get("original_text") or "" for item in end_events)
    text_covered = bool(end_events) and timing_text(event_text) == timing_text(source_text)
    word_items_present = bool(end_events) and all(
        item["word_items_present"] for item in end_events
    )

    if not streaming:
        reason = "nonstreaming_call_has_no_word_events"
    elif model in TIMESTAMP_UNSUPPORTED_MODELS:
        reason = "model_word_timestamps_not_supported"
    elif voice_source != "cloned":
        reason = "voice_timestamp_capability_not_documented"
    elif not completed:
        reason = "provider_result_incomplete"
    elif event_error:
        reason = "provider_event_invalid"
    elif not contiguous:
        reason = "sentence_events_not_contiguous"
    elif not text_covered:
        reason = "sentence_events_do_not_cover_source"
    elif not word_items_present:
        reason = "provider_word_items_missing"
    else:
        reason = "provider_word_item_schema_not_documented"

    words, validation_error = validate_word_timings(
        source_text,
        [],
        complete=completed,
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
            "completed": completed,
            "streaming": streaming,
            "model": model,
            "voice_source": voice_source,
            "normalized_event_count": len(normalized_events),
            "sentence_end_count": len(end_events),
            "sentence_indexes_contiguous": contiguous,
            "sentence_text_covers_source": text_covered,
            "word_items_present": word_items_present,
            "event_error": event_error,
            "documentation": DASHSCOPE_TTS_DOC_URL,
        },
    }


def portable_path(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.name


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_segments(path: Path) -> list[tuple[str, str]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    segments = [
        (f"{index:02d}", text)
        for index, text in enumerate((line for line in lines if line), 1)
    ]
    if not segments:
        raise DashScopeError(f"No non-empty segments in {path}")
    too_long = [name for name, text in segments if len(text) > 20_000]
    if too_long:
        raise DashScopeError(
            "DashScope SpeechSynthesizer.call supports at most 20000 characters "
            f"per segment; too long: {', '.join(too_long)}"
        )
    return segments


def billable_characters(text: str) -> int:
    return sum(
        2 if (
            "\u3400" <= char <= "\u4dbf"
            or "\u4e00" <= char <= "\u9fff"
            or "\uf900" <= char <= "\ufaff"
        ) else 1
        for char in text
    )


def estimate_cost(segments: list[tuple[str, str]], price: float) -> dict[str, Any]:
    units = sum(billable_characters(text) for _, text in segments)
    return {
        "billing_characters_estimate": units,
        "price_cny_per_10000_characters": price,
        "estimated_cost_cny": round(units * price / 10_000, 6),
        "pricing_checked": PRICING_CHECKED,
    }


def optional_file_record(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_file():
        raise DashScopeError(f"Rights/consent record does not exist: {path}")
    return {
        "path": portable_path(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def require_media_tools() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        raise DashScopeError(
            "Execution requires ffmpeg and ffprobe on PATH before any paid call; "
            f"missing: {', '.join(missing)}"
        )


def version_tuple(value: str) -> tuple[int, int, int]:
    numbers = [int(item) for item in re.findall(r"\d+", value)[:3]]
    return tuple((numbers + [0, 0, 0])[:3])


def require_execution(args: argparse.Namespace, estimate: dict[str, Any]) -> tuple[str, str]:
    if not args.confirm_billable:
        raise DashScopeError("Execution requires --confirm-billable")
    if (
        args.max_cost_cny is None
        or not math.isfinite(args.max_cost_cny)
        or args.max_cost_cny <= 0
    ):
        raise DashScopeError("Execution requires a positive finite --max-cost-cny")
    pricing_age = (date.today() - date.fromisoformat(PRICING_CHECKED)).days
    if pricing_age < 0 or pricing_age > PRICING_MAX_AGE_DAYS:
        raise DashScopeError(
            f"Built-in pricing snapshot {PRICING_CHECKED} is stale; verify official "
            "pricing and update the adapter before a billable call"
        )
    if estimate["estimated_cost_cny"] > args.max_cost_cny:
        raise DashScopeError(
            f"Estimated cost CNY {estimate['estimated_cost_cny']:.6f} exceeds cap "
            f"{args.max_cost_cny:.6f}"
        )
    if args.voice_source == "cloned":
        if not args.confirm_voice_rights:
            raise DashScopeError("Cloned voice execution requires --confirm-voice-rights")
        if not args.consent_record:
            raise DashScopeError("Cloned voice execution requires --consent-record")
        optional_file_record(args.consent_record)
    key = os.environ.get(args.api_key_env, "")
    workspace = os.environ.get(args.workspace_id_env, "")
    if not key:
        raise DashScopeError(f"Missing API key environment variable: {args.api_key_env}")
    if not workspace:
        raise DashScopeError(
            f"Missing Workspace ID environment variable: {args.workspace_id_env}"
        )
    if not re.fullmatch(r"[A-Za-z0-9-]+", workspace):
        raise DashScopeError("Workspace ID contains unexpected characters")
    return key, workspace


def probe_duration(path: Path) -> float:
    try:
        value = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ], check=True, capture_output=True, text=True).stdout.strip()
        return float(value)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        raise DashScopeError(f"Could not decode generated audio {path}") from exc


def is_mp3(audio: bytes) -> bool:
    return audio.startswith(b"ID3") or audio[:2] in (
        b"\xff\xfb", b"\xff\xf3", b"\xff\xf2",
    )


def reusable_segment(out_dir: Path, name: str, text: str,
                     args: argparse.Namespace) -> tuple[Path, dict[str, Any]] | None:
    sidecar_path = out_dir / f"{name}.json"
    if not sidecar_path.exists():
        collisions = [
            path for path in out_dir.glob(f"{name}.*")
            if path.name != f"{name}.json"
        ]
        if collisions and not args.overwrite:
            raise DashScopeError(
                f"Orphaned output for segment {name}; inspect it before retrying or "
                "use --overwrite to authorize replacement"
            )
        return None
    if args.overwrite:
        return None
    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DashScopeError(f"Invalid partial sidecar {sidecar_path}: {exc}") from exc
    filename = sidecar.get("file")
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise DashScopeError(f"Unsafe or missing file name in {sidecar_path}")
    audio_path = out_dir / filename
    expected = {
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "voice": args.voice_id,
        "voice_source": args.voice_source,
        "model": args.model,
        "instruction": args.instruction,
        "language_hint": args.language_hint,
        "seed": args.seed,
    }
    if any(sidecar.get(key) != value for key, value in expected.items()):
        raise DashScopeError(
            f"Existing segment {name} does not match this request; use a new output "
            "directory or explicitly authorize --overwrite"
        )
    if not audio_path.is_file() or audio_path.stat().st_size == 0:
        raise DashScopeError(f"Partial segment {name} has no valid audio file: {audio_path}")
    return audio_path, sidecar


def concat_audio(files: list[Path], out_dir: Path, pause_ms: int
                 ) -> tuple[str, list[dict[str, Any]]]:
    silence = out_dir / f"_silence_{pause_ms}ms.mp3"
    if pause_ms > 0:
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono", "-t", str(pause_ms / 1000),
            "-c:a", "libmp3lame", "-b:a", "192k", str(silence),
        ], check=True)
    lines: list[str] = []
    timeline: list[dict[str, Any]] = []
    cursor = 0.0
    for index, path in enumerate(files):
        duration = probe_duration(path)
        lines.append(f"file '{path.name}'")
        timeline.append({
            "name": path.stem,
            "file": path.name,
            "start_s": round(cursor, 3),
            "end_s": round(cursor + duration, 3),
        })
        cursor += duration
        if pause_ms > 0 and index < len(files) - 1:
            lines.append(f"file '{silence.name}'")
            cursor += pause_ms / 1000
    concat_file = out_dir / "_concat_dashscope.txt"
    concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    narration = out_dir / "narration.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
        "-i", concat_file.name, "-c:a", "libmp3lame", "-b:a", "192k",
        "-ar", "44100", "-ac", "1", narration.name,
    ], cwd=str(out_dir), check=True)
    return narration.name, timeline


def make_plan(args: argparse.Namespace) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    source = Path(args.text_file)
    segments = read_segments(source)
    estimate = estimate_cost(segments, args.price_cny_per_10k)
    plan = {
        "schema_version": 1,
        "status": "planned_not_synthesized",
        "provider": "aliyun-dashscope-cn-beijing",
        "model": args.model,
        "model_revision": None,
        "model_revision_note": "Provider-managed alias; pin when a snapshot ID is exposed.",
        "voice_id": args.voice_id,
        "voice_source": args.voice_source,
        "consent_record": optional_file_record(args.consent_record),
        "instruction": args.instruction,
        "language_hint": args.language_hint,
        "seed": args.seed,
        "audio_format": "mp3 (official SDK default)",
        "source": {
            "path": portable_path(source),
            "sha256": sha256_file(source),
            "segment_count": len(segments),
        },
        "estimate": estimate,
        "guards": {
            "dry_run_default": True,
            "requires_execute": True,
            "requires_confirm_billable": True,
            "requires_positive_finite_cost_cap": True,
            "pricing_max_age_days": PRICING_MAX_AGE_DAYS,
            "api_key_environment_variable": args.api_key_env,
            "workspace_id_environment_variable": args.workspace_id_env,
            "beijing_workspace_endpoint_only": True,
            "no_clobber_default": True,
        },
        "timestamp_contract": {
            "mode": "nonstreaming listening A/B",
            "publish_words": "fail closed; nonstreaming call has no word events",
            "streaming_evidence": (
                "documented event envelopes can be normalized offline, but current "
                "word-item fields are not documented"
            ),
            "fallback": "forced alignment",
            "documentation": DASHSCOPE_TTS_DOC_URL,
        },
    }
    return plan, segments


def cmd_synthesize(args: argparse.Namespace) -> None:
    plan, segments = make_plan(args)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "request_plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        print(f"DRY RUN: no API call; plan written to {plan_path}")
        return

    require_media_tools()
    collisions = [
        path for path in (out_dir / "manifest.json", out_dir / "narration.mp3")
        if path.exists()
    ]
    if collisions and not args.overwrite:
        raise DashScopeError(
            "Completed/combined output already exists; use a new directory or pass "
            f"--overwrite explicitly: {', '.join(path.name for path in collisions)}"
        )
    key, workspace = require_execution(args, plan["estimate"])

    prepared = [
        (name, text, reusable_segment(out_dir, name, text, args))
        for name, text in segments
    ]
    need_api = any(existing is None for _, _, existing in prepared)
    SpeechSynthesizer = None
    if need_api:
        try:
            installed = importlib.metadata.version("dashscope")
        except importlib.metadata.PackageNotFoundError as exc:
            raise DashScopeError(
                "Missing isolated-environment dependency: dashscope>=1.26.4"
            ) from exc
        if version_tuple(installed) < MIN_DASHSCOPE_VERSION:
            raise DashScopeError(
                f"dashscope {installed} is too old; require >=1.26.4"
            )
        try:
            import dashscope
            from dashscope.audio.tts_v2 import SpeechSynthesizer as Synthesizer
        except ImportError as exc:
            raise DashScopeError("DashScope TTS v2 SDK import failed") from exc
        dashscope.api_key = key
        dashscope.base_websocket_api_url = (
            f"wss://{workspace}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"
        )
        SpeechSynthesizer = Synthesizer

    outputs: list[Path] = []
    results: list[dict[str, Any]] = []
    reused = 0
    for name, text, existing in prepared:
        if existing:
            path, result = existing
            outputs.append(path)
            results.append(result)
            reused += 1
            continue
        if SpeechSynthesizer is None:
            raise DashScopeError("Internal error: DashScope runtime was not initialized")
        kwargs: dict[str, Any] = {
            "model": args.model,
            "voice": args.voice_id,
            "volume": args.volume,
            "speech_rate": args.speech_rate,
            "pitch_rate": args.pitch_rate,
            "seed": args.seed,
        }
        if args.instruction:
            kwargs["instruction"] = args.instruction
        if args.language_hint:
            kwargs["language_hints"] = [args.language_hint]
        try:
            synthesizer = SpeechSynthesizer(**kwargs)
            audio = synthesizer.call(text)
        except Exception as exc:
            raise DashScopeError(
                f"DashScope synthesis failed for segment {name}: {exc}"
            ) from exc
        if not isinstance(audio, (bytes, bytearray)) or not audio:
            raise DashScopeError(f"DashScope returned no audio bytes for segment {name}")
        audio_bytes = bytes(audio)
        if not is_mp3(audio_bytes):
            raise DashScopeError(
                f"DashScope returned an unexpected audio container for segment {name}"
            )
        path = out_dir / f"{name}.mp3"
        path.write_bytes(audio_bytes)
        duration = probe_duration(path)
        request_id = None
        first_delay = None
        try:
            request_id = synthesizer.get_last_request_id()
            first_delay = synthesizer.get_first_package_delay()
        except Exception:
            pass
        timing = dashscope_timing_contract(
            [],
            text,
            model=args.model,
            voice_source=args.voice_source,
            completed=True,
            streaming=False,
        )
        result = {
            "name": name,
            "text": text,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "file": path.name,
            "duration_s": round(duration, 3),
            "voice": args.voice_id,
            "voice_source": args.voice_source,
            "model": args.model,
            "instruction": args.instruction,
            "language_hint": args.language_hint,
            "seed": args.seed,
            "request_id": request_id,
            "first_package_delay_ms": first_delay,
            "words": timing["words"],
            "timestamps_source": timing["timestamps_source"],
            "timing_contract": timing,
        }
        (out_dir / f"{name}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        outputs.append(path)
        results.append(result)

    try:
        narration, timeline = concat_audio(outputs, out_dir, args.pause_ms)
    except (OSError, subprocess.CalledProcessError, ValueError, DashScopeError) as exc:
        raise DashScopeError(
            "Audio concatenation failed after segment generation. Paid segment sidecars "
            "were preserved; fix ffmpeg/input files and rerun in the same directory."
        ) from exc
    by_name = {item["name"]: item for item in results}
    for item in timeline:
        item["text"] = by_name[item["name"]]["text"]
    total_duration = round(float(timeline[-1]["end_s"]), 3) if timeline else 0.0
    manifest = {
        **plan,
        "status": "synthesized_shadow_candidate_alignment_required",
        "generated_on": date.today().isoformat(),
        "narration": narration,
        "audio_path": narration,
        "pause_ms": args.pause_ms,
        "total_duration_s": total_duration,
        "duration_sec": total_duration,
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
            "Listening A/B shadow only. Forced alignment and blind/stability/rights "
            "gates are required before G3 use."
        ),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Generated {len(outputs)} DashScope segments in {out_dir}")
    print(f"Manifest: {out_dir / 'manifest.json'}")


def cmd_self_test(_: argparse.Namespace) -> None:
    def check(condition: bool, message: str) -> None:
        if not condition:
            raise DashScopeError(f"self-test failed: {message}")

    check(billable_characters("中文 A!") == 7, "billing character rule")
    estimate = estimate_cost([("01", "中文"), ("02", "API")], 1.4)
    check(estimate["billing_characters_estimate"] == 7, "billing estimate")
    check(estimate["estimated_cost_cny"] == 0.00098, "cost estimate")
    check(version_tuple("1.26.4") == MIN_DASHSCOPE_VERSION, "SDK version parsing")
    check(is_mp3(b"ID3fixture"), "MP3 detection")
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
    mock_event = {
        "header": {"task_id": "offline-fixture", "event": "result-generated"},
        "payload": {
            "output": {
                "type": "sentence-end",
                "original_text": "你好",
                "sentence": {
                    "index": 0,
                    "words": [{"undocumented": "intentionally-not-mapped"}],
                },
            }
        },
    }
    normalized = normalize_dashscope_event(mock_event)
    check(normalized["word_item_count"] == 1, "documented event envelope parsing")
    timing = dashscope_timing_contract(
        [mock_event],
        "你好",
        model="cosyvoice-v3.5-plus",
        voice_source="cloned",
        completed=True,
        streaming=True,
    )
    check(not timing["words"], "undocumented DashScope word schema stays empty")
    check(
        timing["reason"] == "provider_word_item_schema_not_documented",
        "DashScope word schema evidence classification",
    )
    unsupported = dashscope_timing_contract(
        [mock_event],
        "你好",
        model="qwen-audio-3.0-tts-plus",
        voice_source="system",
        completed=True,
        streaming=True,
    )
    check(
        unsupported["reason"] == "model_word_timestamps_not_supported",
        "Qwen-Audio Plus timestamp refusal",
    )
    print("self-test passed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="DashScope Qwen-Audio/CosyVoice adapter (dry-run/budget guarded)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    synth = sub.add_parser("synthesize", help="plan or synthesize one segment per line")
    synth.add_argument("--text-file", required=True)
    synth.add_argument("--out", required=True)
    synth.add_argument("--model", choices=MODELS, default="qwen-audio-3.0-tts-plus")
    synth.add_argument("--voice-id", required=True)
    synth.add_argument(
        "--voice-source", choices=("system", "designed", "cloned"), default="system"
    )
    synth.add_argument("--instruction", default="")
    synth.add_argument("--language-hint", choices=LANGUAGE_HINTS)
    synth.add_argument("--seed", type=int, default=42)
    synth.add_argument("--volume", type=int, default=50)
    synth.add_argument("--speech-rate", type=float, default=1.0)
    synth.add_argument("--pitch-rate", type=float, default=1.0)
    synth.add_argument("--pause-ms", type=int, default=350)
    synth.add_argument("--price-cny-per-10k", type=float)
    synth.add_argument("--execute", action="store_true")
    synth.add_argument("--confirm-billable", action="store_true")
    synth.add_argument("--max-cost-cny", type=float)
    synth.add_argument("--api-key-env", default="DASHSCOPE_API_KEY")
    synth.add_argument("--workspace-id-env", default="DASHSCOPE_WORKSPACE_ID")
    synth.add_argument("--consent-record")
    synth.add_argument("--confirm-voice-rights", action="store_true")
    synth.add_argument(
        "--overwrite", action="store_true",
        help="explicitly allow replacing existing output files (may repeat paid work)",
    )
    synth.set_defaults(func=cmd_synthesize)
    test = sub.add_parser("self-test", help="run offline contract tests")
    test.set_defaults(func=cmd_self_test)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if hasattr(args, "model"):
        if args.price_cny_per_10k is None:
            args.price_cny_per_10k = MODEL_PRICE_CNY_PER_10K[args.model]
        if (
            not math.isfinite(args.price_cny_per_10k)
            or args.price_cny_per_10k <= 0
        ):
            raise DashScopeError("--price-cny-per-10k must be positive and finite")
        if args.price_cny_per_10k < MODEL_PRICE_CNY_PER_10K[args.model]:
            raise DashScopeError(
                "--price-cny-per-10k cannot be lower than the built-in verified "
                f"price floor ({MODEL_PRICE_CNY_PER_10K[args.model]} CNY for {args.model})"
            )
        if not args.voice_id.strip():
            raise DashScopeError("--voice-id must be non-empty")
        if args.model.startswith("cosyvoice-") and args.voice_source == "system":
            raise DashScopeError(
                "CosyVoice 3.5 has no system voices; use a designed or authorized cloned voice"
            )
        if not 0 <= args.volume <= 100:
            raise DashScopeError("--volume must be between 0 and 100")
        for name in ("speech_rate", "pitch_rate"):
            value = getattr(args, name)
            if not math.isfinite(value) or not 0.5 <= value <= 2.0:
                raise DashScopeError(f"--{name.replace('_', '-')} must be between 0.5 and 2.0")
        if not 0 <= args.seed <= 65535:
            raise DashScopeError("--seed must be between 0 and 65535")
        if args.pause_ms < 0:
            raise DashScopeError("--pause-ms must be non-negative")
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except DashScopeError as exc:
        sys.exit(f"error: {exc}")
