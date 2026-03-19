# Runbook: zero setup to validated result

## 1. Purpose and scope

This repository is a **benchmark-analysis and packaging workspace** for the Wonderland-style reasoning competition described in `AGENTS.md` and the project docs. The checked-in code does **not** train or serve a final model end to end yet. What it currently does is:

1. inspect and profile the benchmark CSVs,
2. route prompts into benchmark families,
3. run honest offline baseline evaluation on `train.csv`,
4. generate approved synthetic data for the safest families,
5. convert real and synthetic rows into chat-style SFT JSONL files, and
6. validate/package a **Nemotron-3-Nano-30B-compatible LoRA adapter directory** for submission.

In this repo, a **"result"** can mean two different things depending on stage:

- **Current implemented result:** a reproducible offline evaluation summary plus optional synthetic/SFT/packaging artifacts.
- **Final competition result:** a packaged LoRA adapter bundle containing at minimum `adapter_config.json` and, in a real submission, adapter weights compatible with NVIDIA Nemotron-3-Nano-30B and vLLM.

### Expected outputs

Depending on which stage you run, expect these outputs:

- Console reports from:
  - `scripts/profile_dataset.py`
  - `scripts/build_router.py`
  - `scripts/eval_baselines.py`
- Synthetic CSV files under `artifacts/synthetic/`
- SFT JSONL datasets plus a summary JSON under `artifacts/sft/`
- Submission bundles under `artifacts/submission/`
- No training checkpoints, no inference server outputs, and no final leaderboard predictions are produced by the current checked-in code.

---

## 2. Repository overview

## Top-level files

- `train.csv`: the real labeled development dataset used for profiling, offline evaluation, and SFT-data preparation.
- `test.csv`: a tiny visible smoke-test file. Existing docs and profiler output show it is fully overlapped with train and **must not** be treated as a real validation set.
- `AGENTS.md`: project-level instructions and benchmark assumptions.

## `docs/`

These documents explain the intended strategy and should be read before changing the workflow:

- `docs/dataset_forensics.md`: benchmark-specific findings from direct CSV inspection.
- `docs/task_taxonomy.md`: top-level task families and suspected subfamilies.
- `docs/system_architecture.md`: intended router-first / solver-first architecture.
- `docs/synthetic_data_plan.md`: which families are safe vs unsafe for synthetic generation.
- `docs/eval_plan.md`: honest offline evaluation design and cautions.
- `docs/lora_plan.md`: when LoRA is justified and how minimal it should be.
- `docs/submission_checklist.md`: packaging and final-deliverable checks.
- `docs/experiment_backlog.md`: prioritized next experiments.
- `docs/work_plan.md`: implementation work plan for the current repo stage.
- `docs/run_from_zero_to_result.md`: this runbook.

## `scripts/`

These are the executable workflow components currently implemented:

- `scripts/profile_dataset.py`: profiles `train.csv` and `test.csv`; reports family counts, answer schemas, and specialized statistics.
- `scripts/build_router.py`: evaluates a hand-built prompt router and prints normalization rules for final answers.
- `scripts/eval_baselines.py`: evaluates simple baseline predictors across random and structure-aware folds.
- `scripts/generate_synthetic.py`: generates approved synthetic rows for `roman_numeral`, `unit_conversion`, and `gravity` only.
- `scripts/prepare_sft_data.py`: converts real and optional synthetic rows into chat-style JSONL SFT datasets.
- `scripts/package_lora_submission.py`: validates an adapter directory and packages it as a submission bundle.

## `src/`

- **Current status:** this directory does **not exist** in the checked-in repo.
- The docs reference possible future modules such as `src/router.py` and `src/solvers.py`, but the current implementation keeps logic inside `scripts/`.

## `configs/`

- **Current status:** this directory does **not exist**.
- No training config files, YAML experiment configs, or inference configs are checked in yet.

## `outputs/`

- **Current status:** this directory does **not exist**.
- The actual scripts write to `artifacts/`, not `outputs/`.

## `experiments/`

