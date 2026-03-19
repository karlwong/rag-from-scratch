# Synthetic data plan

## Executive decision
Synthetic augmentation should be **selective, benchmark-faithful, and solver-aligned**, not volume-driven.

The current evidence supports **high-confidence synthetic generation for only three families**:
1. `roman_numeral`
2. `unit_conversion`
3. `gravity`

Those families have clear latent generators already visible in `train.csv`, low ambiguity, and straightforward output schemas. By contrast, `bit_transform`, `text_cipher`, and especially `equation_transform` still have too much latent-rule uncertainty to justify large-scale synthetic expansion without risking harmful bias.

## Why synthetic data is not the default answer
The benchmark looks like a mixture of six synthetic puzzle generators, but only half of them are currently reverse-engineered with enough confidence for faithful regeneration. Adding synthetic data from guessed generators would make the adapter better at *our assumptions*, not necessarily better on the hidden test.

The safest use of synthetic data here is:
- reinforce **answer formatting and concise emission**,
- improve **single-pass reliability** on deterministic numeric families,
- provide a small amount of **distribution widening** near boundary values,
- avoid replacing explicit solver logic for families that are already almost deterministic.

## Family-by-family synthetic usefulness

| Family | Synthetic usefulness | Recommendation | Rationale | Main risk |
|---|---|---|---|---|
| `roman_numeral` | Medium | **Generate now** | Generator is standard Roman conversion over 1..100, so we can safely widen boundary coverage and formatting discipline. | Overweighting an already-easy family and wasting training budget. |
| `unit_conversion` | High | **Generate now** | The family appears to be a pure multiplicative map with 2-decimal output. Synthetic examples can target slope extremes, rounding edges, and answer-only formatting. | Teaching the model to memorize a rounded heuristic if generated ratios are noisy. |
| `gravity` | High | **Generate now** | The latent rule `d = 0.5 * g * t^2` is clear. Synthetic data can stress precision handling, time-range boundaries, and concise output formatting. | Incorrect precision policy can poison answer rendering. |
| `bit_transform` | Low for now | **Do not augment yet** | We still do not know the true operator library, program depth, or tie-breaking behavior. Naive generation would bake in the wrong DSL. | Hidden-test mismatch from synthetic rules that are simpler or different than the real benchmark. |
| `text_cipher` | Low for now | **Do not augment yet** | The small lexicon is clear, but the cipher family is not fully reverse-engineered. We do not yet know whether the mapping class is monoalphabetic, affine, position-dependent, or something else. | Harmful overfitting to a fake cipher generator that teaches the wrong invariants. |
| `equation_transform` | Very low for now | **Do not augment yet** | This family is heterogeneous and likely mixes multiple latent generators. Synthetic data is much more likely to narrow the model incorrectly than to help. | Severe hidden-test overfitting to our guessed operator set or symbolic grammar. |

## Approved synthetic families

### 1. `roman_numeral`
**Use case:** low-risk formatting reinforcement and boundary coverage.

**What to generate:**
- prompts with 3 to 5 demonstration pairs,
- query integers across the full `1..100` range,
- emphasis on Roman-boundary numbers: `4, 9, 14, 19, 39, 40, 44, 49, 90, 94, 99, 100`.

**Why useful despite solver availability:**
- helps LoRA learn the benchmark narration and answer-only response style,
- reinforces uppercase Roman formatting,
- gives safe low-risk supervised data while harder families remain solver-driven.

**Expected gain:** modest. Mostly format stabilization rather than new reasoning skill.

### 2. `unit_conversion`
**Use case:** reliable numeric formatting and robustness to unseen slope values.

**What to generate:**
- prompt-specific multiplicative factors in roughly the observed `0.50..2.00` range,
- 3 to 5 examples per prompt,
- measurement values spanning the observed `5.00..49.99` range,
- query cases chosen near rounding boundaries.

**Why useful:**
- this family is large,
- synthetic generation is faithful,
- exact 2-decimal formatting matters,
- generated prompts can widen slope coverage more efficiently than duplicating train-like prompts.

**Expected gain:** moderate, especially if the final system still uses an LM for some numeric decisions.

### 3. `gravity`
**Use case:** precision control and latent-parameter generalization.

**What to generate:**
- prompt-specific `g` values in roughly the observed `4.9..19.6` range,
- 3 to 5 observation lines,
- times spanning `1.0s..5.0s`,
- two tracks:
  - **stable 2-decimal track** for easy exact-format learning,
  - **precision-stress track** with occasional 1-decimal outputs when the rendered value naturally ends in a trailing zero after 2-decimal rounding.

**Why useful:**
- the underlying rule is clear,
- the family is large,
- visible data shows real precision variability,
- this is the cleanest place to teach the model to avoid unnecessary prose while preserving numeric schema.

**Expected gain:** moderate to high for output-format reliability.

## Families to explicitly avoid for synthetic augmentation

### `bit_transform`
Synthetic generation is unsafe until we know the real program library and search depth. Generating from a toy DSL would likely make the adapter overconfident on incorrect bit rules.

