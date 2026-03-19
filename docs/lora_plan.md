# LoRA plan

## Executive recommendation
The benchmark evidence still argues **against defaulting to broad LoRA training**. Four of the six visible families look deterministic or near-deterministic, and the hardest remaining mass is concentrated in `bit_transform`, `text_cipher`, and especially `equation_transform`. That means the most useful LoRA here is **small, format-focused, and benchmark-conditioned**, not generic instruction tuning.

My current recommendation is:
1. keep a strong **prompt-only / solver-first baseline** as the control,
2. test a **minimal LoRA that teaches terse boxed-answer emission plus benchmark surface style**,
3. only scale to mixed real+synthetic or family-conditioned LoRA if real-only validation shows non-trivial gains on the unsolved families,
4. stop immediately if LoRA gains are format-only and do not improve exact match on real held-out rows.

## Assumptions and evidence base
This recommendation is based on the current repository evidence:
- `train.csv` has 9,500 labeled rows spread almost evenly across six synthetic-looking families.
- The checked-in `test.csv` is only a 3-row train-overlap smoke sample, so it is not suitable for model selection.
- `roman_numeral`, `unit_conversion`, and `gravity` already appear solvable with deterministic logic.
- `bit_transform`, `text_cipher`, and `equation_transform` remain the real uncertainty buckets.
- Exact symbolic formatting is disproportionately important because answers are usually one short string, integer, decimal, Roman numeral, or lowercase phrase.

## Option comparison for this benchmark

| Option | Expected gain | Effort | Overfitting risk | When it helps | Why it may fail | Recommendation |
|---|---:|---:|---:|---|---|---|
| Prompt-only | High baseline ROI | Low | Low | When deterministic families dominate and prompt constraints stabilize output | May not fix brittle emission or ambiguous symbolic families | **Must be baseline** |
| Original-train SFT | Low to medium | Medium | Medium | If the base model already has latent capability and mostly needs style adaptation | Can waste capacity re-learning easy families and overfit template phrasing | **Test only as a small control** |
| Original + synthetic SFT | Medium | Medium | Medium-high | If synthetic rows are benchmark-faithful and focus on approved families / formatting | Safe synthetic families are mostly easy ones, so gains may be narrow | **Best LoRA candidate after prompt-only** |
| Family-conditioned SFT | Medium-high | Medium | Medium | If routing is available and the model benefits from explicit family priors at inference | Extra control tokens may not match hidden-test usage unless the router is reliable | **Best 1-2 week stretch LoRA** |
| Answer-format stabilization tuning | Medium for exact-match uplift, low for reasoning uplift | Low | Low-medium | When the model already gets latent reasoning mostly right but drops formatting or verbosity | Can become pure cosmetic tuning with no real problem-solving gain | **Best 48-hour LoRA MVP** |

## Detailed take on each option

### 1. Prompt-only
**Role:** mandatory baseline and probably the highest ROI starting point.

Why it fits this benchmark:
- deterministic families likely do not need training,
- the benchmark rewards single-pass final answers rather than long reasoning,
- prompt work can directly enforce `\boxed{answer}` and schema discipline.

Expected use:
- establish a clean baseline with answer-only prompting,
- pair with solver and normalization logic before touching LoRA,
- use it as the control for every later training experiment.

Decision:
- **Do this first and keep it as the comparison anchor.**

### 2. Original-train SFT
**Role:** low-cost check on whether the base model mainly needs benchmark adaptation.

Potential upside:
- may teach the model the benchmark narration and short-answer style,
- may stabilize outputs for families where the model already infers the rule but talks too much,
- uses only real data, so it avoids synthetic-generator mistakes.

Main risks:
- the model may mostly memorize surface templates rather than learn the latent generators,
- easy deterministic families may dominate the loss and hide whether hard families improved,
- exact-match gains may be small relative to a better inference contract.

Decision:
- **Run only one small original-train SFT control, not a broad sweep.**

### 3. Original + synthetic SFT
**Role:** best practical LoRA path if prompt-only is not enough.

Why it can help:
- we already have reasonably safe synthetic plans for `roman_numeral`, `unit_conversion`, and `gravity`,
- synthetic rows can teach compact answer emission and boundary formatting,
- mixed training is safer than synthetic-only because the real benchmark style still anchors the model.

Main risks:
- synthetic support is strongest for the easier families, not the hardest ones,
- too much synthetic volume could distort family balance,
- gains may come mostly from formatting, not latent reasoning.

