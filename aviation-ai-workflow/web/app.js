let submissionData = null;
let evidenceData = null;
let latestAnalysisPayload = null;
let submissionSourceName = "Uploaded submission";
let exceptionDispositions = {};
let sessionAuditEvents = [];

const $ = (id) => document.getElementById(id);

const fileInput = $('fileInput');
const dropZone = $('dropZone');
const fileRow = $('fileRow');
const fileName = $('fileName');
const fileMeta = $('fileMeta');
const clearButton = $('clearButton');
const loadSampleButton = $('loadSampleButton');
const landingSampleButton = $('landingSampleButton');
const landingUploadButton = $('landingUploadButton');
const analyzeButton = $('analyzeButton');
const statusBox = $('statusBox');
const resultState = $('resultState');
const reportActions = $('reportActions');
const previewReportButton = $('previewReportButton');
const reportModal = $('reportModal');
const reportModalBackdrop = $('reportModalBackdrop');
const closeReportPreviewButton = $('closeReportPreviewButton');
const reportPreviewFrame = $('reportPreviewFrame');
const previewDownloadReportButton = $('previewDownloadReportButton');
const previewPrintReportButton = $('previewPrintReportButton');
let reportPreviewReturnFocus = null;

function setStatus(message, tone = 'neutral') {
  statusBox.textContent = message;
  statusBox.className = `status-box ${tone === 'neutral' ? '' : tone}`.trim();
}

function nowLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function resetReviewState() {
  latestAnalysisPayload = null;
  exceptionDispositions = {};
  sessionAuditEvents = [];
  reportActions.hidden = true;
}

function setSubmission(data, name, sizeText = '', evidence = null) {
  submissionData = data;
  evidenceData = evidence;
  submissionSourceName = name || 'Uploaded submission';
  resetReviewState();
  fileName.textContent = name;
  fileMeta.textContent = sizeText;
  fileRow.hidden = false;
  analyzeButton.disabled = false;
  resultState.textContent = 'Waiting for analysis';
  $('evidenceNote').textContent = evidence
    ? 'Complete synthetic package loaded: submission + authority, insurance certificate, aircraft registry, event history, and filing evidence.'
    : 'Submission-only mode: external evidence reconciliation will not run.';
  setStatus(evidence ? 'Synthetic case loaded. Ready to run reconciliation.' : 'Submission loaded. Ready for submission-only analysis.');
}

function clearSubmission() {
  submissionData = null;
  evidenceData = null;
  submissionSourceName = 'Uploaded submission';
  resetReviewState();
  fileInput.value = '';
  fileRow.hidden = true;
  analyzeButton.disabled = true;
  resultState.textContent = 'Waiting for analysis';
  $('evidenceNote').textContent = 'Load the synthetic case to include authority, OST 6410-style, registry, event, and filing evidence.';
  setStatus('Choose a case to begin.');
}

async function readJsonFile(file) {
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) {
    setStatus('The demo accepts JSON files up to 2 MB.', 'error');
    return;
  }

  try {
    const text = await file.text();
    const data = JSON.parse(text);
    if (!data || Array.isArray(data) || typeof data !== 'object') {
      throw new Error('Submission must be a JSON object.');
    }
    setSubmission(data, file.name, `${Math.max(1, Math.round(file.size / 1024))} KB`, null);
  } catch (error) {
    setStatus(error.message || 'Unable to read that JSON file.', 'error');
  }
}

fileInput.addEventListener('change', () => readJsonFile(fileInput.files[0]));
clearButton.addEventListener('click', clearSubmission);

['dragenter', 'dragover'].forEach(eventName => {
  dropZone.addEventListener(eventName, event => {
    event.preventDefault();
    dropZone.classList.add('dragging');
  });
});

['dragleave', 'drop'].forEach(eventName => {
  dropZone.addEventListener(eventName, event => {
    event.preventDefault();
    dropZone.classList.remove('dragging');
  });
});

dropZone.addEventListener('drop', event => {
  const [file] = event.dataTransfer.files;
  readJsonFile(file);
});

