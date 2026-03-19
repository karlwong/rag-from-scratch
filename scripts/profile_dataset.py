#!/usr/bin/env python3
"""Profile the Wonderland reasoning benchmark for reverse-engineering work."""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "train.csv"
TEST_PATH = ROOT / "test.csv"

FAMILY_RULES = [
    (
        "bit_transform",
        "8-bit bit transform",
        "In Alice's Wonderland, a secret bit manipulation rule transforms 8-bit binary numbers.",
    ),
    (
        "text_cipher",
        "text decryption",
        "In Alice's Wonderland, secret encryption rules are used on text.",
    ),
    (
        "roman_numeral",
        "roman numeral conversion",
        "In Alice's Wonderland, numbers are secretly converted into a different numeral system.",
    ),
    (
        "unit_conversion",
        "linear unit conversion",
        "In Alice's Wonderland, a secret unit conversion is applied to measurements.",
    ),
    (
        "gravity",
        "quadratic gravity",
        "In Alice's Wonderland, the gravitational constant has been secretly changed.",
    ),
    (
        "equation_transform",
        "equation transform",
        "In Alice's Wonderland, a secret set of transformation rules is applied to equations.",
    ),
]

NUMERIC_EXPR_RE = re.compile(r"^[0-9]{2}([^A-Za-z0-9\s])[0-9]{2}$")
BINARY_ANSWER_RE = re.compile(r"^[01]{8}$")
ROMAN_RE = re.compile(r"^[IVXLCDM]+$")
DECIMAL_2_RE = re.compile(r"^-?\d+\.\d{2}$")
DECIMAL_OTHER_RE = re.compile(r"^-?\d+\.\d+$")
INTEGER_RE = re.compile(r"^-?\d+$")
LOWER_TEXT_RE = re.compile(r"^[a-z ]+$")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    return statistics.quantiles(values, n=100, method="inclusive")[int(q * 100) - 1]


def summarize_lengths(values: list[int]) -> dict[str, float]:
    return {
        "min": min(values),
        "p10": quantile(values, 0.10),
        "median": statistics.median(values),
        "p90": quantile(values, 0.90),
        "max": max(values),
    }


def classify_family(prompt: str) -> tuple[str, str]:
    first_line = prompt.splitlines()[0]
    for family_id, label, prefix in FAMILY_RULES:
        if first_line.startswith(prefix):
            return family_id, label
    return "unknown", first_line


def classify_answer(answer: str) -> str:
    if BINARY_ANSWER_RE.fullmatch(answer):
        return "binary8"
    if ROMAN_RE.fullmatch(answer):
        return "roman"
    if DECIMAL_2_RE.fullmatch(answer):
        return "decimal_2dp"
    if DECIMAL_OTHER_RE.fullmatch(answer):
        return "decimal_other"
    if INTEGER_RE.fullmatch(answer):
        return "integer"
    if LOWER_TEXT_RE.fullmatch(answer):
        return "lowercase_text"
    return "symbolic"


def example_count(prompt: str, family_id: str) -> int:
    lines = prompt.splitlines()
    if family_id in {"bit_transform", "text_cipher", "roman_numeral"}:
        return sum(" -> " in line for line in lines)
    if family_id == "unit_conversion":
        return sum(" becomes " in line for line in lines)
    if family_id == "gravity":
        return sum(line.startswith("For t =") for line in lines)
    if family_id == "equation_transform":
        return sum(" = " in line for line in lines)
    return 0


def analyze_text_family(rows: list[dict[str, str]]) -> dict[str, Any]:
    plaintext_vocab = Counter()
    answer_length_counter = Counter()
    unseen_answer_word_counter = Counter()
    for row in rows:
        seen_plain = set()
        for line in row["prompt"].splitlines():
            if " -> " in line:
                _, plain = line.split(" -> ", 1)
                words = plain.split()
                plaintext_vocab.update(words)
                seen_plain.update(words)
        answer_words = row["answer"].split()
        answer_length_counter[len(answer_words)] += 1
        unseen = sum(word not in seen_plain for word in answer_words)
        unseen_answer_word_counter[unseen] += 1
    return {
        "plaintext_vocab_size": len(plaintext_vocab),
        "top_plaintext_tokens": plaintext_vocab.most_common(25),
        "answer_word_lengths": dict(answer_length_counter),
        "unseen_answer_words_per_prompt": dict(unseen_answer_word_counter),
    }


