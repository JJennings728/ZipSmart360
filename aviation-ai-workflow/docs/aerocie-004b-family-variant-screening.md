# AeroCIE-004b — Conservative series-to-variant candidate screening

## Purpose
FAA AD 2024-05-11 (Federal Register document 2024-06419) references the **PW1100G** engine series in its summary but enumerates variants such as `PW1122G-JM` and `PW1127G-JM` in paragraph **(c) Applicability**. Simple exact-string searching for `PW1100G` in paragraph (c) therefore under-reports possible relevance. This patch adds **review candidates**, not engine-specific applicability findings.

## What it does
- Maintains the original live full-text downloader, immutable SHA-256 source snapshots and cached/offline review.
- Preserves existing `total_model_mentions` and `mentions_in_candidate_applicability_section` fields.
- Adds `family_variant_candidate_count`, `family_variant_candidates`, `family_variant_candidates_truncated`, and `family_variant_matching_basis`.
- For `--model PW1100G`, searches the identified applicability paragraph for `PW11...-JM`-shaped tokens. For `--model PW1400G`, searches for `PW14...-JM`-shaped tokens. This is a **limited naming-pattern heuristic**, not an authoritative type-certificate mapping. It must be human-verified before using results commercially.
- Candidate examples **outside** the applicability paragraph and unrelated `PW14...` tokens do not generate PW1100G family candidates.
- Does not create a compliance determination, verified asset applicability, or proof that unrelated models are exempt.

## Installation on user's Windows computer
Save ZIP into Downloads; PowerShell from any directory:

```powershell
Expand-Archive -Path "$HOME\Downloads\AeroCIE_004b_Family_Variant_Candidates.zip" -DestinationPath "$HOME\Documents\SRP\ZipSmart360-main" -Force
cd "$HOME\Documents\SRP\ZipSmart360-main\aviation-ai-workflow"
py -m unittest tests.test_aerocie_full_text_review -v
py -m src.aerocie.full_text_review --document-number 2024-06419 --model PW1100G --as-of 2026-10-20 --offline
```

The last command reads the previously saved source **without a network request**. If you changed the original evidence location, pass the original `--evidence-dir`. Existing SQLite regulatory records and full-text evidence are not overwritten by this patch.

## Interpret results carefully
`series_variant_candidates_in_applicability_review_required` = candidate model-variant names detected in a text span labeled as applicability. **Not** confirmation an individual engine is affected. Verify the official Federal Register PDF, FAA DRS, any subsequent AD changes/supersedures, exact engine model, installed part numbers, parts serial numbers, original manufacturing records, exclusions, incorporation-by-reference documents, and relevant compliance provisions before drawing asset-specific conclusions.

### Source
https://www.federalregister.gov/documents/2024/03/27/2024-06419/airworthiness-directives-international-aero-engines-llc-engines