async function loadSyntheticSample({ scrollToDemo = false } = {}) {
  const triggerButtons = [loadSampleButton, landingSampleButton].filter(Boolean);
  triggerButtons.forEach(button => { button.disabled = true; });

  try {
    const [submissionResponse, evidenceResponse] = await Promise.all([
      fetch('/sample-data/synthetic_submission.json'),
      fetch('/sample-data/synthetic_evidence.json'),
    ]);
    if (!submissionResponse.ok || !evidenceResponse.ok) {
      throw new Error('Unable to load the complete synthetic case.');
    }
    const [submission, evidence] = await Promise.all([
      submissionResponse.json(),
      evidenceResponse.json(),
    ]);

    setSubmission(
      submission,
      'PrairieJet synthetic case',
      'Submission + 5 supporting evidence sources',
      evidence,
    );

    if (scrollToDemo) {
      $('demo')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      window.setTimeout(() => analyzeButton.focus({ preventScroll: true }), 550);
    }
  } catch (error) {
    setStatus(error.message || 'Unable to load the synthetic case.', 'error');
  } finally {
    triggerButtons.forEach(button => { button.disabled = false; });
  }
}

loadSampleButton.addEventListener('click', () => loadSyntheticSample());
landingSampleButton?.addEventListener('click', () => loadSyntheticSample({ scrollToDemo: true }));
landingUploadButton?.addEventListener('click', () => {
  $('demo')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  window.setTimeout(() => fileInput.click(), 500);
});

function normalizeStatus(value) {
  return String(value || 'review').replaceAll('_', ' ');
}

function statusTone(value) {
  const status = String(value || '').toUpperCase();
  if (['VERIFIED', 'READY', 'NO_EXCEPTION_IDENTIFIED'].some(token => status.includes(token))) return 'good';
  if (['REFER', 'REVIEW', 'MISSING', 'UNRESOLVED', 'ADDITIONAL', 'PENDING'].some(token => status.includes(token))) return 'warn';
  if (['MISMATCH', 'BLOCKED', 'INVALID', 'INCOMPLETE'].some(token => status.includes(token))) return 'bad';
  return 'neutral';
}

function formatUsd(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return '—';
  if (Math.abs(amount) >= 1_000_000_000) return '$' + (amount / 1_000_000_000).toFixed(2).replace(/\.00$/, '') + 'B';
  if (Math.abs(amount) >= 1_000_000) return '$' + (amount / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  if (Math.abs(amount) >= 1_000) return '$' + (amount / 1_000).toFixed(1).replace(/\.0$/, '') + 'K';
  return '$' + amount.toLocaleString();
}

function formatNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString() : '—';
}

function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(1).replace(/\.0$/, '') + '%' : '—';
}

function setList(elementId, items, emptyMessage) {
  const target = $(elementId);
  target.innerHTML = '';
  const values = Array.isArray(items) ? items : [];
  if (!values.length) {
    const li = document.createElement('li');
    li.className = 'placeholder';
    li.textContent = emptyMessage;
    target.appendChild(li);
    return;
  }
  values.forEach(item => {
    const li = document.createElement('li');
    li.textContent = String(item);
    target.appendChild(li);
  });
}

function renderRiskFlags(flags) {
  const target = $('riskList');
  target.innerHTML = '';
  const values = Array.isArray(flags) ? flags : [];
  $('riskCount').textContent = values.length;

  if (!values.length) {
    const p = document.createElement('p');
    p.className = 'placeholder';
    p.textContent = 'No risk flags returned.';
    target.appendChild(p);
    return;
  }

  values.forEach(flag => {
    const item = document.createElement('div');
    item.className = 'risk-item';
    const title = document.createElement('strong');
    title.textContent = flag.category || 'review item';
    const fact = document.createElement('p');
    fact.textContent = flag.fact || 'No fact supplied.';
    const why = document.createElement('p');
    why.textContent = flag.why_review ? `Why review: ${flag.why_review}` : '';
    item.append(title, fact);
    if (why.textContent) item.appendChild(why);
    target.appendChild(item);
  });
}