def analyze_roman_family(rows: list[dict[str, str]]) -> dict[str, Any]:
    targets = []
    for row in rows:
        match = re.search(r"write the number (\d+) in the Wonderland numeral system", row["prompt"])
        if match:
            targets.append(int(match.group(1)))
    return {
        "target_min": min(targets),
        "target_max": max(targets),
        "target_unique_values": len(set(targets)),
        "top_targets": Counter(targets).most_common(10),
    }


def analyze_unit_family(rows: list[dict[str, str]]) -> dict[str, Any]:
    slopes = []
    query_values = []
    for row in rows:
        prompt_slopes = []
        for line in row["prompt"].splitlines():
            match = re.match(r"([0-9.]+) m becomes ([0-9.]+)", line)
            if match:
                left, right = map(float, match.groups())
                prompt_slopes.append(right / left)
            query_match = re.search(r"convert the following measurement: ([0-9.]+) m", line)
            if query_match:
                query_values.append(float(query_match.group(1)))
        if prompt_slopes:
            slopes.append(sum(prompt_slopes) / len(prompt_slopes))
    return {
        "slope_min": min(slopes),
        "slope_median": statistics.median(slopes),
        "slope_max": max(slopes),
        "query_value_min": min(query_values),
        "query_value_max": max(query_values),
    }


def analyze_gravity_family(rows: list[dict[str, str]]) -> dict[str, Any]:
    g_values = []
    query_times = []
    for row in rows:
        inferred = []
        for line in row["prompt"].splitlines():
            match = re.match(r"For t = ([0-9.]+)s, distance = ([0-9.]+) m", line)
            if match:
                time_value, distance = map(float, match.groups())
                inferred.append((2.0 * distance) / (time_value * time_value))
            query_match = re.search(r"for t = ([0-9.]+)s given d", line, flags=re.IGNORECASE)
            if query_match:
                query_times.append(float(query_match.group(1)))
        if inferred:
            g_values.append(sum(inferred) / len(inferred))
    return {
        "g_min": min(g_values),
        "g_median": statistics.median(g_values),
        "g_max": max(g_values),
        "query_time_min": min(query_times),
        "query_time_max": max(query_times),
    }


def analyze_equation_family(rows: list[dict[str, str]]) -> dict[str, Any]:
    subfamilies = Counter()
    numeric_operator_counter = Counter()
    integer_answers = 0
    negative_integer_answers = 0
    leading_zero_integer_answers = 0
    for row in rows:
        query = row["prompt"].splitlines()[-1].split(": ", 1)[1]
        match = NUMERIC_EXPR_RE.fullmatch(query)
        if match:
            subfamilies["numeric_expression"] += 1
            numeric_operator_counter[match.group(1)] += 1
        else:
            subfamilies["symbol_string"] += 1
        if INTEGER_RE.fullmatch(row["answer"]):
            integer_answers += 1
            if row["answer"].startswith("-"):
                negative_integer_answers += 1
            if len(row["answer"]) > 1 and row["answer"].startswith("0"):
                leading_zero_integer_answers += 1
    return {
        "subfamilies": dict(subfamilies),
        "numeric_query_operators": numeric_operator_counter.most_common(),
        "integer_answers": integer_answers,
        "negative_integer_answers": negative_integer_answers,
        "leading_zero_integer_answers": leading_zero_integer_answers,
    }


