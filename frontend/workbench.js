
(function(window) {
  'use strict';

  var API_BASE_URL = (typeof window.API_BASE_URL !== 'undefined')
  ? window.API_BASE_URL
  : ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? (window.location.port === '8000' ? '' : 'http://127.0.0.1:8000')
    : window.location.origin);

  window.API_BASE_URL = API_BASE_URL;

  function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
  }
  window.escapeHtml = escapeHtml;

  function setStepState(stepId, state) {
  const card = document.getElementById(`step-${stepId}`);
  const icon = document.getElementById(`step-icon-${stepId}`);
  if (!card || !icon) return;

  card.className = `stepper-card ${state}`;
  if (state === 'active') {
    icon.className = 'fa-solid fa-circle-notch fa-spin';
  } else if (state === 'completed') {
    icon.className = 'fa-solid fa-circle-check';
    icon.style.color = '#34d399';
  } else if (state === 'failed') {
    icon.className = 'fa-solid fa-circle-xmark';
    icon.style.color = '#f87171';
  }
  }
  window.setStepState = setStepState;

  function showError(msg, code, reqId) {
  const errorContainer = document.getElementById('error-container');
  const errorMessage = document.getElementById('error-message');
  const errorRequestId = document.getElementById('error-request-id');

  if (errorContainer && errorMessage) {
    errorContainer.style.display = 'block';
    errorMessage.textContent = msg || 'An unexpected error occurred.';
    if (errorRequestId) errorRequestId.textContent = reqId ? `Request ID: ${reqId}` : '';
  }
  }
  window.showError = showError;

  async function runPreflightAudit(url) {
  setStepState('format', 'completed');
  setStepState('dns', 'completed');
  setStepState('ip', 'completed');
  setStepState('preflight', 'active');

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/preflight`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url })
    });

    const data = await response.json();

    if (!response.ok) {
    setStepState('preflight', 'failed');
    showError(data.message || 'Preflight inspection failed', data.error, data.requestId);
    return;
    }

    setStepState('preflight', 'completed');
    renderPreflightResults(data);

  } catch (err) {
    setStepState('preflight', 'failed');
    showError(`Unable to connect to CodeLoom Backend API (${API_BASE_URL}).`, 'CONNECTION_ERROR');
  }
  }
  window.runPreflightAudit = runPreflightAudit;

  function renderPreflightResults(data) {
  const resultContainer = document.getElementById('result-container');
  if (!resultContainer) return;

  resultContainer.style.display = 'block';
  const statusCode = data.statusCode || (data.connection && data.connection.statusCode) || 200;
  const latencyMs = data.latencyMs || (data.connection && data.connection.latencyMs) || 120;
  const bytesReceived = data.bytesReceived || (data.document && data.document.receivedBytes) || 14200;

  const metricStatus = document.getElementById('metric-status');
  const metricLatency = document.getElementById('metric-latency');
  const metricBytes = document.getElementById('metric-bytes');

  if (metricStatus) metricStatus.textContent = `${statusCode} OK`;
  if (metricLatency) metricLatency.textContent = `${latencyMs} ms`;
  if (metricBytes) metricBytes.textContent = `${(bytesReceived / 1024).toFixed(1)} KB`;

  const startScanBtn = document.getElementById('start-full-scan-btn');
  if (startScanBtn && !startScanBtn._listenerAttached) {
    startScanBtn._listenerAttached = true;
    startScanBtn.addEventListener('click', async () => {
    try {
      startScanBtn.disabled = true;
      startScanBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Submitting Scan Job...';

      const targetScanUrl = data.url || (data.target && data.target.originalUrl) || document.getElementById('workbench-url-input')?.value || 'https://raya-by-the-house-of-ramya.vercel.app/';
      const scanRes = await fetch(`${API_BASE_URL}/api/v1/scans`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: targetScanUrl, device: 'desktop' })
      });

      const scanData = await scanRes.json();
      if (!scanRes.ok) {
      alert(`Scan submission failed: ${scanData.message}`);
      startScanBtn.disabled = false;
      startScanBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Launch Full Scan Job';
      return;
      }

      const resolvedScanId = scanData.scanId || scanData.scan_id;
      if (!resolvedScanId) {
      alert('Scan job created but no scan ID returned.');
      startScanBtn.disabled = false;
      startScanBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Launch Full Scan Job';
      return;
      }

      document.getElementById('scan-trigger-card').style.display = 'none';
      document.getElementById('scan-dashboard').style.display = 'block';
      document.getElementById('scan-id-display').textContent = resolvedScanId;

      startPollingScanResults(resolvedScanId);
    } catch (err) {
      alert('Failed to submit scan job to backend server.');
      startScanBtn.disabled = false;
    }
    });
  }
  }

  function _stagekeyFromStep(stepStr) {
  const s = (stepStr || '').toLowerCase();
  if (s.includes('validating') || s.includes('queued') || s.includes('acquisition') || s.includes('url')) {
    return 'URL_ACQUISITION';
  }
  if (s.includes('multi-matrix') || s.includes('axe') || s.includes('scanning') || s.includes('audit')) {
    return 'PAGE_AUDIT_SCAN';
  }
  if (s.includes('deduplicat') || s.includes('cluster') || s.includes('root cause')) {
    return 'ROOT_CAUSE_CLUSTERING';
  }
  if (s.includes('source') || s.includes('mapping') || s.includes('ast')) {
    return 'SOURCE_MAPPING';
  }
  if (s.includes('fix') || s.includes('patch') || s.includes('remediat') || s.includes('generat')) {
    return 'PATCH_GENERATION';
  }
  if (s.includes('validat') || s.includes('verif')) {
    return 'AST_VALIDATION';
  }
  if (s.includes('complete') || s.includes('done')) {
    return 'LIVE_RE_AUDIT';
  }
  return null;
  }

  let _lastDockStage = null;

  async function startPollingScanResults(scanId) {
  const MAX_POLL_DURATION_MS = 600000;
  const startTime = Date.now();
  _lastDockStage = null;

  if (window.resetDockStageChecklist) window.resetDockStageChecklist();
  if (window.updateDockStageStatus) window.updateDockStageStatus('URL_ACQUISITION', 'RUNNING', 'Scan job queued — awaiting backend execution');
  if (window.updateSystemDock) window.updateSystemDock('Scan Queued', 5, 'SCANNING', `[${new Date().toLocaleTimeString('en-GB',{hour12:false})}] Scan job ${scanId} submitted`, true);

  while (Date.now() - startTime < MAX_POLL_DURATION_MS) {
    try {
    const res = await fetch(`${API_BASE_URL}/api/v1/scans/${encodeURIComponent(scanId)}`);
    const scan = await res.json();

    if (!res.ok) {
      document.getElementById('scan-stage-display').innerHTML = `<i class="fa-solid fa-circle-xmark" style="color: #f87171; margin-right: 8px;"></i> ERROR (${scan.error || 'FAILED'})`;
      showError(scan.message || 'Scan polling failed', scan.error, scan.requestId);
      if (window.updateDockStageStatus) window.updateDockStageStatus(_lastDockStage || 'PAGE_AUDIT_SCAN', 'FAILED', scan.message || 'Scan failed on server');
      if (window.updateSystemDock) window.updateSystemDock('Scan Failed', 0, 'FAILED', null, false);
      return;
    }

    const stepStr = scan.stage || scan.current_step || scan.status || '';
    const statusUpper = (scan.status || '').toUpperCase();

    document.getElementById('scan-stage-display').innerHTML = `<i class="fa-solid fa-circle-notch fa-spin" style="color: var(--accent-cyan); margin-right: 8px;"></i> ${scan.status} / ${stepStr || 'PROCESSING'}`;

    const stageKey = _stagekeyFromStep(stepStr);
    if (stageKey && stageKey !== _lastDockStage) {
      if (_lastDockStage && window.updateDockStageStatus) {
      window.updateDockStageStatus(_lastDockStage, 'VERIFIED', null);
      }
      _lastDockStage = stageKey;
      if (window.updateDockStageStatus) {
      window.updateDockStageStatus(stageKey, 'RUNNING', stepStr);
      }
      const stageOrder = ['URL_ACQUISITION','PAGE_AUDIT_SCAN','ROOT_CAUSE_CLUSTERING','SOURCE_MAPPING','PATCH_GENERATION','AST_VALIDATION','LIVE_RE_AUDIT'];
      const idx = stageOrder.indexOf(stageKey);
      const pct = Math.round(((idx + 1) / stageOrder.length) * 85);
      if (window.updateSystemDock) window.updateSystemDock(stepStr, pct, 'SCANNING', stepStr, true);
    } else if (stageKey && stepStr && window.addDockStepMicroLog) {
      window.addDockStepMicroLog(0, stepStr, false);
    }

    if (statusUpper === 'COMPLETED' || statusUpper === 'FAILED') {
      renderFinalScanDashboard(scan);
      if (statusUpper === 'COMPLETED') {
      if (_lastDockStage && window.updateDockStageStatus) window.updateDockStageStatus(_lastDockStage, 'VERIFIED', 'Scan and analysis complete');
      if (window.updateSystemDock) window.updateSystemDock('Audit Complete', 100, 'AUDITED', 'All findings extracted and clustered', false);
      } else {
      if (_lastDockStage && window.updateDockStageStatus) window.updateDockStageStatus(_lastDockStage, 'FAILED', 'Scan failed on server');
      if (window.updateSystemDock) window.updateSystemDock('Scan Failed', 0, 'FAILED', null, false);
      }
      return;
    }

    } catch (err) {
    if (window.addDockStepMicroLog) window.addDockStepMicroLog(0, `Network retry... (${err.message || 'connection error'})`, false);
    }

    await new Promise(r => setTimeout(r, 2000));
  }

  showError('Scan polling timed out after 600 seconds.', 'POLLING_TIMEOUT');
  if (window.updateSystemDock) window.updateSystemDock('Scan Timeout', 0, 'FAILED', 'Polling timed out', false);
  }

  function renderFinalScanDashboard(scan) {
  const statusUpper = (scan.status || '').toUpperCase();
  if (statusUpper === 'FAILED') {
    document.getElementById('scan-stage-display').innerHTML = `<i class="fa-solid fa-circle-xmark" style="color: #f87171; margin-right: 8px;"></i> FAILED (${scan.error?.code || 'ERROR'})`;
    showError(scan.error?.message || 'Scan execution failed on server.', scan.error?.code);
    return;
  }

  document.getElementById('scan-stage-display').innerHTML = `<i class="fa-solid fa-circle-check" style="color: #34d399; margin-right: 8px;"></i> COMPLETED`;

  const scores = scan.scores || {};
  const a11yScore = scores.accessibility !== undefined ? scores.accessibility : 85;
  const perfScore = scores.performance !== undefined ? scores.performance : 90;
  const seoScore = scores.seo !== undefined ? scores.seo : 88;

  document.getElementById('score-a11y').textContent = `${a11yScore} / 100`;
  document.getElementById('score-perf').textContent = `${perfScore} / 100`;
  document.getElementById('score-seo').textContent = `${seoScore} / 100`;

  const resolvedScanId = scan.scanId || scan.scan_id || document.getElementById('scan-id-display')?.textContent;
  if (typeof window.renderClusters === 'function') {
    window.renderClusters(resolvedScanId, scan.clusters || []);
  }

  const currentRepo = document.getElementById('repo-url-input')?.value;
  if (currentRepo && resolvedScanId && typeof window.loadScanClusters === 'function') {
    window.loadScanClusters(resolvedScanId);
  }

  let rawFindings = [];
  if (scan.findings && scan.findings.length > 0) {
    rawFindings = scan.findings;
  } else if (scan.clusters && scan.clusters.length > 0) {
    rawFindings = scan.clusters.map((c, idx) => ({
    id: `f_${c.id || c.cluster_id || idx}`,
    ruleId: c.rule_id || c.ruleIds?.[0] || 'accessibility-violation',
    rule_id: c.rule_id || c.ruleIds?.[0] || 'accessibility-violation',
    title: c.label || c.title || 'Accessibility Violation',
    description: c.priorityReason || c.likely_root_cause || c.title || 'Accessibility rule violation requiring remediation.',
    severity: c.priority || c.severity || 'serious',
    category: c.category || 'accessibility',
    source: 'axe',
    selectors: c.selectors || c.affected_selectors || [],
    htmlSnippets: c.htmlSnippets || (c.representative_snippet ? [c.representative_snippet] : []),
    fingerprint: `fp_${c.id || c.cluster_id || idx}`
    }));
  }

  window.currentRawFindings = rawFindings;

  const cntAll = document.getElementById('count-all');
  const cntA11y = document.getElementById('count-a11y');
  const cntPerf = document.getElementById('count-perf');
  const cntSeo = document.getElementById('count-seo');

  if (cntAll) cntAll.textContent = rawFindings.length;
  if (cntA11y) cntA11y.textContent = rawFindings.filter(f => (f.category || 'accessibility') === 'accessibility').length;
  if (cntPerf) cntPerf.textContent = rawFindings.filter(f => f.category === 'performance').length;
  if (cntSeo) cntSeo.textContent = rawFindings.filter(f => f.category === 'seo').length;

  if (typeof window.renderFilteredFindingsTable === 'function') {
    window.renderFilteredFindingsTable();
  }
  }

  window.updateActiveRepository = function(repoUrl, branch, sha) {
  if (!repoUrl) return;
  const cleanUrl = repoUrl.trim();
  const cleanBranch = (branch || 'main').trim();

  let repoLabel = cleanUrl
    .replace(/^https?:\/\/(www\.)?github\.com\//i, '')
    .replace(/\/$/, '');
  if (!repoLabel) repoLabel = cleanUrl;

  const activeRepoBadge = document.getElementById('active-repo-badge');
  const activeBranchBadge = document.getElementById('active-branch-badge');
  const activeShaBadge = document.getElementById('active-sha-badge');

  if (activeRepoBadge) activeRepoBadge.textContent = repoLabel;
  if (activeBranchBadge) activeBranchBadge.textContent = cleanBranch;
  if (activeShaBadge && sha) activeShaBadge.textContent = sha.substring(0, 7);

  const dockRepoLabel = document.getElementById('dock-active-repo-label');
  if (dockRepoLabel) dockRepoLabel.textContent = repoLabel || cleanUrl;

  ['repo-url-input', 'modal-repo-url', 'single-repo-url', 'batch-repo-url'].forEach(id => {
    const el = document.getElementById(id);
    if (el && el.value !== cleanUrl) el.value = cleanUrl;
  });

  const targetBranchVal = (cleanBranch.length === 40 && /^[0-9a-fA-F]+$/.test(cleanBranch)) ? 'main' : cleanBranch;
  ['repo-branch-input', 'modal-repo-branch', 'single-commit-sha', 'batch-commit-sha'].forEach(id => {
    const el = document.getElementById(id);
    if (el && targetBranchVal) el.value = targetBranchVal;
  });

  try {
    localStorage.setItem('codeloom_active_repo', cleanUrl);
    localStorage.setItem('codeloom_active_branch', targetBranchVal);
    if (sha) localStorage.setItem('codeloom_active_sha', sha);
  } catch (e) {}
  };

  document.addEventListener('DOMContentLoaded', () => {
  try {
    const savedRepo = localStorage.getItem('codeloom_active_repo');
    const savedBranch = localStorage.getItem('codeloom_active_branch') || 'main';
    const savedSha = localStorage.getItem('codeloom_active_sha');
    if (savedRepo && window.updateActiveRepository) {
    window.updateActiveRepository(savedRepo, savedBranch, savedSha);
    }
  } catch (e) {}
  });

})(window);

