#!/usr/bin/env python3
"""Validate matrix experiment CSV data and report per-platform medians.

This tool intentionally does not produce one cross-platform score. It checks the
experimental contract, sample coverage, and robust (median) summaries only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


REQUIRED_FIELDS = (
    "experiment_id",
    "hypothesis_id",
    "experiment_type",
    "content_id",
    "account_id",
    "platform",
    "series",
    "variant",
    "changed_variable",
    "published_at",
    "window_hours",
    "views",
    "safety_issue",
)

NUMBER_FIELDS = (
    "window_hours",
    "views",
    "impressions",
    "avg_watch_seconds",
    "completion_rate",
    "likes",
    "saves",
    "comments",
    "effective_comments",
    "shares",
    "follows",
    "production_minutes",
    "cost_cny",
)

RATE_FIELDS = ("completion_rate",)
COUNT_FIELDS = (
    "views",
    "impressions",
    "likes",
    "saves",
    "comments",
    "effective_comments",
    "shares",
    "follows",
)

TRUE_VALUES = {"1", "true", "yes", "y", "是", "有"}
FALSE_VALUES = {"0", "false", "no", "n", "否", "无"}
EXPERIMENT_TYPES = {"pilot", "discovery", "controlled"}


def parse_number(value: str, field: str, row_number: int, errors: list[str]):
    value = value.strip()
    if value == "":
        return None
    try:
        number = float(value)
    except ValueError:
        errors.append(f"row {row_number}: {field} must be numeric, got {value!r}")
        return None
    if not math.isfinite(number):
        errors.append(f"row {row_number}: {field} must be finite")
        return None
    if number < 0:
        errors.append(f"row {row_number}: {field} cannot be negative")
    if field in RATE_FIELDS and number > 1:
        errors.append(f"row {row_number}: {field} must be 0..1, not a percentage")
    if field in COUNT_FIELDS and not number.is_integer():
        errors.append(f"row {row_number}: {field} must be an integer count")
    return number


def parse_safety(value: str, row_number: int, errors: list[str]) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    errors.append(
        f"row {row_number}: safety_issue must be yes/no, true/false, 1/0, 是/否 or 有/无"
    )
    return False


def normalize_rows(raw_rows: list[dict[str, str]]):
    rows: list[dict[str, object]] = []
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[tuple[str, str, float | None]] = set()

    for row_number, raw in enumerate(raw_rows, start=2):
        row: dict[str, object] = {key: (raw.get(key) or "").strip() for key in raw}
        for field in REQUIRED_FIELDS:
            if field != "safety_issue" and not str(row.get(field, "")).strip():
                errors.append(f"row {row_number}: missing {field}")

        for field in NUMBER_FIELDS:
            row[field] = parse_number(str(row.get(field, "")), field, row_number, errors)

        published_at = str(row.get("published_at", ""))
        if published_at:
            try:
                datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except ValueError:
                errors.append(
                    f"row {row_number}: published_at must be ISO-8601, got {published_at!r}"
                )
        experiment_type = str(row.get("experiment_type", "")).lower()
        if experiment_type not in EXPERIMENT_TYPES:
            errors.append(
                f"row {row_number}: experiment_type must be pilot, discovery or controlled"
            )
        row["experiment_type"] = experiment_type

        row["safety_issue"] = parse_safety(
            str(raw.get("safety_issue") or ""), row_number, errors
        )

        views = row.get("views")
        if isinstance(row.get("window_hours"), float) and row["window_hours"] <= 0:
            errors.append(f"row {row_number}: window_hours must be > 0")
        for count_field in ("likes", "saves", "comments", "effective_comments", "shares", "follows"):
            count = row.get(count_field)
            if isinstance(views, float) and isinstance(count, float) and count > views:
                warnings.append(
                    f"row {row_number}: {count_field} ({count:g}) exceeds views ({views:g})"
                )
        comments = row.get("comments")
        effective_comments = row.get("effective_comments")
        if (
            isinstance(comments, float)
            and isinstance(effective_comments, float)
            and effective_comments > comments
        ):
            errors.append(
                f"row {row_number}: effective_comments cannot exceed comments"
            )
        if row["safety_issue"]:
            warnings.append(
                f"row {row_number}: safety_issue=yes; stop expansion and review before interpreting performance"
            )

        key = (
            str(row.get("content_id", "")),
            str(row.get("platform", "")),
            row.get("window_hours"),
        )
        if key in seen:
            errors.append(
                f"row {row_number}: duplicate content/platform/window {key[0]}/{key[1]}/{key[2]}"
            )
        seen.add(key)
        row["_row_number"] = row_number
        rows.append(row)

    by_experiment: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_experiment[str(row.get("experiment_id", ""))].append(row)

    for experiment_id, experiment_rows in sorted(by_experiment.items()):
        changed = {str(r.get("changed_variable", "")) for r in experiment_rows}
        if len(changed) > 1:
            errors.append(
                f"experiment {experiment_id}: multiple changed_variable values: {sorted(changed)}"
            )
        hypotheses = {str(r.get("hypothesis_id", "")) for r in experiment_rows}
        if len(hypotheses) > 1:
            warnings.append(
                f"experiment {experiment_id}: multiple hypothesis_id values: {sorted(hypotheses)}"
            )
        experiment_types = {str(r.get("experiment_type", "")) for r in experiment_rows}
        if len(experiment_types) > 1:
            errors.append(
                f"experiment {experiment_id}: multiple experiment_type values: {sorted(experiment_types)}"
            )

    return rows, errors, warnings


def load_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        missing = [field for field in REQUIRED_FIELDS if field not in headers]
        if missing:
            return [], [f"missing CSV columns: {', '.join(missing)}"], []
        return normalize_rows(list(reader))


def safe_rate(numerator, denominator):
    if not isinstance(numerator, float) or not isinstance(denominator, float) or denominator <= 0:
        return None
    return numerator / denominator


def row_metrics(row: dict[str, object]):
    views = row.get("views")
    metrics = {
        "views": views,
        "avg_watch_seconds": row.get("avg_watch_seconds"),
        "completion_rate": row.get("completion_rate"),
        "like_rate": safe_rate(row.get("likes"), views),
        "save_rate": safe_rate(row.get("saves"), views),
        "comment_rate": safe_rate(row.get("comments"), views),
        "share_rate": safe_rate(row.get("shares"), views),
        "follows_per_1k": None,
    }
    follow_rate = safe_rate(row.get("follows"), views)
    if follow_rate is not None:
        metrics["follows_per_1k"] = follow_rate * 1000
    return metrics


def median(values):
    values = [value for value in values if isinstance(value, float)]
    return statistics.median(values) if values else None


def summarize(rows: list[dict[str, object]], min_samples: int):
    grouped: dict[tuple[str, str, str, str, float | None], list[dict[str, object]]] = defaultdict(list)
    coverage: dict[tuple[str, str, str, float | None], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    warnings: list[str] = []

    for row in rows:
        key = (
            str(row.get("platform", "")),
            str(row.get("experiment_id", "")),
            str(row.get("experiment_type", "")),
            str(row.get("variant", "")),
            row.get("window_hours"),
        )
        grouped[key].append(row)
        coverage[(key[0], key[1], key[2], key[4])][key[3]] += 1

    summaries = []
    metric_names = (
        "views",
        "avg_watch_seconds",
        "completion_rate",
        "like_rate",
        "save_rate",
        "comment_rate",
        "share_rate",
        "follows_per_1k",
    )
    for key, group_rows in sorted(grouped.items(), key=lambda item: tuple(str(x) for x in item[0])):
        metrics_by_name: dict[str, list[float | None]] = defaultdict(list)
        account_ids = sorted({str(row.get("account_id", "")) for row in group_rows})
        series_names = sorted({str(row.get("series", "")) for row in group_rows})
        if len(account_ids) > 1:
            warnings.append(
                f"{key[0]}/{key[1]}/{key[3]}/{key[4]:g}h spans accounts {account_ids}; verify this is the intended changed variable"
            )
        if len(series_names) > 1:
            warnings.append(
                f"{key[0]}/{key[1]}/{key[3]}/{key[4]:g}h spans series {series_names}; attribution may be confounded"
            )
        for row in group_rows:
            for name, value in row_metrics(row).items():
                metrics_by_name[name].append(value)
        summaries.append(
            {
                "platform": key[0],
                "experiment_id": key[1],
                "experiment_type": key[2],
                "variant": key[3],
                "window_hours": key[4],
                "account_ids": account_ids,
                "series": series_names,
                "n": len(group_rows),
                "safety_issues": sum(bool(row.get("safety_issue")) for row in group_rows),
                "medians": {name: median(metrics_by_name[name]) for name in metric_names},
            }
        )

    coverage_rows = []
    for (platform, experiment_id, experiment_type, window_hours), variants in sorted(
        coverage.items(), key=lambda item: tuple(str(x) for x in item[0])
    ):
        coverage_rows.append(
            {
                "platform": platform,
                "experiment_id": experiment_id,
                "experiment_type": experiment_type,
                "window_hours": window_hours,
                "variants": dict(sorted(variants.items())),
            }
        )
        if experiment_type == "controlled" and len(variants) < 2:
            warnings.append(
                f"{platform}/{experiment_id}/{window_hours:g}h has only one variant; treat as baseline, not A/B"
            )
        for variant, count in variants.items():
            if count < min_samples:
                warnings.append(
                    f"{platform}/{experiment_id}/{window_hours:g}h variant {variant}: n={count} < {min_samples}"
                )

    return summaries, coverage_rows, warnings


def fmt(value, kind="number"):
    if value is None:
        return "—"
    if kind == "rate":
        return f"{value * 100:.2f}%"
    if kind == "int":
        return f"{value:,.0f}"
    return f"{value:.2f}"


def render_markdown(path: Path, rows, summaries, coverage, warnings):
    lines = [
        f"# Matrix experiment report: `{path}`",
        "",
        f"Rows: **{len(rows)}**. Comparisons stay inside the same platform and observation window.",
        "",
        "## Coverage",
        "",
        "| platform | experiment | type | window | variant counts |",
        "|---|---|---|---:|---|",
    ]
    if not coverage:
        lines.append("| — | — | — | — | no observations yet |")
    for item in coverage:
        variants = ", ".join(f"{name}={count}" for name, count in item["variants"].items())
        lines.append(
            f"| {item['platform']} | {item['experiment_id']} | {item['experiment_type']} | {item['window_hours']:g}h | {variants} |"
        )

    lines += [
        "",
        "## Per-platform medians",
        "",
        "| platform | experiment | type | variant | account | series | window | n | views | avg watch s | completion | like | save | comment | share | follows/1k | safety |",
        "|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if not summaries:
        lines.append("| — | — | — | — | — | — | — | 0 | — | — | — | — | — | — | — | — | 0 |")
    for item in summaries:
        m = item["medians"]
        lines.append(
            "| {platform} | {experiment_id} | {experiment_type} | {variant} | {account} | {series} | {window:g}h | {n} | {views} | "
            "{watch} | {completion} | {like} | {save} | {comment} | {share} | {follow} | {safety} |".format(
                platform=item["platform"],
                experiment_id=item["experiment_id"],
                experiment_type=item["experiment_type"],
                variant=item["variant"],
                account=", ".join(item["account_ids"]),
                series=", ".join(item["series"]),
                window=item["window_hours"],
                n=item["n"],
                views=fmt(m["views"], "int"),
                watch=fmt(m["avg_watch_seconds"]),
                completion=fmt(m["completion_rate"], "rate"),
                like=fmt(m["like_rate"], "rate"),
                save=fmt(m["save_rate"], "rate"),
                comment=fmt(m["comment_rate"], "rate"),
                share=fmt(m["share_rate"], "rate"),
                follow=fmt(m["follows_per_1k"]),
                safety=item["safety_issues"],
            )
        )

    lines += ["", "## Warnings", ""]
    lines.extend(f"- {warning}" for warning in warnings)
    if not warnings:
        lines.append("- none")
    lines += [
        "",
        "> This report does not declare a winner. Interpret medians together with individual samples, comments, and safety signals.",
    ]
    return "\n".join(lines)


def self_test():
    raw_rows = []
    for variant, views in (("A", 100.0), ("A", 120.0), ("A", 110.0), ("B", 150.0), ("B", 160.0), ("B", 140.0)):
        raw_rows.append(
            {
                "experiment_id": "EXP-TEST",
                "hypothesis_id": "H-TEST",
                "experiment_type": "controlled",
                "content_id": f"C-{variant}-{int(views)}",
                "account_id": "incubator",
                "platform": "bilibili",
                "series": "test",
                "variant": variant,
                "changed_variable": "hook",
                "published_at": "2026-07-28",
                "window_hours": "48",
                "views": str(views),
                "impressions": "",
                "avg_watch_seconds": "30",
                "completion_rate": "0.5",
                "likes": "10",
                "saves": "2",
                "comments": "1",
                "effective_comments": "1",
                "shares": "1",
                "follows": "1",
                "production_minutes": "60",
                "cost_cny": "1.2",
                "safety_issue": "no",
                "notes": "",
            }
        )
    rows, errors, warnings = normalize_rows(raw_rows)
    summaries, coverage, coverage_warnings = summarize(rows, min_samples=3)
    assert not errors, errors
    assert not warnings, warnings
    assert not coverage_warnings, coverage_warnings
    assert len(summaries) == 2
    assert len(coverage) == 1
    assert summaries[0]["n"] == 3
    bad = dict(raw_rows[0])
    bad["safety_issue"] = ""
    _, bad_errors, _ = normalize_rows([bad])
    assert any("safety_issue" in error for error in bad_errors)
    print("matrix_tracker self-test: OK")


def main():
    parser = argparse.ArgumentParser(
        description="Validate matrix experiment CSV and report per-platform medians."
    )
    parser.add_argument("csv_path", nargs="?", type=Path)
    parser.add_argument("--min-samples", type=int, default=3)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    parser.add_argument("--strict", action="store_true", help="return exit 1 when warnings exist")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if args.csv_path is None:
        parser.error("csv_path is required unless --self-test is used")
    if args.min_samples < 1:
        parser.error("--min-samples must be >= 1")
    if not args.csv_path.is_file():
        print(f"error: file not found: {args.csv_path}", file=sys.stderr)
        return 2

    rows, errors, parse_warnings = load_csv(args.csv_path)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2

    summaries, coverage, coverage_warnings = summarize(rows, args.min_samples)
    warnings = parse_warnings + coverage_warnings
    payload = {
        "source": str(args.csv_path),
        "row_count": len(rows),
        "cross_platform_score": None,
        "coverage": coverage,
        "summaries": summaries,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(args.csv_path, rows, summaries, coverage, warnings))
    return 1 if args.strict and warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
