# Submission checklist

Use this checklist before packaging and uploading the final LoRA adapter.

## 1. Nemotron-3-Nano-30B compatibility
- [ ] The adapter was trained against the exact intended base model family: **NVIDIA Nemotron-3-Nano-30B**.
- [ ] `adapter_config.json` contains a `base_model_name_or_path` that clearly points to a Nemotron-3-Nano-30B base.
- [ ] `adapter_config.json` has `peft_type` set to `LORA`.
- [ ] `adapter_config.json` includes `target_modules` and they match modules that exist in the chosen Nemotron checkpoint.
- [ ] The adapter loads cleanly with the intended PEFT/vLLM runtime stack without shape mismatches.

## 2. Required submission files
- [ ] `adapter_config.json` is present.
- [ ] Adapter weight file is present as `adapter_model.safetensors` or `adapter_model.bin`.
- [ ] Any extra config files required by the runtime are included intentionally, not accidentally omitted.
- [ ] The packaged submission directory contains only the files needed for inference and light documentation.

## 3. vLLM inference assumptions
- [ ] The final inference path assumes **vLLM loads the base Nemotron model plus the LoRA adapter**.
- [ ] The adapter has been smoke-tested under the intended vLLM-compatible loading path, not just in a notebook.
- [ ] The prompt template used for evaluation matches the one used during final validation.
- [ ] Generation settings favor single-pass exact answers, e.g. low temperature / deterministic decoding where appropriate.
- [ ] The model is instructed to emit **one boxed final answer only**.

## 4. Final answer formatting behavior
- [ ] The model's final non-whitespace text is exactly one `\boxed{answer}` block.
- [ ] No explanation, apology, units, or trailing punctuation appears after the box.
- [ ] `bit_transform` answers remain exactly 8 binary digits.
- [ ] `text_cipher` answers remain lowercase words separated by single spaces.
- [ ] `roman_numeral` answers remain uppercase Roman numerals.
- [ ] `unit_conversion` answers remain decimals with exactly 2 places.
- [ ] `gravity` answers preserve prompt-consistent decimal precision.
- [ ] `equation_transform` answers preserve leading zeros, minus signs, and exact symbolic characters.

## 5. Pre-submission QA checks
- [ ] Run real-only validation on the frozen development split, not the checked-in `test.csv`.
- [ ] Compare the final adapter against the prompt-only baseline.
- [ ] Confirm gains hold on both stratified-random and structure-aware splits.
- [ ] Review per-family exact match, not just overall score.
- [ ] Review answer-format accuracy separately from exact match.
- [ ] Spot-check hard families: `bit_transform`, `text_cipher`, and `equation_transform`.
- [ ] Spot-check edge formatting cases: Roman boundaries, unit rounding edges, gravity 1-decimal vs 2-decimal cases, leading-zero equation outputs.
- [ ] Verify no synthetic rows were used for unsupported families unless the generators were newly validated and documented.

## 6. Packaging and handoff
- [ ] Run `scripts/package_lora_submission.py` on the final adapter directory.
- [ ] Inspect the generated `manifest.json` and `README_submission.md`.
- [ ] Confirm the packaged archive includes `adapter_config.json`.
- [ ] Confirm the packaged archive name and directory contents are upload-ready.
- [ ] Record the exact git commit, training recipe, and validation summary used to produce the submission.

## 7. Final go / no-go decision
### Go if:
- [ ] The adapter beats prompt-only on real held-out exact match.
- [ ] The gain is not just a formatting-only artifact.
- [ ] The adapter remains loadable and stable under the intended vLLM path.
- [ ] The final answer contract is reliably obeyed.

### No-go if:
- [ ] The improvement disappears on structure-aware validation.
- [ ] Gains are only cosmetic formatting gains.
- [ ] The adapter causes schema drift, verbosity, or loader instability.
- [ ] Prompt-only is equally good or better.
