#!/usr/bin/env python3
"""Generate selective synthetic data for high-confidence Wonderland families.

This script intentionally supports only the currently approved synthetic families:
- roman_numeral
- unit_conversion
- gravity

The goal is benchmark-faithful augmentation for formatting and parameter coverage,
not brute-force volume generation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Callable, Iterable, Sequence

getcontext().prec = 28

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "train.csv"
DEFAULT_OUTPUT = ROOT / "artifacts" / "synthetic" / "synthetic_train.csv"

SUPPORTED_FAMILIES = ("roman_numeral", "unit_conversion", "gravity")
ROMAN_BOUNDARIES = {4, 9, 14, 19, 39, 40, 44, 49, 90, 94, 99, 100}


@dataclass(frozen=True)
class SyntheticRow:
    row_id: str
    family: str
    synthetic_tier: str
    prompt: str
    answer: str


def stable_id(prefix: str, index: int, seed: int) -> str:
    digest = hashlib.md5(f"{prefix}:{index}:{seed}".encode("utf-8")).hexdigest()
    return f"syn_{digest[:12]}"


def read_existing_prompts(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["prompt"] for row in csv.DictReader(handle)}


def decimal_places(text: str) -> int:
    return len(text.split(".", 1)[1]) if "." in text else 0


def quantize(value: Decimal, places: int) -> str:
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
    remaining = number
    for value, token in pairs:
        while remaining >= value:
            output.append(token)
            remaining -= value
    return "".join(output)


def render_roman_prompt(rng: random.Random, tier: str) -> tuple[str, str]:
    example_count = rng.randint(3, 5)
    if tier == "stress":
        query = rng.choice(sorted(ROMAN_BOUNDARIES))
    else:
        query = rng.randint(1, 100)

    support_pool = [value for value in range(1, 101) if value != query]
    if tier == "stress":
        prioritized = [value for value in sorted(ROMAN_BOUNDARIES) if value != query]
        filler = [value for value in support_pool if value not in ROMAN_BOUNDARIES]
        rng.shuffle(prioritized)
        rng.shuffle(filler)
        support_numbers = prioritized[: example_count - 1]
        while len(support_numbers) < example_count:
            support_numbers.append(filler.pop())
    else:
        support_numbers = rng.sample(support_pool, example_count)

    examples = "\n".join(f"{value} -> {roman_encode(value)}" for value in support_numbers)
    prompt = (
        "In Alice's Wonderland, numbers are secretly converted into a different numeral system. "
        "Some examples are given below:\n"
        f"{examples}\n"
        f"Now, write the number {query} in the Wonderland numeral system."
    )
    return prompt, roman_encode(query)


def sample_decimal(rng: random.Random, minimum: str, maximum: str) -> Decimal:
    lower = int(Decimal(minimum) * 100)
    upper = int(Decimal(maximum) * 100)
    return Decimal(rng.randint(lower, upper)) / Decimal(100)


def render_unit_prompt(rng: random.Random, tier: str) -> tuple[str, str]:
    example_count = rng.randint(3, 5)
    if tier == "stress":
        slope = rng.choice(
            [Decimal("0.50"), Decimal("0.51"), Decimal("1.99"), Decimal("2.00"), Decimal("1.25")]
        )
    else:
        slope = sample_decimal(rng, "0.50", "2.00")

    used_inputs: set[Decimal] = set()

    def fresh_input() -> Decimal:
        while True:
            candidate = sample_decimal(rng, "5.00", "49.99")
            if candidate not in used_inputs:
                used_inputs.add(candidate)
                return candidate

    examples: list[tuple[Decimal, str]] = []
    for _ in range(example_count):
        left = fresh_input()
        right = quantize(left * slope, 2)
        examples.append((left, right))

    if tier == "stress":
        query = None
        for left_int in range(500, 5000):
            candidate = Decimal(left_int) / Decimal(100)
            if candidate in used_inputs:
                continue
            raw = candidate * slope
            thousandths = int((raw * 1000) % 10)
            if thousandths in {4, 5, 6}:
                query = candidate
                used_inputs.add(candidate)
                break
        if query is None:
            query = fresh_input()
    else:
        query = fresh_input()

    example_lines = "\n".join(f"{left:.2f} m becomes {right}" for left, right in examples)
    answer = quantize(query * slope, 2)
    prompt = (
        "In Alice's Wonderland, a secret unit conversion is applied to measurements. For example:\n"
        f"{example_lines}\n"
        f"Now, convert the following measurement: {query:.2f} m"
    )
    return prompt, answer


def infer_precision(example_values: Sequence[str], computed: Decimal, tier: str) -> int:
    if tier != "stress":
        return 2
    if any(decimal_places(value) == 1 for value in example_values):
        rounded_2 = quantize(computed, 2)
        if rounded_2.endswith("0"):
            return 1
    return 2


def render_gravity_prompt(rng: random.Random, tier: str) -> tuple[str, str]:
    example_count = rng.randint(3, 5)
    if tier == "stress":
        g = rng.choice(
            [Decimal("4.90"), Decimal("5.00"), Decimal("9.81"), Decimal("12.50"), Decimal("19.60")]
        )
    else:
        g = sample_decimal(rng, "4.90", "19.60")

    used_times: set[Decimal] = set()

    def fresh_time() -> Decimal:
        while True:
            candidate = Decimal(rng.randint(100, 500)) / Decimal(100)
            if candidate not in used_times:
                used_times.add(candidate)
                return candidate

    example_lines: list[str] = []
    example_distances: list[str] = []
    for index in range(example_count):
        time_value = fresh_time()
        raw_distance = Decimal("0.5") * g * time_value * time_value
        if tier == "stress" and index == 0:
            rendered_distance = quantize(raw_distance, 1)
        else:
            rendered_distance = quantize(raw_distance, 2)
        example_distances.append(rendered_distance)
        time_text = f"{time_value:.2f}".rstrip("0").rstrip(".")
        example_lines.append(f"For t = {time_text}s, distance = {rendered_distance} m")

    query_time = fresh_time()
    raw_answer = Decimal("0.5") * g * query_time * query_time
    precision = infer_precision(example_distances, raw_answer, tier)
    answer = quantize(raw_answer, precision)
    query_time_text = f"{query_time:.2f}".rstrip("0").rstrip(".")
    rendered_examples = "\n".join(example_lines)
    prompt = (
        "In Alice's Wonderland, the gravitational constant has been secretly changed. Here are some example observations:\n"
        f"{rendered_examples}\n"
        f"Now, determine the falling distance for t = {query_time_text}s given d = 0.5*g*t^2."
    )
    return prompt, answer


GENERATOR_MAP: dict[str, Callable[[random.Random, str], tuple[str, str]]] = {
    "roman_numeral": render_roman_prompt,
    "unit_conversion": render_unit_prompt,
    "gravity": render_gravity_prompt,
}


def answer_matches_schema(family: str, answer: str) -> bool:
    patterns = {
        "roman_numeral": re.compile(r"^[IVXLCDM]+$"),
        "unit_conversion": re.compile(r"^-?\d+\.\d{2}$"),
        "gravity": re.compile(r"^-?\d+\.\d{1,2}$"),
    }
    return bool(patterns[family].fullmatch(answer))


def generate_rows(
    family: str,
    count: int,
    seed: int,
    tier: str,
    existing_prompts: set[str],
) -> list[SyntheticRow]:
    rng = random.Random(seed)
    generator = GENERATOR_MAP[family]
    rows: list[SyntheticRow] = []
    seen_prompts: set[str] = set(existing_prompts)
    attempts = 0
    target = count
    while len(rows) < target:
        attempts += 1
        if attempts > target * 50:
            raise RuntimeError(f"Could not generate enough unique rows for {family} ({len(rows)}/{target}).")
        prompt, answer = generator(rng, tier)
        if prompt in seen_prompts:
            continue
        if not answer_matches_schema(family, answer):
            continue
        seen_prompts.add(prompt)
        rows.append(
            SyntheticRow(
                row_id=stable_id(family, len(rows), seed),
                family=family,
                synthetic_tier=tier,
                prompt=prompt,
                answer=answer,
            )
        )
    return rows


def preset_counts(preset: str) -> dict[str, int]:
    if preset == "mvp":
        return {"roman_numeral": 600, "unit_conversion": 1200, "gravity": 1200}
    if preset == "full":
        return {"roman_numeral": 2000, "unit_conversion": 4000, "gravity": 4000}
    raise ValueError(f"Unknown preset: {preset}")


def write_rows(path: Path, rows: Iterable[SyntheticRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "family", "synthetic_tier", "prompt", "answer"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": row.row_id,
                    "family": row.family,
                    "synthetic_tier": row.synthetic_tier,
                    "prompt": row.prompt,
                    "answer": row.answer,
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preset",
        choices=("mvp", "full"),
        default="mvp",
        help="Synthetic curriculum preset to generate.",
    )
    parser.add_argument(
        "--families",
        nargs="+",
        choices=SUPPORTED_FAMILIES,
        default=list(SUPPORTED_FAMILIES),
        help="Approved families to generate.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to write the generated CSV.",
    )
    parser.add_argument("--seed", type=int, default=7, help="Random seed.")
    parser.add_argument(
        "--stress-fraction",
        type=float,
        default=0.15,
        help="Fraction of each family to sample from the stress tier.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    counts = preset_counts(args.preset)
    existing_prompts = read_existing_prompts(TRAIN_PATH)
    all_rows: list[SyntheticRow] = []
    for offset, family in enumerate(args.families):
        total = counts[family]
        stress_count = int(round(total * args.stress_fraction))
        core_count = total - stress_count
        family_seed = args.seed + (offset * 1000)
        all_rows.extend(generate_rows(family, core_count, family_seed, "core", existing_prompts))
        all_rows.extend(generate_rows(family, stress_count, family_seed + 1, "stress", existing_prompts))

    write_rows(args.output, all_rows)

    print(f"Wrote {len(all_rows)} synthetic rows to {args.output}")
    by_family: dict[str, int] = {family: 0 for family in args.families}
    by_tier: dict[str, int] = {"core": 0, "stress": 0}
    for row in all_rows:
        by_family[row.family] += 1
        by_tier[row.synthetic_tier] += 1
    for family, count in by_family.items():
        print(f"  - {family}: {count}")
    for tier, count in by_tier.items():
        print(f"  - {tier}: {count}")


if __name__ == "__main__":
    main()
