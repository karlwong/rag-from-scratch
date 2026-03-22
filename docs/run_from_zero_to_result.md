# Run from zero to result

This guide is the **user-facing execution runbook** for the current state of this repository. It covers what you can run today, what each script produces, and where the current repo still depends on external training/inference infrastructure.

If you prefer a runnable onboarding flow inside Jupyter, use `notebooks/run_full_pipeline.ipynb`. The notebook mirrors the implemented script workflow instead of inventing missing training or inference features.

## 1. What “result” means in this repo

This repository currently supports a **benchmark-analysis to submission-packaging workflow**, not a full train-and-serve stack.

### Implemented results you can produce now
- dataset profiling summaries from `scripts/profile_dataset.py`
- router validation reports from `scripts/build_router.py`
- offline baseline metrics from `scripts/eval_baselines.py`
- approved synthetic training rows from `scripts/generate_synthetic.py`
- chat-style SFT datasets from `scripts/prepare_sft_data.py`
- a validated submission bundle from `scripts/package_lora_submission.py`, **if you already have a Nemotron-compatible LoRA adapter directory**

### Not implemented in the checked-in repo
- LoRA training script
- vLLM inference launcher
- end-to-end hidden-test prediction runner
- solver modules under `src/` (the repo docs discuss them, but the current implementation keeps logic in `scripts/`)

### Key assumption
The project docs and `AGENTS.md` assume the eventual submission target is a **NVIDIA Nemotron-3-Nano-30B compatible LoRA adapter** loaded with **vLLM**. This runbook only documents the pieces that actually exist in the repository today.

---

## 2. Repo-specific prerequisites

## Required files already in the repo
- `train.csv`
- `test.csv`
- `scripts/profile_dataset.py`
- `scripts/build_router.py`
- `scripts/eval_baselines.py`
- `scripts/generate_synthetic.py`
- `scripts/prepare_sft_data.py`
- `scripts/package_lora_submission.py`

## Python
- Recommended: **Python 3.10+**
- Current scripts use only the **Python standard library**.
- There is **no** checked-in `requirements.txt`, `pyproject.toml`, or Conda environment file.

## System dependencies
- No GPU is needed for the implemented scripts.
- No CUDA, PyTorch, PEFT, or vLLM installation is needed for profiling, routing, evaluation, synthetic generation, SFT-data preparation, or packaging validation.
- A GPU stack becomes your responsibility only when you train or run a real Nemotron LoRA outside this repo's current checked-in workflow.

## Assumptions to keep in mind
- The visible `test.csv` is **not** a realistic validation set. Existing forensics show it overlaps fully with `train.csv`.
- The repo is optimized for **benchmark-specific reverse engineering and reproducible artifact preparation**, not generic LLM fine-tuning.
- Packaging assumes you already have an adapter directory containing at minimum `adapter_config.json`, and usually a weight file such as `adapter_model.safetensors` or `adapter_model.bin`.

---

## 3. Environment setup

Create and activate a local virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python --version
```

Because the repo has no external Python dependencies today, that is usually enough.

Optional sanity check:

```bash
python scripts/profile_dataset.py --help
python scripts/build_router.py --help
python scripts/eval_baselines.py --help
python scripts/generate_synthetic.py --help
python scripts/prepare_sft_data.py --help
python scripts/package_lora_submission.py --help
```

If those help commands run, the local CLI workflow is ready.

---

## 4. Inspect the dataset before doing anything major

The project instructions explicitly require direct dataset inspection before major recommendations or implementation work.

### Quick raw inspection

```bash
python - <<'PY'
import csv
from itertools import islice
for path in ["train.csv", "test.csv"]:
    print(f"\n== {path} ==")
    with open(path, newline="", encoding="utf-8") as handle:
        for row in islice(csv.reader(handle), 5):
            print(row)
