# Work plan

## Current stage: notebook-based execution path and onboarding flow
1. Re-read the benchmark forensics, taxonomy, architecture notes, existing scripts, and direct `train.csv` / `test.csv` samples before documenting the runnable workflow.
2. Audit every checked-in script for real CLI arguments, output paths, and current limitations so the notebook stays repo-specific and does not invent missing training/inference features.
3. Build `notebooks/run_full_pipeline.ipynb` as the top-to-bottom Jupyter path covering setup, repo discovery, profiling, router validation, baseline evaluation, approved synthetic generation, SFT-data preparation, optional submission packaging, evaluation interpretation, troubleshooting, and reproducibility.
4. Update repo entry points so new engineers can discover both the notebook path and the CLI-first runbook quickly.
5. Verify the documented commands and notebook-facing paths run successfully in the current environment, then commit the update and prepare PR metadata.
