let submissionData = null;

const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const fileRow = document.getElementById('fileRow');
const fileName = document.getElementById('fileName');
const fileMeta = document.getElementById('fileMeta');
const clearButton = document.getElementById('clearButton');
const loadSampleButton = document.getElementById('loadSampleButton');
const analyzeButton = document.getElementById('analyzeButton');
const statusBox = document.getElementById('statusBox');
const resultState = document.getElementById('resultState');

function setStatus(message, tone = 'neutral') {
  statusBox.textContent = message;
  statusBox.className = `status-box ${tone === 'neutral' ? '' : tone}`.trim();
}

function setSubmission(data, name, sizeText = '') {
  submissionData = data;
  fileName.textContent = name;
  fileMeta.textContent = sizeText;
  fileRow.hidden = false;
  analyzeButton.disabled = false;
  setStatus('Submission loaded. Ready to analyze.');
}

function clearSubmission() {
  submissionData = null;
  fileInput.value = '';
  fileRow.hidden = true;
  analyzeButton.disabled = true;
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

loadSampleButton.addEventListener('click', async () => {
  try {
    const response = await fetch('/sample-data/synthetic_submission.json');
    if (!response.ok) throw new Error('Unable to load the synthetic sample.');
    const data = await response.json();
    setSubmission(data, 'synthetic_submission.json', 'Repository sample');
  } catch (error) {
    setStatus(error.message, 'error');
  }
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
  const review = payload.review || {};
  const readiness = review.submission_readiness || {};
  const readinessStatus = document.getElementById('readinessStatus');

  readinessStatus.textContent = normalizeStatus(readiness.status);
  readinessStatus.className = `status-pill ${statusTone(readiness.status)}`;
  document.getElementById('readinessSummary').textContent = readiness.summary || 'No readiness summary returned.';

  const missing = Array.isArray(review.missing_information) ? review.missing_information : [];
  document.getElementById('missingCount').textContent = missing.length;
  setList('missingList', missing, 'No missing information returned.');

  renderRiskFlags(review.risk_flags);

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
