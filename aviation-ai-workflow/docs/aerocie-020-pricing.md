# AeroCIE proposed pricing | Discovery hypotheses

The figures below are pricing positions to test with aviation insurance buyers. They are not validated market-clearing prices or statements that the prototype presently delivers all proposed services.

| Package | Buyer | Proposed commercial price | Present product fit | Additional delivery requirements |
| --- | --- | --- | --- | --- |
| Paid evaluation | One MGA/coverholder underwriting desk | **$2,500 total / 60 days** | Synthetic case triage, source display, offline evidence and reporting tools | Written scope, data access authorization, evaluation, reviewer and process baseline |
| Starter | Specialized MGA, 1–3 reviewers | **$1,500–$2,500 / month** | Local SQL + Power BI research starter, advisory triage template | Secure authorized intake, licensed current sources, support and refresher operations |
| Growth | Multi-underwriter MGA or E&S desk | **$4,500–$7,500 / month** | Unified research architecture is in development | Stable feeds, bespoke underwriting controls, integration, support and service targets |
| Enterprise | Large carrier or syndicate | **$15,000–$25,000+ / month**, possible onboarding fee | Future product tier | Security reviews, SSO, audit controls, cloud warehouse integrations, contractual SLAs and validated models |

A volume limit, overage charge, seat count or service-level obligation should be included only after operating costs and actual delivered capabilities are defined. Do not state unlimited automated quote decisions or live MRO data availability for the current prototype.

## Pricing discovery sequence

1. Ask the underwriter to describe one recent difficult submission and its actual evidence review process.
2. Obtain the last quarter's submission volume, paired analyst minutes, hourly loaded cost, and an appropriately bounded example of MRO exposure.
3. Model their operational cost using `src/aerocie/pilot_economics.py`. Label any avoidable claim amount as an unverified scenario unless there is evidence of a causal prevention mechanism.
4. Offer the 60-day evaluation with mutually defined data, outcome labels, timing study and review checkpoints.
5. Review actual results. Negotiate a subscription or stop the engagement based on observed buyer value.

Example: at 100 submissions/month, 40 minutes of baseline analyst effort, 15 minutes with AeroCIE, $65/hour loaded analyst cost, $5,000/month subscription and $750/month data/support costs, modeled gross labor value is **$2,708.33/month** against **$5,750/month** recurring costs. This is a *negative* modeled monthly operating benefit of **$3,041.67**. At those assumptions approximately **213 submissions/month** are needed for labor savings alone to cover recurring costs. This example does not value improved underwriting decisions or reduced losses.

## Revenue arithmetic

- One $5,000/month contract contributes **$60,000 contracted annualized subscription value** when active for 12 months.
- Three such contracts contribute **$180,000 annualized recurring revenue**, contingent on active signed contracts and collections, not on marketing commitments or pilot enrollment.
- Enterprise close-rate claims, customer retention, actuarial benefit and valuation multiples require evidence; do not represent them as proven AeroCIE results.

## Positioning

AeroCIE sells transparent aviation research and underwriting workflow support. The buyer controls eligibility, quoting, coverage and pricing decisions. Sell traceability, usable analyst time and properly measured business value; avoid presenting a heuristic triage score as a calibrated actuarial loss predictor.
