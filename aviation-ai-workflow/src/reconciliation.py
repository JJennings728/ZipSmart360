from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


STATUS_VERIFIED = "VERIFIED"
STATUS_MISSING = "MISSING_EVIDENCE"
STATUS_MISMATCH = "MISMATCH"
STATUS_UNRESOLVED = "UNRESOLVED"
STATUS_REFER = "REFER"

EXCEPTION_STATUSES = {STATUS_MISSING, STATUS_MISMATCH, STATUS_UNRESOLVED, STATUS_REFER}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _reg(value: Any) -> str:
    value = str(value or "").strip().upper().replace(" ", "").replace("-", "")
    if value and not value.startswith("N"):
        value = "N" + value
    return value


def _ev(source_id: str, location: str, value: Any = None) -> dict[str, Any]:
    item: dict[str, Any] = {"source_id": source_id, "location": location}
    if value is not None:
        item["value"] = value
    return item


def _check(
    rule_id: str,
    label: str,
    status: str,
    summary: str,
    evidence: list[dict[str, Any]],
    *,
    severity: str = "INFO",
    category: str | None = None,
    suggested_action: str | None = None,
    subject: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "rule_id": rule_id,
        "label": label,
        "status": status,
        "summary": summary,
        "severity": severity,
        "evidence": evidence,
    }
    if category:
        result["category"] = category
    if suggested_action:
        result["suggested_action"] = suggested_action
    if subject:
        result["subject"] = subject
    return result


def _submission_aircraft(submission: dict[str, Any]) -> list[dict[str, Any]]:
    exposures = submission.get("exposures") or {}
    values = exposures.get("aircraft_schedule") or []
    return [row for row in values if isinstance(row, dict)]


def _known_missing_documents(submission: dict[str, Any]) -> list[str]:
    block = submission.get("submission") or {}
    missing: list[str] = []
    if not isinstance(block, dict):
        return missing
    for key, value in block.items():
        if key.endswith("_received") and value is False:
            missing.append(key.removesuffix("_received").replace("_", " "))
    return missing


