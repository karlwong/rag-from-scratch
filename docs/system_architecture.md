# System architecture

## Objective
Build a benchmark-faithful inference stack that treats the Wonderland benchmark as a **mixture of synthetic puzzle generators**, not a generic instruction-following task. The architecture should maximize hidden-test exact-match accuracy by:
- routing each prompt into the correct latent task family,
- solving with family-specific deterministic or semi-deterministic logic,
- normalizing the final answer into the benchmark's expected schema, and
- falling back conservatively when confidence is low.

This is a routing-centered design because the dataset evidence strongly suggests that most leaderboard gain will come from solving the six prompt generators directly rather than from broad LoRA-only adaptation.

## High-level architecture

### Inference pipeline
1. **Prompt parser**
   - Extract the query line, example pairs, numeric observations, answer alphabet, and prompt markers.
   - Compute structural features such as number of `input -> output` pairs, number of gravity observations, whether the query is punctuation-only, and whether the prompt includes Roman-style examples.
2. **Top-level family router**
   - Score the prompt against the six known families using multiple weighted triggers rather than a single keyword.
   - Produce a ranked family list, confidence, ambiguity flag, and family-specific answer schema.
3. **Sub-router**
   - For `equation_transform`, split into `numeric_expression`, `punctuation_string`, or `mixed_symbolic`.
   - For `text_cipher`, tag likely clause length template (`three_word_clause`, `four_word_clause`, `five_word_clause`) to select grammar constraints.
4. **Family-specific solver**
   - Run deterministic or constrained-search logic tailored to the predicted family.
5. **Answer validator + normalizer**
   - Enforce family schema, round/format exactly, preserve leading zeros when needed, and reject malformed outputs.
6. **Emission wrapper**
   - Return the final normalized answer only, ideally as `\boxed{answer}` with no extra prose after the box.

### Why routing is the center of the system
The benchmark appears balanced across six generators, but those generators differ radically in latent structure:
- three are nearly deterministic math/format problems,
- one is a constrained text-cipher problem,
- one is a bit-program search problem,
- one is a heterogeneous symbolic transformation bucket.

A monolithic prompting policy would have to be simultaneously good at exact numeric formatting, Roman numeral conversion, bitwise synthesis, lexical cipher recovery, and symbolic program induction. That is a poor bias. Routing lets the system apply the right inductive bias for each family while keeping hidden-test overfitting risk low.

## Routing decision design

### Stage 1: prompt feature extraction
For every prompt, parse and cache:
- **marker phrases** such as `8-bit binary numbers`, `decrypt the following text`, `write the number`, `convert the following measurement`, `d = 0.5*g*t^2`, and `determine the result for:`
- **structural counts** such as:
  - binary IO pairs,
  - Roman example pairs,
  - unit-conversion example lines,
  - gravity observation lines,
  - number of `becomes` or `->` tokens,
- **query shape**:
  - 8-bit binary,
  - natural-language token sequence,
  - integer request,
  - decimal measurement request,
  - punctuation-only expression,
  - `DD?DD` numeric-expression pattern.

The key design principle is **marker + structure + query-shape agreement**. A prompt should not route purely because of one phrase if its example layout contradicts that route.

### Stage 2: weighted top-level family router
Use a weighted scoring model rather than hard first-match rules.

#### Top-level route triggers
| Family | Primary triggers | Structural confirmation | Target answer schema |
|---|---|---|---|
| `bit_transform` | `8-bit binary numbers`, `bit manipulation rule`, `determine the output for:` | at least 3 binary `input -> output` examples; query contains an 8-bit string | exactly 8 bits |
| `text_cipher` | `secret encryption rules are used on text`, `decrypt the following text` | several example sentence pairs with lowercase plaintext outputs; query is 3-5 tokens | lowercase phrase |
| `roman_numeral` | `different numeral system`, `write the number` | at least 2 example pairs where outputs are Roman numerals | uppercase Roman numeral |
| `unit_conversion` | `secret unit conversion`, `convert the following measurement` | several `x m becomes y` lines | decimal with 2 places |
| `gravity` | `gravitational constant has been secretly changed`, `d = 0.5*g*t^2` | multiple `For t = ... distance = ...` lines | decimal with prompt-consistent precision |
| `equation_transform` | `transformation rules are applied to equations`, `determine the result for:` | example lines of symbolic/numeric equation-like rewrites | symbolic or integer string |

