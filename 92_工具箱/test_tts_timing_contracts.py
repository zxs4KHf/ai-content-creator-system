#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline contract tests for guarded MiniMax and DashScope timing evidence."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOL_DIR))

import tts_dashscope as dashscope  # noqa: E402
import tts_minimax as minimax  # noqa: E402


def dashscope_event(
    *,
    event_type: str = "sentence-end",
    index: int = 0,
    text: str = "你好",
    words: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "header": {"task_id": "offline-fixture", "event": "result-generated"},
        "payload": {
            "output": {
                "type": event_type,
                "original_text": text,
                "sentence": {
                    "index": index,
                    "words": words if words is not None else [],
                },
            }
        },
    }


class CanonicalWordTimingTests(unittest.TestCase):
    def test_both_validators_accept_complete_monotonic_coverage(self) -> None:
        words = [
            {"text": "你", "start_ms": 0, "end_ms": 100},
            {"text": "好", "start_ms": 100, "end_ms": 240},
            {"text": "API", "start_ms": 300, "end_ms": 620},
        ]
        for module in (minimax, dashscope):
            with self.subTest(module=module.__name__):
                result, reason = module.validate_word_timings(
                    "你好， API！",
                    words,
                    complete=True,
                    audio_duration_ms=700,
                )
                self.assertIsNone(reason)
                self.assertEqual([item["text"] for item in result], ["你", "好", "API"])

    def test_both_validators_reject_incomplete_overlap_and_missing_text(self) -> None:
        cases = [
            (
                [{"text": "你好", "start_ms": 0, "end_ms": 200}],
                False,
                "provider_result_incomplete",
            ),
            (
                [
                    {"text": "你", "start_ms": 0, "end_ms": 200},
                    {"text": "好", "start_ms": 150, "end_ms": 300},
                ],
                True,
                "word_1_time_not_monotonic",
            ),
            (
                [{"text": "你", "start_ms": 0, "end_ms": 200}],
                True,
                "word_text_does_not_cover_source",
            ),
        ]
        for module in (minimax, dashscope):
            for words, complete, expected in cases:
                with self.subTest(module=module.__name__, expected=expected):
                    result, reason = module.validate_word_timings(
                        "你好", words, complete=complete
                    )
                    self.assertEqual(result, [])
                    self.assertEqual(reason, expected)

    def test_boolean_and_audio_overflow_are_not_valid_milliseconds(self) -> None:
        result, reason = minimax.validate_word_timings(
            "你",
            [{"text": "你", "start_ms": False, "end_ms": 100}],
            complete=True,
        )
        self.assertEqual(result, [])
        self.assertEqual(reason, "word_0_time_not_integer_ms")
        result, reason = dashscope.validate_word_timings(
            "你",
            [{"text": "你", "start_ms": 0, "end_ms": 101}],
            complete=True,
            audio_duration_ms=100,
        )
        self.assertEqual(result, [])
        self.assertEqual(reason, "word_0_exceeds_audio_duration")


class MiniMaxEvidenceTests(unittest.TestCase):
    def test_documented_subtitle_url_is_evidence_not_words(self) -> None:
        response = {
            "data": {
                "status": 2,
                "subtitle_file": "https://example.invalid/expiring-subtitle",
            },
            "extra_info": {"audio_length": 500},
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }
        timing = minimax.minimax_timing_contract(response, "你好")
        self.assertEqual(timing["words"], [])
        self.assertEqual(timing["status"], "forced_alignment_required")
        self.assertEqual(
            timing["reason"], "provider_subtitle_item_schema_not_documented"
        )
        cleaned = minimax.clean_response(response)
        self.assertNotIn("subtitle_file", cleaned["data"])
        self.assertTrue(cleaned["data"]["subtitle_file_available"])

    def test_nonfinal_response_fails_closed(self) -> None:
        timing = minimax.minimax_timing_contract(
            {"data": {"status": 1}, "base_resp": {"status_code": 0}},
            "你好",
        )
        self.assertEqual(timing["reason"], "provider_result_incomplete")
        self.assertEqual(timing["words"], [])


class DashScopeEvidenceTests(unittest.TestCase):
    def test_documented_event_envelope_normalizes_without_word_aliases(self) -> None:
        event = dashscope_event(words=[{"unknown-provider-field": 1}])
        normalized = dashscope.normalize_dashscope_event(json.dumps(event))
        self.assertEqual(normalized["type"], "sentence-end")
        self.assertEqual(normalized["sentence_index"], 0)
        self.assertEqual(normalized["word_item_count"], 1)
        self.assertNotIn("words", normalized)

    def test_malformed_event_is_evidence_failure_not_partial_words(self) -> None:
        timing = dashscope.dashscope_timing_contract(
            ["not-json"],
            "你好",
            model="cosyvoice-v3.5-plus",
            voice_source="cloned",
            completed=True,
            streaming=True,
        )
        self.assertEqual(timing["reason"], "provider_event_invalid")
        self.assertEqual(timing["words"], [])

    def test_event_sequence_must_be_contiguous_and_cover_source(self) -> None:
        skipped = dashscope.dashscope_timing_contract(
            [dashscope_event(index=1, words=[{"unknown": 1}])],
            "你好",
            model="cosyvoice-v3.5-plus",
            voice_source="cloned",
            completed=True,
            streaming=True,
        )
        self.assertEqual(skipped["reason"], "sentence_events_not_contiguous")
        mismatch = dashscope.dashscope_timing_contract(
            [dashscope_event(text="您好", words=[{"unknown": 1}])],
            "你好",
            model="cosyvoice-v3.5-plus",
            voice_source="cloned",
            completed=True,
            streaming=True,
        )
        self.assertEqual(mismatch["reason"], "sentence_events_do_not_cover_source")

    def test_current_qwen_audio_plus_and_nonstreaming_paths_stay_untimed(self) -> None:
        event = dashscope_event(words=[{"unknown": 1}])
        unsupported = dashscope.dashscope_timing_contract(
            [event],
            "你好",
            model="qwen-audio-3.0-tts-plus",
            voice_source="system",
            completed=True,
            streaming=True,
        )
        self.assertEqual(unsupported["reason"], "model_word_timestamps_not_supported")
        nonstreaming = dashscope.dashscope_timing_contract(
            [],
            "你好",
            model="cosyvoice-v3.5-plus",
            voice_source="cloned",
            completed=True,
            streaming=False,
        )
        self.assertEqual(nonstreaming["reason"], "nonstreaming_call_has_no_word_events")

    def test_documented_envelope_still_needs_real_word_item_schema(self) -> None:
        timing = dashscope.dashscope_timing_contract(
            [dashscope_event(words=[{"unknown": 1}])],
            "你好",
            model="cosyvoice-v3.5-plus",
            voice_source="cloned",
            completed=True,
            streaming=True,
        )
        self.assertEqual(timing["words"], [])
        self.assertEqual(timing["reason"], "provider_word_item_schema_not_documented")


if __name__ == "__main__":
    unittest.main()
