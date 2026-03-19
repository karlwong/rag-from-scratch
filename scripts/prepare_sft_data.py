#!/usr/bin/env python3
"""Prepare benchmark-specific SFT data for minimal Nemotron LoRA experiments.

The benchmark favors terse, exact outputs. This script converts the original
training rows plus optional approved synthetic rows into chat-style JSONL files
that emphasize the final answer contract used at inference time.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAIN_PATH = ROOT / "train.csv"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "sft"

FAMILY_PREFIXES: Sequence[tuple[str, str]] = (
    (
        "bit_transform",
        "In Alice's Wonderland, a secret bit manipulation rule transforms 8-bit binary numbers.",
    ),
    (
        "text_cipher",
        "In Alice's Wonderland, secret encryption rules are used on text.",
    ),
    (
        "roman_numeral",
        "In Alice's Wonderland, numbers are secretly converted into a different numeral system.",
    ),
    (
        "unit_conversion",
        "In Alice's Wonderland, a secret unit conversion is applied to measurements.",
    ),
    (
        "gravity",
        "In Alice's Wonderland, the gravitational constant has been secretly changed.",
    ),
    (
        "equation_transform",
        "In Alice's Wonderland, a secret set of transformation rules is applied to equations.",
    ),
)

DEFAULT_SYSTEM_PROMPT = (
    "You solve Wonderland benchmark prompts. Infer the rule silently and return only the final "
    "answer in a single LaTeX box like \\boxed{answer}. Never add explanation, units, or extra text."
)

SCHEMA_HINTS = {
    "bit_transform": "Return exactly 8 binary digits inside one box.",
    "text_cipher": "Return only the decrypted lowercase phrase inside one box.",
    "roman_numeral": "Return only the uppercase Roman numeral inside one box.",
    "unit_conversion": "Return only the converted decimal with exactly 2 digits after the decimal point inside one box.",
    "gravity": "Return only the distance as a decimal using the prompt-consistent precision inside one box.",
    "equation_transform": "Return only the exact symbolic or integer result inside one box, preserving minus signs and leading zeros when present.",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-path", type=Path, default=DEFAULT_TRAIN_PATH)
    parser.add_argument(
        "--synthetic-path",
        dest="synthetic_paths",
        action="append",
        type=Path,
        default=[],
        help="Optional synthetic CSV path(s) with at least prompt and answer columns.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--recipe",
        choices=("original_sft", "mixed_sft", "family_conditioned", "format_stabilization"),
        default="mixed_sft",
        help="Training recipe to materialize.",
    )
    parser.add_argument(
        "--family-filter",
        nargs="*",
        help="Optional list of family ids to keep. Default keeps all real rows and all provided synthetic rows.",
    )
    parser.add_argument(
        "--dev-fraction",
        type=float,
        default=0.1,
        help="Fraction of rows assigned to the dev split using a stable hash.",
    )
    parser.add_argument(
        "--box-style",
        choices=("boxed", "plain"),
        default="boxed",
        help="Assistant target style. 'boxed' is recommended for final-contract tuning.",
    )
    parser.add_argument(
        "--max-synthetic-per-family",
        type=int,
        default=0,
        help="Optional cap per synthetic family after loading. 0 means no cap.",
    )
    return parser.parse_args()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def classify_family(prompt: str) -> str:
    for family, prefix in FAMILY_PREFIXES:
        if prompt.startswith(prefix):
            return family
    raise ValueError(f"Unknown family prefix for prompt: {prompt[:120]!r}")


def stable_bucket(key: str) -> float:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def load_real_rows(path: Path) -> list[dict[str, str]]:
    rows = []
    for row in read_csv_rows(path):
        rows.append(
            {
                "id": row["id"],
                "prompt": row["prompt"],
                "answer": row["answer"],
                "family": classify_family(row["prompt"]),
                "source": "real",
            }
        )
    return rows


def load_synthetic_rows(paths: Iterable[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        for index, row in enumerate(read_csv_rows(path)):
            prompt = row["prompt"]
            rows.append(
                {
                    "id": row.get("id") or row.get("row_id") or f"{path.stem}_{index}",
                    "prompt": prompt,
                    "answer": row["answer"],
                    "family": row.get("family") or classify_family(prompt),
                    "source": row.get("source") or "synthetic",
                }
            )
    return rows


def maybe_cap_synthetic(rows: list[dict[str, str]], cap: int) -> list[dict[str, str]]:
    if cap <= 0:
        return rows
    kept: list[dict[str, str]] = []
    per_family = Counter()
    for row in rows:
        family = row["family"]
        if per_family[family] >= cap:
            continue
        per_family[family] += 1
        kept.append(row)
    return kept


def build_user_prompt(row: dict[str, str], recipe: str) -> str:
    prompt = row["prompt"].strip()
    family = row["family"]
    if recipe == "family_conditioned":
        return f"[family={family}]\n{prompt}\n\nSchema hint: {SCHEMA_HINTS[family]}"
    if recipe == "format_stabilization":
        return f"{prompt}\n\nReturn only the boxed final answer. {SCHEMA_HINTS[family]}"
    return prompt


def build_system_prompt(row: dict[str, str], recipe: str) -> str:
    if recipe == "family_conditioned":
        return DEFAULT_SYSTEM_PROMPT + f" The routed family is {row['family']}."
    if recipe == "format_stabilization":
        return DEFAULT_SYSTEM_PROMPT + " Prioritize format obedience over explanation."
    return DEFAULT_SYSTEM_PROMPT


def render_target(answer: str, box_style: str) -> str:
    return f"\\boxed{{{answer}}}" if box_style == "boxed" else answer


def make_record(row: dict[str, str], recipe: str, box_style: str) -> dict[str, object]:
    return {
        "id": row["id"],
        "source": row["source"],
        "family": row["family"],
        "messages": [
            {"role": "system", "content": build_system_prompt(row, recipe)},
            {"role": "user", "content": build_user_prompt(row, recipe)},
            {"role": "assistant", "content": render_target(row["answer"], box_style)},
        ],
        "metadata": {
            "benchmark": "wonderland_reasoning",
            "recipe": recipe,
            "answer": row["answer"],
            "target_format": box_style,
        },
    }


def assign_split(row_id: str, source: str, dev_fraction: float) -> str:
    if source == "synthetic":
        return "train"
    return "dev" if stable_bucket(row_id) < dev_fraction else "train"


def write_jsonl(path: Path, records: Iterable[dict[str, object]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> int:
    args = parse_args()
    real_rows = load_real_rows(args.train_path)
    synthetic_rows = maybe_cap_synthetic(load_synthetic_rows(args.synthetic_paths), args.max_synthetic_per_family)

    rows: list[dict[str, str]] = list(real_rows)
    if args.recipe in {"mixed_sft", "family_conditioned", "format_stabilization"}:
        rows.extend(synthetic_rows)

    if args.recipe == "original_sft":
        rows = [row for row in rows if row["source"] == "real"]

    if args.family_filter:
        allowed = set(args.family_filter)
        rows = [row for row in rows if row["family"] in allowed]

    if not rows:
        raise SystemExit("No rows selected. Check --recipe, --family-filter, or synthetic inputs.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    dataset_name = f"{args.recipe}_{args.box_style}"
    train_records: list[dict[str, object]] = []
    dev_records: list[dict[str, object]] = []
    source_counter = Counter()
    family_counter = Counter()

    for row in rows:
        source_counter[row["source"]] += 1
        family_counter[row["family"]] += 1
        split = assign_split(row["id"], row["source"], args.dev_fraction)
        record = make_record(row, args.recipe, args.box_style)
        if split == "dev":
            dev_records.append(record)
        else:
            train_records.append(record)

    train_path = args.output_dir / f"{dataset_name}.train.jsonl"
    dev_path = args.output_dir / f"{dataset_name}.dev.jsonl"
    summary_path = args.output_dir / f"{dataset_name}.summary.json"

    train_count = write_jsonl(train_path, train_records)
    dev_count = write_jsonl(dev_path, dev_records)

    summary = {
        "dataset_name": dataset_name,
        "recipe": args.recipe,
        "box_style": args.box_style,
        "train_rows": train_count,
        "dev_rows": dev_count,
        "sources": dict(source_counter),
        "families": dict(family_counter),
        "synthetic_inputs": [str(path) for path in args.synthetic_paths],
        "family_filter": args.family_filter or [],
        "train_path": str(train_path),
        "dev_path": str(dev_path),
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