PY
```

### Structured profiling

```bash
python scripts/profile_dataset.py
```

### Optional machine-readable profile

```bash
python scripts/profile_dataset.py --json > artifacts_profile.json
```

### What the current repo profile shows
At the time this guide was verified locally:
- `train.csv` had **9,500** rows.
- `test.csv` had **3** rows.
- All **3** visible test rows overlapped with train, so `test.csv` should be treated as a smoke-test sample, not a model-selection target.
- The training set split almost evenly across six families: `bit_transform`, `text_cipher`, `roman_numeral`, `unit_conversion`, `gravity`, and `equation_transform`.

### Why this step matters
The rest of the workflow assumes a six-family synthetic puzzle benchmark with short exact-match answers. That assumption is grounded in the data and the profiler, not just in narrative docs.

---

## 5. Understand the repo structure

### Top-level data
- `train.csv`: real labeled development data used for profiling, evaluation, and SFT-data creation.
- `test.csv`: tiny visible smoke-test file; do not use it for serious validation.

### `scripts/`
- `profile_dataset.py`: benchmark forensics and family statistics.
- `build_router.py`: rule-based family router evaluation and answer-normalization policy summary.
- `eval_baselines.py`: offline exact-match baselines on `train.csv` with random and structure-aware folds.
- `generate_synthetic.py`: approved synthetic generation for `roman_numeral`, `unit_conversion`, and `gravity` only.
- `prepare_sft_data.py`: converts real and optional synthetic rows to chat-style JSONL.
- `package_lora_submission.py`: validates and packages an adapter directory.

### `docs/`
The docs are part of the workflow, not just commentary:
- `docs/dataset_forensics.md`
- `docs/task_taxonomy.md`
- `docs/system_architecture.md`
- `docs/synthetic_data_plan.md`
- `docs/eval_plan.md`
- `docs/lora_plan.md`
- `docs/submission_checklist.md`
- `docs/experiment_backlog.md`
- `docs/work_plan.md`

### Output directories
The scripts write artifacts only when asked to do so. Typical output roots are:
- `artifacts/synthetic/`
- `artifacts/sft/`
- `artifacts/submission/`

If those directories do not exist yet, that is normal.

---

## 6. Baseline execution path: zero to first useful result

If you want the shortest honest workflow, run these three commands first.

### Step 1: profile the dataset

```bash
python scripts/profile_dataset.py
```

You should get a benchmark summary including family counts and answer schema counts.

### Step 2: validate the router

```bash
python scripts/build_router.py --skip-demo
```

What this does:
- evaluates the current hand-built router on a CSV, defaulting to `train.csv`
- reports top-level family accuracy
- reports equation subfamily routing accuracy
- prints the current final-answer normalization policy

What was observed during local verification:
- top-level routing accuracy: **1.0000**
- ambiguity-flag share: **0.0000**
- equation subfamily accuracy: **1.0000**

Interpretation:
- the checked-in router is a reliable dispatcher for the visible six-family benchmark structure
- this does **not** mean the benchmark is solved; it only means the task-family identification is easy on visible data

### Step 3: run the offline baseline

```bash
python scripts/eval_baselines.py --baseline solver_lite
```

What this does:
- scores a lightweight baseline on all `train.csv` rows
- reports both `stratified_random_hash` and `structure_aware_hash` metrics
- shows exact-match accuracy, answer-format accuracy, and per-family accuracy

What was observed during local verification:
- overall accuracy: **0.4336**
- answer-format accuracy: **1.0000**
- per-family accuracy:
  - `roman_numeral`: **1.0000**
  - `unit_conversion`: **0.8350**
  - `gravity`: **0.7502**
  - `bit_transform`: **0.0056**
  - `text_cipher`: **0.0000**
  - `equation_transform`: **0.0032**

Interpretation:
- the current baseline already solves the obvious deterministic family (`roman_numeral`) and partially solves `unit_conversion` and `gravity`
- the hard unsolved families remain `bit_transform`, `text_cipher`, and `equation_transform`
- perfect format accuracy means exact-match losses are coming from reasoning, not formatting, in this specific offline heuristic baseline

That baseline report is the repo's current “first useful result.”

---

## 7. Router and solver execution

This repo does **not** yet contain standalone solver modules under `src/`. The runnable family logic lives inside the evaluation and routing scripts.

### Current router execution

```bash
python scripts/build_router.py --skip-demo
```

### Optional router demo mode

```bash
python scripts/build_router.py --demo-limit 5
```

Use demo mode if you want example routes and confidence annotations printed to the terminal.

### Important limitation
There is **no** checked-in script that takes `test.csv`, runs a full family-specific solver stack, and emits final predictions for submission. The current repo supports:
- routing analysis
- baseline evaluation
- data preparation
- submission packaging

If you need a true prompt-to-prediction runner, that is future work implied by the architecture docs, not current functionality.

---

## 8. Synthetic data generation, when applicable

Synthetic generation is intentionally restricted.

### What is implemented
`scripts/generate_synthetic.py` only supports these approved families:
- `roman_numeral`
- `unit_conversion`
- `gravity`

### What is intentionally not implemented
No synthetic generator is currently exposed for:
- `bit_transform`
- `text_cipher`
- `equation_transform`

That restriction is deliberate and benchmark-specific; the docs treat those families as too risky to synthesize casually.

### Generate the MVP synthetic set

```bash
python scripts/generate_synthetic.py --preset mvp --output artifacts/synthetic/synthetic_train.csv
```

### Optional controls
- generate only selected families:

```bash
python scripts/generate_synthetic.py \
  --preset mvp \
  --families roman_numeral unit_conversion \
  --output artifacts/synthetic/synthetic_subset.csv