function evidenceValueText(value) {
  if (value === null || value === undefined) return 'Not supplied';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function renderSources(sources) {
  const target = $('sourceGrid');
  target.innerHTML = '';
  const values = Array.isArray(sources) ? sources : [];
  $('sourceCount').textContent = values.length;

  if (!values.length) {
    const p = document.createElement('p');
    p.className = 'placeholder';
    p.textContent = 'No external evidence package supplied.';
    target.appendChild(p);
    return;
  }

  values.forEach(source => {
    const card = document.createElement('div');
    card.className = 'source-card';

    const top = document.createElement('div');
    top.className = 'source-card-top';

    const id = document.createElement('span');
    id.className = 'source-id';
    id.textContent = source.source_id || 'SOURCE';

    const status = document.createElement('span');
    status.className = 'source-status';
    status.textContent = source.status || 'LOADED';

    const name = document.createElement('strong');
    name.textContent = source.name || source.type || 'Evidence source';

    const type = document.createElement('span');
    type.className = 'source-type';
    type.textContent = normalizeStatus(source.type || 'evidence');

    top.append(id, status);
    card.append(top, name, type);
    target.appendChild(card);
  });
}

function renderChecks(checks) {
  const body = $('checkTableBody');
  body.innerHTML = '';
  const values = Array.isArray(checks) ? checks : [];
  $('checkCount').textContent = values.length;

  if (!values.length) {
    const row = document.createElement('tr');
    row.innerHTML = '<td colspan="4" class="placeholder-cell">No deterministic evidence checks were run.</td>';
    body.appendChild(row);
    return;
  }

  values.forEach(check => {
    const row = document.createElement('tr');

    const rule = document.createElement('td');
    rule.className = 'rule-id-cell';
    rule.textContent = check.rule_id || '—';

    const label = document.createElement('td');
    label.textContent = check.label || 'Reconciliation check';

    const result = document.createElement('td');
    const pill = document.createElement('span');
    pill.className = `status-pill ${statusTone(check.status)}`;
    pill.textContent = normalizeStatus(check.status);
    result.appendChild(pill);

    const summary = document.createElement('td');
    summary.className = 'check-summary';
    summary.textContent = check.summary || '';

    row.append(rule, label, result, summary);
    body.appendChild(row);
  });
}

function addSessionAudit(event, actor = 'reviewer') {
  sessionAuditEvents.push({
    timestamp: new Date().toISOString(),
    event,
    actor,
  });
  renderAuditTrail();
}

function currentExceptions() {
  const exceptions = latestAnalysisPayload?.reconciliation?.exceptions || [];
  return exceptions.map(item => ({
    ...item,
    status: exceptionDispositions[item.exception_id] || item.status || 'OPEN',
  }));
}

function renderExceptionEvidence(container, evidence) {
  const values = Array.isArray(evidence) ? evidence : [];
  if (!values.length) return;

  const title = document.createElement('div');
  title.className = 'exception-evidence-title';
  title.textContent = 'Evidence';
  container.appendChild(title);

  values.forEach(item => {
    const row = document.createElement('div');
    row.className = 'evidence-row';

    const source = document.createElement('span');
    source.className = 'evidence-source';
    source.textContent = item.source_id || 'SOURCE';

    const loc = document.createElement('span');
    loc.className = 'evidence-location';
    loc.textContent = item.location || 'record';

    const value = document.createElement('span');
    value.className = 'evidence-value';
    value.textContent = evidenceValueText(item.value);

    row.append(source, loc, value);
    container.appendChild(row);
  });
}

function renderExceptions() {
  const target = $('exceptionList');
  target.innerHTML = '';
  const values = currentExceptions();
  $('exceptionCount').textContent = values.length;

  if (!values.length) {
    const p = document.createElement('p');
    p.className = 'placeholder';
    p.textContent = 'No exceptions generated.';
    target.appendChild(p);
    return;
  }

  values.forEach(item => {
    const card = document.createElement('article');
    card.className = 'exception-card';

    const header = document.createElement('div');
    header.className = 'exception-header';

    const titleBlock = document.createElement('div');
    const kicker = document.createElement('div');
    kicker.className = 'exception-kicker';
    kicker.textContent = `${item.exception_id} · ${item.rule_id} · ${item.severity || 'REVIEW'}`;
    const title = document.createElement('h3');
    title.textContent = item.title || 'Review exception';
    titleBlock.append(kicker, title);

    const result = document.createElement('span');
    result.className = `status-pill ${statusTone(item.result_status)}`;
    result.textContent = normalizeStatus(item.result_status);

    header.append(titleBlock, result);

    const summary = document.createElement('p');
    summary.className = 'exception-summary';
    summary.textContent = item.summary || '';

    card.append(header, summary);

    if (item.subject) {
      const subject = document.createElement('p');
      subject.className = 'exception-subject';
      subject.textContent = `Subject: ${item.subject}`;
      card.appendChild(subject);
    }

    renderExceptionEvidence(card, item.evidence);

    if (item.suggested_action) {
      const action = document.createElement('p');
      action.className = 'suggested-action';
      action.textContent = `Suggested review action: ${item.suggested_action}`;
      card.appendChild(action);
    }

    const disposition = document.createElement('div');
    disposition.className = 'disposition-row';

    const label = document.createElement('label');
    label.textContent = 'Human disposition';

    const select = document.createElement('select');
    select.className = 'disposition-select';
    [
      ['OPEN', 'Open'],
      ['REQUEST_INFORMATION', 'Request information'],
      ['UNDERWRITING_REFERRAL', 'Underwriting referral'],
      ['REGULATORY_FILING_REVIEW', 'Regulatory filing review'],
      ['RESOLVED', 'Resolved'],
      ['CLOSED_NO_ACTION', 'Closed — no action'],
    ].forEach(([value, text]) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = text;
      if ((exceptionDispositions[item.exception_id] || item.status || 'OPEN') === value) option.selected = true;
      select.appendChild(option);
    });

    select.addEventListener('change', () => {
      exceptionDispositions[item.exception_id] = select.value;
      addSessionAudit(`${item.exception_id} disposition changed to ${normalizeStatus(select.value)}`);
      updateHumanControl();
    });

    disposition.append(label, select);
    card.appendChild(disposition);
    target.appendChild(card);
  });
}

