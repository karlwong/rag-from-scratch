# AGENTS.md

## Mission
Build a competition-grade solution for a reasoning benchmark evaluated on hidden test prompts using NVIDIA Nemotron-3-Nano-30B with a compatible LoRA adapter.

## Competition facts
- Input files:
  - train.csv with columns: id, prompt, answer
  - test.csv with columns: id, prompt
- Final submission must be a Nemotron-3-Nano-30B compatible LoRA adapter
- adapter_config.json must be included
- Inference uses vLLM
- Evaluation extracts the final answer, prioritizing content inside \boxed{}
- Correctness is based on exact string match or allowed numeric tolerance
- Single-pass inference matters more than verbose reasoning

## Working assumptions
- Treat this benchmark as a deterministic or semi-deterministic puzzle benchmark unless evidence disproves it
- Reverse-engineering the puzzle families is mandatory before proposing training
- Prompt-only, routing, solver design, synthetic data, and lightweight LoRA should all be considered
- Generic fine-tuning is not the default answer

## Core objectives
1. Maximize hidden-test accuracy
2. Maximize single-pass correctness
3. Minimize output-format failures
4. Avoid hidden-test overfitting
5. Produce concrete docs, scripts, and reproducible experiments

## Required engineering behavior
1. Always inspect train.csv and test.csv directly before making major recommendations
2. Write benchmark-specific findings, not generic ML advice
3. Prefer small, verifiable deliverables in each step
4. Before major implementation work, write or update a short plan in docs/
5. Save artifacts to files, not only chat responses
6. Use reproducible Python scripts for profiling, routing, evaluation, and packaging
7. Never overwrite the original CSV files
8. State assumptions explicitly when uncertain
9. Rank recommendations by expected leaderboard gain vs effort vs overfitting risk
10. Verify scripts run before declaring completion

## Expected benchmark angle
The likely winning strategy is some combination of:
- dataset reverse-engineering
- family taxonomy and routing
- family-specific solver logic
- benchmark-faithful synthetic data
- prompt and output-format optimization
- minimal useful LoRA
This should be tested, not assumed.

## Required deliverables
Codex should gradually produce these files as the staged prompts progress:

### Docs
- docs/dataset_forensics.md
- docs/task_taxonomy.md
- docs/system_architecture.md
- docs/synthetic_data_plan.md
- docs/eval_plan.md
- docs/lora_plan.md
- docs/submission_checklist.md
- docs/experiment_backlog.md

### Scripts
- scripts/profile_dataset.py
- scripts/build_router.py
- scripts/eval_baselines.py
- scripts/generate_synthetic.py
- scripts/prepare_sft_data.py
- scripts/package_lora_submission.py

### Optional source modules
- src/router.py
- src/solvers.py
- src/normalization.py
- src/inference_prompt.py
- src/validation.py

## Quality gates
A task is not done unless:
- requested files were created
- reasoning is benchmark-specific
- scripts run successfully or the failure is clearly explained
- recommendations include risks and fallback options
- final-answer formatting considerations are explicitly handled

## Output preferences
When replying in chat:
- be concise and decisive
- summarize what was created
- summarize what was learned
- state risks or unknowns
- state the next highest-value step
