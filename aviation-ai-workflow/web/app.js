let submissionData = null;
let latestAnalysisPayload = null;
let submissionSourceName = "Uploaded submission";

const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const fileRow = document.getElementById('fileRow');
const fileName = document.getElementById('fileName');
const fileMeta = document.getElementById('fileMeta');
const clearButton = document.getElementById('clearButton');
const loadSampleButton = document.getElementById('loadSampleButton');
const landingSampleButton = document.getElementById('landingSampleButton');
const landingUploadButton = document.getElementById('landingUploadButton');
const analyzeButton = document.getElementById('analyzeButton');
const statusBox = document.getElementById('statusBox');
const resultState = document.getElementById('resultState');
const reportActions = document.getElementById('reportActions');
const previewReportButton = document.getElementById('previewReportButton');
const reportModal = document.getElementById('reportModal');
const reportModalBackdrop = document.getElementById('reportModalBackdrop');
const closeReportPreviewButton = document.getElementById('closeReportPreviewButton');
const reportPreviewFrame = document.getElementById('reportPreviewFrame');
const previewDownloadReportButton = document.getElementById('previewDownloadReportButton');
const previewPrintReportButton = document.getElementById('previewPrintReportButton');
let reportPreviewReturnFocus = null;

function setStatus(message, tone = 'neutral') {
  statusBox.textContent = message;
  statusBox.className = `status-box ${tone === 'neutral' ? '' : tone}`.trim();
}

function setSubmission(data, name, sizeText = '') {
  submissionData = data;
  submissionSourceName = name || 'Uploaded submission';
  latestAnalysisPayload = null;
  reportActions.hidden = true;
  fileName.textContent = name;
  fileMeta.textContent = sizeText;
  fileRow.hidden = false;
  analyzeButton.disabled = false;
  resultState.textContent = 'Waiting for analysis';
  setStatus('Submission loaded. Ready to analyze.');
}

function clearSubmission() {
  submissionData = null;
  latestAnalysisPayload = null;
  submissionSourceName = 'Uploaded submission';
  fileInput.value = '';
  fileRow.hidden = true;
  analyzeButton.disabled = true;
  reportActions.hidden = true;
  resultState.textContent = 'Waiting for analysis';
  setStatus('Choose a JSON submission to begin.');
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
    setSubmission(data, file.name, `${Math.max(1, Math.round(file.size / 1024))} KB`);
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
  triggerButtons.forEach(button => {
    button.disabled = true;
  });

  try {
    const response = await fetch('/sample-data/synthetic_submission.json');
    if (!response.ok) throw new Error('Unable to load the synthetic sample.');
    const data = await response.json();
    setSubmission(data, 'synthetic_submission.json', 'Repository sample');

    if (scrollToDemo) {
      document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      window.setTimeout(() => analyzeButton.focus({ preventScroll: true }), 550);
    }
  } catch (error) {
    setStatus(error.message, 'error');
  } finally {
    triggerButtons.forEach(button => {
      button.disabled = false;
    });
  }
}

loadSampleButton.addEventListener('click', () => loadSyntheticSample());
landingSampleButton?.addEventListener('click', () => loadSyntheticSample({ scrollToDemo: true }));

landingUploadButton?.addEventListener('click', () => {
  document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  window.setTimeout(() => fileInput.click(), 500);
});

function normalizeStatus(value) {
  return String(value || 'review').replaceAll('_', ' ');
}