```

- change seed or stress fraction:

```bash
python scripts/generate_synthetic.py \
  --preset full \
  --seed 17 \
  --stress-fraction 0.20 \
  --output artifacts/synthetic/synthetic_full.csv
```

### What was observed during local verification
The `mvp` preset produced:
- **3,000** synthetic rows total
- `roman_numeral`: **600**
- `unit_conversion`: **1,200**
- `gravity`: **1,200**

### Output schema
The generated CSV contains:
- `id`
- `family`
- `synthetic_tier`
- `prompt`
- `answer`

### When to use this step
Use synthetic generation only if you plan to:
- prepare mixed SFT data, or
- inspect benchmark-faithful extra coverage for the approved families

If you only want profiling and baseline metrics, you can skip this stage.

---

## 9. SFT data preparation, when applicable

Use `scripts/prepare_sft_data.py` when you want training-ready JSONL from real data, or from real plus approved synthetic data.

### Supported recipes
- `original_sft`
- `mixed_sft`
- `family_conditioned`
- `format_stabilization`

### Common use cases

#### A. Real-only SFT data

```bash
python scripts/prepare_sft_data.py \
  --output-dir artifacts/sft \
  --recipe original_sft \
  --box-style boxed
```

#### B. Mixed real + synthetic SFT data

```bash
python scripts/prepare_sft_data.py \
  --synthetic-path artifacts/synthetic/synthetic_train.csv \
  --output-dir artifacts/sft \
  --recipe mixed_sft \
  --box-style boxed
```

#### C. Family-conditioned data

```bash
python scripts/prepare_sft_data.py \
  --synthetic-path artifacts/synthetic/synthetic_train.csv \
  --output-dir artifacts/sft \
  --recipe family_conditioned \
  --box-style boxed
```

### Useful guardrail options
- keep only certain families:

```bash
python scripts/prepare_sft_data.py \
  --output-dir artifacts/sft \
  --recipe original_sft \
  --family-filter roman_numeral unit_conversion gravity
```

- cap synthetic volume per family:

```bash
python scripts/prepare_sft_data.py \
  --synthetic-path artifacts/synthetic/synthetic_train.csv \
  --output-dir artifacts/sft \
  --recipe mixed_sft \
  --max-synthetic-per-family 200
