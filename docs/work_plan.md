# Work plan

## Current stage: Kaggle-self-contained notebook execution path
1. Re-read the benchmark forensics, taxonomy, architecture notes, existing scripts, and direct `train.csv` / `test.csv` samples before changing the notebook workflow.
2. Audit every checked-in script for real CLI arguments, output paths, and current limitations so the notebook stays repo-specific and does not invent missing training or inference features.
3. Make `notebooks/run_full_pipeline.ipynb` runnable in Kaggle without extra uploaded Python files by embedding the checked-in script sources and materializing them into `/kaggle/working/` at runtime.
4. Keep the local-repo execution path working so the same notebook still runs unchanged for repository users outside Kaggle.
5. Verify the notebook-facing workflow in both local and simulated Kaggle-style environments, then commit the update and prepare PR metadata.
