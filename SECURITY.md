# Security and Responsible Disclosure

## Project status

ZIPSmart360 and the AeroCIE materials in this repository are **research, synthetic-data demonstrations, and development work**. They are not represented as a deployed, security-certified service, a validated actuarial model, or an FAA applicability determination. An open pull request is not released functionality.

## Reporting a security concern

Please report suspected security defects, exposed credentials, accidental private-data publication, or an unsafe source-integrity condition privately to **info@sriskpartners.com**. Include the affected repository/path, a reproducible explanation, expected impact, and non-sensitive reproduction steps. Do **not** include passwords, tokens, private customer data, or exploit material in a public GitHub issue.

No vulnerability-reward program, guaranteed response deadline, or permission to test third-party systems is offered by this document.

## Data and publication boundaries

- Do not commit personal ChatGPT conversations, personal financial or medical records, customer submissions, confidential pricing, legal documents, invoices, government registration correspondence, or proposal material.
- Never commit API keys, private keys, service-account files, passwords, connection strings, or production configuration; use secure local/managed configuration and rotate any exposed secret.
- Use synthetic, expressly permitted sample data in public code and reports.
- Keep proposal-stage business planning, prospect research, private communications, and unreleased product economics in controlled private records.
- Do not publicly describe source-link checks, manual review journals, or passed CI as independent authorization, compliance certification, FAA legal applicability, or production readiness.
- Review public pull-request bodies, comments, CI logs, and attachments for unintended disclosures before publication.

## Engineering review gates

Before a future release or external customer-data evaluation, verify relevant access control, provenance, privacy and retention requirements, supply-chain dependencies, security testing, human review, contractual authority, and independent technical acceptance. Record what was actually tested and what remains unverified.

.gitignore prevents many accidental additions but **does not protect content already tracked or present in Git history**. Historical remediation must be evaluated separately and may require credential rotation, a coordinated repository-history cleanup, and removal of cached or forked copies.

## Scope

Security reports relating to this repository can be submitted to **info@sriskpartners.com**. This file is a reporting and disclosure notice, not a guarantee of monitoring or a substitute for any customer-facing privacy policy or security agreement.