- **Current status:** this directory does **not exist**.
- Experiment tracking is currently documented in markdown rather than stored as structured experiment manifests.

## `artifacts/`

- **Current status:** created on demand by the scripts.
- This is the practical output root used by the implemented workflow.
- Expected subdirectories:
  - `artifacts/synthetic/`
  - `artifacts/sft/`
  - `artifacts/submission/`

---

## 3. Prerequisites

## Python version

Assumption from the local environment and script style:

- **Python 3.10+ recommended**.
- The repo was exercised successfully here with Python 3.10.

The scripts use only the Python standard library, so there is currently no checked-in `requirements.txt`, `pyproject.toml`, or Conda environment file.

## Package / dependency assumptions

Current scripts rely only on standard-library modules such as:

- `argparse`
- `csv`
- `json`
- `hashlib`
- `statistics`
- `decimal`
- `pathlib`
- `tarfile`
- `shutil`

That means the **current implemented workflow has no mandatory external Python dependencies**.

## GPU / CUDA assumptions

- **Not required** for the currently implemented scripts.
- A GPU will become relevant only when you actually train or run a Nemotron LoRA outside the current checked-in workflow.
- Repo docs assume the final submission target is **NVIDIA Nemotron-3-Nano-30B** with **vLLM** inference compatibility, but there is no training or vLLM launch script in this repo yet.

## Environment variables

- No environment variables are required by the current scripts.
- If you build your own training or inference stack later, you will likely need your own CUDA / HF / experiment-tracking environment variables, but those are not defined by the current codebase.

## Required files before running

Minimum files that must exist:

- `train.csv`
- `test.csv`
- the `scripts/` directory

Additional files needed for specific stages:

- For SFT data prep with synthetic augmentation: a synthetic CSV produced by `scripts/generate_synthetic.py` or an equivalent CSV with `prompt` and `answer` columns.
- For submission packaging: an adapter directory containing at least:
  - `adapter_config.json`
  - plus normally either `adapter_model.safetensors` or `adapter_model.bin`

---

## 4. Quick start

If you want the **shortest path from zero setup to a first working result**, do this:

### Step 1: verify Python

```bash
python --version
```

### Step 2: inspect the dataset profile

```bash
python scripts/profile_dataset.py
```

What you get:

- a benchmark summary printed to stdout,
- family counts,
- answer schema counts,
- confirmation that visible `test.csv` is not a real evaluation target.

### Step 3: verify the router

```bash
python scripts/build_router.py --skip-demo
```

What you get:

- top-level router accuracy on the checked-in dataset,
- equation subfamily routing accuracy,
- normalization rules for final answer formatting.

### Step 4: run the baseline evaluation

```bash
python scripts/eval_baselines.py --baseline solver_lite
```

What you get:

- overall exact-match accuracy,
- per-family exact-match accuracy,
- answer-format accuracy,
- random-vs-structure-aware split comparison.

### Where outputs appear

- For quick start, outputs are printed to the terminal only.
- No files are created unless you run synthetic generation, SFT prep, or packaging.

### What counts as the first working result

For the current repo state, the first useful result is the offline baseline report from `scripts/eval_baselines.py`. In the checked-in implementation, that shows:

- perfect format accuracy,
- perfect Roman-numeral accuracy,
- strong but incomplete unit/gravity accuracy,
- near-zero performance on text, bit, and equation families.

That establishes the current baseline honestly before you add solver or LoRA work.

---

## 5. Full end-to-end workflow

This section walks through the **actual implemented project workflow**, from empty environment to packaged artifact.

## Stage 0: clone repo and enter it

```bash
git clone <repo-url>
cd rag-from-scratch
```

## Stage 1: setup environment

Because there is no dependency file yet, the practical setup is minimal:

```bash
python -m venv .venv
source .venv/bin/activate
python --version
```

If you prefer not to use a venv, the scripts still run as long as a compatible Python is available.

## Stage 2: inspect data directly

You should inspect the raw CSVs before trusting the docs.

