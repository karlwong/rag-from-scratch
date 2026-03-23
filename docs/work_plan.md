# Work plan

## Current stage: notebook experiment-ladder expansion
1. Re-read the benchmark forensics, LoRA/eval docs, existing scripts, and direct `train.csv` / `test.csv` samples before changing the notebook workflow.
2. Audit notebook sections 5.4, 5.5, the results-inspection cell, reproducibility notes, and the Definition of Success so the update stays aligned with the checked-in CLI behavior in `scripts/generate_synthetic.py` and `scripts/prepare_sft_data.py`.
3. Replace the single MVP synthetic path with a loop that materializes the full documented synthetic ladder (`none`, `mvp`, `full`) and records explicit artifact metadata.
4. Replace the single mixed-SFT run with the documented recipe matrix across `original_sft`, `mixed_sft`, `family_conditioned`, and `format_stabilization`, including only the boxed/plain variants that the docs explicitly call for.
5. Render a notebook summary table that records synthetic source, recipe, box style, synthetic cap, output path, and train/dev row counts for every generated dataset.
6. Update the success criteria and saved-artifact checklist to require the full experiment ladder, then validate the notebook JSON, review the diff, commit the changes, and prepare PR metadata.