#### Confidence logic
Compute confidence from:
- **absolute top score**: how strongly the prompt matches the winning family,
- **margin to runner-up**: whether an alternate family also fits,
- **trigger diversity**: whether the score comes from both lexical and structural evidence.

Recommended policy:
- **high confidence**: top score is strong and the margin is comfortably above the next family,
- **medium confidence**: top family is clear but one structural confirmation is missing,
- **low confidence / ambiguous**: top family wins only narrowly or relies on a single brittle cue.

The current router implementation in `scripts/build_router.py` marks a prompt ambiguous when confidence drops below the operational threshold or when the score margin is small.

### Stage 3: sub-routing

#### `equation_transform` sub-routing
Use the extracted query string:
- `^[0-9]{2}\D[0-9]{2}$` -> `numeric_expression`
- punctuation-only query -> `punctuation_string`
- otherwise -> `mixed_symbolic`

This matters because numeric-expression solvers should search over digit transforms and overloaded operators, while punctuation-string solvers should search over symbolic string rewrite programs.

#### `text_cipher` sub-routing
Use query token count as a proxy for grammar template:
- 3 tokens -> `three_word_clause`
- 4 tokens -> `four_word_clause`
- 5 tokens -> `five_word_clause`

This does not solve the cipher by itself, but it constrains decoding and candidate ranking.

## Family-specific solver strategies

### 1. `roman_numeral`
**Expected value:** very high.  
**Effort:** very low.  
**Overfitting risk:** minimal.

#### Strategy
Ignore the distractor examples after using them to confirm routing. Parse the query integer and convert with a direct Roman numeral routine for `1..100`.

#### Why this should work
The forensics suggest the prompt wording is fake complexity; the output is standard Roman notation.

#### Failure controls
- reject lowercase output,
- reject non-Roman letters,
- emit the numeral only,
- wrap as `\boxed{...}` in the final response.

### 2. `unit_conversion`
**Expected value:** very high.  
**Effort:** low.  
**Overfitting risk:** low.

#### Strategy
Infer the scalar factor `k` from demonstrations using robust ratio aggregation:
- parse each `(x, y)` pair,
- estimate `k_i = y / x`,
- use median or weighted mean across examples,
- compute query output `k * x_query`,
- round to exactly 2 decimals.

#### Route-specific triggers
- `convert the following measurement`
- repeated `m becomes`
- examples consistent with a no-intercept linear map.

#### Confidence logic
- high confidence if all ratios cluster tightly,
- lower confidence if example rounding noise makes the ratios inconsistent.

#### Ambiguity handling
If examples do not fit a multiplicative map tightly enough, fall back to a constrained regression sanity check; if still inconsistent, use a generic numeric fallback prompt that asks the model to infer the scale factor but still force the final answer format.

### 3. `gravity`
**Expected value:** very high.  
**Effort:** low.  
**Overfitting risk:** low.

#### Strategy
Infer `g` from demonstrations via `g_i = 2d / t^2`, aggregate across examples, and compute `d_query = 0.5 * g * t_query^2`.

#### Precision policy
This family is riskier than unit conversion because visible answers do not all use the exact same decimal precision.
- infer the dominant decimal precision from demonstrations,
- round the final result consistently with that observed precision,
- preserve trailing zeros if the prompt examples preserve them.

#### Confidence logic
- high confidence when estimated `g` values cluster tightly,
- medium confidence when one outlier example is inconsistent because of rounding,
- low confidence if the prompt cannot be parsed or if observation fit error is too large.

### 4. `bit_transform`
**Expected value:** high.  
**Effort:** medium to high.  
**Overfitting risk:** moderate if the operator library is too narrow.

#### Strategy
Treat each prompt as a prompt-specific small program induction problem.