```bash
python - <<'PY'
import csv
from itertools import islice
for name in ['train.csv', 'test.csv']:
    print(f'\n{name}')
    with open(name, newline='', encoding='utf-8') as f:
        for row in islice(csv.reader(f), 5):
            print(row)
PY
```

Reads from:

- `train.csv`
- `test.csv`

Writes to:

- stdout only

## Stage 3: profile the dataset

```bash
python scripts/profile_dataset.py
```

Optional JSON output:

```bash
python scripts/profile_dataset.py --json > artifacts/profile.json
```

Reads from:

- `train.csv`
- `test.csv`

Writes to:

- stdout only by default
- user-chosen file if you redirect output

Purpose:

- establish family counts,
- validate benchmark assumptions,
- confirm visible-test leakage,
- understand answer-format requirements.

## Stage 4: build / run router components

There is no persisted router artifact yet; `scripts/build_router.py` evaluates the hand-built routing logic directly.

```bash
python scripts/build_router.py
```

For a concise report:

```bash
python scripts/build_router.py --skip-demo
```

Reads from:

- `train.csv` by default
- another CSV if you pass `--csv <path>`

Writes to:

- stdout only

Purpose:

- verify the prompt-family router,
- inspect route confidence and ambiguity behavior,
- print the expected answer normalization rules.

## Stage 5: generate synthetic data if applicable

Current implementation supports **only these approved families**:

- `roman_numeral`
- `unit_conversion`
- `gravity`

Generate the MVP synthetic set:

```bash
python scripts/generate_synthetic.py \
  --preset mvp \
  --output artifacts/synthetic/mvp_synthetic_train.csv
```

Generate only selected families:

```bash
python scripts/generate_synthetic.py \
  --preset mvp \
  --families roman_numeral unit_conversion \
  --output artifacts/synthetic/mvp_numeric_only.csv
```

Reads from:

- `train.csv` only for prompt deduplication against existing prompts

Writes to:

- `artifacts/synthetic/*.csv`

Notes:

- `mvp` preset targets 3,000 rows total.
- `full` preset targets 10,000 rows total.
- The script does **not** generate text, bit, or equation synthetic data.

## Stage 6: prepare SFT data if applicable

The repo does not train a model yet, but it **does** build SFT-ready JSONL datasets.

### Real-only SFT set

```bash
python scripts/prepare_sft_data.py \
  --recipe original_sft \
  --output-dir artifacts/sft
```

### Mixed real + synthetic SFT set

```bash
python scripts/prepare_sft_data.py \
  --recipe mixed_sft \
  --synthetic-path artifacts/synthetic/mvp_synthetic_train.csv \
  --output-dir artifacts/sft
```

### Format-stabilization variant

```bash
python scripts/prepare_sft_data.py \
  --recipe format_stabilization \
  --synthetic-path artifacts/synthetic/mvp_synthetic_train.csv \
  --output-dir artifacts/sft
```

Reads from:

- `train.csv`
- optional synthetic CSV(s)

Writes to:

- `artifacts/sft/<dataset>.train.jsonl`
- `artifacts/sft/<dataset>.dev.jsonl`
- `artifacts/sft/<dataset>.summary.json`

Important split behavior:

- real rows are split into train/dev by stable hash using `--dev-fraction`,
- synthetic rows are always assigned to train.

## Stage 7: run evaluation

The current offline evaluation script is baseline-oriented.

```bash
python scripts/eval_baselines.py --baseline solver_lite
```

Alternative weaker reference:

```bash
python scripts/eval_baselines.py --baseline last_demo
```

Reads from:

- `train.csv`

Writes to:

- stdout only

Purpose:

- establish reproducible baselines,
- compare random vs structure-aware splits,
- inspect family-specific performance before adding more complexity.

## Stage 8: run inference if applicable

### Current status

This repo **does not provide a final inference runner** for:

- loading a trained Nemotron LoRA,
- executing vLLM generation,
- routing between symbolic solvers and model generation,
- producing final test predictions.

Most likely intended future workflow, based on the docs:

