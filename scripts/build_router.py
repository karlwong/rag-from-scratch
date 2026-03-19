#!/usr/bin/env python3
"""Build and evaluate a benchmark-specific router for the Wonderland reasoning suite.

The router is intentionally hand-crafted from dataset forensics rather than learned from
surface labels. It combines lexical markers with structural checks so that routing does
not depend on a single brittle keyword.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

FAMILY_ORDER: Sequence[str] = (
    "bit_transform",
    "text_cipher",
    "roman_numeral",
    "unit_conversion",
    "gravity",
    "equation_transform",
)

TOP_LEVEL_MARKERS: Dict[str, Sequence[str]] = {
    "bit_transform": (
        "8-bit binary numbers",
        "input -> output",
        "bit manipulation rule",
    ),
    "text_cipher": (
        "secret encryption rules are used on text",
        "decrypt the following text",
        "here are some examples:",
    ),
    "roman_numeral": (
        "different numeral system",
        "write the number",
        "wonderland numeral system",
    ),
    "unit_conversion": (
        "secret unit conversion",
        "convert the following measurement",
        "becomes",
    ),
    "gravity": (
        "gravitational constant has been secretly changed",
        "d = 0.5*g*t^2",
        "for t =",
    ),
    "equation_transform": (
        "transformation rules is applied to equations",
        "transformation rules are applied to equations",
        "determine the result for:",
    ),
}

ROMAN_NUMERAL_RE = re.compile(r"\b([1-9][0-9]?)\s*->\s*([IVXLCDM]+)\b")
UNIT_EXAMPLE_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*m becomes\s*([0-9]+(?:\.[0-9]+)?)")
GRAVITY_EXAMPLE_RE = re.compile(
    r"For t = ([0-9]+(?:\.[0-9]+)?)s, distance = ([0-9]+(?:\.[0-9]+)?) m",
    re.IGNORECASE,
)
BINARY_IO_RE = re.compile(r"\b[01]{8}\b\s*->\s*\b[01]{8}\b")
QUERY_RE = re.compile(r"Now,\s*(?:decrypt the following text|write the number .*?|convert the following measurement|determine the output for|determine the result for|determine the falling distance for)\s*:?\s*(.+)", re.IGNORECASE | re.DOTALL)
NUMERIC_EQUATION_QUERY_RE = re.compile(r"^[0-9]{2}\D[0-9]{2}$")
PUNCT_QUERY_RE = re.compile(r"^[\W_]+$")
LOWER_ALPHA_RE = re.compile(r"^[a-z]+(?: [a-z]+){2,4}$")


@dataclass
class RouteResult:
    family: str
    confidence: float
    subfamily: Optional[str]
    triggers: List[str]
    score_breakdown: Dict[str, float]
    ambiguity_flag: bool
    fallback_policy: str
    answer_schema: str
    second_choice: Optional[str]
    margin: float


@dataclass
class PromptFeatures:
    prompt: str
    prompt_lower: str
    marker_hits: Dict[str, List[str]]
    query: str
    binary_example_count: int
    roman_example_count: int
    unit_example_count: int
    gravity_example_count: int
    arrow_count: int
    becomes_count: int
    has_decrypt_query: bool
    has_bit_query: bool
    has_gravity_formula: bool
    has_equation_query: bool
    has_roman_instruction: bool
    has_unit_instruction: bool


def extract_query(prompt: str) -> str:
    match = QUERY_RE.search(prompt)
    if not match:
        return ""
    return match.group(1).strip().rstrip(".")


def extract_features(prompt: str) -> PromptFeatures:
    prompt_lower = prompt.lower()
    marker_hits: Dict[str, List[str]] = {}
    for family, markers in TOP_LEVEL_MARKERS.items():
        hits = [marker for marker in markers if marker in prompt_lower]
        if hits:
            marker_hits[family] = hits

    return PromptFeatures(
        prompt=prompt,
        prompt_lower=prompt_lower,
        marker_hits=marker_hits,
        query=extract_query(prompt),
        binary_example_count=len(BINARY_IO_RE.findall(prompt)),
        roman_example_count=len(ROMAN_NUMERAL_RE.findall(prompt)),
        unit_example_count=len(UNIT_EXAMPLE_RE.findall(prompt)),
        gravity_example_count=len(GRAVITY_EXAMPLE_RE.findall(prompt)),
        arrow_count=prompt.count("->"),
        becomes_count=prompt_lower.count(" becomes "),
        has_decrypt_query="decrypt the following text" in prompt_lower,
        has_bit_query="determine the output for:" in prompt_lower,
        has_gravity_formula="d = 0.5*g*t^2" in prompt_lower,
        has_equation_query="determine the result for:" in prompt_lower,
        has_roman_instruction="write the number" in prompt_lower,
        has_unit_instruction="convert the following measurement" in prompt_lower,
    )


def score_family(features: PromptFeatures, family: str) -> Tuple[float, List[str]]:
    score = 0.0
    triggers: List[str] = []

    for marker in features.marker_hits.get(family, []):
        score += 0.34
        triggers.append(f"marker:{marker}")

    if family == "bit_transform":
        if features.binary_example_count >= 3:
            score += 0.28
            triggers.append(f"structure:{features.binary_example_count}_binary_io_pairs")
        if features.has_bit_query and re.search(r"\b[01]{8}\b", features.query):
            score += 0.18
            triggers.append("query:8bit_binary_target")
        if "bit shift" in features.prompt_lower or "xor" in features.prompt_lower:
            score += 0.15
            triggers.append("ops:bitwise_operator_inventory")

    elif family == "text_cipher":
        if features.has_decrypt_query:
            score += 0.24
            triggers.append("query:decrypt_text")
        if features.arrow_count >= 3 and " -> " in features.prompt and re.search(r"\b[a-z]{3,}\b", features.query.lower()):
            score += 0.18
            triggers.append("structure:example_cipher_pairs")
        if "secret encryption rules" in features.prompt_lower:
            score += 0.15
            triggers.append("theme:text_encryption")

    elif family == "roman_numeral":
        if features.roman_example_count >= 2:
            score += 0.28
            triggers.append(f"structure:{features.roman_example_count}_roman_examples")
        if features.has_roman_instruction and re.search(r"\bnumber\s+[0-9]{1,3}\b", features.prompt_lower):
            score += 0.20
            triggers.append("query:write_number_as_numeral")
        if "numeral system" in features.prompt_lower:
            score += 0.18
            triggers.append("theme:numeral_system")

    elif family == "unit_conversion":
        if features.unit_example_count >= 2:
            score += 0.28
            triggers.append(f"structure:{features.unit_example_count}_unit_pairs")
        if features.has_unit_instruction:
            score += 0.20
            triggers.append("query:convert_measurement")
        if features.becomes_count >= 2:
            score += 0.16
            triggers.append(f"pattern:{features.becomes_count}_becomes_lines")

    elif family == "gravity":
        if features.gravity_example_count >= 2:
            score += 0.28
            triggers.append(f"structure:{features.gravity_example_count}_gravity_observations")
        if features.has_gravity_formula:
            score += 0.22
            triggers.append("formula:d=0.5*g*t^2")
        if "falling distance" in features.prompt_lower:
            score += 0.14
            triggers.append("query:falling_distance")

    elif family == "equation_transform":
        if features.has_equation_query:
            score += 0.22
            triggers.append("query:determine_equation_result")
        if "examples:" in features.prompt_lower and "=" in features.prompt:
            score += 0.18
            triggers.append("structure:equation_examples")
        if re.search(r"[`'\\/|@#^&!?()\[\]{}<>*-]", features.query):
            score += 0.18
            triggers.append("query:symbolic_operator_alphabet")
        if re.search(r"`.+? = .+", features.prompt):
            score += 0.16
            triggers.append("format:backticked_symbol_examples")

    return min(score, 1.6), triggers


def infer_subfamily(features: PromptFeatures, family: str) -> Optional[str]:
    query = features.query.strip()
    if family == "equation_transform":
        if NUMERIC_EQUATION_QUERY_RE.fullmatch(query):
            return "numeric_expression"
        if PUNCT_QUERY_RE.fullmatch(query):
            return "punctuation_string"
        return "mixed_symbolic"
    if family == "text_cipher":
        token_count = len(query.split())
        if token_count == 3:
            return "three_word_clause"
        if token_count == 4:
            return "four_word_clause"
        if token_count == 5:
            return "five_word_clause"
        return "other_clause_length"
    return None


def answer_schema_for_family(family: str, subfamily: Optional[str]) -> str:
    if family == "bit_transform":
        return "exactly 8 binary digits"
    if family == "text_cipher":
        return "3-5 lowercase words separated by single spaces"
    if family == "roman_numeral":
        return "uppercase Roman numeral"
    if family == "unit_conversion":
        return "decimal with exactly 2 places"
    if family == "gravity":
        return "decimal matching inferred benchmark precision"
    if family == "equation_transform":
        if subfamily == "numeric_expression":
            return "short symbolic or integer string; preserve leading zeros/minus sign"
        return "symbolic punctuation string; preserve exact characters"
    return "unconstrained"


def route_prompt(prompt: str) -> RouteResult:
    features = extract_features(prompt)
    score_breakdown: Dict[str, float] = {}
    trigger_map: Dict[str, List[str]] = {}
    for family in FAMILY_ORDER:
        score, triggers = score_family(features, family)
        score_breakdown[family] = score
        trigger_map[family] = triggers

    ranked = sorted(score_breakdown.items(), key=lambda item: item[1], reverse=True)
    top_family, top_score = ranked[0]
    second_family, second_score = ranked[1]
    margin = top_score - second_score

    raw_confidence = 0.45 + 0.35 * min(top_score / 1.2, 1.0) + 0.20 * min(max(margin, 0.0) / 0.6, 1.0)
    confidence = max(0.0, min(raw_confidence, 0.99))
    ambiguity_flag = confidence < 0.72 or margin < 0.18

    if top_score < 0.55:
        fallback_policy = "send to general symbolic fallback prompt and log for taxonomy review"
    elif ambiguity_flag:
        fallback_policy = (
            f"run {top_family} solver first, then backoff to {second_family} solver if schema validation fails"
        )
    else:
        fallback_policy = f"run {top_family} solver only; if output schema check fails, use generic benchmark fallback"

    subfamily = infer_subfamily(features, top_family)
    return RouteResult(
        family=top_family,
        confidence=round(confidence, 4),
        subfamily=subfamily,
        triggers=trigger_map[top_family],
        score_breakdown={k: round(v, 3) for k, v in score_breakdown.items()},
        ambiguity_flag=ambiguity_flag,
        fallback_policy=fallback_policy,
        answer_schema=answer_schema_for_family(top_family, subfamily),
        second_choice=second_family,
        margin=round(margin, 4),
    )


def infer_gold_family(prompt: str) -> str:
    prompt_lower = prompt.lower()
    if "8-bit binary numbers" in prompt_lower:
        return "bit_transform"
    if "decrypt the following text" in prompt_lower:
        return "text_cipher"
    if "write the number" in prompt_lower and "numeral system" in prompt_lower:
        return "roman_numeral"
    if "convert the following measurement" in prompt_lower:
        return "unit_conversion"
    if "d = 0.5*g*t^2" in prompt_lower:
        return "gravity"
    if "determine the result for:" in prompt_lower:
        return "equation_transform"
    raise ValueError("Unable to infer gold family from prompt template")


def infer_gold_subfamily(prompt: str, family: str) -> Optional[str]:
    if family != "equation_transform":
        return None
    query = extract_query(prompt)
    if NUMERIC_EQUATION_QUERY_RE.fullmatch(query):
        return "numeric_expression"
    if PUNCT_QUERY_RE.fullmatch(query):
        return "punctuation_string"
    return "mixed_symbolic"


def load_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def evaluate_router(rows: Iterable[Dict[str, str]]) -> Dict[str, object]:
    total = 0
    correct = 0
    ambiguous = 0
    family_counts = Counter()
    family_correct = Counter()
    confidence_by_family: Dict[str, List[float]] = defaultdict(list)
    eq_total = 0
    eq_correct = 0
    examples: List[Tuple[str, str, str, float, List[str]]] = []

    for row in rows:
        prompt = row["prompt"]
        gold_family = infer_gold_family(prompt)
        routed = route_prompt(prompt)
        total += 1
        family_counts[gold_family] += 1
        confidence_by_family[gold_family].append(routed.confidence)
        if routed.ambiguity_flag:
            ambiguous += 1
        if routed.family == gold_family:
            correct += 1
            family_correct[gold_family] += 1
        elif len(examples) < 10:
            examples.append((row.get("id", "?"), gold_family, routed.family, routed.confidence, routed.triggers))

        if gold_family == "equation_transform":
            eq_total += 1
            if routed.subfamily == infer_gold_subfamily(prompt, gold_family):
                eq_correct += 1

    summary = {
        "rows": total,
        "top_level_accuracy": (correct / total) if total else math.nan,
        "ambiguous_share": (ambiguous / total) if total else math.nan,
        "family_accuracy": {
            family: {
                "count": family_counts[family],
                "accuracy": (family_correct[family] / family_counts[family]) if family_counts[family] else math.nan,
                "mean_confidence": mean(confidence_by_family[family]) if confidence_by_family[family] else math.nan,
            }
            for family in FAMILY_ORDER
        },
        "equation_subfamily_accuracy": (eq_correct / eq_total) if eq_total else math.nan,
        "misroutes": examples,
    }
    return summary


def print_evaluation(summary: Dict[str, object]) -> None:
    print("=== Router evaluation ===")
    print(f"Rows: {summary['rows']}")
    print(f"Top-level routing accuracy: {summary['top_level_accuracy']:.4f}")
    print(f"Ambiguity-flag share: {summary['ambiguous_share']:.4f}")
    print(f"Equation subfamily accuracy: {summary['equation_subfamily_accuracy']:.4f}")
    print("\nPer-family metrics:")
    family_accuracy: Dict[str, Dict[str, float]] = summary["family_accuracy"]  # type: ignore[assignment]
    for family in FAMILY_ORDER:
        stats = family_accuracy[family]
        print(
            f"  - {family:<18} count={stats['count']:>4} "
            f"accuracy={stats['accuracy']:.4f} mean_confidence={stats['mean_confidence']:.4f}"
        )

    misroutes: List[Tuple[str, str, str, float, List[str]]] = summary["misroutes"]  # type: ignore[assignment]
    if misroutes:
        print("\nSample misroutes:")
        for row_id, gold, pred, conf, triggers in misroutes:
            joined = ", ".join(triggers)
            print(f"  - id={row_id} gold={gold} pred={pred} confidence={conf:.4f} triggers=[{joined}]")
    else:
        print("\nNo misroutes found on the evaluated split.")


def demo_routes(rows: Sequence[Dict[str, str]], limit: int) -> None:
    print("\n=== Sample routes ===")
    for row in rows[:limit]:
        routed = route_prompt(row["prompt"])
        print(f"id={row.get('id', '?')} family={routed.family} subfamily={routed.subfamily} confidence={routed.confidence:.4f}")
        print(f"  triggers: {', '.join(routed.triggers)}")
        print(f"  fallback: {routed.fallback_policy}")
        print(f"  answer schema: {routed.answer_schema}")


NORMALIZATION_RULES = {
    "bit_transform": "Emit only the final 8-bit string; left-pad with zeros to width 8 if solver returns fewer bits.",
    "text_cipher": "Lowercase all tokens, collapse repeated whitespace, and reject punctuation outside apostrophe-free words.",
    "roman_numeral": "Emit uppercase Roman numeral letters only; no surrounding prose.",
    "unit_conversion": "Round to exactly two decimals using decimal arithmetic and always print two digits after the point.",
    "gravity": "Infer the prompt precision from demonstrations, round consistently, and avoid trimming required trailing zeros.",
    "equation_transform": "Preserve exact symbolic characters, leading zeros, minus signs, and output length; never paraphrase or add spaces.",
}


def print_normalization_rules() -> None:
    print("\n=== Final answer normalization policy ===")
    for family in FAMILY_ORDER:
        print(f"  - {family}: {NORMALIZATION_RULES[family]}")
    print("  - final emission: wrap the normalized answer as \\boxed{answer} and avoid extra reasoning after the box.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build and evaluate the Wonderland task-family router.")
    parser.add_argument("--csv", type=Path, default=Path("train.csv"), help="CSV file to evaluate. Defaults to train.csv")
    parser.add_argument("--demo-limit", type=int, default=5, help="Number of example routes to print")
    parser.add_argument("--skip-demo", action="store_true", help="Skip sample route printing")
    args = parser.parse_args()

    rows = load_rows(args.csv)
    summary = evaluate_router(rows)
    print_evaluation(summary)
    if not args.skip_demo:
        demo_routes(rows, args.demo_limit)
    print_normalization_rules()
