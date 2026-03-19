# Evaluation plan

## Evaluation objective
The offline evaluation stack should estimate hidden-test performance honestly enough to answer three questions:
1. Are we actually improving exact-match accuracy on untouched real rows?
2. Are gains concentrated in the intended families rather than coming only from format compliance?
3. Are we overfitting to the visible benchmark distribution or to our own synthetic assumptions?

The visible `test.csv` is unusable as a serious validation target because it is just a tiny leaked train subset. All meaningful evaluation should happen inside `train.csv` with carefully designed real-only validation splits.

## Core evaluation principles
- **Never score model selection on the checked-in `test.csv`.**
- **Keep a permanently untouched real validation pool.**
- **Measure exact match and format compliance separately.**
- **Use at least one structure-aware split in addition to a random split.**
- **Judge synthetic data only on real held-out rows, never on synthetic validation rows.**

## Split strategy

### Split 1: stratified random hash split
Purpose: estimate in-distribution generalization while preserving family balance.

Implementation:
- assign rows to folds using a stable hash of `id`,
- preserve family balance approximately through the naturally balanced dataset,
- use 5 folds and report mean metrics across folds.

Why we need it:
- it gives a low-variance estimate of baseline model quality,
- it is useful for comparing prompt or normalization changes that should generalize broadly.

### Split 2: structure-aware hash split
Purpose: estimate robustness to prompt-generator drift inside each family.

Implementation idea:
- build a family-specific structure signature,
- hash the structure signature rather than the row id,
- assign the resulting bucket to one of 5 folds.

Recommended structure signatures:
- `roman_numeral`: target decade + example count + whether the target is a Roman-boundary number.
- `unit_conversion`: slope bin + example count + query-value bin.
- `gravity`: `g` bin + example count + query-time bin + observed precision profile.
- `text_cipher`: answer length + example count + query token count.
- `bit_transform`: example count + query Hamming-weight bin.
- `equation_transform`: numeric-vs-symbolic branch + operator token or punctuation class + answer kind.

Why this matters:
- random splits can leak generator patterns too easily,
- structure-aware folds provide a harsher but more honest proxy for hidden-test drift.

### Split 3: family holdout stress checks where practical
Purpose: test narrow hypotheses rather than define the main metric.

Examples:
- Roman boundary-only validation set,
- unit extreme-slope subset,
- gravity precision-mismatch subset,
- equation numeric-expression vs symbolic subset.

This split is for diagnostics, not leaderboard selection.

## Primary metrics

### 1. Overall accuracy
Definition: exact string match between normalized prediction and gold answer.

Why primary:
- hidden evaluation is exact-match oriented,
- this is the closest offline proxy to the leaderboard.

Reporting rule:
- report mean and per-fold range for both split types.

### 2. Per-family accuracy
Definition: exact-match accuracy broken out by the six top-level families.

Why mandatory:
- the benchmark is almost perfectly family-balanced,
- aggregate gains can hide regressions in the hard families,
- synthetic data should only be trusted if it improves the families it targets without hurting others.

Required reporting:
- per-family mean accuracy,
- family counts in each validation fold,
- deltas vs previous baseline.

### 3. Answer-format accuracy
Definition: fraction of predictions that match the expected family-specific output schema, regardless of whether the value is correct.

Schema checks:
- `bit_transform`: exactly 8 binary digits,
- `text_cipher`: 3 to 5 lowercase words,
- `roman_numeral`: uppercase Roman numeral alphabet only,
- `unit_conversion`: decimal with exactly 2 places,
- `gravity`: decimal with 1 or 2 places,
- `equation_transform`: non-empty symbolic/integer string preserving allowed punctuation.

Why separate this metric:
- synthetic data can improve format accuracy without improving reasoning,
- some interventions should be rejected if they mostly reduce formatting errors but do not raise exact match.

### 4. Confidence-conditioned accuracy when available
If the final system emits solver/router confidence, report accuracy by confidence bucket.

Why useful:
- supports selective fallback decisions,
- helps decide when the LM should trust deterministic solvers vs generic generation.

## Robustness and drift checks

### 1. Random-split vs structure-split gap
Compute the gap between stratified-random accuracy and structure-aware accuracy.

Interpretation:
- a small gap suggests stable generalization across latent parameter buckets,
- a large gap suggests the system is memorizing prompt-local patterns or overfitting to common generator regions.

### 2. Per-family drift gap
For each family, compare random-split and structure-split performance.

Most important families for drift inspection:
- `unit_conversion`
- `gravity`
- `equation_transform`
- `text_cipher`

### 3. Stress-subset checks
Evaluate targeted slices such as:
- Roman boundary numbers,
- unit slopes near `0.50` or `2.00`,
- gravity rows with 1-decimal answers,
- equation numeric-expression rows with uncommon operator symbols,
- bit-transform rows with 11 demonstrations.

### 4. Synthetic contamination checks
Whenever synthetic data is added:
- keep validation real-only,
- tag training rows as real vs synthetic,
- compare performance using no synthetic / MVP synthetic / full synthetic,
- stop scaling if gains vanish on structure-aware validation.

## Validation design that reduces hidden-test overfitting

### Recommended honest-offline protocol
1. Freeze a **real-only 5-fold stratified hash split**.
2. Freeze a **real-only 5-fold structure-aware split**.
3. Tune major modeling decisions only on a development subset of those folds.
4. Reserve at least one structure-aware fold as a late-stage confirmation fold.
5. Evaluate synthetic-data decisions only against untouched real validation rows.
6. Do not keep redesigning the structure signature after seeing results, except when the taxonomy itself changes for documented benchmark reasons.

### Why this is the best current design
- it respects the benchmark's family structure,
- it reduces false optimism from prompt-template leakage,
- it keeps synthetic data from grading itself,
- it is strict enough to catch format-only improvements masquerading as reasoning gains.

## Ablation priorities
Ranked by expected signal value.

### Priority 1: solver / prompting foundation
1. router only vs router + exact normalizer,
2. answer-only prompt vs verbose prompt,
3. Roman/unit/gravity deterministic solvers on vs off.

### Priority 2: synthetic-data value test
4. no synthetic vs MVP synthetic,
5. MVP synthetic with and without boxed-answer targets,
6. MVP synthetic with different real:synthetic mixing ratios.

### Priority 3: robustness checks
7. random split only vs random + structure-aware model selection,
8. gravity precision heuristic variants,
9. unit rounding policy variants.

### Priority 4: risky later-stage work
10. experimental text synthetic on vs off,
11. experimental equation synthetic on vs off.

The last two should remain disabled until the latent generators are validated.

## Practical baseline evaluation workflow
The `scripts/eval_baselines.py` script should be used to produce a reproducible first reference point.

It should:
- classify each row into a family,
- create both split strategies,
- run lightweight heuristic baselines,
- report overall accuracy,
- report per-family accuracy,
- report answer-format accuracy,
- report drift gaps between split strategies.

This baseline is not expected to solve the full benchmark. Its job is to give a stable, honest yardstick before solver-heavy or synthetic-heavy iterations begin.

## Decision rules after each experiment
Approve an experiment only if:
1. overall real-validation exact match improves,
2. structure-aware validation does not regress materially,
3. answer-format accuracy improves or stays stable,
4. gains are visible in the intended target families,
5. no hidden regressions appear in untouched non-target families.

If an experiment fails those checks, it should not be scaled even if it looks good on a random split.