1. use router / solver logic for families that can be solved deterministically,
2. use a minimal LoRA or fallback LM on unsolved families,
3. normalize and emit a single boxed final answer.

Treat any full inference command beyond packaging as an **assumption / not-yet-implemented step**.

## Stage 9: package submission artifact if applicable

Once you have a real adapter directory, package it like this:

```bash
python scripts/package_lora_submission.py \
  --adapter-dir path/to/adapter_dir \
  --output-dir artifacts/submission \
  --submission-name wonderland_nemotron_lora
```

Dry-run packaging, if you only want to validate config structure before weights exist:

```bash
python scripts/package_lora_submission.py \
  --adapter-dir path/to/adapter_dir \
  --output-dir artifacts/submission \
  --submission-name wonderland_nemotron_lora \
  --allow-missing-weight-file
```

Reads from:

- adapter directory contents

Writes to:

- `artifacts/submission/<submission-name>/`
- `artifacts/submission/<submission-name>.tar.gz`

Generated support files include:

- `README_submission.md`
- `manifest.json`

---

## 6. Exact command examples

This section lists concrete repo-aligned commands in the most practical order.

## A. Inspect the benchmark

```bash
python scripts/profile_dataset.py
```

```bash
python scripts/profile_dataset.py --json > artifacts/profile.json
```

## B. Inspect router behavior

```bash
python scripts/build_router.py --skip-demo
```

```bash
python scripts/build_router.py --csv train.csv --demo-limit 3
```

## C. Run baseline evaluation

```bash
python scripts/eval_baselines.py --baseline solver_lite --num-folds 5
```

```bash
python scripts/eval_baselines.py --baseline last_demo --num-folds 5
```

## D. Generate synthetic data

```bash
python scripts/generate_synthetic.py \
  --preset mvp \
  --output artifacts/synthetic/mvp_synthetic_train.csv
```

```bash
python scripts/generate_synthetic.py \
  --preset full \
  --families roman_numeral gravity \
  --stress-fraction 0.20 \
  --output artifacts/synthetic/full_roman_gravity.csv
```

## E. Build SFT JSONL datasets

Real only:

```bash
python scripts/prepare_sft_data.py \
  --recipe original_sft \
  --box-style boxed \
  --output-dir artifacts/sft
```

Mixed training with synthetic augmentation:

```bash
python scripts/prepare_sft_data.py \
  --recipe mixed_sft \
  --synthetic-path artifacts/synthetic/mvp_synthetic_train.csv \
  --box-style boxed \
  --output-dir artifacts/sft
```

Family-conditioned variant:

```bash
python scripts/prepare_sft_data.py \
  --recipe family_conditioned \
  --synthetic-path artifacts/synthetic/mvp_synthetic_train.csv \
  --box-style boxed \
  --output-dir artifacts/sft
```

Limit synthetic rows per family:

```bash
python scripts/prepare_sft_data.py \
  --recipe mixed_sft \
  --synthetic-path artifacts/synthetic/mvp_synthetic_train.csv \
  --max-synthetic-per-family 500 \
  --output-dir artifacts/sft
```

## F. Package the final adapter

```bash
python scripts/package_lora_submission.py \
  --adapter-dir path/to/final_adapter \
  --output-dir artifacts/submission \
  --submission-name final_nemotron_adapter
```

Dry-run validation without weights:

```bash
python scripts/package_lora_submission.py \
  --adapter-dir path/to/final_adapter \
  --output-dir artifacts/submission \
  --submission-name config_only_check \
  --allow-missing-weight-file
```

## Not implemented yet, but likely intended usage

The docs strongly imply future commands for:

- actual LoRA training,
- actual vLLM inference on held-out prompts,
- solver-backed final prediction generation.

Those commands are **not implemented** in the current repo, so do not assume a missing `train.py`, `infer.py`, or `serve.py` exists.

---

## 7. Evaluation guide

## How to run evaluation

The current evaluation entry point is:

```bash
python scripts/eval_baselines.py --baseline solver_lite
```

This script evaluates rows from `train.csv` using two split strategies:

