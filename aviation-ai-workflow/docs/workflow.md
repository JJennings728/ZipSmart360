# Workflow Definition

## Candidate workflow

**Aviation submission and evidence reconciliation before the underwriting decision**

### Current-state hypothesis to validate

Aviation underwriting teams may receive information across broker submissions, aircraft schedules, policy/certificate records, operator-authority material, aircraft records, loss histories, event data, pilot information, and supporting correspondence.

The customer may spend meaningful time locating records, comparing fields, resolving mismatches, identifying missing evidence, and preparing a review-ready file before a senior underwriter makes a decision.

This remains a hypothesis until validated with actual customer users.

## Proof-of-value target

Test whether a controlled workflow can:

1. normalize selected fields from supplied evidence;
2. reconcile identity, aircraft, certificate, event, filing-evidence, and submission-completeness facts;
3. surface evidence-backed exceptions using conservative statuses;
4. prepare a structured AI-assisted summary without overriding deterministic results; and
5. preserve explicit human disposition before consequential action.

## Bundled synthetic case

The PrairieJet synthetic case uses a submission plus five supporting evidence sources. Seven exception rules are intentionally planted:

- `R-020` requested liability limit vs. certificate evidence;
- `R-030` aircraft-scope mismatch;
- `R-031` registration / serial mismatch;
- `R-041` missing filing receipt evidence;
- `R-054` external event not reconciled to submitted loss history;
- `R-060` missing supporting documents; and
- `R-070` synthetic delegated-authority referral conditions.

The answer key exists only to evaluate the prototype. It is not a claim about production accuracy.

## Suggested design-partner scope

A real design partnership can begin with one narrow aviation workflow and a representative, customer-approved test set.

### Weeks 1–2 — discovery and answer key

- map the current review workflow;
- identify authoritative source systems and documents;
- define exactly which fields and mismatches matter;
- select 20–50 representative historical or synthetic cases;
- create a reviewer-approved answer key;
- agree human-review and escalation rules; and
- agree baseline and success metrics.

### Weeks 3–5 — controlled implementation

- map customer evidence into the normalized case schema;
- configure deterministic reconciliation rules;
- implement customer-specific evidence references;
- validate access/security boundaries;
- test AI synthesis against reconciled evidence; and
- run failure-mode and unsupported-claim tests.

### Weeks 6–8 — evaluation

- compare assisted output against the answer key;
- measure extraction and reconciliation accuracy;
- measure false positives / unnecessary referrals;
- measure unsupported-claim rate;
- compare review cycle time against the agreed baseline;
- gather reviewer usefulness ratings; and
- document required product iterations.

### Optional weeks 9–12 — iteration and scale assessment

- refine rules and interfaces;
- test additional business segments or evidence sources;
- assess integration effort;
- define production operating model;
- estimate security, support, and implementation requirements; and
- prepare a commercial scale/no-scale recommendation.

## Evidence to capture in discovery

| Area | Evidence to capture |
|---|---|
| Customer problem | What business problem is the customer trying to solve? |
| Workflow pain | Where does delay, rework, searching, inconsistency, or manual effort occur? |
| Owner | Who owns the workflow and desired outcome? |
| Affected users | Who performs or receives the work? |
| Impact signal | Time, backlog, rework, errors, service delay, quality, cost, or risk |
| Authoritative data | Which systems/documents govern each field? |
| Reconciliation rules | What exact mismatch should produce what review state? |
| Governance | Human approval, audit, privacy, security, compliance, retention |
| Success criteria | What would constitute a useful proof of value? |
| Next step | What has the customer actually agreed to do? |

## Proposed measures

Do not promise improvements before measuring a baseline.

Potential measures:

- field extraction accuracy;
- aircraft/entity reconciliation accuracy;
- known-exception recall;
- false-positive rate;
- unsupported-claim rate;
- reviewer correction rate;
- percentage of observations traceable to evidence;
- time to prepare a review package;
- number of source files/screens manually reviewed;
- reviewer usefulness score; and
- percentage of consequential actions that preserve required human approval.

## Human-control boundary

The system does not independently:

- quote or bind;
- set or approve price;
- deploy capacity;
- accept or decline risk;
- determine coverage;
- determine whether a regulatory requirement is legally satisfied;
- determine sanctions status;
- decide claims; or
- make actuarial, engineering, or catastrophe-model conclusions.

## Exit criteria

A proof of value should proceed toward production only when:

- the workflow owner confirms the use case remains valuable;
- output quality meets agreed criteria;
- evidence lineage is adequate;
- security/governance requirements can be satisfied;
- the human-review operating model is accepted;
- integration dependencies are understood;
- ownership/support responsibilities are defined; and
- both parties agree there is a credible commercial pathway beyond the experiment.