Decision:
- **Recommended as the smallest useful expansion beyond original-only SFT.**
- Start with the MVP synthetic package already proposed in the repo: 600 Roman + 1,200 unit + 1,200 gravity.

### 4. Family-conditioned SFT
**Role:** strongest medium-horizon LoRA design if routing is reliable.

What it means here:
- prepend a family tag such as `[family=gravity]` to the user prompt during training,
- teach the adapter to obey family-specific answer-schema expectations,
- optionally use the router at inference to add the same family tag before prompting.

Why it fits this benchmark:
- the benchmark is unusually routeable from lexical markers,
- the families have very different output contracts,
- one small adapter may benefit from explicit family disambiguation.

Main risks:
- it depends on routing quality and inference-time control-token consistency,
- family tags do not solve the hardest latent-rule search problem by themselves,
- it adds one more moving piece to final submission.

Decision:
- **Best 1-2 week stretch LoRA if the 48-hour MVP shows LoRA signal at all.**

### 5. Answer-format stabilization tuning
**Role:** minimal useful LoRA.

What it should train:
- always emit exactly one final answer,
- prefer `\boxed{answer}`,
- avoid any trailing prose,
- preserve family-specific schema such as binary width, Roman uppercase, fixed decimals, lowercase text, and leading zeros.

Why this is unusually valuable here:
- the benchmark's answers are extremely short,
- one format mistake can turn a solved item into an incorrect exact match,
- this objective can improve single-pass behavior without pretending to teach all latent reasoning families.

Decision:
- **Single best LoRA MVP for the next 48 hours.**

## Recommended smallest experiment set with highest ROI

### Minimal experiment ladder
Ranked by expected gain per unit effort.

1. **Prompt-only control**
   - No LoRA.
   - Use the final output contract below.
   - Purpose: determine whether prompt tightening alone already solves most formatting failures.

2. **Format-stabilization LoRA on real rows**
   - Train on original `train.csv` only.
   - Targets are boxed final answers only.
   - No chain-of-thought, no rationale targets.
   - Purpose: test whether a tiny adapter improves exact-match via emission discipline.

3. **Mixed real + approved synthetic LoRA**
   - Add only approved synthetic families: `roman_numeral`, `unit_conversion`, `gravity`.
   - Keep synthetic ratio modest.
   - Purpose: improve answer contract reliability and numeric boundary coverage.

4. **Family-conditioned mixed LoRA**
   - Same data as #3, but with explicit family tags.
   - Only proceed if #3 beats #2 on real held-out rows.

### Explicitly *not* recommended in the first wave
- large unconditioned LoRA sweeps,
- synthetic augmentation for `bit_transform`, `text_cipher`, or `equation_transform`,
- rationale-rich SFT targets,
- high-rank / high-epoch training before proving any LoRA signal.

## Single best 48-hour MVP
**Answer-format stabilization LoRA trained on original `train.csv`, with boxed-answer-only targets and no reasoning traces.**

Why this is the best 48-hour MVP:
- lowest implementation risk,
- directly aligned with exact-match failure modes,
- uses only real benchmark rows,
- provides a clean read on whether LoRA is helping beyond prompt-only prompting.

Suggested run shape:
- recipe: `format_stabilization`,
- data: all real rows, boxed targets,
- adapter: lightweight LoRA only,
- evaluation: real-only random + structure-aware folds,
- success condition: exact-match gain on real validation with equal or better format accuracy on every family.

## Single best 1-2 week stretch solution
**Router-assisted family-conditioned mixed SFT, plus deterministic solvers for Roman/unit/gravity and strong formatting normalization.**

Why this is the best stretch solution:
- it combines the benchmark's strongest observed bias—family separability—with minimal adapter scope,
- it lets the adapter specialize in family-specific answer schemas while solvers handle deterministic families,
- it leaves room to plug in solver-derived synthetic data later if bit/text/equation generators become better understood.

Stretch architecture:
1. rules-based router,
2. deterministic solvers where available,
3. family-conditioned prompt wrapper for remaining LM calls,
4. small LoRA trained on real + approved synthetic rows with boxed-answer targets,
5. strict answer normalizer and extractor.

## Stop/go criteria: is LoRA actually worth using?