```

### What the script writes
For a dataset name like `mixed_sft_boxed`, the output files are:
- `artifacts/sft/mixed_sft_boxed.train.jsonl`
- `artifacts/sft/mixed_sft_boxed.dev.jsonl`
- `artifacts/sft/mixed_sft_boxed.summary.json`

### What was observed during local verification
Using a synthetic input plus `--max-synthetic-per-family 5` produced a summary with:
- `train_rows`: **8573**
- `dev_rows`: **942**
- `sources.real`: **9500**
- `sources.synthetic`: **15**

### Important assumption
This script prepares **training data only**. It does **not** train an adapter. You must use your own training stack outside this repo to consume the JSONL.

---

## 10. Evaluation workflow

The checked-in repo's main evaluation script is `scripts/eval_baselines.py`.

### Baseline options
- `last_demo`
- `solver_lite`

### Run both baselines if you want a comparison

```bash
python scripts/eval_baselines.py --baseline last_demo
python scripts/eval_baselines.py --baseline solver_lite
```

### Control the number of folds

```bash
python scripts/eval_baselines.py --baseline solver_lite --num-folds 5
```

### How to read the outputs
Each run reports:
- overall accuracy
- answer-format accuracy
- per-family accuracy
- metrics for both split strategies:
  - `stratified_random_hash`
  - `structure_aware_hash`
- the random-vs-structure gap

### Recommended workflow for experiments
1. Keep `solver_lite` as the reference baseline.
2. If you change prompts, synthetic-data selection, or later add your own trainer, compare against this baseline on **real held-out rows**, not `test.csv`.
3. Watch the structure-aware split especially closely; the docs treat it as a better hidden-test proxy than naive random splitting.

### Important limitation
The repo does **not** include an evaluator for a trained adapter checkpoint. If you train outside the repo, you will need to write or add your own prediction-and-scoring loop.

---

## 11. Result interpretation

Use the outputs conservatively.

### Profiling results
These tell you:
- whether the benchmark still looks like the six known families
- whether answer schemas are stable
- whether visible data still supports the reverse-engineering assumptions in the docs

### Router results
A perfect router score means:
- the family labels are easy to recover from prompt structure
- routing is a viable design choice

It does **not** mean:
- the downstream solvers are good
- the hidden benchmark has no drift

### Baseline metrics
Interpret family accuracy directly:
- high `roman_numeral` confirms deterministic conversion is easy
- middling `unit_conversion` and `gravity` show numeric heuristics are partly right but not yet robust enough
- near-zero `bit_transform`, `text_cipher`, and `equation_transform` confirm the hardest work is still ahead

### Synthetic-data outputs
Synthetic rows are useful only if they stay benchmark-faithful. The current repo approves only the safest families; do not treat synthetic volume as progress by itself.

### SFT prep outputs
A generated JSONL file is **not** evidence that LoRA will help. It only means the repo has prepared benchmark-shaped training records for an external trainer.

### Submission packaging outputs
A successful package run means:
- directory structure and metadata passed local checks
- the bundle is ready for handoff

It does **not** prove:
- the adapter is good
- the adapter loads under your exact vLLM environment
- the adapter improves accuracy

---

## 12. Submission packaging

Use this step only when you already have an adapter directory.

### Minimum expected adapter contents
Required:
- `adapter_config.json`

Usually required in a real submission:
- `adapter_model.safetensors` or `adapter_model.bin`

### Package a real adapter

```bash
python scripts/package_lora_submission.py \
  --adapter-dir /path/to/adapter_dir \
  --output-dir artifacts/submission \
  --submission-name wonderland_nemotron_lora
```

### Dry-run validation for config-only inspection
If you only want to validate packaging structure before weights exist:

```bash
python scripts/package_lora_submission.py \
  --adapter-dir /path/to/adapter_dir \
  --output-dir artifacts/submission \
  --submission-name wonderland_nemotron_lora \
  --allow-missing-weight-file
