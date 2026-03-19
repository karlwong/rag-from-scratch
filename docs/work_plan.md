# Work plan

## Current stage: user-facing execution guide and repo entry point
1. Re-read the benchmark forensics, taxonomy, architecture notes, existing scripts, and direct `train.csv` / `test.csv` samples before documenting the runnable workflow.
2. Audit every checked-in script for real CLI arguments, output paths, and current limitations so the guide stays repo-specific and does not invent missing training/inference features.
3. Rewrite `docs/run_from_zero_to_result.md` as the end-to-end runbook covering setup, profiling, routing, synthetic generation, SFT prep, evaluation, result interpretation, packaging, troubleshooting, and reproducibility.
4. Add a short `README.md` that explains project purpose, repo structure, quick start, and points users to the full runbook.
5. Verify the documented commands run successfully in the current environment, then commit the docs update and prepare PR metadata.
