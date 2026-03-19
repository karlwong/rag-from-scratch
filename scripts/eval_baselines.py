#!/usr/bin/env python3
"""Evaluate lightweight offline baselines for the Wonderland benchmark.

The goal is not to solve every family. The goal is to establish a reproducible,
honest reference point across both random and structure-aware validation splits.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Callable, Iterable, Sequence

getcontext().prec = 28

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "train.csv"

FAMILIES: Sequence[str] = (
    "bit_transform",
    "text_cipher",
    "roman_numeral",
    "unit_conversion",
    "gravity",
    "equation_transform",
)


@dataclass(frozen=True)
class RowRecord:
    row_id: str
    prompt: str
    answer: str
    family: str
    subfamily: str | None
    structure_signature: str


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def classify_family(prompt: str) -> str:
    if "8-bit binary numbers" in prompt:
        return "bit_transform"
    if "secret encryption rules are used on text" in prompt:
        return "text_cipher"
    if "different numeral system" in prompt:
        return "roman_numeral"
    if "secret unit conversion" in prompt:
        return "unit_conversion"
    if "gravitational constant has been secretly changed" in prompt:
        return "gravity"
    if "transformation rules are applied to equations" in prompt or "transformation rules is applied to equations" in prompt:
        return "equation_transform"
    raise ValueError(f"Unknown family for prompt: {prompt[:80]!r}")


def extract_query(prompt: str, prefix: str) -> str:
    match = re.search(re.escape(prefix) + r"\s*(.+)", prompt, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def stable_fold(key: str, num_folds: int) -> int:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % num_folds


def decimal_quantize(value: Decimal, places: int) -> str:
    quantum = Decimal("1") if places == 0 else Decimal("1." + ("0" * places))
    return format(value.quantize(quantum, rounding=ROUND_HALF_UP), f".{places}f")


def roman_encode(number: int) -> str:
    pairs = (
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    output: list[str] = []
    remainder = number
    for value, token in pairs:
        while remainder >= value:
            output.append(token)
            remainder -= value
    return "".join(output)


def gravity_precision(distances: Sequence[str], value: Decimal) -> int:
    if any(distance.endswith(".0") or re.fullmatch(r"\d+\.\d", distance) for distance in distances):
        rounded_2 = decimal_quantize(value, 2)
        if rounded_2.endswith("0"):
            return 1
    return 2


def normalize_prediction(text: str) -> str:
    box_match = re.search(r"\\boxed\{([^{}]+)\}", text)
    if box_match:
        text = box_match.group(1)
    return text.strip()


def validate_answer_format(family: str, prediction: str) -> bool:
    patterns = {
        "bit_transform": re.compile(r"^[01]{8}$"),
        "text_cipher": re.compile(r"^[a-z]+(?: [a-z]+){2,4}$"),
        "roman_numeral": re.compile(r"^[IVXLCDM]+$"),
        "unit_conversion": re.compile(r"^-?\d+\.\d{2}$"),
        "gravity": re.compile(r"^-?\d+\.\d{1,2}$"),
        "equation_transform": re.compile(r"^\S+$"),
    }
    return bool(patterns[family].fullmatch(prediction))


def build_structure_signature(prompt: str, family: str, answer: str) -> tuple[str, str | None]:
    if family == "roman_numeral":
        query = int(re.search(r"write the number (\d+)", prompt).group(1))
        subfamily = None
        signature = f"roman|decade={query//10}|boundary={int(query in {4,9,14,19,39,40,44,49,90,94,99,100})}|examples={prompt.count('->')}"
        return signature, subfamily
    if family == "unit_conversion":
        pairs = [(Decimal(m.group(1)), Decimal(m.group(2))) for m in re.finditer(r"([0-9.]+) m becomes ([0-9.]+)", prompt)]
        slope = statistics.median(float(y / x) for x, y in pairs)
        query = float(re.search(r"measurement: ([0-9.]+) m", prompt).group(1))
        subfamily = None
        signature = f"unit|slope_bin={int(slope*10)}|query_bin={int(query//5)}|examples={len(pairs)}"
        return signature, subfamily
    if family == "gravity":
        triples = [(Decimal(m.group(1)), Decimal(m.group(2))) for m in re.finditer(r"For t = ([0-9.]+)s, distance = ([0-9.]+) m", prompt)]
        g_value = statistics.median(float((Decimal('2') * d) / (t * t)) for t, d in triples)
        precisions = sorted({len(m.group(2).split('.', 1)[1]) if '.' in m.group(2) else 0 for m in re.finditer(r"For t = ([0-9.]+)s, distance = ([0-9.]+) m", prompt)})
        query_t = float(re.search(r"for t = ([0-9.]+)s given d", prompt, flags=re.IGNORECASE).group(1))
        subfamily = None
        signature = f"gravity|g_bin={int(g_value)}|query_bin={int(query_t)}|prec={'-'.join(map(str, precisions))}|examples={len(triples)}"
        return signature, subfamily
    if family == "text_cipher":
        query = extract_query(prompt, "Now, decrypt the following text:")
        token_count = len(query.split())
        subfamily = {3: "three_word_clause", 4: "four_word_clause", 5: "five_word_clause"}.get(len(answer.split()), "other")
        signature = f"text|tokens={token_count}|answer_len={len(answer.split())}|examples={prompt.count('->')}"
        return signature, subfamily
    if family == "bit_transform":
        query = extract_query(prompt, "Now, determine the output for:")
        hamming_weight = query.count("1")
        subfamily = None
        signature = f"bit|examples={prompt.count('->')}|hw_bin={hamming_weight//2}"
        return signature, subfamily
    query = extract_query(prompt, "Now, determine the result for:")
    numeric_match = re.fullmatch(r"[0-9]{2}(\D)[0-9]{2}", query)
    subfamily = "numeric_expression" if numeric_match else "symbol_string"
    operator = numeric_match.group(1) if numeric_match else f"len{len(query)}"
    answer_kind = "integer" if re.fullmatch(r"-?\d+", answer) else "symbolic"
    signature = f"equation|sub={subfamily}|op={operator}|answer={answer_kind}|examples={prompt.count('=')}"
    return signature, subfamily


def build_records(rows: Iterable[dict[str, str]]) -> list[RowRecord]:
    records: list[RowRecord] = []
    for row in rows:
        family = classify_family(row["prompt"])
        signature, subfamily = build_structure_signature(row["prompt"], family, row["answer"])
        records.append(
            RowRecord(
                row_id=row["id"],
                prompt=row["prompt"],
                answer=row["answer"],
                family=family,
                subfamily=subfamily,
                structure_signature=signature,
            )
        )
    return records


def baseline_last_demo(record: RowRecord) -> str:
    lines = [line.strip() for line in record.prompt.splitlines() if line.strip()]
    if record.family in {"bit_transform", "text_cipher", "roman_numeral"}:
        example_lines = [line for line in lines if " -> " in line]
        return example_lines[-1].split(" -> ", 1)[1] if example_lines else ""
    if record.family == "unit_conversion":
        example_lines = [line for line in lines if " becomes " in line]
        return example_lines[-1].split(" becomes ", 1)[1] if example_lines else ""
    if record.family == "gravity":
        example_lines = [line for line in lines if line.startswith("For t =")]
        return example_lines[-1].rsplit("=", 1)[1].replace("m", "").strip() if example_lines else ""
    example_lines = [line for line in lines if " = " in line]
    return example_lines[-1].split(" = ", 1)[1] if example_lines else ""


def baseline_solver_lite(record: RowRecord) -> str:
    prompt = record.prompt
    if record.family == "roman_numeral":
        value = int(re.search(r"write the number (\d+)", prompt).group(1))
        return roman_encode(value)
    if record.family == "unit_conversion":
        pairs = [(Decimal(m.group(1)), Decimal(m.group(2))) for m in re.finditer(r"([0-9.]+) m becomes ([0-9.]+)", prompt)]
        slope = statistics.median(y / x for x, y in pairs)
        query = Decimal(re.search(r"measurement: ([0-9.]+) m", prompt).group(1))
        return decimal_quantize(query * slope, 2)
    if record.family == "gravity":
        pairs = [(Decimal(m.group(1)), Decimal(m.group(2))) for m in re.finditer(r"For t = ([0-9.]+)s, distance = ([0-9.]+) m", prompt)]
        inferred_g = statistics.median((Decimal("2") * d) / (t * t) for t, d in pairs)
        query_t = Decimal(re.search(r"for t = ([0-9.]+)s given d", prompt, flags=re.IGNORECASE).group(1))
        predicted = Decimal("0.5") * inferred_g * query_t * query_t
        distances = [m.group(2) for m in re.finditer(r"For t = ([0-9.]+)s, distance = ([0-9.]+) m", prompt)]
        places = gravity_precision(distances, predicted)
        return decimal_quantize(predicted, places)
    if record.family == "bit_transform":
        query = extract_query(prompt, "Now, determine the output for:")
        return query.zfill(8)[:8]
    if record.family == "text_cipher":
        example_lines = [line for line in prompt.splitlines() if " -> " in line]
        return example_lines[0].split(" -> ", 1)[1] if example_lines else "the cat sees"
    example_lines = [line for line in prompt.splitlines() if " = " in line]
    return example_lines[-1].split(" = ", 1)[1] if example_lines else "0"


BASELINES: dict[str, Callable[[RowRecord], str]] = {
    "last_demo": baseline_last_demo,
    "solver_lite": baseline_solver_lite,
}


def evaluate(records: Sequence[RowRecord], fold_assignments: dict[str, int], num_folds: int, baseline_name: str) -> dict[str, object]:
    predictor = BASELINES[baseline_name]
    fold_metrics: list[dict[str, object]] = []
    all_predictions: list[tuple[RowRecord, str]] = []
    for record in records:
        prediction = normalize_prediction(predictor(record))
        all_predictions.append((record, prediction))

    for fold in range(num_folds):
        subset = [(record, prediction) for record, prediction in all_predictions if fold_assignments[record.row_id] == fold]
        if not subset:
            continue
        correct = sum(prediction == record.answer for record, prediction in subset)
        format_ok = sum(validate_answer_format(record.family, prediction) for record, prediction in subset)
        family_total = Counter(record.family for record, _ in subset)
        family_correct = Counter(record.family for record, prediction in subset if prediction == record.answer)
        fold_metrics.append(
            {
                "fold": fold,
                "count": len(subset),
                "accuracy": correct / len(subset),
                "format_accuracy": format_ok / len(subset),
                "family_total": family_total,
                "family_correct": family_correct,
            }
        )

    total = len(all_predictions)
    overall_correct = sum(prediction == record.answer for record, prediction in all_predictions)
    overall_format = sum(validate_answer_format(record.family, prediction) for record, prediction in all_predictions)
    family_total = Counter(record.family for record, _ in all_predictions)
    family_correct = Counter(record.family for record, prediction in all_predictions if prediction == record.answer)
    return {
        "overall_accuracy": overall_correct / total,
        "answer_format_accuracy": overall_format / total,
        "per_family_accuracy": {family: family_correct[family] / family_total[family] for family in FAMILIES},
        "fold_metrics": fold_metrics,
    }


def summarize_fold_range(fold_metrics: Sequence[dict[str, object]], key: str) -> tuple[float, float]:
    values = [metric[key] for metric in fold_metrics]
    return min(values), max(values)


def print_result(split_name: str, result: dict[str, object]) -> None:
    low_acc, high_acc = summarize_fold_range(result["fold_metrics"], "accuracy")
    low_fmt, high_fmt = summarize_fold_range(result["fold_metrics"], "format_accuracy")
    print(f"  {split_name}:")
    print(
        f"    overall_accuracy={result['overall_accuracy']:.4f} "
        f"fold_range=[{low_acc:.4f}, {high_acc:.4f}]"
    )
    print(
        f"    answer_format_accuracy={result['answer_format_accuracy']:.4f} "
        f"fold_range=[{low_fmt:.4f}, {high_fmt:.4f}]"
    )
    print("    per_family_accuracy:")
    for family in FAMILIES:
        print(f"      - {family:<18} {result['per_family_accuracy'][family]:.4f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-folds", type=int, default=5, help="Number of folds per split strategy.")
    parser.add_argument(
        "--baseline",
        choices=tuple(BASELINES),
        default="solver_lite",
        help="Which baseline predictor to evaluate.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = build_records(read_rows(TRAIN_PATH))
    random_split = {record.row_id: stable_fold(record.row_id, args.num_folds) for record in records}
    structure_split = {record.row_id: stable_fold(record.structure_signature, args.num_folds) for record in records}

    random_result = evaluate(records, random_split, args.num_folds, args.baseline)
    structure_result = evaluate(records, structure_split, args.num_folds, args.baseline)

    print(f"Baseline: {args.baseline}")
    print(f"Rows evaluated: {len(records)}")
    print_result("stratified_random_hash", random_result)
    print_result("structure_aware_hash", structure_result)
    drift_gap = random_result["overall_accuracy"] - structure_result["overall_accuracy"]
    print(f"  random_vs_structure_accuracy_gap={drift_gap:.4f}")


if __name__ == "__main__":
    main()
