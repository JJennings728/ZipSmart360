# AeroCIE Phase 23 | Model Assurance and Research Traceability

**Product:** AeroCIE (aviation insurance, specialty carriers, MGAs, reinsurers)

This phase introduces an independent, reproducible evaluation of synthetic binary probability outputs and a provenance check for exact quotations. This is the first foundation for model reliability and explainable AI. No live predictive models or actuarial assumptions are implemented.

## Problems documented in 2026 sector research

| ID | Reported issue | Source | AeroCIE capability | Verified phase 23 status | Further product work |
|---|---|---|---|---|---|
| R01 | AI decision opacity | S&P Reinsurance 2026 | Model metadata, metrics, reasons, input SHA256, original sources | Deterministic report built and tested | Explanation of actual third-party model decisions; reviewer studies |
| R02 | AI false information | S&P Reinsurance 2026 | Exact quote evidence checks, missing/unsupported citations flagged | Tests pass for synthetic excerpts | Semantic entailment and independent source verification |
| R03 | Data security/privacy | S&P Reinsurance 2026 | Schema restricts sample to synthetic entries, new output only | Structural synthetic checks pass | Access control, encryption, retention, security assessment for real data |
| R04 | Model vulnerability | S&P Reinsurance 2026 | Evaluation gate, validation errors and signed-off reasons | Reproducible metrics | Model red teaming, drift monitoring, adversarial evaluations |
| R05 | Supply chain model vulnerability | S&P Reinsurance 2026 | Dataset digest and declared model version | Model lineage fields present | Vendor model inventory, dependency attestations, SBOM |
| R06 | Calibration, decision reliability | S&P Reinsurance 2026 | Brier score, expected calibration error, subgroup diagnostics | Synthetic metrics and tests | Actuarial validation, independent test sets, thresholds by use case |
| R07 | Geopolitical and war exposure | Marsh 2026; IUAI 2026 | Existing linked regulatory research documents | Research prototype only | Licensed geospatial / war aggregation data, portfolio exposure |
| R08 | Supply chain / maintenance | Marsh 2026; IUAI 2026 | Structured source register and technical research packets | Research prototype only | Live maintenance/parts feeds with permissions and benchmark data |
| R09 | Social / claims inflation | Marsh 2026; WTW 2026 | Evidence reports and caveat fields | Research prototype only | Claims and inflation datasets, actuarial model validation |
| R10 | Catastrophe/large event losses | S&P Reinsurance 2026 | Review traceability and model evaluation architecture | Evaluation infrastructure only | Exposure accumulation and catastrophe modeling |
| R11 | Underwriting submission quality | Marsh 2026 | Source provenance, chronology, brief, synthetic intake | Existing Phase 13-22 modules | Buyer-tested submission schema and review process |
| R12 | Reserve volatility / profitability | S&P Reinsurance 2026 | Model assurance diagnostic building block | Evaluation infrastructure only | Reserving and portfolio financial models |
| R13 | Ceded/MGA oversight | S&P Reinsurance 2026 | Source traceability and evidence review | Research prototype only | MGA bordereaux/data quality reconciliations |
| R15 | Source and legal change tracking | Existing AeroCIE requirements | Document lineage, hashes, review checklist | Offline code and CI tests | Current authoritative checks, licensing, human review |

Market evidence:
- S&P Global Ratings, *Global Reinsurance Sector View 2026*, https://insight.spglobal.com/story/global-reinsurance-highlights-2026/page/2
- Marsh, *Aviation insurance market overview H1 2026*, 2026-09-29, https://www.marsh.com/en/industries/aviation-space/insights/aviation-insurance-market-overview-h1-2026.html
- WTW, *Global aviation and space marketplace realities*, 2026-05-07, https://www.wtwco.com/en-ca/insights/2026/05/insurance-marketplace-realities-2026-spring-update-global-aviation-and-space
- IUAI/IUA, *CERSG survey 2026*, 2026-06-08, https://staff.iua.co.uk/IUA/NewsPages/Press-Releases-2026/Nearly-75--of-aviation-insurance-professionals-rank-geopolitical-instability-as-the-sector-s-biggest.aspx
- NIST AI Risk Management Framework Generative AI Profile, https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence

## Public interface

```powershell
python -m src.aerocie.model_assurance `
  --input sample-data/phase23/synthetic-model-eval.json `
  --out-json "${env:TEMP}\aerocie-model-assurance-result.json"
```

Expected result: JSON containing SHA256 of the exact evaluation input, model metadata and limitations, 24 synthetic evaluation rows, aggregate Brier score, expected calibration error, segment diagnostics, five largest prediction errors, model lineage disclosure, absent explanation flags, evidence citation status and explicit reasons for `REVIEW_REQUIRED`.

### Interpretation

- **A Brier score is descriptive, not proof of insurance pricing quality.** The 100-row minimum, Brier 0.20, ECE 0.10 and segment spread 0.10 are initial engineering thresholds with no actuarial endorsement.
- The quote checker requires an exact text excerpt; paraphrased output remains unsupported. Passing quote checks does not prove that source text is true or current.
- The `operator_checked` flag records a review assertion; it is not external authentication. The fictional sample evidence URL uses the reserved `.invalid` domain.
- Probabilities are for synthetic sample events, not actual loss frequencies.
- The current synthetic evaluator always flags missing individual model explanations. A configured metric threshold cannot substitute for a validated prediction or approved insurance use.
- A passing research gate cannot authorize external release. Real use requires production access controls, independent validation and source verification.

## Release milestones

1. Evaluate an independently labeled, representative dataset with defensible target definitions and enough observations per segment.
2. Pin upstream datasets and verify their legal usage and provenance.
3. Record real model version and prompt configuration, plus reproducible inference artifacts.
4. Perform calibration, sensitivity, drift, bias and adversarial tests; choose thresholds approved for the business task.
5. Present rationale, citations, uncertainty, alternative explanations and reviewer disposition in the operator workbench.
6. Conduct security/privacy testing and an end-user study before processing real insurance data.
