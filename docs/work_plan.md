# Work plan

## Current stage: minimal useful LoRA and submission packaging
1. Re-read the benchmark forensics, taxonomy, architecture notes, existing scripts, and direct `train.csv` / `test.csv` samples before recommending any LoRA work.
2. Compare prompt-only, original-only SFT, mixed real+synthetic SFT, family-conditioned SFT, and answer-format-only tuning against the observed six-family benchmark structure.
3. Write `docs/lora_plan.md` and `docs/submission_checklist.md` with a benchmark-specific minimal-LoRA recommendation, explicit stop/go gates, final answer contract, and vLLM-compatible submission QA.
4. Implement `scripts/prepare_sft_data.py` to build reproducible SFT JSONL datasets from real rows plus optional approved synthetic rows, including family tags and boxed-answer targets.
5. Implement `scripts/package_lora_submission.py` to validate Nemotron-compatible adapter contents, emit a packaging manifest, and bundle a submission directory for handoff.
6. Run both scripts in verification mode, then commit the changes and prepare PR metadata.
