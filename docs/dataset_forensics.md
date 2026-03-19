# Dataset forensics

## Scope and inspection notes
- I inspected `train.csv` and `test.csv` directly and profiled them with `scripts/profile_dataset.py`.
- `train.csv` has 9,500 labeled rows; the visible `test.csv` has only 3 rows.
- All 3 visible test prompts are exact duplicates of training prompts, so the checked-in `test.csv` looks like a smoke-test sample rather than a realistic proxy for the hidden evaluation set.
- The benchmark is not a generic instruction-tuning corpus. It is a tightly templated algorithmic puzzle set with short exact-match targets.

## High-level dataset shape

### Family counts in `train.csv`
| Family | Count | Share | Primary answer schema |
|---|---:|---:|---|
| 8-bit bit transform | 1,602 | 16.9% | 8-character binary string |
| Gravity / changed `g` | 1,597 | 16.8% | decimal with 2 digits |
| Linear unit conversion | 1,594 | 16.8% | decimal with 2 digits |
| Text decryption | 1,576 | 16.6% | lowercase text phrase |
| Roman numeral conversion | 1,576 | 16.6% | Roman numeral |
| Equation transform | 1,555 | 16.4% | symbolic string or integer |

The family mix is almost perfectly balanced, which strongly suggests synthetic generation from six prompt templates.

### Length distributions
| Metric | Min | P10 | Median | P90 | Max |
|---|---:|---:|---:|---:|---:|
| Prompt characters | 177 | 197 | 281 | 468 | 510 |
| Answer characters | 1 | 3 | 5 | 24 | 39 |
| Prompt words | 32 | 33 | 46 | 70 | 78 |
| Answer words | 1 | 1 | 1 | 4 | 5 |

Interpretation:
- Prompts are short enough that routing and in-context algorithm induction should be cheap.
- Answers are extremely short. Format failures will be disproportionately costly.
- Only one family regularly needs multi-word generation: the text decryption task.

### Output schema mix
| Schema | Count |
|---|---:|
| decimal with exactly 2 decimals | 3,034 |
| 8-bit binary string | 1,602 |
| lowercase text | 1,576 |
| Roman numeral | 1,576 |
| symbolic punctuation string | 868 |
| integer | 687 |
| other decimal precision | 157 |

Important consequence: the benchmark is dominated by exact symbolic rendering, not long-form reasoning. A solution that over-explains is structurally mismatched to the task.

## Family-by-family reverse-engineering findings

### 1. 8-bit bit transform
**Marker:** `8-bit binary numbers` and `input -> output` pairs.

Observed structure:
- 8 to 11 demonstrations per prompt.
- Output is always an 8-bit binary string.
- Input/output examples look consistent with per-prompt Boolean / bit-permutation programs rather than global memorization.

Likely latent generator:
- Sample a small bitwise program from a library of shifts, rotates, XOR/AND/OR/NOT, and possibly majority / choice-style gates.
- Emit 8 to 11 IO pairs and one held-out query.

Implication:
- This family likely rewards explicit solver search over a limited operator library more than language-model pattern matching.

### 2. Text decryption
**Marker:** `decrypt the following text`.

Observed structure:
- 3 to 5 demonstration sentence pairs per prompt.
- Answers are always 3, 4, or 5 lowercase words.
- Global plaintext vocabulary size is only 77 tokens.
- The answer words are almost never fully present in the example outputs for the same prompt: only 7 of 1,576 prompts have all answer words already seen in the plaintext side.

What that means:
- This is **not** a simple per-prompt word lookup table.
- The examples are consistent with a per-prompt cipher over characters, applied to a sentence generator built from a small fixed lexicon.

Likely subfamilies by grammar:
- 3-word template: subject + verb + object/place.
- 4-word template: either subject + verb + preposition + place, or `the + adjective + noun + verb` style sequences.
- 5-word template: subject + verb + `the + adjective + noun`.

Implication:
- Solver should decode a prompt-specific cipher and then rely on grammar constraints over the small benchmark lexicon.

### 3. Roman numeral conversion
**Marker:** `write the number ... in the Wonderland numeral system`.