def build_profile(train_rows: list[dict[str, str]], test_rows: list[dict[str, str]]) -> dict[str, Any]:
    family_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    family_labels: dict[str, str] = {}
    family_first_lines: dict[str, str] = {}
    for row in train_rows:
        family_id, label = classify_family(row["prompt"])
        family_rows[family_id].append(row)
        family_labels[family_id] = label
        family_first_lines[family_id] = row["prompt"].splitlines()[0]

    overall = {
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "exact_test_prompt_overlap_with_train": sum(
            1 for row in test_rows if any(row["id"] == train["id"] and row["prompt"] == train["prompt"] for train in train_rows)
        ),
        "prompt_char_lengths": summarize_lengths([len(row["prompt"]) for row in train_rows]),
        "answer_char_lengths": summarize_lengths([len(row["answer"]) for row in train_rows]),
        "prompt_word_lengths": summarize_lengths([len(row["prompt"].split()) for row in train_rows]),
        "answer_word_lengths": summarize_lengths([len(row["answer"].split()) for row in train_rows]),
        "answer_schema_counts": dict(Counter(classify_answer(row["answer"]) for row in train_rows)),
    }

    family_summary: dict[str, Any] = {}
    for family_id, rows in family_rows.items():
        family_summary[family_id] = {
            "label": family_labels[family_id],
            "first_line": family_first_lines[family_id],
            "count": len(rows),
            "share": len(rows) / len(train_rows),
            "prompt_char_lengths": summarize_lengths([len(row["prompt"]) for row in rows]),
            "answer_char_lengths": summarize_lengths([len(row["answer"]) for row in rows]),
            "example_count_distribution": dict(Counter(example_count(row["prompt"], family_id) for row in rows)),
            "answer_schema_counts": dict(Counter(classify_answer(row["answer"]) for row in rows)),
            "sample_ids": [row["id"] for row in rows[:3]],
        }

    family_summary["text_cipher"]["specialized"] = analyze_text_family(family_rows["text_cipher"])
    family_summary["roman_numeral"]["specialized"] = analyze_roman_family(family_rows["roman_numeral"])
    family_summary["unit_conversion"]["specialized"] = analyze_unit_family(family_rows["unit_conversion"])
    family_summary["gravity"]["specialized"] = analyze_gravity_family(family_rows["gravity"])
    family_summary["equation_transform"]["specialized"] = analyze_equation_family(family_rows["equation_transform"])

    return {
        "overall": overall,
        "families": family_summary,
    }


def render_report(profile: dict[str, Any]) -> str:
    lines: list[str] = []
    overall = profile["overall"]
    lines.append("Wonderland benchmark profile")
    lines.append("=" * 28)
    lines.append(f"Train rows: {overall['train_rows']}")
    lines.append(f"Visible test rows: {overall['test_rows']}")
    lines.append(
        f"Visible test rows that exactly overlap train: {overall['exact_test_prompt_overlap_with_train']}"
    )
    lines.append("")
    lines.append("Overall length statistics")
    lines.append("-" * 24)
    for key in ["prompt_char_lengths", "answer_char_lengths", "prompt_word_lengths", "answer_word_lengths"]:
        lines.append(f"{key}: {overall[key]}")
    lines.append(f"answer_schema_counts: {overall['answer_schema_counts']}")
    lines.append("")
    lines.append("Family summary")
    lines.append("-" * 14)
    for family_id, family in sorted(profile["families"].items(), key=lambda item: (-item[1]["count"], item[0])):
        lines.append(f"{family_id}: {family['count']} rows ({family['share']:.1%})")
        lines.append(f"  marker: {family['first_line']}")
        lines.append(f"  example_count_distribution: {family['example_count_distribution']}")
        lines.append(f"  answer_schema_counts: {family['answer_schema_counts']}")
        lines.append(f"  prompt_char_lengths: {family['prompt_char_lengths']}")
        lines.append(f"  answer_char_lengths: {family['answer_char_lengths']}")
        if "specialized" in family:
            lines.append(f"  specialized: {family['specialized']}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a text report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_rows = read_csv(TRAIN_PATH)
    test_rows = read_csv(TEST_PATH)
    profile = build_profile(train_rows, test_rows)
    if args.json:
        print(json.dumps(profile, indent=2, sort_keys=True))
    else:
        print(render_report(profile))


if __name__ == "__main__":
    main()