Recommended solver stack:
1. search over a **library of primitive bit operators**:
   - identity,
   - bitwise NOT,
   - left/right shifts,
   - left/right rotates,
   - XOR/AND/OR with masks,
   - XOR/AND/OR with shifted copies,
   - majority / choice-style bit combinations.
2. compose up to a limited depth,
3. score candidates by exact consistency across all support examples,
4. if multiple candidates fit, use minimum-description-length tie-breaking,
5. apply the best program to the query.

#### Key subfamilies
- permutation / rotation dominated,
- affine mask transforms,
- mixed nonlinear Boolean transforms.

#### Ambiguity handling
When multiple programs fit the supports:
- rank by simplicity,
- then by stability under held-out-style perturbation tests,
- if still tied, produce the answer from the simplest consistent candidate and mark the route as low confidence for later analysis.

#### Fallback behavior
If no candidate matches exactly within the current operator depth, back off to a broader synthesis prompt or a deeper search budget. This is a good place for lightweight LoRA assistance later, but only after a strong symbolic baseline exists.

### 5. `text_cipher`
**Expected value:** high.  
**Effort:** high.  
**Overfitting risk:** moderate.

#### Strategy
Assume a prompt-specific character-level cipher over a small fixed lexicon plus constrained grammar.

Recommended solver stack:
1. build the benchmark lexicon from training plaintext outputs,
2. infer a candidate character mapping from the support pairs,
3. decode the query into candidate plaintext token sequences,
4. rank candidates by:
   - exact consistency with learned cipher constraints,
   - compatibility with the subfamily grammar template,
   - membership in the benchmark lexicon,
   - language-template plausibility under the observed benchmark sentence forms.

#### Key subfamilies
- `three_word_clause`: subject + verb + object/location,
- `four_word_clause`: either prepositional clause or determiner/adjective/noun/verb template,
- `five_word_clause`: subject + verb + `the + adjective + noun`.

#### Confidence logic
- high confidence if the cipher mapping is nearly complete and yields one lexicon-consistent decode,
- medium confidence if two candidate decodes survive grammar filtering,
- low confidence if the support pairs are insufficient to disambiguate several character mappings.

#### Ambiguity handling
If multiple plaintext candidates remain:
- prefer candidates seen in benchmark grammar templates,
- prefer complete lexicon matches over partial OOV decodes,
- if ambiguity persists, use the shortest consistent explanation and log the prompt for synthetic-data augmentation.

### 6. `equation_transform`
**Expected value:** highest upside, highest risk.  
**Effort:** high.  
**Overfitting risk:** high if solver search is not carefully regularized.

#### Why this family is special
The family is heterogeneous enough that it should not be solved by a single heuristic. It needs its own internal router.

#### Subfamily A: `numeric_expression`
**Recommended strategy:** operator-search over digit/string transforms.

Candidate rule library:
- arithmetic on the 2-digit numbers,
- digitwise addition/subtraction/multiplication,
- concatenation,
- reversal,
- sorting digits,
- interleaving digits,
- operator-dependent branch rules,
- symbolic post-formatting that preserves leading zeros or emits short symbolic outputs.

Because some answers remain symbolic rather than numeric, this branch should allow the operator to behave like a named transform rather than assume ordinary arithmetic.

#### Subfamily B: `punctuation_string`
**Recommended strategy:** symbolic string rewrite search.

Candidate rule library:
- character substitution,
- position-based deletion/retention,
- reversal / chunk reversal,
- mirroring,
- duplication / compression,
- pairwise replacement,
- rewrite conditioned on repeated symbols.

#### Confidence logic
- high confidence when one candidate program exactly fits every support example,
- medium confidence when several programs tie but all predict the same query answer,
- low confidence when tied programs disagree on the query.

#### Fallback behavior
If the exact search space fails:
1. expand the rule library carefully,
2. run a constrained LM prompt seeded with parsed supports and an explicit output schema,
3. if still unresolved, default to schema-safe shortest output rather than verbose speculation.

## Confidence and fallback policy