1. **stratified_random_hash**: fold assignment from row id
2. **structure_aware_hash**: fold assignment from a family-specific structure signature

## Metrics reported

### Overall accuracy

Definition:

- exact string match between prediction and gold answer after minimal normalization.

Why it matters:

- this is the closest available proxy to leaderboard scoring.

### Per-family accuracy

Reported for:

- `bit_transform`
- `text_cipher`
- `roman_numeral`
- `unit_conversion`
- `gravity`
- `equation_transform`

Why it matters:

- the dataset is nearly balanced across families,
- aggregate gains can hide regressions in the hard families.

### Answer-format accuracy

Definition:

- fraction of predictions matching family-specific formatting constraints, regardless of correctness.

Examples:

- bit: exactly 8 binary digits
- Roman: uppercase Roman numeral only
- unit conversion: exactly 2 decimal places
- gravity: 1 or 2 decimal places
- text: 3 to 5 lowercase words
- equation: non-empty exact symbolic/integer string

### Random-vs-structure gap

Definition:

- `overall_accuracy(random_split) - overall_accuracy(structure_split)`

Why it matters:

- a large positive gap suggests your system relies too much on easy structural overlap rather than real generalization.

## How to interpret the current baseline

Using the checked-in `solver_lite` baseline, expect roughly:

- overall accuracy around **0.4336**,
- answer-format accuracy of **1.0000**,
- Roman accuracy of **1.0000**,
- unit accuracy around **0.8350**,
- gravity accuracy around **0.7502**,
- near-zero text / bit / equation accuracy.

Interpretation:

- the current code has strong formatting discipline,
- deterministic numeric families are partially solved,
- the highest-value missing work is still in bit, text, and equation solving.

## How to compare experiments fairly

Use these rules:

1. **Never use checked-in `test.csv` for model selection.**
2. Compare the same evaluation script, same fold count, and same split definitions across runs.
3. Compare overall accuracy **and** per-family accuracy.
4. Track answer-format accuracy separately from exact-match accuracy.
5. If synthetic data is involved, keep validation rows real-only.
6. Prefer structure-aware metrics when deciding whether a change is robust.

## How to avoid misleading results or overfitting

Avoid these mistakes:

- treating the 3-row visible `test.csv` as meaningful validation,
- claiming improvement based only on format accuracy,
- over-weighting easy synthetic Roman/unit/gravity data and then calling the result a general benchmark gain,
- tuning repeatedly against the same split without recording what changed,
- ignoring leading zeros, decimal precision, or boxed-answer formatting.

---

## 8. Result interpretation

## How to tell whether the pipeline worked correctly

### Dataset/profile stage

Success signs:

- script runs without error,
- family counts sum to 9,500 train rows,
- visible test overlap is reported as 3/3,
- family distributions look close to the documented balanced six-family mix.

### Router stage

Success signs:

- top-level router accuracy is effectively 1.0 on checked-in data,
- equation subfamily accuracy is effectively 1.0,
- normalization policy is printed.

### Synthetic generation stage

Success signs:

- output CSV is created,
- row count matches the preset,
- family counts match requested families,
- only approved families are present.

### SFT data stage

Success signs:

- train/dev JSONL files are created,
- summary JSON is created,
- row counts in the summary match what you intended,
- synthetic rows are included only when requested.

### Packaging stage

Success signs:

- submission directory is created,
- `manifest.json` and `README_submission.md` are present,
- `.tar.gz` archive is created,
- config validation passes.

## What a “good” result looks like right now

Given current repo scope, a good result is:

- reproducible baseline evaluation output,
- generated synthetic data for the approved families,
- SFT JSONL files ready for an external trainer,
- a submission bundle that passes structural validation.

A “good” result is **not yet** a fully trained or leaderboard-optimized model, because the repo does not contain that implementation.

## Common failure patterns

- trying to use `test.csv` as validation,
- assuming there is already a training script,
- forgetting that synthetic rows are always train-only in SFT prep,
- misreading high format accuracy as high true reasoning accuracy,
- packaging an adapter config that does not reference Nemotron-3-Nano-30B,
- missing weight files when not using `--allow-missing-weight-file`.