function renderEvaluation(evaluation) {
  const value = evaluation || {};
  $('evalExpected').textContent = value.ground_truth_available ? formatNumber(value.expected_exception_count) : '—';
  $('evalDetected').textContent = value.ground_truth_available ? formatNumber(value.detected_expected_count) : '—';
  $('evalUnexpected').textContent = value.ground_truth_available
    ? formatNumber((value.unexpected_exception_rule_ids || []).length)
    : '—';

  $('evaluationSummary').textContent = value.ground_truth_available
    ? `${formatPercent(value.detection_rate_percent)} of the intentionally planted exception rules were detected. This is synthetic ground-truth evaluation, not a customer performance claim.`
    : 'No synthetic ground-truth answer key was supplied for this case.';
}

function renderAuditTrail() {
  const target = $('auditList');
  target.innerHTML = '';

  const base = latestAnalysisPayload?.reconciliation?.audit_events || [];
  const values = [...base, ...sessionAuditEvents];

  if (!values.length) {
    const li = document.createElement('li');
    li.className = 'placeholder';
    li.textContent = 'No activity yet.';
    target.appendChild(li);
    return;
  }

  values.forEach(item => {
    const li = document.createElement('li');
    const time = document.createElement('span');
    time.className = 'audit-time';
    const parsed = item.timestamp ? new Date(item.timestamp) : null;
    time.textContent = parsed && !Number.isNaN(parsed.getTime())
      ? parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      : nowLabel();

    const actor = document.createElement('span');
    actor.className = 'audit-actor';
    actor.textContent = item.actor || 'system';

    const event = document.createElement('span');
    event.className = 'audit-event';
    event.textContent = item.event || '';

    li.append(time, actor, event);
    target.appendChild(li);
  });
}

function updateHumanControl() {
  const values = currentExceptions();
  const open = values.filter(item => !['RESOLVED', 'CLOSED_NO_ACTION'].includes(item.status)).length;
  const status = $('humanStatus');
  status.textContent = open ? `${open} requiring disposition` : 'Disposition complete';
  status.className = `status-pill ${open ? 'warn' : 'good'}`;
  $('humanCopy').textContent = open
    ? 'An authorized human reviewer must disposition open exceptions before consequential underwriting action.'
    : 'All prototype exceptions have a recorded session disposition. This does not itself authorize a consequential underwriting action.';
}

