# Task taxonomy

## Top-level taxonomy
The benchmark currently looks like a six-family synthetic reasoning suite, with each family wrapped in a fixed Wonderland narrative.

| Family ID | Family | Count | Core skill | Recommended first-pass solver |
|---|---|---:|---|---|
| `bit_transform` | 8-bit bit transform | 1,602 | infer prompt-specific bit program from IO pairs | operator-library search / constrained synthesis |
| `gravity` | changed gravity constant | 1,597 | infer scalar `g` in `d = 0.5*g*t^2` | deterministic numeric estimator |
| `unit_conversion` | linear unit conversion | 1,594 | infer multiplicative factor | deterministic numeric estimator |
| `text_cipher` | lexical text decryption | 1,576 | infer prompt-specific cipher over small grammar | cipher decoder + lexicon + grammar constraints |
| `roman_numeral` | Roman numeral conversion | 1,576 | convert integer 1..100 to Roman numeral | direct deterministic converter |
| `equation_transform` | symbolic equation transform | 1,555 | infer prompt-specific string/arithmetic rule | sub-router + program search |

## Subfamily hypotheses

### `roman_numeral`
This family appears to have no meaningful subfamilies.
- Query domain: integers 1 to 100.
- Output form: uppercase Roman numerals only.
- The demonstrations mainly anchor formatting and distract from the fact that the underlying rule is standard Roman notation.

### `unit_conversion`
Plausible subfamilies are weak; this looks mostly homogeneous.
- Shared rule: `y = kx` with prompt-specific `k`.
- Examples vary only in number of support rows and conversion factor.
- Hidden risk is not rule diversity but rounding behavior.

### `gravity`
Also mostly homogeneous.
- Shared rule: `d = 0.5 * g * t^2`.
- Prompt-specific latent variable: `g`.
- Hidden risk is numeric precision / rounding rather than family drift.

### `text_cipher`
This family likely contains **surface grammar subfamilies** rather than different underlying math.

#### Text subfamily A: 3-word outputs
Examples look like:
- `cat imagines book`
- `king chases castle`
- `knight dreams key`

Likely schema:
- subject + verb + object/location

#### Text subfamily B: 4-word outputs
Examples look like:
- `wizard watches through library`
- `rabbit creates in ocean`
- `the secret cat sees`

Likely schemas:
- subject + verb + preposition + location
- determiner + adjective + noun + verb

#### Text subfamily C: 5-word outputs
Examples look like:
- `queen sees the hidden book`
- `dragon imagines the dark treasure`

Likely schema:
- subject + verb + `the + adjective + noun`

Latent generator hypothesis:
- fixed benchmark lexicon,
- small grammar/template sampler,
- prompt-specific substitution cipher over letters.

### `bit_transform`
This family likely hides multiple operator programs but one broad solver class.

Plausible latent subfamilies:
- pure bit permutation / rotation,
- affine-style XOR with masks or shifted variants,
- mixed nonlinear Boolean rules involving AND/OR/NOT/majority.

The key distinction is probably **operator composition depth**, not prompt wording.

### `equation_transform`
This is the only family where a deeper taxonomy already looks necessary.

#### Equation subfamily A: numeric expression prompts
Typical query form: `DD?DD`.
Examples suggest prompt-specific operator semantics such as:
- arithmetic over whole numbers,
- digitwise arithmetic,
- concatenation,
- reversal / sorting / interleaving,
- operator overloading where punctuation is just a symbol name.

Why this matters:
- some targets are integers,
- some are negative,
- some preserve leading zeros,
- output length ranges from 1 to 4 characters.

#### Equation subfamily B: punctuation-string prompts
Typical query form is arbitrary punctuation-only strings.
Examples suggest transforms such as:
- character deletion / retention,
- local substitution maps,
- position-dependent rewrites,
- symmetry or duplication rules,
- composition of smaller string operators.

Why this matters:
- answer alphabet is symbolic rather than numeric,
- operator-search space differs from numeric-expression rules,
- tokenization mistakes can corrupt the output.

## Latent rule-generator hypotheses

### Most likely prompt generators
1. **Deterministic mathematical generator** for Roman numerals.
2. **Scalar parameter generator** for unit conversion and gravity.
3. **Small program sampler** for bit transforms.
4. **Cipher + grammar generator** for text prompts.
5. **Mixed symbolic program sampler** for equation transforms.

### Why this matters for modeling
If the hidden benchmark is generated from these same underlying programs, then the best path is to solve the generator families, not to imitate answers statistically.

## Routing blueprint implied by the taxonomy

### Stage 1: exact lexical routing
Use fixed marker strings to map prompts into one of the six top-level families.

### Stage 2: sub-routing inside `equation_transform`
Split by query pattern:
- `^[0-9]{2}[^A-Za-z0-9\s][0-9]{2}$` -> numeric-expression branch.
- otherwise -> punctuation-string branch.

### Stage 3: answer-schema validation
Before final emission, enforce family-specific normalizers:
- `bit_transform`: exactly 8 binary digits.
- `roman_numeral`: uppercase Roman numeral alphabet only.
- `unit_conversion`: exactly two decimal places.
- `gravity`: preserve observed decimal precision rather than forcing `%.2f`.
- `text_cipher`: lowercase words separated by single spaces.
- `equation_transform`: preserve symbolic characters, leading zeros, and minus signs.

## What not to assume yet
- Do **not** assume a single fine-tuned LM can internalize the equation family without explicit structure.
- Do **not** assume the visible `test.csv` is representative; it is fully leaked from train.
- Do **not** assume text decryption is word-level substitution; the training evidence argues against that.
