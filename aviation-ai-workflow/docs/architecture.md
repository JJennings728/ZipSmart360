# Reference Architecture

## Objective

Demonstrate a controlled aviation underwriting-intelligence workflow that reconciles supplied evidence before any AI-assisted synthesis and preserves human authority over consequential decisions.

## Logical flow

    [Underwriting submission]
              +
    [Authority / insurance / aircraft / event / filing evidence]
              |
              v
    [Deterministic input validation]
              |
              v
    [Normalization + evidence indexing]
              |
              v
    [Versionable reconciliation rules]
              |
              +--> VERIFIED
              +--> MISSING_EVIDENCE
              +--> MISMATCH
              +--> UNRESOLVED
              +--> REFER
              |
              v
    [Evidence-backed exception register]
              |
              v
    [Controlled AI synthesis]
              |
              v
    [Authorized human reviewer]
              |
              +--> Request information
              +--> Underwriting referral
              +--> Regulatory filing review
              +--> Resolve / close
              |
              v
    [Audit trail + review package]

## Components

### 1. Case and source layer

The bundled proof of value uses a synthetic PrairieJet submission plus five supporting source types:

- synthetic Part 298 / operating-authority record;
- synthetic OST 6410-style insurance-certificate evidence;
- synthetic FAA-style aircraft registry snapshot;
- synthetic aviation event history; and
- synthetic aircraft-change filing evidence.

Each evidence reference carries a source identifier so a reviewer can see which supplied record supports a check or exception.

### 2. Deterministic pre-check

Before model use, the application checks required top-level submission sections and explicitly supplied missing-document indicators.

### 3. Deterministic reconciliation engine

`src/reconciliation.py` performs record comparison without a generative model. The reference rules include:

- `R-001` operator identity;
- `R-002` FAA certificate number;
- `R-010` insurance-certificate evidence;
- `R-020` requested liability limit vs. supplied certificate evidence;
- `R-030` aircraft scope;
- `R-031` aircraft registration / serial;
- `R-032` registry status;
- `R-041` aircraft-change filing evidence;
- `R-050` external-event aircraft linkage;
- `R-054` external event vs. submitted loss history;
- `R-060` supporting evidence completeness; and
- `R-070` synthetic delegated-authority referral conditions.

These rule outcomes are evidence-reconciliation states, not legal conclusions.

### 4. Exception register

Any MISSING_EVIDENCE, MISMATCH, UNRESOLVED, or REFER result becomes an exception with:

- exception ID;
- rule ID;
- severity;
- subject;
- evidence references;
- conservative review action; and
- human disposition state.

The browser prototype records human dispositions only for the current session; production persistence is intentionally out of scope.

### 5. Controlled AI synthesis

The reconciliation result is supplied to the AI-assisted review as context. The model is instructed not to override deterministic evidence states and not to turn an external aviation event into an insurance claim or “undisclosed loss” without evidence.

The AI layer remains responsible only for synthesis, review preparation, and explanation.

### 6. Evaluation layer

The bundled synthetic case contains a known answer key listing intentionally planted exception rules. This supports prototype evaluation such as:

- expected exceptions;
- detected expected exceptions;
- detection rate; and
- unexpected exception rules.

Synthetic ground-truth performance must not be presented as customer performance.

### 7. Human decision point

The prototype supports human dispositions such as request information, underwriting referral, regulatory filing review, resolve, or close with no action.

An authorized customer reviewer remains responsible for any consequential underwriting, pricing, capacity, coverage, claims, legal, regulatory, or sanctions decision.

### 8. Auditability

The prototype emits system audit events for case load, source registration, reconciliation execution, and exception generation. Reviewer dispositions are appended in the browser session.

A production implementation should persist source versions, rule versions, model/prompt versions, reviewer identity/role, overrides, final disposition, and timestamps in an append-oriented audit store.

## Production integration options

Depending on customer discovery, the workflow could become:

- an analyst-facing review application;
- an underwriting-workbench component;
- an API service feeding an existing policy/admin or underwriting system;
- a controlled pre-underwriting reconciliation service; or
- a design-partner sandbox integrated with customer-approved identity and data controls.

The correct deployment model should be selected only after customer workflow, security, data, governance, and integration requirements are validated.

## Failure handling

A production design should explicitly handle:

- unavailable or malformed source files;
- conflicting source records;
- extraction failure;
- stale source evidence;
- rule-engine errors;
- model/API errors;
- invalid output schemas;
- unsupported AI claims;
- missing reviewer authority; and
- unavailable downstream systems.

The safe default is to stop progression and route the item to human review.