function renderReconciliation(reconciliation) {
  if (!reconciliation) {
    $('caseStatus').textContent = 'Submission only';
    $('caseStatus').className = 'status-pill neutral';
    ['metricSources','metricChecks','metricVerified','metricExceptions','metricAircraftReconciled','metricDetection'].forEach(id => { $(id).textContent = '—'; });
    $('reconciliationDisclaimer').textContent = 'No supporting evidence package was supplied, so external reconciliation was not performed.';
    renderSources([]);
    renderChecks([]);
    $('exceptionList').innerHTML = '<p class="placeholder">No evidence reconciliation available in submission-only mode.</p>';
    $('exceptionCount').textContent = '0';
    renderEvaluation(null);
    renderAuditTrail();
    updateHumanControl();
    return;
  }

  const summary = reconciliation.summary || {};
  $('caseStatus').textContent = normalizeStatus(reconciliation.status);
  $('caseStatus').className = `status-pill ${statusTone(reconciliation.status)}`;
  $('metricSources').textContent = formatNumber(summary.source_count);
  $('metricChecks').textContent = formatNumber(summary.check_count);
  $('metricVerified').textContent = formatNumber(summary.verified_count);
  $('metricExceptions').textContent = formatNumber(summary.exception_count);
  $('metricAircraftReconciled').textContent =
    Number.isFinite(Number(summary.aircraft_total))
      ? `${formatNumber(summary.aircraft_reconciled_to_certificate)}/${formatNumber(summary.aircraft_total)}`
      : '—';
  $('metricDetection').textContent = reconciliation.evaluation?.ground_truth_available
    ? formatPercent(reconciliation.evaluation.detection_rate_percent)
    : '—';
  $('reconciliationDisclaimer').textContent = reconciliation.disclaimer || '';

  renderSources(reconciliation.sources);
  renderChecks(reconciliation.checks);
  renderExceptions();
  renderEvaluation(reconciliation.evaluation);
  renderAuditTrail();
  updateHumanControl();
}

function renderReview(payload) {
  latestAnalysisPayload = payload;
  reportActions.hidden = false;

  renderReconciliation(payload.reconciliation);

  const review = payload.review || {};
  const readiness = review.submission_readiness || {};
  const readinessStatus = $('readinessStatus');

  readinessStatus.textContent = normalizeStatus(readiness.status);
  readinessStatus.className = `status-pill ${statusTone(readiness.status)}`;
  $('readinessSummary').textContent = readiness.summary || 'No readiness summary returned.';

  const exposure = review.exposure_summary || {};
  $('exposureSummary').textContent = exposure.summary || 'No exposure summary returned.';
  $('metricAircraft').textContent = formatNumber(exposure.aircraft_count);
  $('metricHullTiv').textContent = formatUsd(exposure.total_hull_value_usd);
  $('metricLargestHull').textContent = formatUsd(exposure.largest_single_aircraft_hull_usd);
  $('metricLiability').textContent = formatUsd(exposure.requested_liability_limit_usd);
  $('metricHours').textContent = formatNumber(exposure.projected_flight_hours);
  $('metricUtilization').textContent = formatPercent(exposure.utilization_change_percent);

  const missing = Array.isArray(review.missing_information) ? review.missing_information : [];
  $('missingCount').textContent = missing.length;
  setList('missingList', missing, 'No missing information returned.');
  renderRiskFlags(review.risk_flags);

  const hull = review.hull_asset_analysis || {};
  $('hullStatus').textContent = normalizeStatus(hull.status);
  $('hullStatus').className = 'status-pill ' + statusTone(hull.status);
  $('hullSummary').textContent = hull.summary || 'No hull analysis returned.';
  setList('hullIssues', hull.issues, 'No hull or asset issues returned.');

  const authority = review.delegated_authority_review || {};
  $('authorityStatus').textContent = normalizeStatus(authority.status);
  $('authorityStatus').className = 'status-pill ' + statusTone(authority.status);
  $('authoritySummary').textContent = authority.summary || 'No authority review returned.';
  setList('authorityReasons', authority.reasons, 'No referral reasons returned.');
  $('authorityDisclaimer').textContent = authority.disclaimer || '';

  const fac = review.fac_review || {};
  $('facSummary').textContent = fac.summary || 'No FAC summary returned.';
  setList('facIssues', fac.issues, 'No FAC issues returned.');

  $('nextAction').textContent = review.recommended_next_action || 'No next action returned.';

  const mode = payload.review_mode === 'live_ai' ? 'Live AI synthesis' : 'Repository reference output';
  $('reviewModeLabel').textContent = mode;
  resultState.textContent = payload.reconciliation ? 'Reconciliation complete' : 'Analysis complete';
}