### Go criteria
Proceed with LoRA only if at least one of these is true on **real held-out validation**:
1. overall exact match improves by a meaningful margin over prompt-only,
2. gains appear in hard or unsolved families rather than only easy deterministic families,
3. answer-format accuracy improves without reducing structure-aware exact match,
4. single-pass boxed-answer compliance becomes materially more reliable.

### Stop criteria
Do **not** use LoRA in the final stack if any of these hold:
1. gains are only cosmetic formatting gains with no exact-match improvement,
2. improvements appear on random splits but disappear on structure-aware splits,
3. original-only SFT and mixed SFT both fail to beat prompt-only materially,
4. LoRA hurts any solver-dominated family by encouraging verbose or schema-breaking outputs,
5. the adapter introduces instability in boxed-answer emission or vLLM loading.

### Practical go/no-go rule
- **Go** if format-stabilization LoRA beats prompt-only by enough to matter and remains stable across both split types.
- **Stop** if the gain is within noise or concentrated only in formatting metrics.

## Training-data preparation approach

### Core principle
Prepare data to teach **benchmark-faithful final answers**, not generic reasoning prose.

### Data sources
1. **Real rows:** all of `train.csv`.
2. **Optional synthetic rows:** only approved high-confidence synthetic data for `roman_numeral`, `unit_conversion`, and `gravity`.
3. **No synthetic rows** for `bit_transform`, `text_cipher`, or `equation_transform` until their latent generators are validated.

### Record format
Each SFT example should be a 3-message chat record:
- `system`: benchmark-specific instruction to infer silently and output only one boxed answer,
- `user`: raw prompt, optionally prefixed with a family tag for family-conditioned experiments,
- `assistant`: target string only, ideally `\boxed{answer}`.

### Recommended recipes
1. **`original_sft`**
   - real rows only,
   - raw prompt,
   - boxed target.
2. **`mixed_sft`**
   - real rows + approved synthetic rows,
   - no family tag,
   - boxed target.
3. **`family_conditioned`**
   - same mix as above,
   - user message starts with `[family=...]`,
   - boxed target.
4. **`format_stabilization`**
   - real rows, optionally plus approved synthetic,
   - explicit user reminder to return only a boxed final answer,
   - boxed target.

### Split policy
- Keep a stable real-only dev split via hashed `id`.
- Keep synthetic rows in train only.
- Do not let synthetic data dominate the dev signal.

### Sampling policy
- Real rows always included.
- Synthetic rows capped per family in early runs.
- Avoid over-weighting easy families; mixed SFT should not flood the adapter with Roman/unit/gravity just because they are easiest to generate.

## Exact inference-output contract for final answers
This should be treated as **non-negotiable**.

### Contract
1. Return exactly one final answer.
2. The **final non-whitespace text** must be `\boxed{answer}`.
3. Do not include any explanation before or after the boxed answer in the final submission configuration.
4. Preserve the family-specific schema exactly:
   - `bit_transform`: `\boxed{01010101}` with exactly 8 bits,
   - `text_cipher`: `\boxed{queen sees castle}` in lowercase words only,
   - `roman_numeral`: `\boxed{XLII}` uppercase only,
   - `unit_conversion`: `\boxed{12.30}` with exactly 2 decimals,
   - `gravity`: `\boxed{14.7}` or `\boxed{14.70}` according to prompt-consistent precision,
   - `equation_transform`: `\boxed{003}` or `\boxed{-7}` or `\boxed{@!#}` preserving exact characters.
5. Never include units such as `m`, `meters`, or explanatory text like `The answer is`.
6. Never output multiple boxes.
7. Never append punctuation after the closing brace.

### Why boxed answers matter
The competition explicitly prioritizes extracting the final answer from `\boxed{}` when present. Using a single boxed answer gives the cleanest extraction path and minimizes parsing ambiguity.

## Recommended adapter scope
The minimal useful adapter should aim to learn:
- terse benchmark-conditioned decoding,
- reliable `\boxed{}` emission,
- family-specific schema obedience,
- no extra prose.

It should **not** be expected to replace deterministic solvers or fully solve the latent symbolic families by itself.

## Operational recommendation summary
1. Keep prompt-only as the baseline.
2. Run one tiny **format-stabilization LoRA** on real rows.
3. If helpful, expand to **mixed real + approved synthetic**.
4. If still helpful, test **family-conditioned mixed LoRA**.
5. Stop if gains are not robust on real-only held-out evaluation.
