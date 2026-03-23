# rag-from-scratch

A benchmark-analysis and LoRA-packaging workspace for the Wonderland-style reasoning competition described in `AGENTS.md`. The repo is currently built to help you inspect the dataset, route prompts into puzzle families, run offline baselines, generate approved synthetic data, prepare SFT datasets, package an existing Nemotron-compatible LoRA adapter for submission, and now run that checked-in workflow end to end from Jupyter via `notebooks/run_full_pipeline.ipynb`, including a Kaggle-friendly self-contained mode that writes the required script files into `/kaggle/working/` at runtime.

## Repo structure

- `train.csv` / `test.csv` - checked-in benchmark data used for profiling and offline workflow smoke tests.
- `scripts/` - runnable utilities for profiling, routing, evaluation, synthetic generation, SFT prep, and submission packaging.
- `docs/` - benchmark forensics, architecture notes, planning docs, the CLI runbook, and onboarding guidance.
- `notebooks/` - notebook-based execution path for new engineers.
- `artifacts/` - created on demand by scripts or the notebook for profiles, synthetic data, SFT data, and packaged submissions.

## Quick start

### CLI path

```bash
python -m venv .venv
source .venv/bin/activate
python scripts/profile_dataset.py
python scripts/build_router.py --skip-demo
python scripts/eval_baselines.py --baseline solver_lite
```

### Notebook path

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip notebook
jupyter notebook notebooks/run_full_pipeline.ipynb
```

Kaggle notebook path: attach the competition dataset and open `notebooks/run_full_pipeline.ipynb`; the notebook will detect Kaggle automatically, copy `train.csv` / `test.csv` into `/kaggle/working/rag-from-scratch/`, and materialize the checked-in workflow scripts there so no separate `.py` upload is needed.

What to expect:
- `profile_dataset.py` summarizes the checked-in dataset and confirms the visible `test.csv` is only a tiny smoke-test sample.
- `build_router.py` verifies the current rules-based family router.
- `eval_baselines.py` gives the current offline reference point before any new solver or LoRA work.
- `notebooks/run_full_pipeline.ipynb` walks a new engineer through the same workflow end to end, including synthetic-data generation, SFT prep, evaluation interpretation, and optional submission packaging.

## Full execution guide

For the full zero-to-result workflow, use either:
- [`notebooks/run_full_pipeline.ipynb`](notebooks/run_full_pipeline.ipynb) for a runnable notebook onboarding path, or
- [`docs/run_from_zero_to_result.md`](docs/run_from_zero_to_result.md) for the CLI-first runbook.
