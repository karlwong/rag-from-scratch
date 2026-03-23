# Work plan

## Current stage: notebook baseline-matrix offline evaluation update
1. Re-read the benchmark forensics, taxonomy, architecture notes, existing scripts, and direct `train.csv` / `test.csv` samples before changing the notebook workflow.
2. Audit the notebook's offline evaluation, artifact checklist, and reproducibility sections so the update stays aligned with the checked-in CLI behavior in `scripts/eval_baselines.py`.
3. Replace the single-baseline notebook evaluation with a fixed-fold baseline matrix that runs at least `last_demo` and `solver_lite`, writes separate reports, and parses them into a structured comparison object.
4. Render a compact side-by-side comparison table that preserves split names, overall accuracy, answer-format accuracy, and per-family accuracy without changing the split strategy or fold count between runs.
5. Validate the notebook JSON after editing, then review the diff, commit the changes, and prepare PR metadata.
