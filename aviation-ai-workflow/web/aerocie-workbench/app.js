'use strict';
(() => {
  const $ = id => document.getElementById(id);
  let fixture = null;
  let result = null;
  let assurance = null;
  const notify = (msg, isError = false) => {
    $('notification').textContent = msg;
    $('notification').classList.toggle('error', isError);
  };
  const setButtons = enabled => {
    $('download-html').disabled = !enabled;
    $('download-json').disabled = !enabled;
  };
  const resetReport = () => {
    result = null;
    setButtons(false);
    $('report-frame').hidden = true;
    $('empty-state').hidden = false;
    $('report-frame').removeAttribute('srcdoc');
    ['metric-sources', 'metric-links', 'metric-reviewed', 'metric-open'].forEach(id => {
      $(id).textContent = '—';
    });
  };
  const getJSON = async (url, options) => {
    const response = await fetch(url, {cache: 'no-store', ...options});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  };
  const loadAssurance = async () => {
    try {
      const data = await getJSON('/api/model-assurance');
      if (data.external_release_authorized !== false || data.schema !== 'AEROCIE-MODEL-ASSURANCE-REPORT-v1') {
        throw new Error('Model evaluation gate failed');
      }
      assurance = data;
      $('assurance-rows').textContent = data.metrics.count;
      $('assurance-brier').textContent = data.metrics.brier.toFixed(3);
      $('assurance-ece').textContent = data.metrics.ece.toFixed(3);
      $('assurance-open').textContent = data.evidence_audit.unresolved;
      $('assurance-lineage').textContent = `Model: ${data.model.id} | Version: ${data.model.version} | Dataset SHA-256: ${data.model.dataset_digest.slice(0,16)}… (declaration only)`;
      $('assurance-explainability').textContent = data.explainability.per_prediction_rationale_available
        ? 'Instance-level explanations declared.'
        : 'Individual prediction explanations unavailable; inspect the model assurance JSON for the largest observed errors.';
      $('assurance-gate').textContent = data.research_quality_gate.replaceAll('_', ' ');
      $('assurance-reasons').textContent = data.reasons.length
        ? data.reasons.map(s => s.replaceAll('_', ' ')).join(' | ')
        : 'No configured check failures in this synthetic dataset.';
      $('download-assurance').disabled = false;
    } catch (_) {
      $('assurance-gate').textContent = 'Evaluation unavailable';
      $('assurance-reasons').textContent = 'Inspect the local Phase 23 test fixture and server log.';
      $('download-assurance').disabled = true;
    }
  };
  const loadFixture = async () => {
    try {
      const data = await getJSON('/api/fixture');
      fixture = data.intake;
      $('organization').value = fixture.organization;
      $('scope').value = fixture.requested_scope;
      $('case-id').textContent = fixture.case_id;
      $('subject-id').textContent = fixture.subject_id;
      $('document-count').textContent = `${data.publication_count} source record${data.publication_count===1?'':'s'}`;
      $('source-status').textContent = data.candidate_status.replaceAll('_', ' ');
      $('generate').disabled = false;
      notify('Synthetic case loaded. Edit the research question, then generate a preview.');
    } catch (_) {
      $('generate').disabled = true;
      notify('The bundled research evidence could not be validated.', true);
    }
  };
  const saveBlob = (contents, name, mime) => {
    const url = URL.createObjectURL(new Blob([contents], {type: mime}));
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  };
  $('intake-form').addEventListener('submit', async e => {
    e.preventDefault();
    if (!fixture) return;
    resetReport();
    $('generate').disabled = true;
    notify('Checking synthetic intake and preparing the report…');
    const intake = {
      ...fixture,
      organization: $('organization').value.trim(),
      requested_scope: $('scope').value.trim(),
    };
    try {
      const data = await getJSON('/api/report', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({intake}),
      });
      if (data.external_release_authorized !== false || data.release !== 'HOLD_FOR_HUMAN_REVIEW') {
        throw new Error('Report status did not meet internal research restrictions');
      }
      result = data;
      $('report-frame').srcdoc = result.report_html;
      $('report-frame').hidden = false;
      $('empty-state').hidden = true;
      $('metric-sources').textContent = data.metrics.documents;
      $('metric-links').textContent = data.metrics.proposed_correction_links;
      $('metric-reviewed').textContent = data.metrics.recorded_research_checks;
      $('metric-open').textContent = data.metrics.unresolved_review_checks;
      setButtons(true);
      notify('Synthetic internal report generated. Inspect the preview or save the HTML and JSON.');
    } catch (err) {
      notify(err.message || 'Local report generation failed.', true);
    } finally {
      $('generate').disabled = false;
    }
  });
  $('download-html').addEventListener('click', () => {
    if (!result) return;
    saveBlob(result.report_html, 'AeroCIE-Synthetic-Research-Preview.html', 'text/html;charset=utf-8');
  });
  $('download-json').addEventListener('click', () => {
    if (!result) return;
    saveBlob(JSON.stringify(result.report_json, null, 2) + '\n', 'AeroCIE-Synthetic-Research-Evidence.json', 'application/json');
  });
  $('download-assurance').addEventListener('click', () => {
    if (!assurance) return;
    saveBlob(JSON.stringify(assurance, null, 2) + '\n', 'AeroCIE-Model-Assurance-Synthetic.json', 'application/json');
  });
  $('organization').addEventListener('input', resetReport);
  $('scope').addEventListener('input', resetReport);
  resetReport();
  loadFixture();
  loadAssurance();
})();