## How to validate output files and logs

Useful checks:

```bash
python - <<'PY'
from pathlib import Path
for path in [
    Path('artifacts/synthetic/mvp_synthetic_train.csv'),
    Path('artifacts/sft/mixed_sft_boxed.summary.json'),
    Path('artifacts/submission/dryrun_adapter/manifest.json'),
]:
    print(path, path.exists())
PY
```

```bash
head -n 3 artifacts/synthetic/mvp_synthetic_train.csv
```

```bash
head -n 2 artifacts/sft/mixed_sft_boxed.train.jsonl
```

```bash
cat artifacts/sft/mixed_sft_boxed.summary.json
```

---

## 9. Submission / packaging guide

## What the final deliverable is supposed to be

Per repo instructions and packaging code, the final deliverable should be a:

- **Nemotron-3-Nano-30B-compatible LoRA adapter directory**, packaged for handoff,
- including `adapter_config.json`,
- and normally adapter weights in either:
  - `adapter_model.safetensors`, or
  - `adapter_model.bin`

## Packaging checks performed by the script

`python scripts/package_lora_submission.py` validates:

1. `adapter_config.json` exists,
2. adapter weights exist unless `--allow-missing-weight-file` is used,
3. `adapter_config.json["base_model_name_or_path"]` contains `Nemotron-3-Nano-30B` by default,
4. `adapter_config.json["peft_type"] == "LORA"`,
5. `adapter_config.json` includes `target_modules`.

## Nemotron / vLLM assumptions currently encoded

The packaging script writes a manifest and submission README that assume:

- the base model is Nemotron-3-Nano-30B,
- the adapter is loaded as a LoRA,
- inference returns one final boxed answer,
- answer formatting must preserve benchmark schema exactly.

## Pre-submission checklist

Before submission, verify:

- adapter directory contains the right config,
- weight file exists,
- base model string points at Nemotron-3-Nano-30B,
- output formatting contract is preserved,
- no extra text appears after `\boxed{answer}`,
- integer/sign/leading-zero preservation has been tested,
- decimal precision policy has been tested,
- package script succeeds without `--allow-missing-weight-file`.

## Packaging example

```bash
python scripts/package_lora_submission.py \
  --adapter-dir final_adapter \
  --output-dir artifacts/submission \
  --submission-name wonderland_final
```

Expected outputs:

- `artifacts/submission/wonderland_final/`
- `artifacts/submission/wonderland_final.tar.gz`

---

## 10. Troubleshooting

## Likely setup issues

### `python: command not found`

Use a valid Python 3.10+ installation and re-run.

### Missing CSV files

If `train.csv` or `test.csv` are absent, none of the benchmark scripts can run.

### No `artifacts/` directory yet

That is normal. The scripts create needed artifact subdirectories automatically.

## Likely script/runtime issues

### `prepare_sft_data.py` cannot find the synthetic CSV

Cause:

- the synthetic file was never generated,
- the path is wrong,
- or you launched SFT prep before synthetic generation finished.

Fix:

```bash
python scripts/generate_synthetic.py --preset mvp --output artifacts/synthetic/mvp_synthetic_train.csv
python scripts/prepare_sft_data.py --recipe mixed_sft --synthetic-path artifacts/synthetic/mvp_synthetic_train.csv --output-dir artifacts/sft
```

### Packaging fails with missing weight file

Cause:

- adapter weights are not present.

Fix:

- for a real submission, add the weight file,
- for a config-only validation run, use `--allow-missing-weight-file`.

### Packaging fails because base model name does not match

Cause:

- `adapter_config.json` does not mention Nemotron-3-Nano-30B.

Fix:

- correct the config,
- or override the substring check with `--expected-base-model` if you intentionally need a different string.

## Likely evaluation mistakes

- evaluating on `test.csv`,
- comparing runs with different fold counts,
- ignoring per-family breakdowns,
- not separating exact-match from formatting accuracy,
- claiming synthetic gains without keeping validation real-only.