### Confidence policy
- **High confidence**: route directly to one solver and trust normalized output.
- **Medium confidence**: run the primary solver, then validate against family schema; if validation fails, run the runner-up solver.
- **Low confidence**: run a schema-safe generic fallback with explicit examples and strong output constraints, then log the prompt for taxonomy review.

### Ambiguity handling
Ambiguity should be explicit, not hidden.
- save top-two route candidates,
- preserve the trigger list and score margin,
- use schema validation as the first disambiguator,
- only use model-based fallback after deterministic checks fail.

This is important for hidden-test robustness because some future prompts may mutate narrative wording while preserving generator structure.

## Answer normalization rules

### Family-specific normalization
| Family | Normalization rule |
|---|---|
| `bit_transform` | output exactly 8 binary digits; left-pad with zeros if necessary |
| `text_cipher` | lowercase only, single spaces, no punctuation, no trailing period |
| `roman_numeral` | uppercase Roman letters only |
| `unit_conversion` | decimal rendered with exactly 2 places |
| `gravity` | round to inferred precision from examples; preserve trailing zeros if benchmark style implies them |
| `equation_transform` | preserve exact symbols, leading zeros, minus signs, and length; never coerce to float |

### Final emission contract
The benchmark extractor prioritizes content inside `\boxed{}`. Therefore the serving stack should:
1. normalize the raw solver output,
2. validate it against the family schema,
3. emit `\boxed{normalized_answer}`,
4. avoid any extra prose after the boxed answer.

This policy minimizes format-loss errors even when the upstream solver is correct.

## Hidden-test accuracy safeguards

### Avoid shallow keyword overfit
The router should not rely on one exact substring alone. Instead it should require agreement between:
- narrative markers,
- example layout,
- query format,
- expected answer schema.

### Prefer exact solution logic where justified
Deterministic families should stay deterministic:
- Roman numeral conversion,
- unit conversion,
- gravity.

Semi-deterministic search should be used where the latent generator plausibly varies:
- bit transforms,
- text cipher,
- equation transform.

### Keep the fallback narrow
The fallback should not become a generic chain-of-thought generator. It should be a **schema-constrained last resort** that still returns a short exact answer.

## Top failure risks
1. **Equation-family under-modeling**
   - Risk: the search library misses hidden symbolic transforms.
   - Mitigation: use sub-routing, keep the library extensible, log unresolved prompts for synthetic augmentation.
2. **Bit-transform search incompleteness**
   - Risk: hidden prompts require deeper operator composition than the first solver supports.
   - Mitigation: start with an exact shallow search, then add depth selectively based on failure clusters.
3. **Text-cipher ambiguity**
   - Risk: incomplete character mappings leave multiple lexicon-consistent decodes.
   - Mitigation: add grammar-template ranking and lexicon priors.
4. **Formatting losses after correct reasoning**
   - Risk: correct solver output is rendered with the wrong precision, case, spacing, or missing leading zeros.
   - Mitigation: make normalization a first-class stage and validate before emission.
5. **Hidden-set prompt drift**
   - Risk: hidden prompts paraphrase narrative markers.
   - Mitigation: include structural triggers and schema checks, not only literal template matching.

## Ranked solver approaches by expected leaderboard value
1. **Deterministic numeric core (`roman_numeral`, `unit_conversion`, `gravity`)**
   - Best gain-per-effort and lowest risk.
2. **Bit-transform constrained program search**
   - Likely large gain because the family is common and clearly algorithmic.
3. **Equation-transform sub-router plus symbolic search**
   - Highest upside but also the largest implementation risk.
4. **Text-cipher decoder with lexicon + grammar constraints**
   - Valuable, but probably more engineering-heavy than the deterministic families.
5. **LM-only or LoRA-only fallback behavior**
   - Necessary as a safety net, but lower expected value than explicit solver design because the benchmark is dominated by exact symbolic outputs.

## Immediate next build step
Implement the actual solver modules behind this router in roughly this order:
1. Roman/unit/gravity deterministic solvers,
2. shared normalization + boxed emission layer,
3. bit-transform search prototype,
4. equation-transform sub-solvers,
5. text-cipher constrained decoder.
