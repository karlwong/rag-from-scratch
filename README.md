# rag-from-scratch

A benchmark-analysis and LoRA-packaging workspace for the Wonderland-style reasoning competition described in `AGENTS.md`. The repo is currently built to help you inspect the dataset, route prompts into puzzle families, run offline baselines, generate approved synthetic data, prepare SFT datasets, and package an existing Nemotron-compatible LoRA adapter for submission. It does **not** yet include a checked-in trainer, inference server, or end-to-end hidden-test submission runner. See the full runbook in [`docs/run_from_zero_to_result.md`](docs/run_from_zero_to_result.md).

## Repo structure

- `train.csv` / `test.csv` - checked-in benchmark data used for profiling and offline workflow smoke tests.
- `scripts/` - runnable utilities for profiling, routing, evaluation, synthetic generation, SFT prep, and submission packaging.
- `docs/` - benchmark forensics, architecture notes, planning docs, and the full runbook.
- `artifacts/` - created on demand by scripts for synthetic data, SFT data, and packaged submissions.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python scripts/profile_dataset.py
python scripts/build_router.py --skip-demo
python scripts/eval_baselines.py --baseline solver_lite
```

What to expect:
- `profile_dataset.py` summarizes the checked-in dataset and confirms the visible `test.csv` is only a tiny smoke-test sample.
- `build_router.py` verifies the current rules-based family router.
- `eval_baselines.py` gives the current offline reference point before any new solver or LoRA work.

## Full execution guide

For the full zero-to-result workflow, including synthetic generation, SFT prep, evaluation interpretation, submission packaging, troubleshooting, and reproducibility, use [`docs/run_from_zero_to_result.md`](docs/run_from_zero_to_result.md).
