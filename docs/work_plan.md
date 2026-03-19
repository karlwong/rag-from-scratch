# Work plan

1. Re-read the benchmark forensics, taxonomy, router architecture notes, and direct `train.csv` samples to keep the synthetic-data and evaluation design benchmark-specific.
2. Define a selective augmentation policy that only green-lights families with high-confidence latent generators and explicitly blacklists risky families from synthetic expansion.
3. Write `docs/synthetic_data_plan.md` and `docs/eval_plan.md` with family-specific usefulness, hidden-test-safe validation splits, answer-format checks, and ablation priorities.
4. Implement `scripts/generate_synthetic.py` for the approved high-confidence generators and `scripts/eval_baselines.py` for reproducible offline baseline evaluation.
5. Run both scripts, inspect outputs for schema correctness, then commit the changes and prepare PR metadata.