Observed structure:
- 3 to 5 examples per prompt.
- Query integers span the full range 1 to 100, with all 100 values represented in training.
- Outputs are standard Roman numerals, not an unknown numeral system despite the wording.

Likely latent generator:
- Sample a target integer in `[1, 100]`, then provide a few support examples.

Implication:
- This family is essentially solved by deterministic conversion. The examples are mostly distraction / format confirmation.

### 4. Linear unit conversion
**Marker:** `becomes` and `convert the following measurement`.

Observed structure:
- 3 to 5 demonstrations per prompt.
- Answers are always decimals with exactly 2 places.
- Inferred multiplicative factor varies per prompt; sampled slopes span roughly `0.50` to `2.00`.
- The mapping appears purely linear with no intercept.

Likely latent generator:
- Sample a scalar conversion factor `k`, generate several `(x, kx)` examples rounded to 2 decimals, then ask for a new query value.

Implication:
- Family-specific numeric regression / direct ratio estimation should solve this reliably. Output rounding to exactly 2 decimals matters.

### 5. Gravity / changed `g`
**Marker:** `d = 0.5*g*t^2`.

Observed structure:
- 3 to 5 observation lines per prompt.
- Answers are mostly decimals with exactly 2 places, with a smaller one-decimal minority.
- Query time spans `1.0s` to `5.0s`.
- Inferred prompt-specific gravity values span roughly `4.9` to `19.6`.

Likely latent generator:
- Sample a gravity constant `g`, produce several `(t, d)` observations with the quadratic rule, then query one new time point.

Implication:
- Deterministic inference of `g` from one or more examples should be enough. Output formatting still matters, but the solver should preserve the benchmark's observed decimal precision instead of blindly forcing `%.2f`.

### 6. Equation transform
**Marker:** `determine the result for:` with symbolic examples.

Observed structure:
- 3 to 5 demonstrations per prompt.
- This is the broadest and riskiest family.
- Two visible subfamilies:
  - **numeric-expression subtype**: query looks like `DD?DD` (732 rows).
  - **symbol-string subtype**: arbitrary punctuation-heavy strings (823 rows).
- Integer answers occur in 687 rows; 48 are negative and 51 have leading zeros, so normalization mistakes are a real risk.
- Symbolic punctuation answers occur in 868 rows.

Likely latent generator:
- A prompt-specific rule sampled from a library of string transforms, arithmetic-like operators, concatenations, deletions, reversals, or tokenwise substitutions.
- This family probably mixes several generator types under the same narrative wrapper.

Implication:
- A single monolithic LM response policy will likely underperform here. This family needs additional sub-routing and possibly brute-force / program-synthesis style search.

## Structural markers useful for routing
The benchmark is unusually routeable because each family exposes near-exact lexical triggers:

| Marker | Route |
|---|---|
| `8-bit binary numbers` | bit transform |
| `decrypt the following text` | text cipher |
| `Wonderland numeral system` | Roman numeral conversion |
| `convert the following measurement` | unit conversion |
| `d = 0.5*g*t^2` | gravity |
| `determine the result for:` with punctuation-heavy support examples | equation transform |

A lightweight rules-based router should already be near-perfect on the visible corpus.

## Hidden-test implications
1. **Visible test leakage is misleading.** The local `test.csv` should not be treated as a validation target.
2. **Family balance may shift in hidden evaluation.** A robust system should not assume the hidden set is still exactly six-way balanced.
3. **Equation transform is the main uncertainty bucket.** It likely contains multiple latent generators.
4. **Formatting errors are leaderboard killers.** Decimal precision, Roman numeral casing, binary width, and preservation of leading zeros all matter; gravity answers are not uniformly 2-decimal.
5. **Fine-tuning is not yet justified.** Four families are obviously deterministic, one is likely solver-plus-lexicon, and the hardest family first needs taxonomy and solver search work.

## Recommendation at this stage
The evidence favors a **router + deterministic solver stack** over immediate LoRA training:
1. rules-based family router,
2. exact solvers for Roman, unit, and gravity,
3. program-search / heuristic solver for bit transform,
4. cipher decoder constrained by the 77-word lexicon for text,
5. deeper taxonomy work for equation transforms.

That architecture matches the observed benchmark far better than generic supervised fine-tuning.