```

### What the script validates
- `adapter_config.json` exists
- `base_model_name_or_path` contains the expected Nemotron identifier
- `peft_type` is `LORA`
- `target_modules` exists
- a weight file exists, unless `--allow-missing-weight-file` is used

### What the script writes
Under `artifacts/submission/<submission-name>/`:
- copied adapter files
- `README_submission.md`
- `manifest.json`

It also creates:
- `artifacts/submission/<submission-name>.tar.gz`

### Assumption to label clearly
The packaging script is a **validator and bundler**, not a trainer. If the adapter directory is wrong, packaging will fail; if the adapter is weak, packaging can still succeed.

---

## 13. Troubleshooting

### `python: command not found` or wrong Python version
Use a Python 3.10+ interpreter explicitly, for example:

```bash
python3 --version
python3 scripts/profile_dataset.py
```

### `test.csv` looks too easy
That is expected. The checked-in `test.csv` is a smoke-test sample and overlaps with train. Do not use it as your main validation target.

### `prepare_sft_data.py` fails because a synthetic file is missing
Make sure the synthetic CSV exists first:

```bash
python scripts/generate_synthetic.py --preset mvp --output artifacts/synthetic/synthetic_train.csv
```

Then rerun SFT prep using the same path.

### Packaging fails with `missing required file: adapter_config.json`
Your adapter directory is incomplete. Add `adapter_config.json` before rerunning.

### Packaging fails because the base model name is wrong
Check `adapter_config.json` and ensure `base_model_name_or_path` clearly references `Nemotron-3-Nano-30B` or pass a different `--expected-base-model` only if you truly changed the target.

### Packaging fails because weights are missing
That is expected for a config-only dry run. Re-run with:

```bash
python scripts/package_lora_submission.py ... --allow-missing-weight-file
```

Only do this for validation smoke tests, not for the final submission bundle.

### You expected end-to-end model training in this repo
That functionality is not checked in yet. Use the docs and data-prep outputs here, then train with your external stack.

### You expected direct hidden-test inference in this repo
That functionality is also not checked in yet. The current repo stops at offline analysis, data prep, and adapter packaging.

---

## 14. Reproducibility checklist

Use this checklist every time you run the workflow.

### Environment
- [ ] Record Python version.
- [ ] Run from the repo root.
- [ ] Use a clean virtual environment when comparing experiments.

### Data
- [ ] Do not overwrite `train.csv` or `test.csv`.
- [ ] Inspect `train.csv` and `test.csv` directly before major changes.
- [ ] Treat visible `test.csv` as a smoke test only.

### Scripts
- [ ] Capture the exact CLI commands you ran.
- [ ] Record any non-default flags such as `--preset`, `--seed`, `--family-filter`, or `--max-synthetic-per-family`.
- [ ] Save generated artifacts under stable paths like `artifacts/synthetic`, `artifacts/sft`, and `artifacts/submission`.

### Evaluation
- [ ] Compare against the baseline from `python scripts/eval_baselines.py --baseline solver_lite`.
- [ ] Review both random and structure-aware split metrics.
- [ ] Interpret per-family scores, not just overall accuracy.

### Packaging
- [ ] Validate `adapter_config.json` before packaging.
- [ ] Confirm the adapter is actually Nemotron-compatible.
- [ ] Inspect the generated `manifest.json` and archive contents.

### Provenance
- [ ] Record the git commit used to generate artifacts.
- [ ] Record whether synthetic rows were included.
- [ ] Record the exact SFT recipe if you prepared training data.
- [ ] Record any assumptions you made beyond the checked-in scripts.

---

## 15. Recommended next step after following this guide

After you can run the baseline workflow end to end, the highest-value next step is **not** generic fine-tuning. It is to improve the benchmark-specific logic for the unsolved families, especially:
1. `bit_transform`
2. `text_cipher`
3. `equation_transform`

If you do decide to explore LoRA, the repo's current docs recommend starting with **minimal format-stabilization or mixed approved-family SFT data**, then validating on real held-out rows rather than the visible `test.csv`.
