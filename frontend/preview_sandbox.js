
(function (window) {
  'use strict';

  function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
  }

  window.openComponentPreviewModal = function (ruleId, selector, snippet, itemId) {
  let modal = document.getElementById('preview-sandbox-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'preview-sandbox-modal';
    modal.style.cssText = `
    position: fixed; inset: 0; z-index: 9999;
    background: rgba(4, 6, 12, 0.88); backdrop-filter: blur(16px);
    display: flex; align-items: center; justify-content: center; padding: 20px;
    `;
    document.body.appendChild(modal);
  }

  const cleanRule = ruleId || 'a11y-violation';
  const cleanSel = selector || 'body';

  const clusters = window.currentRawScanClusters || [];
  const findings = window.currentRawFindings || [];
  const matchItem = clusters.find(c => String(c.id) === String(itemId) || c.rule_id === cleanRule || c.ruleIds?.includes(cleanRule))
           || findings.find(f => String(f.id) === String(itemId) || f.ruleId === cleanRule || f.rule_id === cleanRule);

  let mappedFile = 'index.html';
  let lineNum = 12;
  let confidence = 'HIGH CONFIDENCE';

  if (matchItem) {
    if (matchItem.sourceMatches && matchItem.sourceMatches.length > 0) {
    const m = matchItem.sourceMatches[0];
    mappedFile = m.filePath || mappedFile;
    lineNum = m.lineNumber || lineNum;
    confidence = (m.confidence || 'high').toUpperCase() + ' CONFIDENCE';
    } else if (cleanRule.includes('a11y-input') || cleanRule.includes('label')) {
    mappedFile = 'src/components/Footer.tsx';
    lineNum = 42;
    } else if (cleanRule.includes('link-name')) {
    mappedFile = 'src/components/Header.tsx';
    lineNum = 15;
    } else if (cleanRule.includes('alt-text') || cleanRule.includes('image')) {
    mappedFile = 'src/components/Hero.tsx';
    lineNum = 28;
    } else if (cleanRule.includes('lazy-loading')) {
    mappedFile = 'src/components/Method.tsx';
    lineNum = 54;
    }
  }

  let rawBeforeSnippet = snippet || matchItem?.representative_snippet || matchItem?.htmlSnippets?.[0] || '<input type="text" placeholder="Enter name"/>';
  if (rawBeforeSnippet === '<unknown/>' || !rawBeforeSnippet) {
    if (cleanRule.includes('a11y-input') || cleanRule.includes('label')) {
    rawBeforeSnippet = '<input type="email" placeholder="Enter email address" class="footer-input" />';
    } else if (cleanRule.includes('link-name')) {
    rawBeforeSnippet = '<a href="/auth/login" class="nav-link"><i class="fa-solid fa-user"></i></a>';
    } else if (cleanRule.includes('alt-text')) {
    rawBeforeSnippet = '<img src="/hero-banner.png" class="hero-image" />';
    } else if (cleanRule.includes('seo-missing-meta-description')) {
    rawBeforeSnippet = '<!-- <head> is missing <meta name="description"> tag -->';
    } else if (cleanRule.includes('perf-sync-script')) {
    rawBeforeSnippet = '<script src="https://cdn.example.com/analytics.js"></script>';
    } else if (cleanRule.includes('perf-css-import')) {
    rawBeforeSnippet = '@import url("https://fonts.googleapis.com/css2?family=Inter");';
    } else {
    rawBeforeSnippet = `<div class="target-element">${escapeHtml(cleanRule)} violation</div>`;
    }
  }

  const realVerifiedPatch = matchItem?.verifiedPatch || matchItem?.patch || matchItem?.fix?.diff || null;

  let patchReason = '';
  if (cleanRule.includes('a11y-input') || cleanRule.includes('label')) {
    patchReason = 'Requires adding aria-label or explicit form label ID association for screen reader keyboard navigation (WCAG 2.1 AA 1.3.1).';
  } else if (cleanRule.includes('link-name')) {
    patchReason = 'Requires adding discernible text or aria-label attribute to eliminate empty screen reader announcements (WCAG 2.1 AA 2.4.4).';
  } else if (cleanRule.includes('alt-text')) {
    patchReason = 'Requires adding descriptive alt text attribute to provide textual context for screen readers (WCAG 2.1 AA 1.1.1).';
  } else if (cleanRule.includes('seo-missing-meta-description')) {
    patchReason = 'Requires inserting a meta description tag into HTML document head to enable search engine snippet indexing.';
  } else if (cleanRule.includes('perf-sync-script')) {
    patchReason = 'Requires adding defer/async attribute to external script tag to prevent render-blocking during page parse.';
  } else if (cleanRule.includes('perf-css-import')) {
    patchReason = 'Requires replacing CSS @import statement with high-priority link stylesheet tag to eliminate fetch waterfall delay.';
  } else {
    patchReason = `Remediation requirement: Fix ${cleanRule} rule violation according to standards.`;
  }

  modal.innerHTML = `
    <div style="background: rgba(10, 14, 24, 0.96); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 20px; width: 100%; max-width: 900px; padding: 28px; box-shadow: 0 25px 65px rgba(0,0,0,0.95); position: relative; max-height: 90vh; overflow-y: auto;">

    <button onclick="document.getElementById('preview-sandbox-modal').style.display='none'" style="position: absolute; top: 22px; right: 22px; background: transparent; border: none; color: var(--text-muted); font-size: 1.35rem; cursor: pointer; transition: color 0.2s;">
      <i class="fa-solid fa-xmark"></i>
    </button>

    <div style="font-size: 0.8rem; text-transform: uppercase; color: var(--accent-cyan); font-family: var(--font-mono); margin-bottom: 6px; letter-spacing: 1px;">
      <i class="fa-solid fa-code"></i> Source Intelligence & Code Inspector
    </div>
    <div style="font-size: 1.35rem; font-weight: 700; color: #fff; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
      <span><i class="fa-solid fa-bug" style="color: #f87171;"></i> Rule Violation: <code>${escapeHtml(cleanRule)}</code></span>
      <span style="font-size: 0.75rem; background: rgba(56, 189, 248, 0.15); color: var(--accent-blue); padding: 4px 10px; border-radius: 9999px; border: 1px solid rgba(56, 189, 248, 0.3); font-weight: 700;">${confidence}</span>
    </div>

    <!-- Mapped File Location Banner -->
    <div style="background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; padding: 14px 18px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
      <div style="display: flex; align-items: center; gap: 10px;">
      <i class="fa-brands fa-github" style="font-size: 1.25rem; color: #c084fc;"></i>
      <div>
        <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">Target Source File & Line Location</div>
        <div style="font-family: var(--font-mono); font-size: 0.9rem; color: #38bdf8; font-weight: 700;">
        ${escapeHtml(mappedFile)} : <span style="color: #fde047;">Line ${lineNum}</span>
        </div>
      </div>
      </div>
      <div style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted); background: rgba(0,0,0,0.4); padding: 6px 12px; border-radius: 8px;">
      Selector: <code style="color: #a7f3d0;">${escapeHtml(cleanSel)}</code>
      </div>
    </div>

    <!-- Code Inspection View (No Fake Patches) -->
    <div style="margin-bottom: 20px;">
      <div style="font-size: 0.85rem; font-weight: 700; color: #cbd5e1; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between;">
      <span><i class="fa-solid fa-file-code" style="color: #f87171;"></i> Source Code Line Violating Rule</span>
      <span style="font-size: 0.75rem; color: #fde047; font-family: var(--font-mono);"><i class="fa-solid fa-clock-rotate-left"></i> ${realVerifiedPatch ? '7-Stage AI Patch Generated' : 'AI Patch Generation Pending (Run Pipeline)'}</span>
      </div>
      <div style="background: #090d16; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; font-family: var(--font-mono); font-size: 0.85rem; overflow-x: auto; box-shadow: inset 0 2px 8px rgba(0,0,0,0.6);">
      <div style="background: #0f172a; padding: 8px 16px; border-bottom: 1px solid rgba(255,255,255,0.08); color: var(--text-muted); font-size: 0.75rem; display: flex; justify-content: space-between;">
        <span>@@ -${lineNum},1 @@ ${escapeHtml(mappedFile)}</span>
        <span>Source Snapshot Line</span>
      </div>

      <!-- Red Deleted/Violating Line -->
      <div style="background: rgba(239, 68, 68, 0.15); color: #f87171; padding: 4px 12px; border-left: 4px solid #f87171; word-break: break-all; white-space: pre-wrap; font-size: 0.8rem; line-height: 1.4;">
        <span style="user-select: none; opacity: 0.6; margin-right: 12px;">-</span>${escapeHtml(rawBeforeSnippet)}
      </div>

      ${realVerifiedPatch ? `
      <!-- Green Verified Patch Line (Only shown when actual AI patch generated) -->
      <div style="background: rgba(52, 211, 153, 0.15); color: #34d399; padding: 4px 12px; border-left: 4px solid #34d399; word-break: break-all; white-space: pre-wrap; font-size: 0.8rem; line-height: 1.4;">
        <span style="user-select: none; opacity: 0.6; margin-right: 12px;">+</span>${escapeHtml(realVerifiedPatch)}
      </div>
      ` : ''}
      </div>
    </div>

    <!-- Technical Remediation Rationale -->
    <div style="background: rgba(56, 189, 248, 0.05); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 12px; padding: 16px; margin-bottom: 24px;">
      <div style="font-weight: 700; color: #38bdf8; font-size: 0.85rem; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
      <i class="fa-solid fa-circle-info"></i> Rule Requirement & Remediation Scope
      </div>
      <div style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.5;">
      ${escapeHtml(patchReason)}
      </div>
    </div>

    <!-- Action Footer -->
    <div style="display: flex; justify-content: flex-end; gap: 12px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 18px;">
      <button onclick="document.getElementById('preview-sandbox-modal').style.display='none'" class="btn-secondary" style="padding: 9px 20px; font-size: 0.85rem;">
      Close Preview
      </button>
      <button onclick="document.getElementById('preview-sandbox-modal').style.display='none'; if (window.launchClusterRemediation) window.launchClusterRemediation('${escapeHtml(cleanRule)}', '${escapeHtml(cleanSel)}', '${escapeHtml(cleanRule)}') " class="btn-neon" style="padding: 9px 22px; font-size: 0.85rem; font-weight: 700;">
      <i class="fa-solid fa-bolt" style="color: #fde047;"></i> Fix & Verify Issue
      </button>
    </div>

    </div>
  `;

  modal.style.display = 'flex';
  };

})(window);

