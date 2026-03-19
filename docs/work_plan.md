# Work plan

1. Re-read `docs/dataset_forensics.md`, `docs/task_taxonomy.md`, and direct `train.csv` / `test.csv` samples to ground the routing architecture in benchmark-specific evidence.
2. Design a two-stage benchmark router: top-level family routing plus targeted sub-routing for equation transforms and text-output grammar shape.
3. Implement `scripts/build_router.py` as a reproducible rule-based router with confidence scoring, ambiguity flags, and a train-set routing evaluation path.
4. Write `docs/system_architecture.md` covering routing decisions, family-specific solver strategies, normalization rules, fallback behavior, and failure risks.
5. Run the router script, inspect the train-set evaluation output, then commit the changes and prepare a PR summary.