## Likely formatting mistakes related to final answers

- emitting prose instead of only the answer,
- forgetting `\boxed{answer}` in the final generation contract,
- outputting lowercase Roman numerals,
- dropping trailing zeros on 2-decimal unit answers,
- trimming gravity precision incorrectly,
- removing leading zeros from equation outputs,
- inserting spaces into symbolic equation answers,
- returning a binary string with fewer than 8 bits.

---

## 11. Reproducibility checklist

For every serious run, save these items:

## Inputs

- exact `train.csv` and `test.csv` versions used,
- any synthetic CSV files used,
- adapter directory contents used for packaging.

## Commands

- exact shell commands run,
- Python version,
- any non-default flags.

## Artifacts to archive

- dataset profile JSON/text output,
- router evaluation output,
- baseline evaluation output,
- synthetic CSV files,
- SFT train/dev JSONL files,
- SFT summary JSON,
- packaged submission directory,
- packaged `.tar.gz` archive,
- manifest and submission README.

## Configs to pin

Even though the repo lacks a `configs/` directory, you should still pin:

- synthetic preset (`mvp` or `full`),
- selected synthetic families,
- stress fraction,
- SFT recipe,
- dev fraction,
- boxed vs plain targets,
- max synthetic per family cap,
- expected base model string for packaging.

## Evaluation settings to pin

- baseline name,
- number of folds,
- split strategy definitions,
- any answer normalization rules used downstream.

---

## 12. Recommended operating sequence

## Best practical order

This is the best repo-aligned order for a new engineer:

1. read `docs/dataset_forensics.md`, `docs/system_architecture.md`, and `docs/eval_plan.md`,
2. inspect `train.csv` and `test.csv` directly,
3. run `scripts/profile_dataset.py`,
4. run `scripts/build_router.py --skip-demo`,
5. run `scripts/eval_baselines.py --baseline solver_lite`,
6. generate approved synthetic data only if you are preparing SFT data,
7. run `scripts/prepare_sft_data.py` to produce JSONL files,
8. train a LoRA externally if you decide the benchmark evidence justifies it,
9. validate/package the trained adapter with `scripts/package_lora_submission.py`,
10. archive all artifacts and command logs.

## Quick MVP path

If you just want the minimal useful repo output:

```bash
python scripts/profile_dataset.py
python scripts/build_router.py --skip-demo
python scripts/eval_baselines.py --baseline solver_lite
```

That gives you the current benchmark profile, router status, and honest offline baseline.

## Fuller experiment path

If you want the fullest currently implemented path:

```bash
python scripts/profile_dataset.py --json > artifacts/profile.json
python scripts/build_router.py --skip-demo
python scripts/eval_baselines.py --baseline solver_lite
python scripts/generate_synthetic.py --preset mvp --output artifacts/synthetic/mvp_synthetic_train.csv
python scripts/prepare_sft_data.py --recipe mixed_sft --synthetic-path artifacts/synthetic/mvp_synthetic_train.csv --output-dir artifacts/sft
python scripts/package_lora_submission.py --adapter-dir path/to/adapter_dir --output-dir artifacts/submission --submission-name wonderland_nemotron_lora
```

This is the closest thing to "zero to result" that the current repo actually supports.

---

## Current gaps

The repo is useful, but it is not yet a complete competition system. Important missing pieces are:

1. **No training script** for LoRA fine-tuning.
2. **No inference runner** that loads a model or vLLM and generates benchmark answers.
3. **No `src/` solver modules** even though the docs describe them.
4. **No experiment config system** under `configs/` or `experiments/`.
5. **No unified end-to-end command** that goes from SFT JSONL to trained adapter to benchmark predictions.
6. **No real held-out test harness** beyond offline train-based evaluation.

So, today, the practical meaning of “run from zero to result” is:

- get to a trustworthy offline benchmark understanding,
- build SFT-ready data,
- and package a structurally valid LoRA adapter once one has been trained elsewhere.