function reportContext() {
  if (!latestAnalysisPayload || !submissionData) {
    throw new Error('Run an analysis before creating a report.');
  }

  const reconciliation = latestAnalysisPayload.reconciliation
    ? {
        ...latestAnalysisPayload.reconciliation,
        exceptions: currentExceptions(),
        audit_events: [
          ...(latestAnalysisPayload.reconciliation.audit_events || []),
          ...sessionAuditEvents,
        ],
      }
    : null;

  return {
    payload: {
      ...latestAnalysisPayload,
      reconciliation,
    },
    submission: submissionData,
    sourceName: submissionSourceName,
  };
}

function openReportPreview() {
  try {
    const context = reportContext();
    reportPreviewReturnFocus = document.activeElement;
    reportPreviewFrame.srcdoc = window.SRiskReport.buildReportHtml({ ...context, preview: true });
    reportModal.hidden = false;
    document.body.classList.add('report-preview-open');
    closeReportPreviewButton.focus();
  } catch (error) {
    setStatus(error.message || 'Unable to create the report preview.', 'error');
  }
}

function closeReportPreview() {
  if (reportModal.hidden) return;
  reportModal.hidden = true;
  reportPreviewFrame.srcdoc = '';
  document.body.classList.remove('report-preview-open');
  if (reportPreviewReturnFocus && typeof reportPreviewReturnFocus.focus === 'function') {
    reportPreviewReturnFocus.focus();
  }
}

previewReportButton.addEventListener('click', openReportPreview);
closeReportPreviewButton.addEventListener('click', closeReportPreview);
reportModalBackdrop.addEventListener('click', closeReportPreview);
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !reportModal.hidden) closeReportPreview();
});

previewDownloadReportButton.addEventListener('click', () => {
  try {
    window.SRiskReport.downloadHtml(reportContext());
  } catch (error) {
    setStatus(error.message || 'Unable to create the HTML report.', 'error');
  }
});

previewPrintReportButton.addEventListener('click', () => {
  try {
    window.SRiskReport.printPdf(reportContext());
  } catch (error) {
    setStatus(error.message || 'Unable to open the printable report.', 'error');
  }
});

analyzeButton.addEventListener('click', async () => {
  if (!submissionData) return;

  analyzeButton.disabled = true;
  analyzeButton.textContent = 'Reconciling…';
  resultState.textContent = 'Running checks';
  setStatus('Running deterministic evidence checks and controlled AI-assisted synthesis…');

  try {
    const body = evidenceData
      ? { submission: submissionData, evidence: evidenceData }
      : submissionData;

    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const payload = await response.json();
    if (!response.ok) {
      const precheckNote = payload.precheck ? ` Precheck: ${JSON.stringify(payload.precheck)}` : '';
      throw new Error(`${payload.error || 'Analysis failed.'}${precheckNote}`);
    }

    renderReview(payload);
    setStatus(
      payload.review_mode === 'live_ai'
        ? 'Reconciliation complete with live AI-assisted synthesis. Human review remains required.'
        : 'Reconciliation complete. AI credentials are not configured, so the repository reference synthesis is shown.',
      'success',
    );
  } catch (error) {
    resultState.textContent = 'Analysis error';
    setStatus(error.message || 'Analysis failed.', 'error');
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.textContent = 'Run reconciliation';
  }
});