function statusTone(value) {
  const status = String(value || '').toLowerCase();
  if (status.includes('ready') && !status.includes('not')) return 'good';
  if (status.includes('additional') || status.includes('review') || status.includes('pending')) return 'warn';
  if (status.includes('incomplete') || status.includes('blocked') || status.includes('not ready')) return 'bad';
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
  const target = document.getElementById(elementId);
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
  const target = document.getElementById('riskList');
  target.innerHTML = '';
  const values = Array.isArray(flags) ? flags : [];
  document.getElementById('riskCount').textContent = values.length;

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

function renderReview(payload) {
  latestAnalysisPayload = payload;
  reportActions.hidden = false;
  const review = payload.review || {};
  const readiness = review.submission_readiness || {};
  const readinessStatus = document.getElementById('readinessStatus');

  readinessStatus.textContent = normalizeStatus(readiness.status);
  readinessStatus.className = `status-pill ${statusTone(readiness.status)}`;
  document.getElementById('readinessSummary').textContent = readiness.summary || 'No readiness summary returned.';

  const exposure = review.exposure_summary || {};
  document.getElementById('exposureSummary').textContent = exposure.summary || 'No exposure summary returned.';
  document.getElementById('metricAircraft').textContent = formatNumber(exposure.aircraft_count);
  document.getElementById('metricHullTiv').textContent = formatUsd(exposure.total_hull_value_usd);
  document.getElementById('metricLargestHull').textContent = formatUsd(exposure.largest_single_aircraft_hull_usd);
  document.getElementById('metricLiability').textContent = formatUsd(exposure.requested_liability_limit_usd);
  document.getElementById('metricHours').textContent = formatNumber(exposure.projected_flight_hours);
  document.getElementById('metricUtilization').textContent = formatPercent(exposure.utilization_change_percent);

  const missing = Array.isArray(review.missing_information) ? review.missing_information : [];
  document.getElementById('missingCount').textContent = missing.length;
  setList('missingList', missing, 'No missing information returned.');

  renderRiskFlags(review.risk_flags);

  const hull = review.hull_asset_analysis || {};
  const hullStatus = document.getElementById('hullStatus');
  hullStatus.textContent = normalizeStatus(hull.status);
  hullStatus.className = 'status-pill ' + statusTone(hull.status);
  document.getElementById('hullSummary').textContent = hull.summary || 'No hull analysis returned.';
  setList('hullIssues', hull.issues, 'No hull or asset issues returned.');

  const authority = review.delegated_authority_review || {};
  const authorityStatus = document.getElementById('authorityStatus');
  authorityStatus.textContent = normalizeStatus(authority.status);
  authorityStatus.className = 'status-pill ' + statusTone(authority.status);
  document.getElementById('authoritySummary').textContent = authority.summary || 'No authority review returned.';
  setList('authorityReasons', authority.reasons, 'No referral reasons returned.');
  document.getElementById('authorityDisclaimer').textContent = authority.disclaimer || '';

  const fac = review.fac_review || {};
  document.getElementById('facSummary').textContent = fac.summary || 'No FAC summary returned.';
  setList('facIssues', fac.issues, 'No FAC issues returned.');

  const human = review.human_review_required === true;
  const humanStatus = document.getElementById('humanStatus');
  humanStatus.textContent = human ? 'Required' : 'Check configuration';
  humanStatus.className = `status-pill ${human ? 'warn' : 'bad'}`;
  document.getElementById('humanCopy').textContent = human
    ? 'An authorized human reviewer is required before any consequential underwriting or reinsurance action.'
    : 'The expected human-review control was not returned. Treat this result as invalid.';

  document.getElementById('nextAction').textContent = review.recommended_next_action || 'No next action returned.';
  resultState.textContent = 'Analysis complete';
}


function reportContext() {
  if (!latestAnalysisPayload || !submissionData) {
    throw new Error('Run an analysis before creating a report.');
  }

  return {
    payload: latestAnalysisPayload,
    submission: submissionData,
    sourceName: submissionSourceName,
  };
}

function openReportPreview() {
  try {
    const context = reportContext();
    reportPreviewReturnFocus = document.activeElement;
    reportPreviewFrame.srcdoc = window.SRiskReport.buildReportHtml({
      ...context,
      preview: true,
    });
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
  if (event.key === 'Escape' && !reportModal.hidden) {
    closeReportPreview();
  }
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
  analyzeButton.textContent = 'Analyzing…';
  resultState.textContent = 'Analyzing';
  setStatus('Running deterministic checks and AI-assisted review…');

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submissionData),
    });

    const payload = await response.json();
    if (!response.ok) {
      const precheckNote = payload.precheck
        ? ` Precheck: ${JSON.stringify(payload.precheck)}`
        : '';
      throw new Error(`${payload.error || 'Analysis failed.'}${precheckNote}`);
    }

    renderReview(payload);
    setStatus('Analysis completed. Review all output before taking any action.', 'success');
  } catch (error) {
    resultState.textContent = 'Analysis error';
    setStatus(error.message || 'Analysis failed.', 'error');
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.textContent = 'Analyze submission';
  }
});
