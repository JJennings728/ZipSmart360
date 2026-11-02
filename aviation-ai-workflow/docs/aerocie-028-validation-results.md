# Phase 28 validation record

Implementation base: `43e140e3f823e824ff3f715a0fb8b9f23d42304f` on `feature/aerocie-027-powerbi-measures`. Implementation branch: `feature/aerocie-028-commercial-dashboard`.

- Report code: four populated pages, 63 native visual containers, SRP theme, editable queries, slicers, page navigation and explicit filter interactions.
- Official offline Microsoft JSON-schema validation: **74 JSON/project/theme files passed**, 16 schema fixture checksums verified.
- UTF-8 AeroCIE and Federal Register regression command: `python -m pytest -p no:cacheprovider -q tests/test_aerocie_*.py tests/test_fr_*.py` — **347 test cases passed, 85 subtests passed; zero failures, errors or skips**. Python 3.12.14, pytest 9.2.0, jsonschema 4.26.0. This includes the new report/relationship/filter contract tests; it is not a Desktop runtime test.
- Fresh exclusive temporary SQLite generation, quality audit and existing `src.aerocie.export_reconciliation`: **PASS**. Seven unique case IDs; Quote=2, Refer=4, Decline=1; two missing-evidence referrals; requested hull=$34,045,000; Low=$46,243; Base=$104,080; High=$208,159; nine manifest digests verified; `release_authorized=false`; `INTERNAL_DEMO_ONLY`.
- All seven existing Power Query partitions and `AeroCIEDataFolder` parameter compared with the base commit: unchanged. Original DAX expressions and synthetic fixtures retained. New measures and three data-backed one-to-one submission relationships are additive.
- Static binding and layout checks: every query field resolves to the semantic model, native role names are checked, every visual stays within its page without overlaps, interaction targets resolve, numeric KPI values come from measures, source registry remains independent. New label measures use `KEEPFILTERS` rather than overwriting selected advisory labels. DAX names, references, delimiters and multiline indentation are checked; DAX is not executed.
- Repository whitespace check: passed. No database, generated export, credential or real customer record is committed. No merge, application publication, service deployment or purchase performed.

## Outstanding runtime acceptance

Power BI Desktop is unavailable on Linux. TMDL engine parsing, DAX evaluation, rendering/font fallback, CSV refresh, navigation and interactive cross-filter behavior still require Windows verification. The generic PBIR schema allows extensible native formatting properties, so schema validation alone cannot prove those objects render as intended. The Windows CSV parameter must point to the new local export folder. See [opening and acceptance instructions](aerocie-028-commercial-dashboard.md).

These are synthetic acceptance benchmarks, not actuarial forecasts or underwriting authority. The draft must remain unmerged until the separately required Windows validation has been reviewed.