### `text_cipher`
Even though the lexicon is small, a guessed cipher generator can easily teach the wrong decoding class. We should revisit synthetic text only after proving the true cipher family on held-out real rows.

### `equation_transform`
This family should be treated as synthetic-data red zone. Until the latent taxonomy is much clearer, any synthetic expansion is more likely to narrow the model toward our wrong symbolic grammar than to help on hidden evaluation.

## Quality filters for approved synthetic data
Every generated example must pass all of these checks before entering training:

1. **Template fidelity**
   - prompt wording must match the benchmark family narration closely,
   - example count must stay inside the observed range,
   - line layout must match the real benchmark.
2. **Schema fidelity**
   - `roman_numeral`: uppercase Roman output only,
   - `unit_conversion`: exactly two decimal places,
   - `gravity`: valid decimal precision consistent with the prompt track.
3. **Deterministic self-verification**
   - regenerate the answer from the latent parameter and compare exactly,
   - reject any row where example rounding makes the latent rule ambiguous.
4. **No support/query leakage inside the prompt**
   - query input must not duplicate a support input,
   - Roman query number must not repeat a support number,
   - unit/gravity query values must be distinct from support values.
5. **Deduplication**
   - reject any generated prompt identical to an existing training prompt,
   - reject duplicate generated prompts and duplicate `(prompt, answer)` pairs.
6. **Boundary tagging**
   - label whether the row is a normal sample or a stress sample,
   - keep stress samples capped so they do not dominate training.
7. **Synthetic ratio cap**
   - start with synthetic volume smaller than the real approved-family volume,
   - do not flood the model with synthetic examples simply because they are cheap to create.

## Minimum viable synthetic set
This is the recommended first offline package.

### MVP objective
Improve formatting reliability and parameter-range robustness on the three approved families without changing the effective benchmark mix too aggressively.

### Suggested MVP size
- `roman_numeral`: 600 rows
- `unit_conversion`: 1,200 rows
- `gravity`: 1,200 rows
- **Total:** 3,000 synthetic rows

### Why this mix
- Roman is already easy, so keep it smaller.
- Unit and gravity are both large, clean, and format-sensitive, so they deserve most of the synthetic budget.
- 3,000 rows is large enough to teach answer-only style and boundary handling without swamping the 9,500-row real set.

### MVP training use
Use the MVP set only for:
- short SFT warm-up or mixed fine-tuning,
- answer-format reinforcement,
- family-specific prompt-template adaptation.

Do **not** use it as evidence that synthetic data helps the hard families.

## Full synthetic curriculum option
This is only for later, after the MVP is evaluated honestly.

### Curriculum stages
1. **Stage A: format-safe core**
   - easy Roman, unit, and gravity rows with no rounding edge cases.
2. **Stage B: boundary coverage**
   - Roman boundary numbers,
   - unit slopes near range limits,
   - gravity `g` and `t` values near limits.
3. **Stage C: precision stress**
   - unit values near `x.xx5` rounding cases,
   - gravity rows mixing 1-decimal and 2-decimal observations.
4. **Stage D: inference-style formatting stress**
   - same task content, but training targets always in final-answer form such as `\boxed{answer}`.

### Suggested full-curriculum size
- `roman_numeral`: 2,000 rows
- `unit_conversion`: 4,000 rows
- `gravity`: 4,000 rows
- **Total:** 10,000 rows

This is the upper bound worth exploring before solving more latent families. Going beyond this is likely wasted budget unless the validation plan shows a real uplift.

## Key risks of harmful synthetic data

### 1. Wrong latent generator risk
The biggest danger is generating synthetic rows from an incorrect causal rule and then teaching the model that fake rule more strongly than the real benchmark.

### 2. Family-balance distortion
If we dump too much safe synthetic Roman/unit/gravity data into training, the adapter may become better at easy numeric families while not improving the real bottlenecks (`bit_transform`, `text_cipher`, `equation_transform`).

### 3. Format-only improvement mistaken for reasoning improvement
Synthetic data can increase answer-format accuracy without improving true latent-rule solving. We should measure both separately.

### 4. Hidden-test overfitting to our boundary choices
Even high-confidence generators can become harmful if we overconcentrate on handcrafted edge cases that are not representative.

### 5. Validation leakage via synthetic-tuned split design
If we optimize the synthetic curriculum against repeatedly reused offline splits, we may simply overfit the validation harness.

## Recommended operating policy
1. Generate synthetic data **only** for `roman_numeral`, `unit_conversion`, and `gravity`.
2. Keep the first package small and tagged.
3. Evaluate on untouched real validation rows only.
4. Require per-family uplift on at least `unit_conversion` and `gravity` before scaling up.
5. Block synthetic generation for `bit_transform`, `text_cipher`, and `equation_transform` until their latent generators are validated on real holdouts.

## What success should look like
A useful synthetic-data intervention should produce:
- better answer-format accuracy,
- better or unchanged real-validation exact match on `unit_conversion` and `gravity`,
- no regression on non-augmented families,
- stable results across both random and structure-aware splits.

If those conditions are not met, synthetic data should remain a small auxiliary component rather than a central strategy.
