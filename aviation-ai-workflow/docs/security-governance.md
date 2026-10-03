# Security & Governance

This checklist is intentionally conservative because aviation, insurance, and reinsurance workflows can involve confidential commercial information and consequential decisions.

## Data governance

Before using customer information:

- classify the data involved;
- confirm the customer has authorized the intended processing;
- minimize fields sent to the model;
- document approved and prohibited data sources;
- define retention and deletion requirements;
- segregate customer environments and files as appropriate; and
- do not use personal or confidential data in public demonstrations.

This repository contains **synthetic data only**.

## Identity and access

A production deployment should use customer-approved identity controls and least privilege. Separate administrative, developer, reviewer, and end-user permissions where appropriate.

API credentials belong in an approved secret-management mechanism, not source control.

## Human authority

The system must not independently quote or bind coverage, set or approve price, deploy insurance/reinsurance capacity, make final claims or coverage determinations, make legal or sanctions determinations, or bypass required referral/underwriting authority.

Model output should be treated as decision support and reviewed by authorized personnel.

## Auditability

For material workflows, consider recording source-document identifiers and versions, workflow/input version, model and prompt/configuration version, output, validation results, reviewer role, reviewer changes or override, and final workflow disposition.

Logging should itself comply with confidentiality and retention requirements.

## Output quality controls

Test representative cases for extraction accuracy, omissions, unsupported claims, arithmetic or unit errors, contradictory-source handling, missing-information detection, wording/FAC exception identification, escalation behavior, and malicious-document or prompt-injection behavior when document ingestion is added.

## Security review before production

Customer technical and security stakeholders should evaluate authentication and authorization, secret handling, network and integration boundaries, encryption requirements, data processing requirements where applicable, logging and monitoring, incident response, vulnerability and dependency management, environment separation, business continuity, and release controls.

## AI governance

Document permitted and prohibited use cases, business owner, technical owner, output reviewer, escalation path, validation criteria, change-approval process, and periodic review cadence.

## Third parties and delivery capacity

Where specialized delivery capacity is required, StrategicRisk Partners should scope responsibilities clearly and use qualified contractors or delivery partners with appropriate customer disclosure, confidentiality obligations, access controls, and oversight.

## Commercial boundary

This reference implementation is a StrategicRisk Partners professional-services demonstration. OpenAI service purchasing, commercial terms, and customer agreements are separate from StrategicRisk Partners' own advisory or implementation services.