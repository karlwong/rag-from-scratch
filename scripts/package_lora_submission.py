#!/usr/bin/env python3
"""Validate and package a Nemotron-compatible LoRA submission bundle.

This script does not train a model. It packages an already produced LoRA adapter
into a reproducible submission directory and validates the minimum assumptions
needed for the competition handoff.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "submission"
EXPECTED_BASE_MODEL = "Nemotron-3-Nano-30B"
REQUIRED_ADAPTER_FILES = ("adapter_config.json",)
OPTIONAL_WEIGHT_FILES = ("adapter_model.safetensors", "adapter_model.bin")

INFERENCE_CONTRACT = """You solve Wonderland benchmark prompts.
- Infer the rule silently.
- Return exactly one final answer.
- The final non-whitespace text must be a single LaTeX box: \\boxed{answer}
- Do not add explanations, units, apologies, or extra punctuation after the box.
- Preserve benchmark schema exactly:
  * bit_transform -> 8 binary digits
  * text_cipher -> lowercase words separated by single spaces
  * roman_numeral -> uppercase Roman numeral
  * unit_conversion -> decimal with exactly 2 digits after the decimal point
  * gravity -> decimal using prompt-consistent precision
  * equation_transform -> exact symbolic/integer string, preserving leading zeros and minus signs
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--submission-name", default="wonderland_nemotron_lora")
    parser.add_argument(
        "--expected-base-model",
        default=EXPECTED_BASE_MODEL,
        help="Substring that must appear in adapter_config.json base_model_name_or_path.",
    )
    parser.add_argument(
        "--allow-missing-weight-file",
        action="store_true",
        help="Allow packaging config-only dry runs without adapter weights.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_adapter_dir(adapter_dir: Path, expected_base_model: str, allow_missing_weight_file: bool) -> tuple[dict, list[str]]:
    errors: list[str] = []
    for filename in REQUIRED_ADAPTER_FILES:
        if not (adapter_dir / filename).exists():
            errors.append(f"missing required file: {filename}")

    weight_candidates = [filename for filename in OPTIONAL_WEIGHT_FILES if (adapter_dir / filename).exists()]
    if not weight_candidates and not allow_missing_weight_file:
        errors.append("missing adapter weights: expected adapter_model.safetensors or adapter_model.bin")

    config = load_json(adapter_dir / "adapter_config.json") if (adapter_dir / "adapter_config.json").exists() else {}
    base_model = str(config.get("base_model_name_or_path", ""))
    if expected_base_model.lower() not in base_model.lower():
        errors.append(
            f"adapter_config.json base_model_name_or_path must contain '{expected_base_model}', got '{base_model or 'MISSING'}'"
        )
    if str(config.get("peft_type", "")).upper() != "LORA":
        errors.append(f"adapter_config.json peft_type must be 'LORA', got '{config.get('peft_type', 'MISSING')}'")
    if "target_modules" not in config:
        errors.append("adapter_config.json missing target_modules")

    return config, errors


def copy_submission_files(adapter_dir: Path, submission_dir: Path) -> list[str]:
    copied: list[str] = []
    for path in adapter_dir.iterdir():
        if path.is_file():
            shutil.copy2(path, submission_dir / path.name)
            copied.append(path.name)
    return sorted(copied)


def write_supporting_files(submission_dir: Path, manifest: dict) -> None:
    (submission_dir / "README_submission.md").write_text(
        "# Wonderland LoRA submission\n\n"
        "This bundle is intended for NVIDIA Nemotron-3-Nano-30B with vLLM-based inference.\n\n"
        "## Inference contract\n"
        f"```text\n{INFERENCE_CONTRACT}```\n",
        encoding="utf-8",
    )
    (submission_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def create_archive(submission_dir: Path) -> Path:
    archive_path = submission_dir.with_suffix(".tar.gz")
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(submission_dir, arcname=submission_dir.name)
    return archive_path


def main() -> int:
    args = parse_args()
    adapter_dir = args.adapter_dir.resolve()
    output_dir = args.output_dir.resolve()
    submission_dir = output_dir / args.submission_name
    output_dir.mkdir(parents=True, exist_ok=True)
    if submission_dir.exists():
        shutil.rmtree(submission_dir)
    submission_dir.mkdir(parents=True, exist_ok=True)

    config, errors = validate_adapter_dir(
        adapter_dir=adapter_dir,
        expected_base_model=args.expected_base_model,
        allow_missing_weight_file=args.allow_missing_weight_file,
    )
    if errors:
        raise SystemExit("Submission validation failed:\n- " + "\n- ".join(errors))

    copied_files = copy_submission_files(adapter_dir, submission_dir)
    manifest = {
        "submission_name": args.submission_name,
        "adapter_dir": str(adapter_dir),
        "copied_files": copied_files,
        "base_model_name_or_path": config.get("base_model_name_or_path"),
        "peft_type": config.get("peft_type"),
        "target_modules": config.get("target_modules"),
        "vllm_assumptions": {
            "base_model": config.get("base_model_name_or_path"),
            "adapter_loaded_via_lora": True,
            "final_answer_emission": "single boxed answer with no trailing text",
        },
        "inference_contract": INFERENCE_CONTRACT.strip().splitlines(),
    }
    write_supporting_files(submission_dir, manifest)
    archive_path = create_archive(submission_dir)

    print(json.dumps({
        "submission_dir": str(submission_dir),
        "archive_path": str(archive_path),
        "copied_files": copied_files,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