def reconcile_case(
    submission: dict[str, Any],
    evidence_package: dict[str, Any] | None,
) -> dict[str, Any]:
    """Deterministically reconcile a synthetic aviation submission against evidence.

    The function deliberately avoids regulatory/legal conclusions. It returns
    evidence-backed matches, mismatches, missing evidence, unresolved items, and
    referral conditions for human review.
    """
    evidence_package = evidence_package or {}
    checks: list[dict[str, Any]] = []

    account = submission.get("account") or {}
    authority = evidence_package.get("operator_authority") or {}
    certificate = evidence_package.get("insurance_certificate") or {}
    registry = evidence_package.get("faa_registry") or {}
    events = evidence_package.get("aviation_events") or []
    filing_events = evidence_package.get("filing_events") or []

    submission_name = account.get("legal_name") or account.get("name")
    authority_name = authority.get("legal_name")
    certificate_name = certificate.get("legal_name")

    names = [_norm(v) for v in (submission_name, authority_name, certificate_name) if v]
    identity_status = STATUS_VERIFIED if len(names) >= 2 and len(set(names)) == 1 else STATUS_MISMATCH
    checks.append(_check(
        "R-001",
        "Operator identity reconciliation",
        identity_status,
        (
            "Submission, authority record, and insurance certificate identify the same legal entity."
            if identity_status == STATUS_VERIFIED
            else "The supplied records do not reconcile to one normalized legal entity name."
        ),
        [
            _ev("SUB-001", "account.legal_name", submission_name),
            _ev("AUTH-001", "operator_authority.legal_name", authority_name),
            _ev("INS-001", "insurance_certificate.legal_name", certificate_name),
        ],
        severity="HIGH" if identity_status != STATUS_VERIFIED else "INFO",
        category="identity",
        suggested_action="Confirm the legal insured/operator identity before consequential action.",
    ))

    cert_values = [
        account.get("faa_certificate_number"),
        authority.get("faa_certificate_number"),
        certificate.get("faa_certificate_number"),
    ]
    present_cert_values = [_norm(v) for v in cert_values if v]
    cert_status = (
        STATUS_VERIFIED
        if len(present_cert_values) >= 2 and len(set(present_cert_values)) == 1
        else STATUS_MISMATCH
    )
    checks.append(_check(
        "R-002",
        "FAA certificate number reconciliation",
        cert_status,
        (
            "FAA certificate number reconciles across supplied records."
            if cert_status == STATUS_VERIFIED
            else "FAA certificate number does not reconcile across supplied records."
        ),
        [
            _ev("SUB-001", "account.faa_certificate_number", account.get("faa_certificate_number")),
            _ev("AUTH-001", "operator_authority.faa_certificate_number", authority.get("faa_certificate_number")),
            _ev("INS-001", "insurance_certificate.faa_certificate_number", certificate.get("faa_certificate_number")),
        ],
        severity="HIGH" if cert_status != STATUS_VERIFIED else "INFO",
        category="identity",
        suggested_action="Confirm the correct FAA certificate identifier.",
    ))

    cert_active = _norm(certificate.get("status")) == "active"
    checks.append(_check(
        "R-010",
        "Insurance certificate evidence",
        STATUS_VERIFIED if cert_active else STATUS_MISSING,
        (
            "A supplied synthetic OST 6410 record is marked active."
            if cert_active
            else "Active insurance-certificate evidence was not supplied."
        ),
        [
            _ev("INS-001", "insurance_certificate.form", certificate.get("form")),
            _ev("INS-001", "insurance_certificate.status", certificate.get("status")),
        ],
        severity="HIGH" if not cert_active else "INFO",
        category="insurance_certificate",
        suggested_action="Obtain current certificate evidence for human review.",
    ))

    requested_limit = (
        (submission.get("exposures") or {})
        .get("liability", {})
        .get("requested_combined_single_limit_usd")
    )
    certificate_limit = (
        (certificate.get("coverage") or {}).get("combined_single_limit_usd")
    )
    if isinstance(requested_limit, (int, float)) and isinstance(certificate_limit, (int, float)):
        limit_status = STATUS_REFER if requested_limit > certificate_limit else STATUS_VERIFIED
        limit_summary = (
            f"Requested liability limit of USD {requested_limit:,.0f} exceeds the USD "
            f"{certificate_limit:,.0f} limit shown on the supplied synthetic certificate evidence."
            if limit_status == STATUS_REFER
            else "Requested liability limit does not exceed the limit shown on the supplied certificate evidence."
        )
    else:
        limit_status = STATUS_MISSING
        limit_summary = "Requested and certificate liability limits cannot both be established from supplied evidence."
    checks.append(_check(
        "R-020",
        "Requested limit vs. certificate evidence",
        limit_status,
        limit_summary,
        [
            _ev("SUB-001", "exposures.liability.requested_combined_single_limit_usd", requested_limit),
            _ev("INS-001", "insurance_certificate.coverage.combined_single_limit_usd", certificate_limit),
        ],
        severity="HIGH" if limit_status != STATUS_VERIFIED else "INFO",
        category="coverage_reconciliation",
        suggested_action=(
            "Route to an authorized reviewer to determine required documentation, program structure, and certificate treatment."
            if limit_status != STATUS_VERIFIED else None
        ),
    ))

    aircraft_rows = _submission_aircraft(submission)
    submission_by_reg = {_reg(row.get("registration")): row for row in aircraft_rows if row.get("registration")}
    cert_scope = certificate.get("aircraft_scope") or {}
    certificate_regs = {_reg(v) for v in (cert_scope.get("registrations") or []) if v}
    missing_from_certificate = sorted(set(submission_by_reg) - certificate_regs)
    extra_on_certificate = sorted(certificate_regs - set(submission_by_reg))

    if missing_from_certificate or extra_on_certificate:
        aircraft_scope_status = STATUS_MISMATCH
        aircraft_scope_summary = (
            f"{len(submission_by_reg) - len(missing_from_certificate)} of {len(submission_by_reg)} "
            "submitted aircraft reconcile to the supplied specific-aircraft certificate schedule."
        )
    else:
        aircraft_scope_status = STATUS_VERIFIED
        aircraft_scope_summary = f"All {len(submission_by_reg)} submitted aircraft reconcile to certificate scope."

    checks.append(_check(
        "R-030",
        "Aircraft scope reconciliation",
        aircraft_scope_status,
        aircraft_scope_summary,
        [
            _ev("SUB-001", "exposures.aircraft_schedule", sorted(submission_by_reg)),
            _ev("INS-001", "insurance_certificate.aircraft_scope.registrations", sorted(certificate_regs)),
        ],
        severity="HIGH" if aircraft_scope_status != STATUS_VERIFIED else "INFO",
        category="aircraft_scope",
        subject=", ".join(missing_from_certificate) if missing_from_certificate else None,
        suggested_action=(
            "Confirm whether omitted or extra aircraft require updated evidence or other authorized review."
            if aircraft_scope_status != STATUS_VERIFIED else None
        ),
    ))

    registry_rows = registry.get("records") or []
    registry_by_reg = {
        _reg(row.get("registration")): row
        for row in registry_rows
        if isinstance(row, dict) and row.get("registration")
    }
    serial_mismatches: list[str] = []
    registry_missing: list[str] = []
    inactive_regs: list[str] = []

    for reg, submitted in submission_by_reg.items():
        registry_row = registry_by_reg.get(reg)
        if not registry_row:
            registry_missing.append(reg)
            continue
        if _norm(submitted.get("serial_number")) != _norm(registry_row.get("serial_number")):
            serial_mismatches.append(reg)
        if _norm(registry_row.get("status")) != "active":
            inactive_regs.append(reg)

    serial_status = STATUS_MISMATCH if serial_mismatches else (STATUS_MISSING if registry_missing else STATUS_VERIFIED)
    serial_bits: list[str] = []
    if serial_mismatches:
        serial_bits.append(f"serial mismatch: {', '.join(serial_mismatches)}")
    if registry_missing:
        serial_bits.append(f"registry evidence missing: {', '.join(registry_missing)}")
    serial_summary = (
        "FAA-style registry evidence reconciles to submitted registrations and serial numbers."
        if serial_status == STATUS_VERIFIED
        else "Aircraft registry reconciliation requires review (" + "; ".join(serial_bits) + ")."
    )
    checks.append(_check(
        "R-031",
        "Aircraft registration and serial reconciliation",
        serial_status,
        serial_summary,
        [
            _ev("SUB-001", "exposures.aircraft_schedule", f"{len(submission_by_reg)} aircraft"),
            _ev("FAA-001", "faa_registry.records", f"{len(registry_by_reg)} aircraft records"),
        ],
        severity="HIGH" if serial_status != STATUS_VERIFIED else "INFO",
        category="aircraft_identity",
        subject=", ".join(serial_mismatches or registry_missing) or None,
        suggested_action="Verify aircraft identity against authoritative records before relying on the schedule.",
    ))

    registry_status = STATUS_REFER if inactive_regs else STATUS_VERIFIED
    checks.append(_check(
        "R-032",
        "Aircraft registry status review",
        registry_status,
        (
            "All supplied registry records are marked active."
            if registry_status == STATUS_VERIFIED
            else f"Registry status requires review for: {', '.join(inactive_regs)}."
        ),
        [_ev("FAA-001", "faa_registry.records.status", "active" if not inactive_regs else inactive_regs)],
        severity="MEDIUM" if registry_status != STATUS_VERIFIED else "INFO",
        category="aircraft_status",
        suggested_action="Confirm registry status and relevance with an authorized reviewer.",
    ))

    relevant_filings = [
        item for item in filing_events
        if isinstance(item, dict) and item.get("event_type") == "aircraft_schedule_change"
    ]
    missing_receipt = [item for item in relevant_filings if not item.get("agency_received_at")]
    filing_status = STATUS_MISSING if missing_receipt else STATUS_VERIFIED
    filing_subjects = [_reg(item.get("registration")) for item in missing_receipt if item.get("registration")]
    checks.append(_check(
        "R-041",
        "Aircraft-change filing evidence",
        filing_status,
        (
            "Agency receipt evidence is supplied for the synthetic aircraft-change record."
            if filing_status == STATUS_VERIFIED
            else "The aircraft-change record has an effective/sent date but no supplied agency receipt evidence."
        ),
        [
            _ev(
                item.get("source_id") or "FILE-001",
                "filing_events",
                {
                    "registration": item.get("registration"),
                    "effective_at": item.get("effective_at"),
                    "notice_sent_at": item.get("notice_sent_at"),
                    "agency_received_at": item.get("agency_received_at"),
                },
            )
            for item in (missing_receipt or relevant_filings)
        ],
        severity="MEDIUM" if filing_status != STATUS_VERIFIED else "INFO",
        category="filing_evidence",
        subject=", ".join(filing_subjects) or None,
        suggested_action=(
            "Obtain receipt/filing evidence and route timing significance to qualified regulatory review."
            if filing_status != STATUS_VERIFIED else None
        ),
    ))

    event_rows = [item for item in events if isinstance(item, dict)]
    matched_event_regs = sorted({_reg(item.get("registration")) for item in event_rows if _reg(item.get("registration")) in submission_by_reg})
    event_link_status = STATUS_VERIFIED if len(matched_event_regs) == len(event_rows) else STATUS_UNRESOLVED
    checks.append(_check(
        "R-050",
        "External event aircraft linkage",
        event_link_status,
        (
            "External-event registrations link to aircraft in the submitted schedule."
            if event_link_status == STATUS_VERIFIED
            else "One or more external-event registrations cannot be linked to the submitted aircraft schedule."
        ),
        [_ev("EVT-001", "aviation_events.registration", [item.get("registration") for item in event_rows])],
        severity="MEDIUM" if event_link_status != STATUS_VERIFIED else "INFO",
        category="external_event",
        suggested_action="Resolve aircraft identity before interpreting event context.",
    ))

    losses = submission.get("loss_history") or []
    reconciled_event_keys = {
        (_reg(loss.get("registration")), str(loss.get("event_date") or ""))
        for loss in losses
        if isinstance(loss, dict)
    }
    unmatched_events = [
        item for item in event_rows
        if (_reg(item.get("registration")), str(item.get("event_date") or "")) not in reconciled_event_keys
    ]
    event_loss_status = STATUS_UNRESOLVED if unmatched_events else STATUS_VERIFIED
    checks.append(_check(
        "R-054",
        "External event vs. submitted loss history",
        event_loss_status,
        (
            f"{len(unmatched_events)} external aviation event(s) are not reconciled to the submitted loss history."
            if unmatched_events
            else "Supplied external aviation events reconcile to submitted loss-history records."
        ),
        [
            _ev(
                item.get("source_id") or "EVT-001",
                "aviation_events",
                {
                    "registration": item.get("registration"),
                    "event_date": item.get("event_date"),
                    "event_type": item.get("event_type"),
                },
            )
            for item in unmatched_events
        ],
        severity="HIGH" if unmatched_events else "INFO",
        category="loss_history_reconciliation",
        subject=", ".join(sorted({_reg(item.get("registration")) for item in unmatched_events})) or None,
        suggested_action=(
            "Ask whether the external event corresponds to a claim, loss, or non-claim event; do not label it an undisclosed loss without confirmation."
            if unmatched_events else None
        ),
    ))

    missing_docs = _known_missing_documents(submission)
    docs_status = STATUS_MISSING if missing_docs else STATUS_VERIFIED
    checks.append(_check(
        "R-060",
        "Submission supporting evidence completeness",
        docs_status,
        (
            f"{len(missing_docs)} supporting item(s) are marked missing in the submitted package."
            if missing_docs
            else "No supporting items are explicitly marked missing."
        ),
        [_ev("SUB-001", "submission.*_received", missing_docs or "complete")],
        severity="MEDIUM" if missing_docs else "INFO",
        category="submission_completeness",
        suggested_action="Request missing evidence before consequential underwriting action." if missing_docs else None,
    ))

    authority_rules = submission.get("delegated_authority", {}).get("rules") or []
    breached_rules = [
        item for item in authority_rules
        if isinstance(item, dict) and _norm(item.get("comparison")) == "exceeded"
    ]
    authority_status = STATUS_REFER if breached_rules else STATUS_VERIFIED
    checks.append(_check(
        "R-070",
        "Synthetic delegated-authority referral conditions",
        authority_status,
        (
            f"{len(breached_rules)} supplied synthetic authority threshold(s) are exceeded."
            if breached_rules
            else "No supplied synthetic authority threshold is marked exceeded."
        ),
        [
            _ev("SUB-001", "delegated_authority.rules", [
                {
                    "rule": item.get("rule"),
                    "threshold": item.get("threshold"),
                    "submission_value": item.get("submission_value"),
                }
                for item in breached_rules
            ])
        ],
        severity="HIGH" if breached_rules else "INFO",
        category="delegated_authority",
        suggested_action=(
            "Route to the authorized underwriting/capacity reviewer. These are synthetic demonstration rules, not actual carrier appetite."
            if breached_rules else None
        ),
    ))

    exceptions: list[dict[str, Any]] = []
    for check in checks:
        if check["status"] not in EXCEPTION_STATUSES:
            continue
        exception_id = f"EX-{len(exceptions) + 1:03d}"
        exception = {
            "exception_id": exception_id,
            "rule_id": check["rule_id"],
            "status": "OPEN",
            "result_status": check["status"],
            "severity": check.get("severity", "MEDIUM"),
            "category": check.get("category", "review"),
            "title": check["label"],
            "summary": check["summary"],
            "subject": check.get("subject"),
            "evidence": check.get("evidence", []),
            "suggested_action": check.get("suggested_action"),
        }
        exceptions.append(exception)
        check["exception_id"] = exception_id

    expected_rule_ids = set(
        (evidence_package.get("ground_truth") or {}).get("expected_exception_rule_ids") or []
    )
    detected_rule_ids = {item["rule_id"] for item in exceptions}
    detected_expected = sorted(expected_rule_ids & detected_rule_ids)
    unexpected = sorted(detected_rule_ids - expected_rule_ids)
    missed = sorted(expected_rule_ids - detected_rule_ids)
    detection_rate = (
        round(len(detected_expected) / len(expected_rule_ids) * 100, 1)
        if expected_rule_ids else None
    )

    aircraft_reconciled = max(0, len(submission_by_reg) - len(missing_from_certificate))
    source_count = len(evidence_package.get("sources") or []) + 1  # submission is a source

    now = datetime.now(timezone.utc).isoformat()
    audit_events = [
        {"timestamp": now, "event": "Case loaded", "actor": "system"},
        {"timestamp": now, "event": f"{source_count} evidence sources registered", "actor": "system"},
        {"timestamp": now, "event": f"{len(checks)} deterministic reconciliation checks completed", "actor": "system"},
        {"timestamp": now, "event": f"{len(exceptions)} exception(s) generated for human review", "actor": "system"},
    ]

    return {
        "case_id": evidence_package.get("case_id") or "UNASSIGNED",
        "status": "REVIEW_REQUIRED" if exceptions else "NO_EXCEPTION_IDENTIFIED",
        "summary": {
            "source_count": source_count,
            "check_count": len(checks),
            "verified_count": sum(1 for item in checks if item["status"] == STATUS_VERIFIED),
            "exception_count": len(exceptions),
            "aircraft_total": len(submission_by_reg),
            "aircraft_reconciled_to_certificate": aircraft_reconciled,
        },
        "sources": [
            {
                "source_id": "SUB-001",
                "type": "underwriting_submission",
                "name": "Synthetic underwriting submission",
                "status": "LOADED",
            },
            *[
                {
                    "source_id": item.get("source_id"),
                    "type": item.get("type"),
                    "name": item.get("name"),
                    "status": "LOADED",
                }
                for item in (evidence_package.get("sources") or [])
                if isinstance(item, dict)
            ],
        ],
        "checks": checks,
        "exceptions": exceptions,
        "evaluation": {
            "ground_truth_available": bool(expected_rule_ids),
            "expected_exception_count": len(expected_rule_ids),
            "detected_expected_count": len(detected_expected),
            "detection_rate_percent": detection_rate,
            "missed_expected_rule_ids": missed,
            "unexpected_exception_rule_ids": unexpected,
            "note": (
                "Ground truth is synthetic and intentionally planted for prototype evaluation. "
                "It is not a customer performance claim."
            ),
        },
        "audit_events": audit_events,
        "disclaimer": (
            "This reconciliation identifies inconsistencies and missing evidence across supplied "
            "underwriting, policy, aircraft, event, and regulatory-style records. It does not "
            "constitute a legal determination of regulatory compliance."
        ),
    }
