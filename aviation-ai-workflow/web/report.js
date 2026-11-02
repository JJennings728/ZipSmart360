(() => {
  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const normalizeStatus = (value) =>
    String(value || "review").replaceAll("_", " ");

  const titleCase = (value) =>
    String(value || "review item")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const formatUsd = (value) => {
    const amount = Number(value);
    if (!Number.isFinite(amount)) return "—";
    if (Math.abs(amount) >= 1_000_000_000) return "$" + (amount / 1_000_000_000).toFixed(2).replace(/\.00$/, "") + "B";
    if (Math.abs(amount) >= 1_000_000) return "$" + (amount / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
    if (Math.abs(amount) >= 1_000) return "$" + (amount / 1_000).toFixed(1).replace(/\.0$/, "") + "K";
    return "$" + amount.toLocaleString();
  };

  const formatNumber = (value) => {
    const number = Number(value);
    return Number.isFinite(number) ? number.toLocaleString() : "—";
  };

  const formatPercent = (value) => {
    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(1).replace(/\.0$/, "") + "%" : "—";
  };

  const listHtml = (items, emptyText) => {
    const values = Array.isArray(items) ? items : [];
    if (!values.length) {
      return `<p class="empty">${escapeHtml(emptyText)}</p>`;
    }
    return `<ul>${values.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  };

  const riskFlagsHtml = (flags) => {
    const values = Array.isArray(flags) ? flags : [];
    if (!values.length) {
      return '<p class="empty">No risk flags returned.</p>';
    }

    return values.map((flag) => `
      <article class="risk-item">
        <h3>${escapeHtml(titleCase(flag?.category))}</h3>
        <p><strong>Fact:</strong> ${escapeHtml(flag?.fact || "No fact supplied.")}</p>
        <p><strong>Why review:</strong> ${escapeHtml(flag?.why_review || "No rationale supplied.")}</p>
      </article>
    `).join("");
  };

  const reconciliationSourcesHtml = (sources) => {
    const values = Array.isArray(sources) ? sources : [];
    if (!values.length) return '<p class="empty">No supporting evidence package supplied.</p>';
    return '<div class="evidence-grid">' + values.map((item) => `
      <div class="evidence-card">
        <span>${escapeHtml(item?.source_id || "SOURCE")}</span>
        <strong>${escapeHtml(item?.name || item?.type || "Evidence source")}</strong>
        <small>${escapeHtml(normalizeStatus(item?.type || "evidence"))}</small>
      </div>`
    ).join("") + '</div>';
  };

  const reconciliationChecksHtml = (checks) => {
    const values = Array.isArray(checks) ? checks : [];
    if (!values.length) return '<p class="empty">No deterministic reconciliation checks were run.</p>';
    return '<table class="recon-table"><thead><tr><th>Rule</th><th>Check</th><th>Result</th><th>Summary</th></tr></thead><tbody>' +
      values.map((item) => `<tr>
        <td>${escapeHtml(item?.rule_id || "—")}</td>
        <td>${escapeHtml(item?.label || "Review")}</td>
        <td><span class="status">${escapeHtml(normalizeStatus(item?.status))}</span></td>
        <td>${escapeHtml(item?.summary || "")}</td>
      </tr>`).join("") + '</tbody></table>';
  };

  const reconciliationExceptionsHtml = (exceptions) => {
    const values = Array.isArray(exceptions) ? exceptions : [];
    if (!values.length) return '<p class="empty">No evidence-backed exceptions generated.</p>';
    return '<div class="exception-stack">' + values.map((item) => {
      const evidence = Array.isArray(item?.evidence) ? item.evidence : [];
      const evidenceHtml = evidence.length
        ? '<ul>' + evidence.map((entry) => `<li><strong>${escapeHtml(entry?.source_id || "SOURCE")}</strong> — ${escapeHtml(entry?.location || "record")}: ${escapeHtml(typeof entry?.value === "object" ? JSON.stringify(entry.value) : entry?.value ?? "Not supplied")}</li>`).join("") + '</ul>'
        : '<p class="empty">No evidence references supplied.</p>';
      return `<article class="exception">
        <div class="exception-head">
          <div><span>${escapeHtml(item?.exception_id || "EX")}</span><h3>${escapeHtml(item?.title || "Review exception")}</h3></div>
          <strong>${escapeHtml(normalizeStatus(item?.result_status))}</strong>
        </div>
        <p>${escapeHtml(item?.summary || "")}</p>
        ${evidenceHtml}
        <p class="disposition"><strong>Human disposition:</strong> ${escapeHtml(normalizeStatus(item?.status || "OPEN"))}</p>
      </article>`;
    }).join("") + '</div>';
  };

  const auditHtml = (events) => {
    const values = Array.isArray(events) ? events : [];
    if (!values.length) return '<p class="empty">No audit events recorded.</p>';
    return '<ol class="audit">' + values.map((item) => `<li><strong>${escapeHtml(item?.actor || "system")}</strong> — ${escapeHtml(item?.event || "")}</li>`).join("") + '</ol>';
  };

  const buildReportHtml = ({ payload, submission, sourceName, preview = false }) => {
    const review = payload?.review || {};
    const reconciliation = payload?.reconciliation || null;
    const readiness = review.submission_readiness || {};
    const exposure = review.exposure_summary || {};
    const hull = review.hull_asset_analysis || {};
    const authority = review.delegated_authority_review || {};
    const fac = review.fac_review || {};
    const humanRequired = review.human_review_required === true;
    const generatedAt = new Date().toLocaleString();
    const accountName = submission?.account?.name || "Submission";
    const submissionType = submission?.account?.submission_type || "Aviation / Specialty Insurance";
    const policyPeriod = submission?.account?.policy_period || "Not supplied";

    return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>StrategicRisk Partners Review Report - ${escapeHtml(accountName)}</title>
  <style>
    :root {
      --navy: #0b2538;
      --navy-2: #153c55;
      --ink: #12222f;
      --muted: #64727e;
      --line: #dce3e8;
      --surface: #ffffff;
      --bg: #f4f6f8;
      --accent: #2f789a;
      --warn-bg: #fff4dc;
      --warn-ink: #76500c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.55;
    }
    .page {
      max-width: 960px;
      margin: 0 auto;
      background: var(--surface);
      min-height: 100vh;
    }
    header {
      background: var(--navy);
      color: white;
      padding: 34px 42px 30px;
      border-bottom: 4px solid #5eb6d8;
    }
    .brand {
      font-weight: 800;
      letter-spacing: .02em;
      font-size: 15px;
    }
    .brand-sub {
      color: rgba(255,255,255,.66);
      font-size: 11px;
      margin-top: 2px;
      text-transform: uppercase;
      letter-spacing: .12em;
    }
    h1 {
      margin: 34px 0 8px;
      font-size: 32px;
      line-height: 1.08;
      letter-spacing: -.025em;
    }
    .subtitle {
      color: rgba(255,255,255,.72);
      max-width: 700px;
    }
    .meta {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 26px;
    }
    .meta div {
      border-top: 1px solid rgba(255,255,255,.22);
      padding-top: 10px;
    }
    .meta span {
      display: block;
      color: rgba(255,255,255,.55);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: .08em;
      margin-bottom: 3px;
    }
    .meta strong {
      font-size: 12px;
      font-weight: 700;
      overflow-wrap: anywhere;
    }
    main { padding: 34px 42px 48px; }
    .notice {
      border-left: 4px solid #c48a22;
      background: var(--warn-bg);
      color: var(--warn-ink);
      padding: 14px 16px;
      margin-bottom: 26px;
      font-size: 13px;
    }
    section {
      border-top: 1px solid var(--line);
      padding: 24px 0;
      break-inside: avoid;
    }
    section:first-of-type { border-top: 0; padding-top: 0; }
    .section-label {
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: .12em;
      font-weight: 800;
      font-size: 10px;
      margin-bottom: 7px;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 20px;
      letter-spacing: -.015em;
    }
    h3 {
      margin: 0 0 7px;
      font-size: 14px;
    }
    p { margin: 0; }
    p + p { margin-top: 8px; }
    ul { margin: 8px 0 0; padding-left: 20px; }
    li + li { margin-top: 6px; }
    .status-row {
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }
    .status {
      border-radius: 999px;
      background: #eef3f6;
      color: var(--navy-2);
      padding: 5px 9px;
      font-size: 11px;
      font-weight: 800;
      text-transform: capitalize;
    }
    .human {
      border: 1px solid #e1c27c;
      background: #fff9e9;
      padding: 16px;
    }
    .human strong {
      color: #6e4a0b;
      display: block;
      margin-bottom: 5px;
    }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 16px;
    }
    .metric {
      border: 1px solid var(--line);
      background: #fafcfd;
      padding: 12px;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: .08em;
      margin-bottom: 5px;
    }
    .metric strong {
      font-size: 16px;
      color: var(--navy);
    }
    .disclaimer {
      margin-top: 12px;
      padding-top: 10px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 11px;
    }
    .risk-list {
      display: grid;
      gap: 10px;
    }
    .risk-item {
      padding: 14px;
      border: 1px solid var(--line);
      border-left: 3px solid #7897a9;
      background: #fafcfd;
      break-inside: avoid;
    }
    .risk-item p {
      color: #425563;
      font-size: 13px;
    }
    .evidence-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }
    .evidence-card {
      border: 1px solid var(--line);
      background: #fafcfd;
      padding: 10px;
      display: grid;
      gap: 3px;
    }
    .evidence-card span {
      color: var(--accent);
      font-size: 9px;
      font-weight: 800;
      letter-spacing: .08em;
    }
    .evidence-card strong { font-size: 11px; line-height: 1.35; }
    .evidence-card small { color: var(--muted); }
    .recon-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 10px;
    }
    .recon-table th, .recon-table td {
      text-align: left;
      padding: 8px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }
    .recon-table th {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .06em;
      font-size: 8px;
    }
    .exception-stack { display: grid; gap: 10px; }
    .exception {
      border: 1px solid var(--line);
      border-left: 3px solid #b98a2f;
      padding: 12px;
      background: #fffdfa;
      break-inside: avoid;
    }
    .exception-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }
    .exception-head span {
      color: var(--accent);
      font-size: 9px;
      font-weight: 800;
      letter-spacing: .08em;
    }
    .exception-head h3 { margin-top: 3px; }
    .exception ul { font-size: 10px; color: var(--muted); }
    .disposition {
      margin-top: 9px;
      padding-top: 8px;
      border-top: 1px solid var(--line);
      font-size: 10px;
    }
    .audit { font-size: 10px; color: #425563; }
    .audit strong { color: var(--accent); text-transform: uppercase; font-size: 9px; }
    .empty { color: var(--muted); font-style: italic; }
    .next-action {
      background: #f4f9fb;
      border: 1px solid #c9dce6;
      padding: 16px;
      font-weight: 650;
    }
    footer {
      padding: 20px 42px 30px;
      color: var(--muted);
      font-size: 10px;
      border-top: 1px solid var(--line);
    }
    .screen-actions {
      max-width: 960px;
      margin: 18px auto;
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }
    .screen-actions button {
      border: 1px solid var(--navy);
      background: var(--navy);
      color: white;
      padding: 10px 14px;
      font: inherit;
      font-weight: 750;
      cursor: pointer;
    }
    .screen-actions button.secondary {
      background: white;
      color: var(--navy);
    }
    ${preview ? ".screen-actions { display: none !important; }" : ""}
    @media (max-width: 700px) {
      header, main, footer { padding-left: 22px; padding-right: 22px; }
      .meta { grid-template-columns: 1fr 1fr; }
      .screen-actions { padding: 0 16px; }
    }
    @media print {
      @page { size: Letter; margin: .55in; }
      body { background: white; }
      .page { max-width: none; min-height: auto; }
      .screen-actions { display: none !important; }
      header {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
      .notice, .human, .next-action, .risk-item {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
    }
  </style>
</head>
<body>
  <div class="screen-actions">
    <button class="secondary" onclick="window.close()">Close</button>
    <button onclick="window.print()">Print / Save as PDF</button>
  </div>

  <div class="page">
    <header>
      <div class="brand">StrategicRisk Partners</div>
      <div class="brand-sub">Aviation &amp; Specialty Insurance</div>
      <h1>AI-Assisted Submission Review Report</h1>
      <p class="subtitle">Structured decision-support output for authorized human review.</p>

      <div class="meta">
        <div><span>Account</span><strong>${escapeHtml(accountName)}</strong></div>
        <div><span>Submission type</span><strong>${escapeHtml(submissionType)}</strong></div>
        <div><span>Policy period</span><strong>${escapeHtml(policyPeriod)}</strong></div>
        <div><span>Generated</span><strong>${escapeHtml(generatedAt)}</strong></div>
      </div>
    </header>

    <main>
      <div class="notice">
        <strong>Decision-support only.</strong> This report does not quote, bind, price, deploy capacity, make coverage or claims determinations, or replace qualified underwriting, reinsurance, legal, sanctions, regulatory, engineering, actuarial, or catastrophe-model review.
      </div>

      ${reconciliation ? `
      <section>
        <div class="section-label">00A · Evidence package</div>
        <h2>Evidence reconciliation</h2>
        <p>${escapeHtml(reconciliation.disclaimer || "")}</p>
        <div class="metric-grid">
          <div class="metric"><span>Sources</span><strong>${escapeHtml(formatNumber(reconciliation.summary?.source_count))}</strong></div>
          <div class="metric"><span>Checks</span><strong>${escapeHtml(formatNumber(reconciliation.summary?.check_count))}</strong></div>
          <div class="metric"><span>Verified</span><strong>${escapeHtml(formatNumber(reconciliation.summary?.verified_count))}</strong></div>
          <div class="metric"><span>Exceptions</span><strong>${escapeHtml(formatNumber(reconciliation.summary?.exception_count))}</strong></div>
          <div class="metric"><span>Aircraft reconciled</span><strong>${escapeHtml(String(reconciliation.summary?.aircraft_reconciled_to_certificate ?? "—") + "/" + String(reconciliation.summary?.aircraft_total ?? "—"))}</strong></div>
          <div class="metric"><span>Ground-truth detection</span><strong>${escapeHtml(formatPercent(reconciliation.evaluation?.detection_rate_percent))}</strong></div>
        </div>
        <h3 style="margin-top:18px">Evidence sources</h3>
        ${reconciliationSourcesHtml(reconciliation.sources)}
      </section>

      <section>
        <div class="section-label">00B · Deterministic checks</div>
        <h2>Reconciliation checks</h2>
        ${reconciliationChecksHtml(reconciliation.checks)}
      </section>

      <section>
        <div class="section-label">00C · Exception register</div>
        <h2>Evidence-backed exceptions</h2>
        ${reconciliationExceptionsHtml(reconciliation.exceptions)}
      </section>

      <section>
        <div class="section-label">00D · Audit trail</div>
        <h2>Reviewer and system activity</h2>
        ${auditHtml(reconciliation.audit_events)}
      </section>
      ` : ""}

      <section>
        <div class="section-label">01 · Submission readiness</div>
        <div class="status-row">
          <h2>Submission readiness</h2>
          <span class="status">${escapeHtml(normalizeStatus(readiness.status))}</span>
        </div>
        <p>${escapeHtml(readiness.summary || "No readiness summary returned.")}</p>
      </section>

      <section>
        <div class="section-label">02 · Exposure summary</div>
        <h2>Commercial aviation exposure</h2>
        <p>${escapeHtml(exposure.summary || "No exposure summary returned.")}</p>
        <div class="metric-grid">
          <div class="metric"><span>Aircraft</span><strong>${escapeHtml(formatNumber(exposure.aircraft_count))}</strong></div>
          <div class="metric"><span>Hull TIV</span><strong>${escapeHtml(formatUsd(exposure.total_hull_value_usd))}</strong></div>
          <div class="metric"><span>Largest hull</span><strong>${escapeHtml(formatUsd(exposure.largest_single_aircraft_hull_usd))}</strong></div>
          <div class="metric"><span>Liability request</span><strong>${escapeHtml(formatUsd(exposure.requested_liability_limit_usd))}</strong></div>
          <div class="metric"><span>Projected hours</span><strong>${escapeHtml(formatNumber(exposure.projected_flight_hours))}</strong></div>
          <div class="metric"><span>Utilization change</span><strong>${escapeHtml(formatPercent(exposure.utilization_change_percent))}</strong></div>
        </div>
      </section>

      <section>
        <div class="section-label">03 · Hull and asset analysis</div>
        <div class="status-row">
          <h2>Hull &amp; asset analysis</h2>
          <span class="status">${escapeHtml(normalizeStatus(hull.status))}</span>
        </div>
        <p>${escapeHtml(hull.summary || "No hull analysis returned.")}</p>
        ${listHtml(hull.issues, "No hull or asset issues returned.")}
      </section>

      <section>
        <div class="section-label">04 · Missing information</div>
        <h2>Missing information</h2>
        ${listHtml(review.missing_information, "No missing information returned.")}
      </section>

      <section>
        <div class="section-label">05 · Risk flags</div>
        <h2>Risk flags</h2>
        <div class="risk-list">${riskFlagsHtml(review.risk_flags)}</div>
      </section>

      <section>
        <div class="section-label">06 · Delegated authority and referral</div>
        <div class="status-row">
          <h2>Authority &amp; referral review</h2>
          <span class="status">${escapeHtml(normalizeStatus(authority.status))}</span>
        </div>
        <p>${escapeHtml(authority.summary || "No authority review returned.")}</p>
        ${listHtml(authority.reasons, "No referral reasons returned.")}
        <p class="disclaimer">${escapeHtml(authority.disclaimer || "")}</p>
      </section>

      <section>
        <div class="section-label">07 · Facultative review</div>
        <h2>FAC review</h2>
        <p>${escapeHtml(fac.summary || "No FAC review summary returned.")}</p>
        ${listHtml(fac.issues, "No FAC issues returned.")}
      </section>

      <section>
        <div class="section-label">08 · Human control</div>
        <h2>Human review required</h2>
        <div class="human">
          <strong>${humanRequired ? "Required" : "Expected control not confirmed"}</strong>
          <p>${humanRequired
            ? "An authorized human reviewer is required before any consequential underwriting or reinsurance action."
            : "The expected human-review control was not returned. Treat this review package as invalid until the control is restored."}</p>
        </div>
      </section>

      <section>
        <div class="section-label">09 · Next action</div>
        <h2>Recommended next action</h2>
        <div class="next-action">${escapeHtml(review.recommended_next_action || "No next action returned.")}</div>
      </section>
    </main>

    <footer>
      Source: ${escapeHtml(sourceName || "Uploaded submission")} · Generated by the StrategicRisk Partners aviation AI workflow reference implementation. Synthetic or customer-approved data only.
    </footer>
  </div>
</body>
</html>`;
  };

  const safeFilenamePart = (value) =>
    String(value || "submission")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "submission";

  const reportFilename = (submission) => {
    const account = safeFilenamePart(submission?.account?.name);
    const date = new Date().toISOString().slice(0, 10);
    return `srisk-review-${account}-${date}.html`;
  };

  const downloadHtml = (context) => {
    const html = buildReportHtml(context);
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = reportFilename(context?.submission);
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  const printPdf = (context) => {
    const html = buildReportHtml(context);
    const reportWindow = window.open("", "_blank", "noopener,noreferrer");

    if (!reportWindow) {
      throw new Error("The browser blocked the report window. Allow pop-ups for this demo and try again.");
    }

    reportWindow.document.open();
    reportWindow.document.write(html);
    reportWindow.document.close();
    reportWindow.focus();

    window.setTimeout(() => {
      try {
        reportWindow.print();
      } catch (_) {
        // The report remains open so the user can print manually.
      }
    }, 350);
  };

  window.SRiskReport = {
    buildReportHtml,
    downloadHtml,
    printPdf,
  };
})();
