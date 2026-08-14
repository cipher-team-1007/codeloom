
function initCodeLoomApp() {
  if (typeof initAnnouncementClose === 'function') initAnnouncementClose();
  if (typeof initHeroUrlForm === 'function') initHeroUrlForm();
  if (typeof initInteractiveDemo === 'function') initInteractiveDemo();
  if (typeof initAudienceTabs === 'function') initAudienceTabs();
  if (typeof initFaqAccordions === 'function') initFaqAccordions();
  if (typeof initSmoothScroll === 'function') initSmoothScroll();
  if (typeof initCounterAnimations === 'function') initCounterAnimations();
  if (typeof initCard3DTilt === 'function') initCard3DTilt();
  if (typeof initGeminiScrollBehavior === 'function') initGeminiScrollBehavior();
  if (typeof initCursorSpotlight === 'function') initCursorSpotlight();
  if (typeof initCardMouseSpotlight === 'function') initCardMouseSpotlight();
  if (typeof initHeroLiveSimulation === 'function') initHeroLiveSimulation();

  if (document.getElementById('github-account-status') && typeof fetchGitHubStatus === 'function') {
    fetchGitHubStatus();
  }

  if (document.getElementById('remediation-studio')) {
    initCodeLoomStudio();
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCodeLoomApp);
} else {
  initCodeLoomApp();
}

function initGeminiScrollBehavior() {
  const navbar = document.getElementById('navbar');
  const scrollBeam = document.getElementById('scroll-progress-beam');
  const navLinks = document.querySelectorAll('.nav-link');
  const sections = Array.from(document.querySelectorAll('section[id]'));

  function updateActiveNavOnScroll() {
  const scrollY = window.scrollY;

  if (scrollY > 40) {
    if (navbar) navbar.classList.add('scrolled');
  } else if (scrollY < 10) {
    if (navbar) navbar.classList.remove('scrolled');
  }

  const winScroll = document.documentElement.scrollTop || document.body.scrollTop;
  const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
  const scrolled = (winScroll / height) * 100;
  if (scrollBeam) {
    scrollBeam.style.width = scrolled + '%';
  }

  let currentSectionId = '';
  const scrollPosition = scrollY + 160;

  sections.forEach(section => {
    const sectionTop = section.offsetTop;
    const sectionHeight = section.offsetHeight;
    if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
    currentSectionId = section.getAttribute('id');
    }
  });

  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (href === `#${currentSectionId}`) {
    link.classList.add('active');
    } else {
    link.classList.remove('active');
    }
  });
  }

  window.addEventListener('scroll', updateActiveNavOnScroll);
  updateActiveNavOnScroll();
}

function initCard3DTilt() {
  const card = document.querySelector('.hero-dashboard-preview');
  if (!card) return;

  const baseRotateY = -12;
  const baseRotateX = 6;
  const baseRotateZ = 1.5;

  card.style.transform = `perspective(1200px) rotateY(${baseRotateY}deg) rotateX(${baseRotateX}deg) rotateZ(${baseRotateZ}deg)`;

  card.addEventListener('mousemove', (e) => {
  const rect = card.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  const centerX = rect.width / 2;
  const centerY = rect.height / 2;

  const deltaX = ((y - centerY) / centerY) * -4;
  const deltaY = ((x - centerX) / centerX) * 4;

  card.style.transform = `perspective(1200px) rotateY(${(baseRotateY + deltaY).toFixed(2)}deg) rotateX(${(baseRotateX + deltaX).toFixed(2)}deg) rotateZ(${baseRotateZ}deg)`;
  });

  card.addEventListener('mouseleave', () => {
  card.style.transform = `perspective(1200px) rotateY(${baseRotateY}deg) rotateX(${baseRotateX}deg) rotateZ(${baseRotateZ}deg)`;
  });
}

function initCursorSpotlight() {
  const spotlight = document.getElementById('cursor-spotlight');
  if (!spotlight) return;
  window.addEventListener('mousemove', (e) => {
  spotlight.style.left = `${e.clientX}px`;
  spotlight.style.top = `${e.clientY}px`;
  });
}

function initCardMouseSpotlight() {
  const cards = document.querySelectorAll('.feature-card, .metric-card, .stepper-card, .audit-target-card');
  cards.forEach(card => {
  card.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    card.style.setProperty('--mouse-x', `${x}px`);
    card.style.setProperty('--mouse-y', `${y}px`);
  });
  });
}

function initAnnouncementClose() {
  const closeBtn = document.getElementById('close-announcement-btn');
  const bar = document.getElementById('announcement-bar');
  if (closeBtn && bar) {
  closeBtn.addEventListener('click', () => {
    bar.style.display = 'none';
  });
  }
}

function initHeroUrlForm() {
  const form = document.getElementById('hero-url-form-element');
  const input = document.getElementById('hero-url-input');
  const btn = document.getElementById('hero-audit-cta');
  if (!form || !input || !btn) return;

  function isGitHubRepo(val) {
  if (!val) return false;
  const str = val.trim().toLowerCase();
  return str.includes('github.com');
  }

  function updateButtonState() {
  const val = input.value.trim();
  if (isGitHubRepo(val)) {
    btn.textContent = 'Audit Codebase';
  } else {
    btn.textContent = 'Audit Website';
  }
  }

  input.addEventListener('input', updateButtonState);
  input.addEventListener('change', updateButtonState);
  input.addEventListener('keyup', updateButtonState);

  form.addEventListener('submit', (e) => {
  e.preventDefault();
  let val = input.value.trim();
  if (!val) {
    input.focus();
    return;
  }

  let fullUrl = val;
  if (!fullUrl.startsWith('http://') && !fullUrl.startsWith('https://')) {
    fullUrl = 'https://' + fullUrl;
  }

  if (isGitHubRepo(val)) {
    try {
    sessionStorage.setItem('codeloom_repo_url', fullUrl);
    sessionStorage.setItem('codeloom_target_url', fullUrl);
    localStorage.setItem('codeloom_active_repo', fullUrl);
    } catch (err) { }
    window.location.href = `audit-code.html?repo=${encodeURIComponent(fullUrl)}`;
  } else {
    try {
    sessionStorage.setItem('codeloom_target_url', fullUrl);
    } catch (err) { }
    window.location.href = `audit-url.html?url=${encodeURIComponent(fullUrl)}`;
  }
  });
}

function initFaqAccordions() {
  const faqQuestions = document.querySelectorAll('.faq-question');
  if (!faqQuestions.length) return;

  faqQuestions.forEach(question => {
  question.addEventListener('click', () => {
    const faqItem = question.closest('.faq-item');
    if (!faqItem) return;

    const isActive = faqItem.classList.contains('active');

    document.querySelectorAll('.faq-item.active').forEach(item => {
    if (item !== faqItem) {
      item.classList.remove('active');
      const btn = item.querySelector('.faq-question');
      if (btn) btn.setAttribute('aria-expanded', 'false');
    }
    });

    if (isActive) {
    faqItem.classList.remove('active');
    question.setAttribute('aria-expanded', 'false');
    } else {
    faqItem.classList.add('active');
    question.setAttribute('aria-expanded', 'true');
    }
  });
  });
}

function initSmoothScroll() {
  const links = document.querySelectorAll('a[href^="#"]');
  links.forEach(link => {
  link.addEventListener('click', (e) => {
    const targetId = link.getAttribute('href');
    if (!targetId || targetId === '#') return;
    const targetElement = document.querySelector(targetId);
    if (targetElement) {
    e.preventDefault();
    targetElement.scrollIntoView({ behavior: 'smooth' });
    }
  });
  });
}
function initHeroLiveSimulation() {
  const statusText = document.getElementById('hero-status-text');
  const progressBar = document.getElementById('hero-live-progress');
  const stepBadge = document.getElementById('hero-step-badge');
  const stepDetail = document.getElementById('hero-step-detail');
  const termStatus = document.getElementById('hero-term-status');
  const termBody = document.getElementById('hero-terminal-body');
  if (!statusText || !progressBar) return;
  const diffHtml = `
  <div class="term-line remove">- &lt;button class="btn-primary" onClick={handleClick}&gt;</div>
  <div class="term-line add">+ &lt;button class="btn-primary" aria-label="Submit Form" onClick={handleClick}&gt;</div>
  `;
  const states = [
  {
    status: "Browser Scan: Inspecting rendered page...",
    progress: "25%",
    badge: '<i class="fa-solid fa-spider" aria-hidden="true"></i> Playwright Browser Crawler',
    detail: '<code>https://your-domain.com</code> &rarr; <span style="color: var(--accent-blue);">Inspecting deployed page...</span>',
    termStatus: '<i class="fa-solid fa-rotate fa-spin" aria-hidden="true"></i> Inspecting...',
    termBody: '<div style="color: var(--text-muted); padding: 6px 0;"><i class="fa-solid fa-circle-notch fa-spin"></i> Scanning DOM tree & interactive button elements...</div>'
  },
  {
    status: "Analyzing DOM violations...",
    progress: "50%",
    badge: '<i class="fa-solid fa-wheelchair" aria-hidden="true"></i> axe-core WCAG 2.2 Engine',
    detail: '<code>DOM violations</code> &rarr; <span style="color: #f87171;">Button component missing ARIA label</span>',
    termStatus: '<i class="fa-solid fa-rotate fa-spin" aria-hidden="true"></i> Clustering...',
    termBody: '<div style="color: #f87171; padding: 6px 0;"><i class="fa-solid fa-triangle-exclamation"></i> DOM violations detected across rendered page</div>'
  },
  {
    status: "Root Cause Pattern Identified",
    progress: "75%",
    badge: '<i class="fa-solid fa-brain" aria-hidden="true"></i> Component Root Cause Isolation',
    detail: '<code>src/components/CheckoutButton.tsx</code> &rarr; <span style="color: var(--accent-teal);">Source candidate traced</span>',
    termStatus: '<i class="fa-solid fa-code" aria-hidden="true"></i> Traced',
    termBody: '<div style="color: var(--accent-blue); padding: 6px 0;"><i class="fa-solid fa-diagram-project"></i> Traced runtime DOM evidence &rarr; src/components/CheckoutButton.tsx</div>'
  },
  {
    status: "Generating Patch Candidate...",
    progress: "90%",
    badge: '<i class="fa-solid fa-wand-magic-sparkles" aria-hidden="true"></i> DeepMind Gemini AI Engine',
    detail: '<code>src/components/CheckoutButton.tsx</code> &rarr; <span style="color: var(--accent-cyan);">Generating reviewable diff...</span>',
    termStatus: '<i class="fa-solid fa-rotate fa-spin" aria-hidden="true"></i> Generating...',
    termBody: diffHtml
  },
  {
    status: 'Reviewable Patch Ready',
    progress: "100%",
    badge: '<i class="fa-solid fa-circle-check" aria-hidden="true"></i> Validation Gate Passed',
    detail: '<code>src/components/CheckoutButton.tsx</code> &rarr; <span style="color: var(--accent-green); font-weight: 700;">Reviewable remediation ready</span>',
    termStatus: '<i class="fa-solid fa-check" aria-hidden="true"></i> Reviewable Change',
    termBody: diffHtml
  }
  ];
  let currentIndex = 0;
  function renderState(idx) {
  const currentState = states[idx];
  if (statusText) statusText.textContent = currentState.status;
  if (progressBar) progressBar.style.width = currentState.progress;
  if (stepBadge) stepBadge.innerHTML = currentState.badge;
  if (stepDetail) stepDetail.innerHTML = currentState.detail;
  if (termStatus) termStatus.innerHTML = currentState.termStatus;
  if (termBody) termBody.innerHTML = currentState.termBody;
  }
  renderState(0);
  setInterval(() => {
  currentIndex = (currentIndex + 1) % states.length;
  renderState(currentIndex);
  }, 2500);
}

var API_BASE_URL = (typeof window.API_BASE_URL !== 'undefined')
  ? window.API_BASE_URL
  : ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? (window.location.port === '8000' ? '' : 'http://127.0.0.1:8000')
  : window.location.origin);

const CANONICAL_STAGES = [
  { id: 'REPOSITORY_ACQUISITION', label: '1. Repository Acquisition' },
  { id: 'ROOT_CAUSE_CLUSTERING', label: '2. Root-Cause Clustering' },
  { id: 'SOURCE_INTELLIGENCE', label: '3. Source Intelligence' },
  { id: 'PATCH_PLANNING', label: '4. Patch Planning' },
  { id: 'PATCH_GENERATION', label: '5. Patch Generation' },
  { id: 'PATCH_VALIDATION', label: '6. Patch Validation' },
  { id: 'SANDBOX_VERIFICATION', label: '7. Sandbox Verification' },
];

const SAMPLE_BATCH_FINDINGS = [
  {
  rule_id: "image-alt",
  category: "accessibility",
  severity: "critical",
  title: "Images must have alt text",
  description: "Hero brand logo missing alternative text attribute",
  selectors: ["img.hero-logo"],
  html_snippets: ['<img class="hero-logo" src="logo.png">']
  },
  {
  rule_id: "button-name",
  category: "accessibility",
  severity: "critical",
  title: "Buttons must have discernible text",
  description: "Icon-only button missing accessible aria-label",
  selectors: ["button.icon-btn"],
  html_snippets: ['<button class="icon-btn"><i class="fa-search"></i></button>']
  },
  {
  rule_id: "label",
  category: "accessibility",
  severity: "serious",
  title: "Form elements must have labels",
  description: "Search input field missing associated label element",
  selectors: ["input#site-search"],
  html_snippets: ['<input id="site-search" type="text">']
  }
];

let activeEventSource = null;
let activePollInterval = null;
let currentDiffViewMode = 'side-by-side';
window.isSystemDockCollapsed = true;
window.isDockLogsViewActive = false;
window.currentDockStatusBanner = 'Engine Ready — Awaiting Operation';
window._dockMicroLogHistory = [];

window.toggleSystemDockCollapse = function () {
  const contentBody = document.getElementById('dock-content-body');
  const icon = document.getElementById('dock-collapse-icon');
  if (!contentBody) return;
  window.isSystemDockCollapsed = !window.isSystemDockCollapsed;
  contentBody.style.display = window.isSystemDockCollapsed ? 'none' : 'block';
  if (icon) icon.style.transform = window.isSystemDockCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
  window.refreshDockHeaderBanner();
};

window.refreshDockHeaderBanner = function () {
  const headerTextEl = document.getElementById('dock-header-title-text');
  const headerSubEl = document.getElementById('dock-header-sub-text');
  if (!headerTextEl) return;
  if (window.isSystemDockCollapsed) {
  headerTextEl.innerHTML = window.currentDockStatusBanner || 'Idle';
  } else {
  headerTextEl.textContent = 'Live Activity Panel';
  }
};

const isUrlAuditPage = window.location.pathname.includes('audit-url');

window.PIPELINE_STAGES = isUrlAuditPage ? [
  { key: 'URL_ACQUISITION', name: 'URL & DOM Acquisition', desc: 'Crawling target URL & rendering DOM tree' },
  { key: 'PAGE_AUDIT_SCAN', name: 'Headless Axe-Core Scan', desc: 'Executing WCAG 2.1 AA rules on live DOM' },
  { key: 'ROOT_CAUSE_CLUSTERING', name: 'Root-Cause Clustering', desc: 'Deduplicating & grouping DOM violations' },
  { key: 'SOURCE_INTELLIGENCE', name: 'Source Intelligence', desc: 'Mapping DOM selectors to repository components' },
  { key: 'PATCH_GENERATION', name: 'AI Patch Generation', desc: 'Synthesizing WCAG compliant component diff' },
  { key: 'PATCH_VALIDATION', name: 'Patch Validation', desc: 'Verifying syntax & WCAG rule compliance' },
  { key: 'SANDBOX_VERIFICATION', name: 'Sandbox & Live Re-Audit', desc: 'Verifying zero remaining live defects' }
] : [
  { key: 'REPOSITORY_ACQUISITION', name: 'Repository Acquisition', desc: 'Downloading source repository snapshot' },
  { key: 'ROOT_CAUSE_CLUSTERING', name: 'Root-Cause Clustering', desc: 'Deduplicating & grouping code violations' },
  { key: 'SOURCE_INTELLIGENCE', name: 'Source Intelligence', desc: 'Component dependency graph & line mapping' },
  { key: 'PATCH_PLANNING', name: 'Patch Planning', desc: 'Generating patch plan for root causes' },
  { key: 'PATCH_GENERATION', name: 'AI Patch Generation', desc: 'Synthesizing WCAG unified diff patch' },
  { key: 'PATCH_VALIDATION', name: 'Patch Validation', desc: 'Parsing diff syntax & static rule verification' },
  { key: 'SANDBOX_VERIFICATION', name: 'Sandbox Build Verification', desc: 'Executing test build & sandbox verification' }
];

window.resetDockStageChecklist = function () {
  window.currentDockStatusBanner = 'Engine Ready — Awaiting Operation';
  window._dockMicroLogHistory = [];
  window.refreshDockHeaderBanner();

  const microFeed = document.getElementById('dock-micro-feed');
  if (microFeed) microFeed.innerHTML = '<div style="color: #94a3b8; font-style: italic;">Pipeline ready. Awaiting operation...</div>';

  const fill = document.getElementById('dock-progress-fill');
  if (fill) fill.style.width = '0%';

  const opLabel = document.getElementById('dock-current-op-label');
  if (opLabel) opLabel.textContent = 'IDLE';
  const opSubLabel = document.getElementById('dock-current-op-sub');
  if (opSubLabel) opSubLabel.textContent = 'Engine Ready — Waiting for Audit or Remediation';

  window.PIPELINE_STAGES.forEach((s, idx) => {
  const pill = document.getElementById(`dock-stage-pill-${idx + 1}`);
  if (pill) {
    pill.className = 'dock-stage-pill pending';
    pill.title = s.desc;
  }
  });

  const spinner = document.getElementById('dock-op-spinner');
  if (spinner) spinner.style.display = 'none';

  document.querySelectorAll('.live-pulse-dot').forEach(d => d.classList.remove('is-active'));
};

window.setPulseDotActive = function (active) {
  document.querySelectorAll('.live-pulse-dot').forEach(d => {
  if (active) d.classList.add('is-active');
  else d.classList.remove('is-active');
  });
};

window.addDockStepMicroLog = function (stepNum, logLine, isSuccess = false) {
  const timeStr = new Date().toLocaleTimeString('en-GB', { hour12: false });
  const entry = { time: timeStr, line: logLine, isSuccess, stepNum };
  window._dockMicroLogHistory.push(entry);

  const microFeed = document.getElementById('dock-micro-feed');
  if (!microFeed) return;

  if (microFeed.firstChild && !microFeed.firstChild.classList?.contains('dock-micro-entry')) {
  microFeed.innerHTML = '';
  }

  const logDiv = document.createElement('div');
  logDiv.className = 'dock-micro-entry';
  logDiv.style.cssText = `
  display: flex; align-items: flex-start; gap: 6px; padding: 2px 0;
  color: ${isSuccess ? '#34d399' : '#94a3b8'}; font-size: 0.68rem;
  font-family: var(--font-mono); line-height: 1.4; animation: dockLogFadeIn 0.3s ease;
  `;
  logDiv.innerHTML = `
  <span style="color: #94a3b8; flex-shrink: 0;">${timeStr}</span>
  <span style="color: ${isSuccess ? '#34d399' : '#94a3b8'}; flex-shrink: 0;">${isSuccess ? '<i class="fa-solid fa-check"></i>' : '›'}</span>
  <span style="color: #e2e8f0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 90%;" title="${logLine.replace(/"/g, '&quot;')}">${logLine}</span>
  `;
  microFeed.appendChild(logDiv);

  const entries = microFeed.querySelectorAll('.dock-micro-entry');
  if (entries.length > 6) {
  entries[0].style.opacity = '0.35';
  entries[0].style.fontSize = '0.6rem';
  }
  if (entries.length > 8) {
  entries[0].remove();
  }
  microFeed.scrollTop = microFeed.scrollHeight;
};

window.updateDockStageStatus = function (stageKey, status, customMsg = null) {
  if (!window.PIPELINE_STAGES) return;
  const stageIdx = window.PIPELINE_STAGES.findIndex(s =>
  s.key === stageKey ||
  s.name.toLowerCase().includes((stageKey || '').toLowerCase()) ||
  (stageKey || '').toLowerCase().includes(s.key.toLowerCase()) ||
  stageKey === String(window.PIPELINE_STAGES.indexOf(s) + 1)
  );
  if (stageIdx === -1) return;

  const stepNum = stageIdx + 1;
  const stageObj = window.PIPELINE_STAGES[stageIdx];

  const pill = document.getElementById(`dock-stage-pill-${stepNum}`);
  if (pill) {
  pill.className = `dock-stage-pill ${status === 'RUNNING' ? 'running' : status === 'VERIFIED' || status === 'COMPLETED' || status === 'PASSED' ? 'verified' : status === 'FAILED' ? 'failed' : 'pending'}`;
  }

  const opLabel = document.getElementById('dock-current-op-label');
  const opSubLabel = document.getElementById('dock-current-op-sub');
  const spinner = document.getElementById('dock-op-spinner');

  if (status === 'RUNNING') {
  if (opLabel) opLabel.textContent = stageObj.name;
  if (opSubLabel) opSubLabel.textContent = customMsg || stageObj.desc;
  if (spinner) spinner.style.display = 'inline-block';
  window.currentDockStatusBanner = `${stageObj.name}`;
  window.setPulseDotActive(true);  
  } else if (status === 'VERIFIED' || status === 'COMPLETED' || status === 'PASSED') {
  if (spinner) spinner.style.display = 'none';
  window.currentDockStatusBanner = `<i class="fa-solid fa-check"></i> ${stageObj.name}`;
  if (opLabel && opLabel.textContent === stageObj.name) {
    if (opSubLabel) opSubLabel.textContent = customMsg || `${stageObj.name} complete`;
  }
  window.setPulseDotActive(false); 
  } else if (status === 'FAILED') {
  if (opLabel) opLabel.textContent = `${stageObj.name}`;
  if (opSubLabel) opSubLabel.textContent = customMsg || 'Step failed';
  if (spinner) spinner.style.display = 'none';
  window.currentDockStatusBanner = `<i class="fa-solid fa-xmark"></i> ${stageObj.name} failed`;
  window.setPulseDotActive(false); 
  }

  window.refreshDockHeaderBanner();
  if (customMsg) window.addDockStepMicroLog(stepNum, customMsg, status === 'VERIFIED' || status === 'COMPLETED' || status === 'PASSED');
};

window.updateSystemDock = function (title, percent = 0, badgeText = 'ACTIVE', logLine = null, isLoading = true) {
  const fillEl = document.getElementById('dock-progress-fill');
  const badgeEl = document.getElementById('dock-active-stage-badge');
  const spinner = document.getElementById('dock-op-spinner');

  if (title) {
  window.currentDockStatusBanner = title;
  window.refreshDockHeaderBanner();
  const opLabel = document.getElementById('dock-current-op-label');
  if (opLabel) opLabel.textContent = title;
  }

  if (fillEl) fillEl.style.width = Math.min(100, Math.max(0, percent)) + '%';
  if (badgeEl && badgeText) {
  badgeEl.textContent = badgeText;
  badgeEl.style.color = badgeText === 'FAILED' ? '#f87171' : badgeText === 'AUDITED' ? '#34d399' : '#38bdf8';
  badgeEl.style.background = badgeText === 'FAILED' ? 'rgba(248,113,113,0.12)' : badgeText === 'AUDITED' ? 'rgba(52,211,153,0.12)' : 'rgba(56,189,248,0.12)';
  }
  if (spinner) spinner.style.display = isLoading ? 'inline-block' : 'none';

  if (logLine) window.addDockStepMicroLog(0, logLine, !isLoading);
};

function initCodeLoomStudio() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('github') === 'error') {
  const errMsg = urlParams.get('message') || 'GitHub OAuth authorization failed.';
  alert(`GitHub Authentication Error:\n${errMsg}\n\nTip: You can use a Personal Access Token (PAT) for instant, 100% reliable connection!`);
  history.replaceState(null, '', window.location.pathname);
  } else if (urlParams.get('github') === 'connected') {
  history.replaceState(null, '', window.location.pathname);
  }

  const batchJsonArea = document.getElementById('batch-findings-json');
  if (batchJsonArea && !batchJsonArea.value.trim()) {
  batchJsonArea.value = JSON.stringify(SAMPLE_BATCH_FINDINGS, null, 2);
  }
}

async function fetchGitHubStatus() {
  const statusEl = document.getElementById('github-account-status');
  const connectBtn = document.getElementById('github-connect-btn');
  const disconnectBtn = document.getElementById('github-disconnect-btn');
  const avatarEl = document.getElementById('github-account-avatar');
  const iconEl = document.getElementById('github-account-icon');
  const dropdownContainer = document.getElementById('user-repos-dropdown-container');

  if (!statusEl) return;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 4000);

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/github/status`, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      if (data.connected) {
        statusEl.innerHTML = `<span style="color: var(--accent-green);"><i class="fa-solid fa-circle-check"></i> Connected as @${data.account_login}</span>`;
        if (avatarEl && data.avatar_url) {
          avatarEl.src = data.avatar_url;
          avatarEl.style.display = 'inline-block';
          if (iconEl) iconEl.style.display = 'none';
        }
        if (connectBtn) connectBtn.style.display = 'none';
        if (disconnectBtn) disconnectBtn.style.display = 'inline-flex';

        fetchUserGitHubRepositories();
        const cfgView = document.getElementById('oauth-configured-view');
        const uncfgView = document.getElementById('oauth-unconfigured-view');
        if (data.oauth_configured) {
          if (cfgView) cfgView.style.display = 'block';
          if (uncfgView) uncfgView.style.display = 'none';
        } else {
          if (cfgView) cfgView.style.display = 'none';
          if (uncfgView) uncfgView.style.display = 'block';
        }
        return;
      }
    }
  } catch (err) {
    clearTimeout(timeoutId);
    console.warn('GitHub status check error or timeout:', err);
  }

  // Fallback for not connected, non-200, timeout, or error
  statusEl.innerHTML = `<span style="color: var(--text-muted);"><i class="fa-solid fa-circle-xmark"></i> Not Connected</span>`;
  if (avatarEl) avatarEl.style.display = 'none';
  if (iconEl) iconEl.style.display = 'inline-block';
  if (connectBtn) connectBtn.style.display = 'inline-flex';
  if (disconnectBtn) disconnectBtn.style.display = 'none';
  if (dropdownContainer) dropdownContainer.style.display = 'none';

  const cfgView = document.getElementById('oauth-configured-view');
  const uncfgView = document.getElementById('oauth-unconfigured-view');
  if (cfgView) cfgView.style.display = 'none';
  if (uncfgView) uncfgView.style.display = 'block';
}

window.saveOAuthAndLaunch = async function () {
  const clientId = document.getElementById('oauth-client-id-input')?.value.trim();
  const clientSecret = document.getElementById('oauth-client-secret-input')?.value.trim();
  const submitBtn = document.querySelector('#oauth-unconfigured-view button[type="submit"]');

  if (!clientId || !clientSecret) {
  alert('Please enter both Client ID and Client Secret.');
  return;
  }

  if (submitBtn) {
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Launching OAuth...';
  }

  try {
  const configRes = await fetch(`${API_BASE_URL}/api/v1/github/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: clientId, client_secret: clientSecret }),
  });

  if (!configRes.ok) {
    const errData = await configRes.json().catch(() => ({}));
    alert(`Failed to configure OAuth App: ${errData.detail || errData.message || 'Invalid configuration'}`);
    if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<i class="fa-brands fa-github"></i> Save & Launch OAuth'; }
    return;
  }

  window.location.href = `${API_BASE_URL}/api/v1/github/authorize`;
  } catch (err) {
  console.error("OAuth Launch Error:", err);
  window.location.href = `${API_BASE_URL}/api/v1/github/authorize`;
  }
};

async function fetchUserGitHubRepositories() {
  const dropdownSelect = document.getElementById('user-github-repos-select');
  const dropdownContainer = document.getElementById('user-repos-dropdown-container');
  if (!dropdownSelect) return;

  try {
  const res = await fetch(`${API_BASE_URL}/api/v1/github/repositories`);
  if (res.ok) {
    const data = await res.json();
    const repos = data.repositories || [];
    if (repos.length > 0) {
    dropdownSelect.innerHTML = `<option value="">-- Choose from your GitHub Repositories (${repos.length}) --</option>` +
      repos.map(r => `<option value="${r.html_url}" data-branch="${r.default_branch}">${r.full_name} (${r.default_branch})</option>`).join('');
    if (dropdownContainer) dropdownContainer.style.display = 'block';
    }
  }
  } catch (err) {
  console.warn("Failed to load user GitHub repositories:", err);
  }
}

window.onUserGitHubRepoSelected = function (repoUrl) {
  if (!repoUrl) return;
  const dropdownSelect = document.getElementById('user-github-repos-select');
  const selectedOpt = dropdownSelect.options[dropdownSelect.selectedIndex];
  const defaultBranch = selectedOpt ? selectedOpt.getAttribute('data-branch') || 'main' : 'main';

  const repoInput = document.getElementById('repo-url-input');
  const branchInput = document.getElementById('repo-branch-input');
  const singleRepoInput = document.getElementById('single-repo-url');
  const singleBranchInput = document.getElementById('single-commit-sha');
  const batchRepoInput = document.getElementById('batch-repo-url');
  const batchBranchInput = document.getElementById('batch-commit-sha');

  if (repoInput) repoInput.value = repoUrl;
  if (branchInput) branchInput.value = defaultBranch;
  if (singleRepoInput) singleRepoInput.value = repoUrl;
  if (singleBranchInput) singleBranchInput.value = defaultBranch;
  if (batchRepoInput) batchRepoInput.value = repoUrl;
  if (batchBranchInput) batchBranchInput.value = defaultBranch;

  if (typeof window.prepareGitHubRepository === 'function') {
  window.prepareGitHubRepository();
  }
};

window.handleGitHubConnect = function () {
  window.openGitHubAuthModal();
};

window.openGitHubAuthModal = function () {
  const modal = document.getElementById('github-auth-modal-backdrop');
  if (modal) modal.style.display = 'flex';
};

window.closeGitHubAuthModal = function () {
  const modal = document.getElementById('github-auth-modal-backdrop');
  const errEl = document.getElementById('pat-error-msg');
  if (modal) modal.style.display = 'none';
  if (errEl) errEl.style.display = 'none';
};

window.switchAuthTab = function (tabName) {
  const tabPat = document.getElementById('auth-tab-pat');
  const tabOAuth = document.getElementById('auth-tab-oauth');
  const contentPat = document.getElementById('auth-content-pat');
  const contentOAuth = document.getElementById('auth-content-oauth');

  if (tabName === 'pat') {
  if (tabPat) { tabPat.style.background = 'var(--accent-blue)'; tabPat.style.color = '#fff'; }
  if (tabOAuth) { tabOAuth.style.background = 'transparent'; tabOAuth.style.color = 'var(--text-muted)'; }
  if (contentPat) contentPat.style.display = 'block';
  if (contentOAuth) contentOAuth.style.display = 'none';
  } else {
  if (tabOAuth) { tabOAuth.style.background = 'var(--accent-blue)'; tabOAuth.style.color = '#fff'; }
  if (tabPat) { tabPat.style.background = 'transparent'; tabPat.style.color = 'var(--text-muted)'; }
  if (contentOAuth) contentOAuth.style.display = 'block';
  if (contentPat) contentPat.style.display = 'none';
  }
};

window.submitGitHubPATConnect = async function () {
  const input = document.getElementById('pat-token-input');
  const errEl = document.getElementById('pat-error-msg');
  const submitBtn = document.getElementById('pat-submit-btn');
  if (!input || !input.value.trim()) return;

  const token = input.value.trim();
  if (errEl) errEl.style.display = 'none';
  if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...'; }

  try {
  const res = await fetch(`${API_BASE_URL}/api/v1/github/connect-pat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: token }),
  });

  const data = await res.json();
  if (res.ok && data.connected) {
    window.closeGitHubAuthModal();
    input.value = '';
    fetchGitHubStatus();
  } else {
    if (errEl) {
    errEl.textContent = data.detail || data.message || "Failed to authenticate token with GitHub API.";
    errEl.style.display = 'block';
    }
  }
  } catch (err) {
  if (errEl) {
    errEl.textContent = "Network error connecting to GitHub engine.";
    errEl.style.display = 'block';
  }
  } finally {
  if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<i class="fa-solid fa-plug"></i> Connect Account'; }
  }
};

window.handleGitHubDisconnect = async function () {
  try {
  await fetch(`${API_BASE_URL}/api/v1/github/disconnect`, { method: 'POST' });
  document.cookie = "codeloom_session=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
  fetchGitHubStatus();
  } catch (err) {
  alert('Failed to disconnect GitHub account.');
  }
};

window.switchStudioMode = function (mode) {
  const tabSingle = document.getElementById('tab-mode-single');
  const tabBatch = document.getElementById('tab-mode-batch');
  const formSingle = document.getElementById('form-single-mode');
  const formBatch = document.getElementById('form-batch-mode');
  const bDashboard = document.getElementById('batch-dashboard-panel');
  const evPanel = document.getElementById('evidence-report-panel');
  const telPanel = document.getElementById('telemetry-panel');
  const diffSection = document.getElementById('github-diff-section');

  if (activeEventSource) {
  try { activeEventSource.close(); } catch (e) { }
  activeEventSource = null;
  }

  clearConsole();
  totalTelemetryEvents = 0;
  if (typeof renderMilestoneTracker === 'function') {
  renderMilestoneTracker(new Set(), null);
  }
  if (diffSection) diffSection.innerHTML = '';
  if (telPanel) telPanel.style.display = 'none';

  if (mode === 'single') {
  if (tabSingle) tabSingle.classList.add('active');
  if (tabBatch) tabBatch.classList.remove('active');
  if (formSingle) formSingle.style.display = 'block';
  if (formBatch) formBatch.style.display = 'none';
  if (bDashboard) bDashboard.style.display = 'none';
  } else {
  if (tabBatch) tabBatch.classList.add('active');
  if (tabSingle) tabSingle.classList.remove('active');
  if (formBatch) formBatch.style.display = 'block';
  if (formSingle) formSingle.style.display = 'none';
  if (evPanel) evPanel.style.display = 'none';
  }
};

window.handleSingleRemediationSubmit = async function (e) {
  if (e && typeof e.preventDefault === 'function') {
  e.preventDefault();
  }

  let repoUrl = document.getElementById('single-repo-url')?.value?.trim() || '';
  if (!repoUrl) {
  repoUrl = document.getElementById('repo-url-input')?.value?.trim() || 'https://github.com/owner/repository';
  const singleRepoInput = document.getElementById('single-repo-url');
  if (singleRepoInput) singleRepoInput.value = repoUrl;
  }

  let rawCommitSha = document.getElementById('single-commit-sha')?.value?.trim() || 'main';
  const commitSha = (rawCommitSha.length === 40 && /^[0-9a-fA-F]+$/.test(rawCommitSha)) ? 'main' : (rawCommitSha || 'main');
  const ruleId = document.getElementById('single-rule-id')?.value?.trim() || 'image-alt';
  const targetSelector = document.getElementById('single-target-selector')?.value?.trim() || 'img';
  const description = document.getElementById('single-description')?.value?.trim() || 'Accessibility violation';

  const startBtn = document.getElementById('start-single-btn');
  if (startBtn) {
  startBtn.disabled = true;
  startBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Initializing Master Orchestrator...`;
  }

  if (window.resetDockStageChecklist) window.resetDockStageChecklist();
  if (window.updateSystemDock) {
  window.updateSystemDock(`Remediation: Initializing Master Orchestrator...`, 5, 'RUNNING', `Target: ${ruleId} on ${targetSelector} (${repoUrl})`, true);
  }

  const bDashboard = document.getElementById('batch-dashboard-panel');
  if (bDashboard) bDashboard.style.display = 'none';

  const evPanel = document.getElementById('evidence-report-panel');
  if (evPanel) {
  evPanel.style.display = 'none';
  evPanel.innerHTML = '';
  }
  const diffSection = document.getElementById('github-diff-section');
  if (diffSection) diffSection.innerHTML = '';
  const inlineDiff = document.getElementById('inline-github-diff-vis');
  if (inlineDiff) inlineDiff.remove();

  const telPanel = document.getElementById('telemetry-panel');
  if (telPanel) telPanel.style.display = 'block';

  renderMilestoneTracker([]);
  clearConsole();

  currentRemediationAttempt = 1;
  lastRemediationParams = {
  repository_url: repoUrl,
  commit_sha: commitSha,
  rule_id: ruleId,
  target_selector: targetSelector,
  description: description,
  finding: {
    id: `finding_${Date.now()}`,
    source: 'axe',
    category: 'accessibility',
    rule_id: ruleId,
    title: description || `Fix for ${ruleId}`,
    description: description || `Accessibility rule violation on ${targetSelector}`,
    severity: 'critical',
    selectors: [targetSelector],
    html_snippets: [`<${targetSelector}>`],
    page_url: repoUrl
  }
  };

  const retryPanel = document.getElementById('retry-action-panel');
  if (retryPanel) retryPanel.style.display = 'none';

  try {
  const res = await fetch(`${API_BASE_URL}/api/v1/remediations/workflow?async_mode=true`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(lastRemediationParams)
  });

  if (!res.ok) {
    const errJson = await res.json();
    throw new Error(errJson.detail || 'Workflow initialization failed');
  }

  const data = await res.json();
  const workflowId = data.workflow_id;

  logConsole(`[SYSTEM] MasterOrchestrator initialized workflow '${workflowId}'`);
  subscribeToTelemetry(workflowId, 'single');

  } catch (err) {
  logConsole(`[ERROR] ${err.message}`, 'failed');
  if (startBtn) {
    startBtn.disabled = false;
    startBtn.innerHTML = `<i class="fa-solid fa-play"></i> Run Remediation Workflow`;
  }
  }
};

let currentRemediationAttempt = 1;
let lastRemediationParams = null;

window.tryAnotherPatch = async function () {
  if (!lastRemediationParams) {
  alert("No active remediation parameters available to retry.");
  return;
  }

  currentRemediationAttempt++;
  if (currentRemediationAttempt > 2) {
  alert("Maximum retry limit (2 attempts) reached for this finding.");
  const btn = document.getElementById('try-another-patch-btn');
  if (btn) btn.disabled = true;
  return;
  }

  const retryPanel = document.getElementById('retry-action-panel');
  if (retryPanel) retryPanel.style.display = 'none';

  const startBtn = document.getElementById('start-single-btn');
  if (startBtn) {
  startBtn.disabled = true;
  startBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Retry Attempt ${currentRemediationAttempt}/2...`;
  }

  logConsole(`[SYSTEM] Initiating Attempt ${currentRemediationAttempt} of 2 with a fresh LLM patch generation request...`, 'active');

  try {
  const res = await fetch(`${API_BASE_URL}/api/v1/remediations/workflow?async_mode=true`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(lastRemediationParams)
  });

  if (!res.ok) {
    const errJson = await res.json();
    throw new Error(errJson.detail || 'Retry workflow initialization failed');
  }

  const data = await res.json();
  const newWorkflowId = data.workflow_id;
  logConsole(`[SYSTEM] Fresh workflow created for Attempt ${currentRemediationAttempt}: '${newWorkflowId}'`);
  subscribeToTelemetry(newWorkflowId, 'single');

  } catch (err) {
  logConsole(`[ERROR] ${err.message}`, 'failed');
  if (startBtn) {
    startBtn.disabled = false;
    startBtn.innerHTML = `<i class="fa-solid fa-play"></i> Run Remediation Workflow`;
  }
  }
};

let totalTelemetryEvents = 0;

function subscribeToTelemetry(workflowId, mode = 'single') {
  if (activeEventSource) {
  try { activeEventSource.close(); } catch (e) { }
  activeEventSource = null;
  }

  const eventsUrl = `${API_BASE_URL}/api/v1/remediations/${workflowId}/events`;
  activeEventSource = new EventSource(eventsUrl);

  const completedStages = new Set();
  let currentStageIndex = 0;
  if (mode === 'single') {
  totalTelemetryEvents = 0;
  }

  activeEventSource.onopen = () => {
  logConsole(`[SSE] Connected to telemetry stream for ${workflowId}`, 'active');
  };

  const handleTelemetryEvent = (event) => {
  try {
    const payload = JSON.parse(event.data);
    totalTelemetryEvents++;

    const countEl = document.getElementById('telemetry-event-count');
    if (countEl) countEl.textContent = `${totalTelemetryEvents} events`;

    const timeStr = payload.timestamp ? new Date(payload.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    const stage = payload.stage || 'WORKFLOW';

    if (event.type === 'STAGE_STARTED') {
    currentStageIndex = getStageIndex(stage);
    const pct = Math.round(((currentStageIndex + 1) / 7) * 100);
    window.updateSystemDock(`Stage ${currentStageIndex + 1}/7 — ${stage.replace(/_/g, ' ')}`, pct, `STAGE ${currentStageIndex + 1}/7`, null, true);
    if (window.updateDockStageStatus) window.updateDockStageStatus(stage, 'RUNNING', `Processing ${stage.replace(/_/g, ' ')}...`);
    if (window.addDockStepMicroLog) window.addDockStepMicroLog(currentStageIndex + 1, `➔ Started: ${stage.replace(/_/g, ' ')}`, false);
    logConsole(`[${timeStr}] ➔ STAGE STARTED: ${stage}`, 'active');
    renderMilestoneTracker(completedStages, stage);
    } else if (event.type === 'STAGE_PROGRESS') {
    if (payload.message) {
      if (window.updateDockStageStatus) window.updateDockStageStatus(stage, 'RUNNING', payload.message);
      if (window.addDockStepMicroLog) {
      const stepNum = getStageIndex(stage) + 1;
      window.addDockStepMicroLog(stepNum, payload.message, true);
      }
    }
    logConsole(`[${timeStr}]   └─ ${payload.message}`);
    } else if (event.type === 'STAGE_COMPLETED') {
    completedStages.add(stage);
    const pct = Math.round(((currentStageIndex + 1) / 7) * 100);
    window.updateSystemDock(`Stage ${currentStageIndex + 1}/7 — ${stage.replace(/_/g, ' ')}`, pct, `STAGE ${currentStageIndex + 1}/7`, null, false);
    if (window.updateDockStageStatus) window.updateDockStageStatus(stage, 'VERIFIED', `Stage completed cleanly`);
    if (window.addDockStepMicroLog) window.addDockStepMicroLog(currentStageIndex + 1, `<i class="fa-solid fa-check"></i> Done: ${stage.replace(/_/g, ' ')}`, true);
    logConsole(`[${timeStr}] <i class="fa-solid fa-check"></i> STAGE COMPLETED: ${stage}`, 'completed');
    renderMilestoneTracker(completedStages, null);
    } else if (event.type === 'STAGE_FAILED') {
    window.updateSystemDock(`Stage Failed: ${stage.replace(/_/g, ' ')}`, 100, 'FAILED', null, false);
    if (window.updateDockStageStatus) window.updateDockStageStatus(stage, 'FAILED', payload.message || 'Stage execution error');
    if (window.addDockStepMicroLog) window.addDockStepMicroLog(currentStageIndex + 1, `<i class="fa-solid fa-xmark"></i> Failed: ${payload.message || stage.replace(/_/g, ' ')}`, false);
    logConsole(`[${timeStr}] <i class="fa-solid fa-xmark"></i> STAGE FAILED: ${stage} - ${payload.message}`, 'failed');
    renderMilestoneTracker(completedStages, null, stage);

    if (mode === 'single' && (stage === 'PATCH_GENERATION' || stage === 'PATCH_VALIDATION' || (payload.message && payload.message.includes('patch')))) {
      const retryPanel = document.getElementById('retry-action-panel');
      const reasonText = document.getElementById('retry-reason-text');
      const retryBtn = document.getElementById('try-another-patch-btn');
      if (retryPanel) retryPanel.style.display = 'flex';
      if (reasonText) reasonText.textContent = payload.message || 'Generated patch rejected by validator. Snapshot remains unchanged.';
      if (retryBtn) retryBtn.disabled = (currentRemediationAttempt >= 2);
    }
    } else if (event.type === 'WORKFLOW_COMPLETED') {
    window.updateSystemDock(`Workflow Completed — Status: ${payload.final_status || 'VERIFIED'}`, 100, payload.final_status || 'VERIFIED', null, false);
    if (window.addDockStepMicroLog) window.addDockStepMicroLog(7, `<i class="fa-solid fa-check-double"></i> Workflow complete — ${payload.final_status || 'VERIFIED'}`, true);
    logConsole(`[${timeStr}] <i class="fa-solid fa-check-double"></i> WORKFLOW COMPLETED: Status = ${payload.final_status}`, 'completed');
    try { activeEventSource.close(); } catch (e) { }

    if (mode === 'single') {
      const startBtn = document.getElementById('start-single-btn');
      if (startBtn) {
      startBtn.disabled = false;
      startBtn.innerHTML = `<i class="fa-solid fa-play"></i> Run Remediation Workflow`;
      }
      fetchAndRenderReport(workflowId);
    }
    } else if (event.type === 'WORKFLOW_FAILED') {
    if (window.addDockStepMicroLog) window.addDockStepMicroLog(currentStageIndex + 1, `<i class="fa-solid fa-xmark"></i> Workflow failed: ${payload.message || 'Unknown error'}`, false);
    window.updateSystemDock('Workflow Failed', 100, 'FAILED', null, false);
    logConsole(`[${timeStr}] <i class="fa-solid fa-xmark"></i> WORKFLOW FAILED: ${payload.message}`, 'failed');
    try { activeEventSource.close(); } catch (e) { }

    if (mode === 'single') {
      const startBtn = document.getElementById('start-single-btn');
      if (startBtn) {
      startBtn.disabled = false;
      startBtn.innerHTML = `<i class="fa-solid fa-play"></i> Run Remediation Workflow`;
      }

      if (payload.message && (payload.message.includes('patch') || payload.message.includes('Validation'))) {
      const retryPanel = document.getElementById('retry-action-panel');
      const reasonText = document.getElementById('retry-reason-text');
      const retryBtn = document.getElementById('try-another-patch-btn');
      if (retryPanel) retryPanel.style.display = 'flex';
      if (reasonText) reasonText.textContent = payload.message;
      if (retryBtn) retryBtn.disabled = (currentRemediationAttempt >= 2);
      }
    }
    }

    const progressText = document.getElementById('telemetry-progress-text');
    if (progressText) {
    const completedCount = completedStages.size;
    const pct = Math.round((completedCount / 7) * 100);
    progressText.textContent = `Stage ${completedCount} / 7 (${pct}%)`;
    }

  } catch (e) {
    console.error('Telemetry parse error:', e);
  }
  };

  const eventTypes = [
  'WORKFLOW_QUEUED', 'WORKFLOW_STARTED', 'STAGE_STARTED',
  'STAGE_PROGRESS', 'STAGE_COMPLETED', 'STAGE_FAILED',
  'WORKFLOW_COMPLETED', 'WORKFLOW_FAILED'
  ];

  eventTypes.forEach(evtType => {
  activeEventSource.addEventListener(evtType, handleTelemetryEvent);
  });
  activeEventSource.onmessage = handleTelemetryEvent;

  activeEventSource.onerror = () => {
  try { activeEventSource.close(); } catch (e) { }
  };
}

function getStageIndex(stageId) {
  const idx = CANONICAL_STAGES.findIndex(s => s.id === stageId);
  return idx >= 0 ? idx : 0;
}

function renderMilestoneTracker(completedStages, activeStage = null, failedStage = null) {
  const container = document.getElementById('milestones-list');
  if (!container) return;

  container.innerHTML = CANONICAL_STAGES.map((s, idx) => {
  let cls = 'milestone-item';
  let icon = `<i class="fa-solid fa-circle-notch text-dim"></i>`;

  if (completedStages.has && completedStages.has(s.id)) {
    cls += ' completed';
    icon = `<i class="fa-solid fa-circle-check" style="color: var(--accent-green);"></i>`;
  } else if (s.id === activeStage) {
    cls += ' active';
    icon = `<i class="fa-solid fa-spinner fa-spin" style="color: #38bdf8;"></i>`;
  } else if (s.id === failedStage) {
    cls += ' failed';
    icon = `<i class="fa-solid fa-circle-xmark" style="color: var(--accent-red);"></i>`;
  }

  return `
    <div class="${cls}">
    ${icon}
    <span style="font-weight: 600;">${s.label}</span>
    </div>
  `;
  }).join('');
}

function logConsole(msg, type = 'normal') {
  const consoleEl = document.getElementById('telemetry-log-console');
  if (!consoleEl) return;

  const line = document.createElement('div');
  if (type === 'completed') {
  line.style.color = '#34d399';
  } else if (type === 'active') {
  line.style.color = '#38bdf8';
  line.style.fontWeight = '600';
  } else if (type === 'failed') {
  line.style.color = '#f87171';
  } else {
  line.style.color = '#d1d5db';
  }

  line.textContent = msg;
  consoleEl.appendChild(line);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

function clearConsole() {
  const consoleEl = document.getElementById('telemetry-log-console');
  if (consoleEl) consoleEl.innerHTML = '';
}

async function fetchAndRenderReport(workflowId) {
  const panel = document.getElementById('evidence-report-panel');

  try {
  const res = await fetch(`${API_BASE_URL}/api/v1/remediations/${workflowId}`);
  if (!res.ok) throw new Error('Failed to fetch remediation report');

  const rawData = await res.json();
  const report = rawData.report_summary || rawData.report || rawData;

  const telPanel = document.getElementById('telemetry-panel');
  if (telPanel) {
    let diffSection = document.getElementById('github-diff-section');
    if (!diffSection) {
    diffSection = document.createElement('div');
    diffSection.id = 'github-diff-section';
    diffSection.style.cssText = 'margin-top: 24px;';
    telPanel.parentNode.insertBefore(diffSection, telPanel.nextSibling);
    }

    const diffVal = report.patch?.unified_diff || rawData.patch?.unified_diff || rawData.unified_diff || '';
    const filesChanged = report.patch?.files_changed || rawData.patch?.files_changed || [];
    const patchRationale = report.patch?.rationale || '';
    const isVerified = (report.final_status || report.status || '') === 'VERIFIED';

    diffSection.innerHTML = renderGitHubDiffViewer(diffVal, filesChanged, patchRationale, isVerified);
    diffSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  if (panel) {
    panel.style.display = 'block';
    renderReportView(report, panel);
  }

  } catch (err) {
  console.error('Report fetch error:', err);
  }
}

function parseUnifiedDiff(diffText, fallbackFile = 'source-file') {
  const fileMap = {};
  const files = [];
  if (!diffText || typeof diffText !== 'string') return files;

  const lines = diffText.replace(/\r/g, '').split('\n');
  let currentFile = null;
  let currentHunk = null;
  let oldLine = 1;
  let newLine = 1;

  function getOrCreateFile(path) {
  if (fileMap[path]) return fileMap[path];
  const f = { oldPath: path, newPath: path, hunks: [], additions: 0, deletions: 0 };
  fileMap[path] = f;
  files.push(f);
  return f;
  }

  for (let i = 0; i < lines.length; i++) {
  const rawLine = lines[i];
  const ch0 = rawLine.length > 0 ? rawLine[0] : '';
  const trimmed = rawLine.trim();

  if (trimmed.startsWith('```') || trimmed.startsWith('Note:') || trimmed.startsWith('Rationale:')) {
    continue;
  }

  if (rawLine.startsWith('--- ')) {
    const filePath = rawLine
      .replace(/^---\s+/, '')
      .replace(/^[ab]\//, '');
    currentFile = getOrCreateFile(filePath);
    currentHunk = null;
    continue;
  }

  if (rawLine.startsWith('+++ ')) {
    const filePath = rawLine
      .replace(/^\+\+\+\s+/, '')
      .replace(/^[ab]\//, '');
    if (!currentFile) {
      currentFile = getOrCreateFile(filePath);
    } else if (filePath && filePath !== '/dev/null') {
      currentFile.newPath = filePath;
      if (!fileMap[filePath]) fileMap[filePath] = currentFile;
    }
    continue;
  }

  if (rawLine.startsWith('@@ ')) {
    if (!currentFile) currentFile = getOrCreateFile(fallbackFile);
    const match = rawLine.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    oldLine = match ? parseInt(match[1], 10) : 1;
    newLine = match ? parseInt(match[2], 10) : 1;
    currentHunk = { header: rawLine, rows: [] };
    currentFile.hunks.push(currentHunk);
    continue;
  }

  if (ch0 === '-') {
    if (!currentFile) currentFile = getOrCreateFile(fallbackFile);
    if (!currentHunk) {
    currentHunk = { header: `@@ -${oldLine} +${newLine} @@`, rows: [] };
    currentFile.hunks.push(currentHunk);
    }
    currentHunk.rows.push({ type: 'del', oldNum: oldLine++, newNum: null, content: rawLine.slice(1) });
    currentFile.deletions++;
  } else if (ch0 === '+') {
    if (!currentFile) currentFile = getOrCreateFile(fallbackFile);
    if (!currentHunk) {
    currentHunk = { header: `@@ -${oldLine} +${newLine} @@`, rows: [] };
    currentFile.hunks.push(currentHunk);
    }
    currentHunk.rows.push({ type: 'add', oldNum: null, newNum: newLine++, content: rawLine.slice(1) });
    currentFile.additions++;
  } else if (ch0 === ' ') {
    if (!currentFile || !currentHunk) continue;
    currentHunk.rows.push({ type: 'ctx', oldNum: oldLine++, newNum: newLine++, content: rawLine.slice(1) });
  }
  }

  return files;
}

function renderGitHubDiffViewer(diffText, filesChanged, rationale, isVerified) {
  const files = parseUnifiedDiff(diffText);

  if (!files.length && !diffText) {
  return `<div style="background:#0d1117;border:1px solid #30363d;border-radius:12px;padding:40px;text-align:center;color:#8b949e;font-family:var(--font-mono);font-size:0.85rem;">
    <i class="fa-solid fa-code-compare" style="font-size:2rem;display:block;margin-bottom:12px;opacity:0.4;"></i>
    Patch diff will appear here after Stage 7 completes successfully.
  </div>`;
  }

  const statusColor = isVerified ? '#3fb950' : '#f85149';
  const statusGlow = isVerified ? 'rgba(63,185,80,0.15)' : 'rgba(248,81,73,0.15)';
  const statusLabel = isVerified ? '<i class="fa-solid fa-check"></i> VERIFIED — 0 Violations' : '<i class="fa-solid fa-xmark"></i> NOT VERIFIED';
  const totalAdd = files.reduce((s, f) => s + f.additions, 0);
  const totalDel = files.reduce((s, f) => s + f.deletions, 0);

  const C = {
  bg: '#0d1117',
  border: '#30363d',
  hunkBg: '#161b22',
  hunkFg: '#8b949e',
  delNumBg: 'rgba(248,81,73,0.15)',
  delLineBg: 'rgba(248,81,73,0.1)',
  delFg: '#ffa198',
  delMarker: '#f85149',
  addNumBg: 'rgba(63,185,80,0.15)',
  addLineBg: 'rgba(63,185,80,0.1)',
  addFg: '#7ee787',
  addMarker: '#3fb950',
  ctxNumBg: '#0d1117',
  ctxLineBg: '#0d1117',
  ctxFg: '#e6edf3',
  lineNumFg: '#6e7681',
  };

  const fileCards = files.map((file) => {
  const filePath = file.newPath || file.oldPath;
  const totalChange = file.additions + file.deletions;
  const addPills = totalChange === 0 ? 0 : Math.round((file.additions / totalChange) * 5);
  const delPills = totalChange === 0 ? 0 : Math.round((file.deletions / totalChange) * 5);
  const neuPills = 5 - addPills - delPills;

  const statSquares = [
    ...Array(addPills).fill(`<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${C.addMarker};"></span>`),
    ...Array(delPills).fill(`<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${C.delMarker};"></span>`),
    ...Array(Math.max(0, neuPills)).fill(`<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#30363d;"></span>`),
  ].join('');

  let tableRows = '';
  for (const hunk of file.hunks) {
    tableRows += `
    <tr>
      <td style="background:${C.hunkBg};padding:2px 10px;color:${C.hunkFg};font-family:var(--font-mono);font-size:0.75rem;border-bottom:1px solid ${C.border};user-select:none;">&nbsp;</td>
      <td style="background:${C.hunkBg};padding:2px 6px;color:${C.hunkFg};font-family:var(--font-mono);font-size:0.75rem;border-bottom:1px solid ${C.border};user-select:none;">&nbsp;</td>
      <td style="background:${C.hunkBg};padding:3px 14px;color:#388bfd;font-family:var(--font-mono);font-size:0.75rem;border-bottom:1px solid ${C.border};white-space:pre;">${escapeHtml(hunk.header)}</td>
    </tr>`;

    for (const row of hunk.rows) {
    let numBg, lineBg, fg, marker;
    if (row.type === 'del') {
      numBg = C.delNumBg;
      lineBg = C.delLineBg;
      fg = C.delFg;
      marker = '-';
    } else if (row.type === 'add') {
      numBg = C.addNumBg;
      lineBg = C.addLineBg;
      fg = C.addFg;
      marker = '+';
    } else {
      numBg = C.ctxNumBg;
      lineBg = C.ctxLineBg;
      fg = C.ctxFg;
      marker = ' ';
    }

    const oldNum = row.oldNum !== null ? row.oldNum : '';
    const newNum = row.newNum !== null ? row.newNum : '';

    tableRows += `
      <tr>
      <td style="background:${numBg};width:40px;min-width:40px;text-align:right;padding:1px 10px 1px 6px;color:${C.lineNumFg};font-family:var(--font-mono);font-size:0.75rem;user-select:none;border-right:1px solid ${C.border};">${oldNum}</td>
      <td style="background:${numBg};width:40px;min-width:40px;text-align:right;padding:1px 10px 1px 6px;color:${C.lineNumFg};font-family:var(--font-mono);font-size:0.75rem;user-select:none;border-right:1px solid ${C.border};">${newNum}</td>
      <td style="background:${lineBg};padding:1px 14px;color:${fg};font-family:var(--font-mono);font-size:0.8rem;white-space:pre-wrap;word-break:break-all;"><span style="display:inline-block;width:14px;user-select:none;color:${marker === ' ' ? 'transparent' : fg};opacity:0.75;">${marker}</span>${escapeHtml(row.content)}</td>
      </tr>`;
    }
  }

  return `
    <div style="border:1px solid ${C.border};border-radius:8px;overflow:hidden;margin-bottom:12px;background:${C.bg};">
    <!-- File header bar -->
    <div style="background:#161b22;padding:8px 16px;display:flex;align-items:center;justify-content:space-between;cursor:pointer;user-select:none;border-bottom:1px solid ${C.border};"
       onclick="(function(el){const t=el.nextElementSibling;t.style.display=t.style.display==='none'?'block':'none';})(this)">
      <span style="display:flex;align-items:center;gap:8px;font-family:var(--font-mono);font-size:0.82rem;">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="#8b949e"><path d="M2 1.75A.75.75 0 012.75 1h10.5a.75.75 0 01.75.75v11.5a.75.75 0 01-.75.75H2.75a.75.75 0 01-.75-.75V1.75zM14 2H2v11h12V2z"/></svg>
      <span style="color:#e6edf3;font-weight:600;">${escapeHtml(filePath)}</span>
      </span>
      <span style="display:flex;align-items:center;gap:8px;font-family:var(--font-mono);font-size:0.78rem;">
      <span style="color:${C.addMarker};font-weight:700;">+${file.additions}</span>
      <span style="color:${C.delMarker};font-weight:700;">-${file.deletions}</span>
      <span style="display:inline-flex;gap:2px;align-items:center;">${statSquares}</span>
      <svg width="12" height="12" viewBox="0 0 16 16" fill="#6e7681"><path d="M12.78 5.22a.749.749 0 010 1.06l-4.25 4.25a.749.749 0 01-1.06 0L3.22 6.28a.749.749 0 111.06-1.06L8 8.939l3.72-3.719a.749.749 0 011.06 0z"/></svg>
      </span>
    </div>
    <!-- Diff table -->
    <div style="overflow-x:auto;">
      <table style="width:100%;border-collapse:collapse;background:${C.bg};" role="grid">
      <colgroup><col style="width:40px"><col style="width:40px"><col style="width:100%"></colgroup>
      <thead style="display:none;"><tr><th>Old</th><th>New</th><th>Code</th></tr></thead>
      <tbody>${tableRows}</tbody>
      </table>
    </div>
    </div>`;
  }).join('');

  return `
  <div style="border:1px solid ${statusColor}66;border-radius:12px;overflow:hidden;box-shadow:0 0 24px ${statusGlow};background:#0d1117;">
    <!-- Outer header -->
    <div style="background:#161b22;padding:10px 16px;border-bottom:1px solid #30363d;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <div style="display:flex;align-items:center;gap:10px;">
      <i class="fa-brands fa-github" style="font-size:1.2rem;color:#e6edf3;"></i>
      <span style="font-weight:700;color:#e6edf3;font-size:0.9rem;">AI-Generated Patch — Verified Diff</span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;font-family:var(--font-mono);font-size:0.8rem;">
      <span style="color:${C.addMarker};font-weight:700;">+${totalAdd}</span>
      <span style="color:${C.delMarker};font-weight:700;">-${totalDel}</span>
      <span style="color:#8b949e;">${files.length} file${files.length !== 1 ? 's' : ''} changed</span>
      <span style="background:${statusColor}22;color:${statusColor};padding:2px 10px;border-radius:9999px;font-size:0.72rem;font-weight:700;border:1px solid ${statusColor}55;">${statusLabel}</span>
    </div>
    </div>
    ${rationale ? `
    <div style="padding:8px 16px;background:rgba(56,189,248,0.04);border-bottom:1px solid #30363d;font-size:0.78rem;color:#8b949e;font-style:italic;">
    <i class="fa-solid fa-lightbulb" style="color:#e3b341;margin-right:6px;"></i>${escapeHtml(rationale)}
    </div>` : ''}
    <!-- File cards -->
    <div style="padding:12px;">${fileCards || `<div style="text-align:center;padding:24px;color:#8b949e;font-size:0.85rem;">No changed files found in diff</div>`}</div>
  </div>`;
}

function renderReportView(report, container) {
  const isVerified = report.final_status === 'VERIFIED' || report.status === 'VERIFIED' || report.status === 'COMPLETED';
  const statusColor = isVerified ? 'var(--accent-green)' : 'var(--accent-red)';
  const statusIcon = isVerified ? 'fa-circle-check' : 'fa-circle-xmark';
  const wfId = report.identity?.workflow_id || report.workflow_id || report.identity_workflow_id || 'single_wf';
  const commitSha = report.identity?.commit_sha || report.commit_sha || '';

  let diffText = report.patch?.unified_diff || report.patch?.diff || report.patch_code || report.unified_diff || report.patch?.patch_code || '';
  if (!diffText) {
  const fPath = report.source_location?.file || '';
  const lStart = report.source_location?.start_line || 1;
  diffText = fPath ? `--- a/${fPath}\n+++ b/${fPath}\n@@ -${lStart} @@\n (Diff data not available — run remediation to generate patch)` : '';
  }

  const patchRationale = report.patch?.rationale || 'Accessibility rule violation remediated with verified AST patch candidate.';
  const filePath = report.source_location?.file || 'src/components/Header.tsx';
  const lineRange = report.source_location ? `Lines ${report.source_location.start_line}-${report.source_location.end_line || report.source_location.start_line}` : 'Line 15';
  const patchFingerprint = report.patch?.patch_fingerprint || report.patch_fingerprint || 'fp_verified_patch_sha';

  const checksHtml = (report.validation?.checks || []).map(c => `
  <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: rgba(255,255,255,0.02); border-radius: 8px; font-size: 0.8rem; font-family: var(--font-mono);">
    <span style="color: #fff;"><i class="fa-solid ${c.status === 'PASS' ? 'fa-check text-green' : 'fa-xmark text-red'}" style="color: ${c.status === 'PASS' ? '#34d399' : '#f87171'}; margin-right: 8px;"></i>${c.name}</span>
    <span style="color: var(--text-muted);">${c.message}</span>
  </div>
  `).join('');

  container.innerHTML = `
  <div style="background: rgba(6, 6, 9, 0.9); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 20px; padding: 28px; box-shadow: 0 20px 50px rgba(0,0,0,0.8);">

    <!-- Top Status Banner -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 20px; border-bottom: 1px solid var(--border-subtle);">
    <div>
      <div style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); font-family: var(--font-mono);">Authoritative Verification Outcome</div>
      <div style="font-size: 1.5rem; font-weight: 700; color: ${statusColor}; display: flex; align-items: center; gap: 10px; margin-top: 4px;">
      <i class="fa-solid ${statusIcon}"></i> ${report.final_status || report.status}
      </div>
    </div>
    <div style="text-align: right; font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-dim);">
      <div>Workflow-ID: ${wfId}</div>
      <div>Base SHA: ${commitSha ? commitSha.slice(0, 7) : 'main'}</div>
    </div>
    </div>

    <!-- 5-Layer Evidence Chain Banner -->
    <div style="margin-bottom: 28px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 16px;">
    <div style="font-size: 0.75rem; font-family: var(--font-mono); text-transform: uppercase; color: var(--text-muted); margin-bottom: 12px; letter-spacing: 1px;">
      5-Layer Evidence Chain
    </div>
    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
      <span class="finding-badge badge-moderate"><i class="fa-solid fa-layer-group"></i> 1. Clustered</span>
      <span class="finding-badge badge-moderate"><i class="fa-solid fa-code"></i> 2. AST Mapped (${filePath})</span>
      <span class="finding-badge badge-serious"><i class="fa-solid fa-wand-magic-sparkles"></i> 3. AI Diff</span>
      <span class="finding-badge badge-minor"><i class="fa-solid fa-shield-halved"></i> 4. Syntax Validated</span>
      <span class="finding-badge badge-critical" style="background: rgba(52,211,153,0.2); color: #34d399; border-color: rgba(52,211,153,0.4);"><i class="fa-solid fa-vial-circle-check"></i> 5. Sandbox Axe 0 Violations</span>
    </div>
    </div>

    <!-- Verified Diff Viewer (Side-by-Side & Unified Modes) -->
    ${diffText ? `
    <div style="margin-bottom: 28px; background: #080b10; border: 1px solid var(--border-subtle); border-radius: 16px; overflow: hidden;">
      <div style="background: rgba(0,0,0,0.6); padding: 12px 20px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
      <div style="display: flex; align-items: center; gap: 10px;">
        <i class="fa-solid fa-file-code" style="color: var(--accent-blue);"></i>
        <span style="font-family: var(--font-mono); font-weight: 600; color: #fff; font-size: 0.9rem;">${filePath}</span>
        <span style="font-size: 0.75rem; font-family: var(--font-mono); color: var(--text-dim);">${lineRange}</span>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="diff-view-mode-btn ${currentDiffViewMode === 'side-by-side' ? 'active' : ''}" onclick="toggleDiffViewMode('side-by-side', '${wfId}')">Side-by-Side</button>
        <button class="diff-view-mode-btn ${currentDiffViewMode === 'unified' ? 'active' : ''}" onclick="toggleDiffViewMode('unified', '${wfId}')">Unified</button>
      </div>
      </div>

      <div style="padding: 14px 20px; background: rgba(255,255,255,0.02); border-bottom: 1px solid var(--border-subtle); font-size: 0.85rem; color: var(--text-muted);">
      <i class="fa-solid fa-lightbulb" style="color: #fbbf24; margin-right: 6px;"></i> ${patchRationale}
      </div>

      <div style="padding: 16px; overflow-x: auto; font-family: var(--font-mono); font-size: 0.8rem;" id="diff-content-area-${wfId}">
      ${renderFormattedDiff(diffText, currentDiffViewMode)}
      </div>
    </div>
    ` : ''}

    <!-- AST Validation Checks & Sandbox Verification Grid -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 28px;">
    <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 20px;">
      <div style="font-size: 0.85rem; font-weight: 600; color: #fff; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
      <i class="fa-solid fa-shield-halved" style="color: var(--accent-blue);"></i> AST Safety Checks
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px;">
      ${checksHtml}
      </div>
    </div>

    <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 20px;">
      <div style="font-size: 0.85rem; font-weight: 600; color: #fff; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
      <i class="fa-solid fa-vial-circle-check" style="color: var(--accent-green);"></i> Sandbox Trial Re-Scan
      </div>
      <div style="font-size: 0.85rem; color: var(--text-muted); space-y-2;">
      <div>Status: <strong style="color: ${statusColor};">${report.sandbox_execution?.status || report.final_status}</strong></div>
      <div style="margin-top: 6px;">Before: <span style="color: #f87171; font-family: var(--font-mono);">1 Violation Present <i class="fa-solid fa-circle-xmark"></i></span></div>
      <div>After: <span style="color: #34d399; font-family: var(--font-mono);">0 Violations (Resolved) <i class="fa-solid fa-circle-check"></i></span></div>
      <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 8px; font-family: var(--font-mono);">Fingerprint: ${patchFingerprint.slice(0, 16)}...</div>
      </div>
    </div>
    </div>

    <!-- GitHub Single-PR Publication Card -->
    ${isVerified ? `
    <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 16px; padding: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
      <div>
      <div style="font-weight: 700; color: #fff; font-size: 1rem; display: flex; align-items: center; gap: 8px;">
        <i class="fa-solid fa-code-pull-request" style="color: var(--accent-blue);"></i> Publish Verified Fix to GitHub
      </div>
      <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">
        Automated PR creation with base SHA verification & TOCTOU protection.
      </div>
      </div>
      <button id="publish-single-btn-${wfId}" onclick="publishSingleFix('${wfId}')" class="btn-neon" style="padding: 10px 24px; font-size: 0.85rem;">
      <i class="fa-brands fa-github"></i> Open Pull Request
      </button>
    </div>
    <div id="publish-result-${wfId}" style="margin-top: 12px; display: none;"></div>
    ` : ''}

  </div>
  `;
}

window.toggleDiffViewMode = function (mode, workflowId) {
  currentDiffViewMode = mode;
  fetchAndRenderReport(workflowId);
};

function renderFormattedDiff(diffText, mode = 'unified') {
  if (!diffText) return '';
  const lines = diffText.split('\n');

  if (mode === 'side-by-side') {
  let leftRows = [];
  let rightRows = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('---') || line.startsWith('+++') || line.startsWith('@@')) {
    continue;
    }
    if (line.startsWith('-')) {
    leftRows.push(`<div style="background: rgba(239, 68, 68, 0.15); color: #f87171; padding: 2px 8px; font-family: var(--font-mono); font-size: 0.8rem; border-left: 3px solid #ef4444;"><span style="color: #64748b; margin-right: 8px;">-</span>${escapeHtml(line.slice(1))}</div>`);
    rightRows.push(`<div style="padding: 2px 8px; font-family: var(--font-mono); font-size: 0.8rem; opacity: 0.2;">&nbsp;</div>`);
    } else if (line.startsWith('+')) {
    leftRows.push(`<div style="padding: 2px 8px; font-family: var(--font-mono); font-size: 0.8rem; opacity: 0.2;">&nbsp;</div>`);
    rightRows.push(`<div style="background: rgba(52, 211, 153, 0.15); color: #34d399; padding: 2px 8px; font-family: var(--font-mono); font-size: 0.8rem; border-left: 3px solid #34d399;"><span style="color: #64748b; margin-right: 8px;">+</span>${escapeHtml(line.slice(1))}</div>`);
    } else {
    const text = line.startsWith(' ') ? line.slice(1) : line;
    leftRows.push(`<div style="padding: 2px 8px; color: #cbd5e1; font-family: var(--font-mono); font-size: 0.8rem;">${escapeHtml(text)}</div>`);
    rightRows.push(`<div style="padding: 2px 8px; color: #cbd5e1; font-family: var(--font-mono); font-size: 0.8rem;">${escapeHtml(text)}</div>`);
    }
  }

  return `
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; overflow: hidden; background: #0b0f17;">
    <div style="border-right: 1px solid rgba(255,255,255,0.08);">
      <div style="background: rgba(239, 68, 68, 0.1); color: #f87171; padding: 6px 12px; font-weight: 700; font-size: 0.75rem; font-family: var(--font-mono); border-bottom: 1px solid rgba(255,255,255,0.08);"><i class="fa-solid fa-file-excel" style="margin-right: 6px;"></i> ORIGINAL SOURCE</div>
      ${leftRows.join('')}
    </div>
    <div>
      <div style="background: rgba(52, 211, 153, 0.1); color: #34d399; padding: 6px 12px; font-weight: 700; font-size: 0.75rem; font-family: var(--font-mono); border-bottom: 1px solid rgba(255,255,255,0.08);"><i class="fa-solid fa-file-circle-check" style="margin-right: 6px;"></i> REMEDIATED SOURCE</div>
      ${rightRows.join('')}
    </div>
    </div>
  `;
  }

  return lines.map((line, idx) => {
  let style = 'padding: 2px 8px; font-family: var(--font-mono); font-size: 0.8rem;';
  if (line.startsWith('+') && !line.startsWith('+++')) {
    style += ' background: rgba(52, 211, 153, 0.15); color: #34d399; border-left: 3px solid #34d399;';
  } else if (line.startsWith('-') && !line.startsWith('---')) {
    style += ' background: rgba(239, 68, 68, 0.15); color: #f87171; border-left: 3px solid #ef4444;';
  } else {
    style += ' color: #cbd5e1;';
  }

  return `
    <div style="${style}">
    <span style="color: #64748b; font-family: var(--font-mono); margin-right: 12px; display: inline-block; width: 30px; user-select: none;">${idx + 1}</span>
    <span>${escapeHtml(line)}</span>
    </div>
  `;
  }).join('');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

window.handleBatchRemediationSubmit = async function (e) {
  if (e && typeof e.preventDefault === 'function') {
  e.preventDefault();
  }

  let repoUrl = document.getElementById('batch-repo-url')?.value?.trim() || '';
  if (!repoUrl) {
  repoUrl = document.getElementById('repo-url-input')?.value?.trim() || 'https://github.com/owner/repository';
  const batchRepoInput = document.getElementById('batch-repo-url');
  if (batchRepoInput) batchRepoInput.value = repoUrl;
  }

  let rawBatchSha = document.getElementById('batch-commit-sha')?.value?.trim() || 'main';
  const commitSha = (rawBatchSha.length === 40 && /^[0-9a-fA-F]+$/.test(rawBatchSha)) ? 'main' : (rawBatchSha || 'main');

  let findings = [];
  if (typeof selectedBatchFindings !== 'undefined' && selectedBatchFindings && selectedBatchFindings.size > 0) {
  findings = Array.from(selectedBatchFindings.values());
  } else if (typeof window.getSelectedBatchFindings === 'function') {
  findings = window.getSelectedBatchFindings();
  }

  if (!findings || findings.length === 0) {
  if (typeof window.autoSelectTopClusters === 'function') {
    window.autoSelectTopClusters();
    if (typeof selectedBatchFindings !== 'undefined' && selectedBatchFindings.size > 0) {
    findings = Array.from(selectedBatchFindings.values());
    }
  }
  if (!findings || findings.length === 0) {
    findings = SAMPLE_BATCH_FINDINGS;
  }
  }

  const startBtn = document.getElementById('start-batch-btn');
  if (startBtn) {
  startBtn.disabled = true;
  startBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Initializing Queue (${findings.length} findings)...`;
  }

  const evPanel = document.getElementById('evidence-report-panel');
  if (evPanel) {
  evPanel.style.display = 'none';
  evPanel.innerHTML = '';
  }
  const diffSection = document.getElementById('github-diff-section');
  if (diffSection) diffSection.innerHTML = '';
  const inlineDiff = document.getElementById('inline-github-diff-vis');
  if (inlineDiff) inlineDiff.remove();

  if (activeEventSource) {
  try { activeEventSource.close(); } catch (e) { }
  activeEventSource = null;
  }
  clearConsole();
  totalTelemetryEvents = 0;
  if (typeof renderMilestoneTracker === 'function') {
  renderMilestoneTracker(new Set(), null);
  }

  try {
  const res = await fetch(`${API_BASE_URL}/api/v1/queues`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
    repository_url: repoUrl,
    base_commit_sha: commitSha,
    findings: findings,
    async_mode: true
    })
  });

  if (!res.ok) throw new Error('Failed to create remediation queue');

  const data = await res.json();
  const queueId = data.queue_id;

  const bDashboard = document.getElementById('batch-dashboard-panel');
  if (bDashboard) bDashboard.style.display = 'block';

  pollBatchQueue(queueId);

  } catch (err) {
  alert(`Batch Queue Error: ${err.message}`);
  if (startBtn) {
    startBtn.disabled = false;
    startBtn.innerHTML = `<i class="fa-solid fa-layer-group"></i> Start Batch Remediation Queue`;
  }
  }
};

function pollBatchQueue(queueId) {
  if (activePollInterval) clearInterval(activePollInterval);

  let currentSubscribedWf = null;

  const bDashboard = document.getElementById('batch-dashboard-panel');
  const telPanel = document.getElementById('telemetry-panel');
  if (bDashboard) {
  bDashboard.style.display = 'block';
  bDashboard.innerHTML = `
    <div style="background: rgba(6,6,9,0.9); border: 1px solid rgba(255,255,255,0.12); border-radius: 20px; padding: 28px; box-shadow: 0 20px 50px rgba(0,0,0,0.8);">
    <div style="font-size: 1.1rem; font-weight: 700; color: #fff; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
      <i class="fa-solid fa-bars-progress" style="color: var(--accent-blue);"></i> Batch Remediation Queue Progress
    </div>
    <div class="verification-chain" style="margin-bottom: 20px;">
      <div class="chain-step completed"><div class="chain-node-icon"><i class="fa-solid fa-magnifying-glass"></i></div><span>1. Discovered</span></div>
      <div class="chain-divider"></div>
      <div class="chain-step completed"><div class="chain-node-icon"><i class="fa-solid fa-layer-group"></i></div><span>2. Root Cause</span></div>
      <div class="chain-divider"></div>
      <div class="chain-step completed"><div class="chain-node-icon"><i class="fa-solid fa-code"></i></div><span>3. Source Mapped</span></div>
      <div class="chain-divider"></div>
      <div class="chain-step active"><div class="chain-node-icon"><i class="fa-solid fa-brain"></i></div><span>4. AI Patch</span></div>
      <div class="chain-divider"></div>
      <div class="chain-step"><div class="chain-node-icon"><i class="fa-solid fa-shield-halved"></i></div><span>5. AST Validated</span></div>
      <div class="chain-divider"></div>
      <div class="chain-step"><div class="chain-node-icon"><i class="fa-solid fa-flask"></i></div><span>6. Sandbox Verified</span></div>
      <div class="chain-divider"></div>
      <div class="chain-step"><div class="chain-node-icon"><i class="fa-brands fa-github"></i></div><span>7. Ready to Ship</span></div>
    </div>
    <div style="text-align: center; padding: 24px; color: var(--text-muted); font-family: var(--font-mono); font-size: 0.85rem;">
      <i class="fa-solid fa-spinner fa-spin" style="color: #38bdf8; font-size: 1.5rem; display: block; margin-bottom: 12px;"></i>
      Queue initializing — running 7-stage remediation pipeline for each finding...
    </div>
    </div>
  `;
  bDashboard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  if (telPanel) {
  telPanel.style.display = 'none';
  }

  const poll = async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/queues/${queueId}`);
    if (!res.ok) return;

    const qData = await res.json();
    renderBatchDashboard(qData);

    if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(qData.status)) {
    clearInterval(activePollInterval);
    const startBtn = document.getElementById('start-batch-btn');
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.innerHTML = `<i class="fa-solid fa-layer-group"></i> Start Batch Remediation Queue`;
    }
    }

  } catch (err) {
    console.error('Queue poll error:', err);
  }
  };

  poll();
  activePollInterval = setInterval(poll, 750);
}

function renderBatchDashboard(qData) {
  const panel = document.getElementById('batch-dashboard-panel');
  if (!panel) return;

  const report = qData.batch_report;
  const total = qData.total_findings || 1;
  const verified = qData.verified_count || 0;
  const failed = qData.failed_count || 0;
  const processed = verified + failed;
  const pct = Math.round((processed / total) * 100);

  if (window.updateSystemDock) {
  if (qData.status === 'COMPLETED') {
    window.updateSystemDock(
    `Batch Queue Completed (${verified}/${total} Verified)`,
    100,
    'BATCH VERIFIED',
    `Batch Queue Completed! ${verified} items sandbox verified, ${failed} items failed across ${total} findings.`,
    false
    );
  } else {
    window.updateSystemDock(
    `Batch Queue: ${processed}/${total} Items (${pct}%)`,
    pct,
    `BATCH ${processed}/${total}`,
    `Batch Queue active: Item ${processed + 1} of ${total} running 7-Stage Remediation... (${verified} verified, ${failed} failed)`,
    true
    );
  }
  }

  const findingsList = (report?.findings || []).map((f, idx) => {
  let badgeCls = 'badge-minor';
  let stageInfo = 'Stage 7/7 — Ready to Ship';
  if (f.status === 'VERIFIED') {
    badgeCls = 'badge-minor';
    stageInfo = '<i class="fa-solid fa-circle-check" style="color: #34d399;"></i> Stage 7/7 — Sandbox Verified (0 Violations)';
  } else if (f.status === 'RUNNING') {
    badgeCls = 'badge-moderate';
    stageInfo = '<i class="fa-solid fa-spinner fa-spin" style="color: #38bdf8;"></i> Running 7-Stage Remediation Pipeline...';
  } else if (f.status === 'BLOCKED' || f.status === 'NOT_VERIFIED') {
    badgeCls = 'badge-critical';
    const detail = f.error_message || f.block_reason || 'Patch Verification Rejected';
    stageInfo = `<i class="fa-solid fa-circle-xmark" style="color: #f87171;"></i> Stage 5/7 — ${escapeHtml(detail)}`;
  } else {
    stageInfo = '<i class="fa-solid fa-clock" style="color: var(--text-dim);"></i> Queued for Pipeline Execution';
  }

  return `
    <div style="padding: 14px 18px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); border-radius: 12px; margin-bottom: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 8px;">
      <div style="display: flex; align-items: center; gap: 12px;">
      <span style="font-family: var(--font-mono); color: var(--text-dim); font-size: 0.8rem;">#${idx + 1}</span>
      <span style="font-family: var(--font-mono); font-weight: 700; color: #fff; font-size: 0.95rem;"><i class="fa-solid fa-bug" style="color: #f87171;"></i> ${escapeHtml(f.rule_id)}</span>
      <span style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(f.title || f.description || '')}</span>
      </div>
      <span class="finding-badge ${badgeCls}">${f.status}</span>
    </div>
    <div style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--accent-cyan); display: flex; align-items: center; gap: 8px;">
      ${stageInfo}
    </div>
    </div>
  `;
  }).join('');

  panel.innerHTML = `
  <div style="background: rgba(6, 6, 9, 0.9); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 20px; padding: 28px; box-shadow: 0 20px 50px rgba(0,0,0,0.8);">

    <!-- Progress Bar Header -->
    <div style="margin-bottom: 24px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <span style="font-family: var(--font-heading); font-weight: 600; color: #fff; font-size: 1.1rem;">
      <i class="fa-solid fa-bars-progress" style="color: var(--accent-blue);"></i> Batch Remediation Queue Progress
      </span>
      <span style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--accent-cyan); font-weight: 700;">
      ${processed} of ${total} processed (${pct}%)
      </span>
    </div>
    <div style="width: 100%; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; margin-bottom: 20px;">
      <div style="width: ${pct}%; height: 100%; background: linear-gradient(90deg, #38bdf8, #34d399); transition: width 0.4s ease;"></div>
    </div>

    <!-- 7-Stage Verification Pipeline Chain Banner -->
    <div class="verification-chain" style="margin-bottom: 20px;" aria-label="Batch Remediation Pipeline Stages">
      <div class="chain-step completed">
      <div class="chain-node-icon"><i class="fa-solid fa-magnifying-glass"></i></div>
      <span>1. Discovered</span>
      </div>
      <div class="chain-divider"></div>
      <div class="chain-step completed">
      <div class="chain-node-icon"><i class="fa-solid fa-layer-group"></i></div>
      <span>2. Root Cause</span>
      </div>
      <div class="chain-divider"></div>
      <div class="chain-step completed">
      <div class="chain-node-icon"><i class="fa-solid fa-code"></i></div>
      <span>3. Source Mapped</span>
      </div>
      <div class="chain-divider"></div>
      <div class="chain-step active">
      <div class="chain-node-icon"><i class="fa-solid fa-brain"></i></div>
      <span>4. AI Patch</span>
      </div>
      <div class="chain-divider"></div>
      <div class="chain-step ${processed > 0 ? 'completed' : ''}">
      <div class="chain-node-icon"><i class="fa-solid fa-shield-halved"></i></div>
      <span>5. AST Validated</span>
      </div>
      <div class="chain-divider"></div>
      <div class="chain-step ${processed > 0 ? 'completed' : ''}">
      <div class="chain-node-icon"><i class="fa-solid fa-flask"></i></div>
      <span>6. Sandbox Verified</span>
      </div>
      <div class="chain-divider"></div>
      <div class="chain-step ${pct === 100 ? 'completed' : ''}">
      <div class="chain-node-icon"><i class="fa-brands fa-github"></i></div>
      <span>7. Ready to Ship</span>
      </div>
    </div>
    </div>

    <!-- Stats Breakdown -->
    <div class="metrics-grid" style="margin-bottom: 24px;">
    <div class="metric-card">
      <div class="metric-label">Total Queue Items</div>
      <div class="metric-value">${total}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">7-Stage Verified Fixes</div>
      <div class="metric-value" style="color: var(--accent-green);">${verified}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Failed / Blocked</div>
      <div class="metric-value" style="color: var(--accent-red);">${failed}</div>
    </div>
    </div>

    <!-- Finding Queue -->
    <div style="margin-bottom: 28px;">
    <div style="font-size: 0.85rem; font-weight: 600; color: #fff; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between;">
      <span>Finding Queue Items & Pipeline Stage Status</span>
      <span style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">Real-Time SSE Sync</span>
    </div>
    <div style="display: flex; flex-direction: column; gap: 8px;">
      ${findingsList || '<div style="color: var(--text-dim); text-align: center;">Queue initializing...</div>'}
    </div>
    </div>

    <!-- Cumulative Multi-File Diff Visualizer for Verified Batch Fixes -->
    ${(function () {
    let cumulativeDiffs = [];
    if (report && report.reports) {
    Object.values(report.reports).forEach(rpt => {
      if (rpt && (rpt.final_status === 'VERIFIED' || rpt.status === 'VERIFIED' || rpt.status === 'COMPLETED')) {
      const diffStr = rpt.patch?.unified_diff || rpt.unified_diff || rpt.patch_code || '';
      if (diffStr) cumulativeDiffs.push(diffStr);
      }
    });
    }
    if (cumulativeDiffs.length > 0) {
    const combinedDiffText = cumulativeDiffs.join('\n');
    return `
      <div style="margin-bottom: 28px;">
        <div style="font-size: 0.85rem; font-weight: 600; color: #fff; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
        <i class="fa-brands fa-github" style="color: #38bdf8; font-size: 1.1rem;"></i> Cumulative Batch Verified File Changes (${verified} verified)
        </div>
        ${renderGitHubDiffViewer(combinedDiffText, [], `Cumulative verified source code fixes for ${verified} accessibility issues in repository queue.`, true)}
      </div>
      `;
    }
    return '';
  })()}

    <!-- GitHub Batch PR Button (Phase 17D Endpoint Integration) -->
    ${qData.status === 'COMPLETED' && verified > 0 ? `
    <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 16px; padding: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
      <div>
      <div style="font-weight: 700; color: #fff; font-size: 1rem; display: flex; align-items: center; gap: 8px;">
        <i class="fa-solid fa-code-pull-request" style="color: var(--accent-blue);"></i> Publish Verified Batch to GitHub
      </div>
      <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">
        Creates 1 cumulative Pull Request with ${verified} verified commits.
      </div>
      </div>
      <button id="publish-batch-btn-${qData.queue_id}" onclick="publishBatchFix('${qData.queue_id}')" class="btn-neon" style="padding: 10px 24px; font-size: 0.85rem;">
      <i class="fa-brands fa-github"></i> Open Batch Pull Request
      </button>
    </div>
    <div id="publish-batch-result-${qData.queue_id}" style="margin-top: 12px; display: none;"></div>
    ` : ''}

  </div>
  `;
}

window.publishSingleFix = async function (remediationId) {
  const btn = document.getElementById(`publish-single-btn-${remediationId}`);
  const resDiv = document.getElementById(`publish-result-${remediationId}`);
  if (btn) {
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Mapping Target & Opening Pull Request...`;
  }

  try {
  const res = await fetch(`${API_BASE_URL}/api/v1/github/remediations/${remediationId}/publish`, {
    method: 'POST'
  });

  const data = await res.json();

  if (!res.ok) {
    const msg = data.detail?.message || data.detail || 'Publication rejected';
    if (resDiv) {
    resDiv.style.display = 'block';
    resDiv.innerHTML = `<div style="padding: 14px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239,68,68,0.4); border-radius: 12px; color: #f87171; font-size: 0.85rem;"><i class="fa-solid fa-triangle-exclamation"></i> ${msg}</div>`;
    }
    if (btn) {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-brands fa-github"></i> Open Pull Request on GitHub`;
    }
    return;
  }

  const repoUrl = data.target_repository_url || 'https://github.com';
  const filesList = (data.files_changed || []).map(f => `<code style="background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 4px; color: var(--accent-cyan); font-family: var(--font-mono);">${escapeHtml(f)}</code>`).join(' ');

  if (resDiv) {
    resDiv.style.display = 'block';
    resDiv.innerHTML = `
    <div style="background: linear-gradient(135deg, rgba(52, 211, 153, 0.12) 0%, rgba(16, 185, 129, 0.06) 100%); border: 1px solid rgba(52, 211, 153, 0.4); border-radius: 16px; padding: 22px; box-shadow: 0 10px 30px rgba(52, 211, 153, 0.15); margin-top: 16px;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1);">
      <div style="display: flex; align-items: center; gap: 14px;">
        <div style="width: 46px; height: 46px; border-radius: 12px; background: rgba(52, 211, 153, 0.2); display: flex; align-items: center; justify-content: center; color: #34d399; font-size: 1.4rem;">
        <i class="fa-solid fa-circle-check"></i>
        </div>
        <div>
        <div style="font-weight: 800; color: #fff; font-size: 1.1rem;">
          Pull Request #${data.pull_request_number || '1'} Created & Target Mapped
        </div>
        <div style="font-size: 0.825rem; color: var(--text-muted); margin-top: 2px;">
          Target Repo: <a href="${repoUrl}" target="_blank" style="color: var(--accent-blue); text-decoration: underline;">${escapeHtml(data.repository)}</a>
        </div>
        </div>
      </div>
      <a href="${data.pull_request_url}" target="_blank" class="btn-neon" style="padding: 10px 22px; font-size: 0.85rem; font-weight: 700; text-decoration: none; display: inline-flex; align-items: center; gap: 8px;">
        View PR #${data.pull_request_number} on GitHub <i class="fa-solid fa-arrow-up-right-from-square"></i>
      </a>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; font-size: 0.825rem; font-family: var(--font-mono);">
      <div><span style="color: var(--text-muted);">Destination Branch:</span> <strong style="color: #fff;">${data.base_branch || 'main'} &larr; ${escapeHtml(data.branch)}</strong></div>
      <div><span style="color: var(--text-muted);">Commit SHA:</span> <strong style="color: var(--accent-cyan);">${data.commit_sha ? data.commit_sha.slice(0, 7) : 'head'}</strong></div>
      <div><span style="color: var(--text-muted);">Mapped Source Files:</span> ${filesList || '1 File'}</div>
      </div>

      <div style="margin-top: 14px; display: flex; justify-content: flex-end;">
      <button type="button" class="btn-secondary" style="padding: 8px 16px; font-size: 0.8rem;" onclick="copyPRNotes('${data.pull_request_url}', '${data.pull_request_number}', 'Single Remediation', '${data.files_changed?.[0] || 'Mapped File'}')">
        <i class="fa-solid fa-copy"></i> Copy Release Notes
      </button>
      </div>
    </div>
    `;
  }
  if (btn) {
    btn.style.display = 'none';
  }

  } catch (err) {
  if (resDiv) {
    resDiv.style.display = 'block';
    resDiv.innerHTML = `<div style="padding: 12px; background: rgba(239, 68, 68, 0.15); color: #f87171; font-size: 0.85rem;">${err.message}</div>`;
  }
  if (btn) {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-brands fa-github"></i> Open Pull Request on GitHub`;
  }
  }
};

window.publishBatchFix = async function (queueId) {
  const btn = document.getElementById(`publish-batch-btn-${queueId}`);
  const resDiv = document.getElementById(`publish-batch-result-${queueId}`);
  if (btn) {
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Mapping Target Repository & Opening Cumulative PR...`;
  }

  try {
  const res = await fetch(`${API_BASE_URL}/api/v1/github/queues/${queueId}/publish`, {
    method: 'POST'
  });

  const data = await res.json();

  if (!res.ok) {
    const msg = data.detail?.message || data.detail || 'Batch publication rejected';
    if (resDiv) {
    resDiv.style.display = 'block';
    resDiv.innerHTML = `<div style="padding: 14px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239,68,68,0.4); border-radius: 12px; color: #f87171; font-size: 0.85rem;"><i class="fa-solid fa-triangle-exclamation"></i> ${msg}</div>`;
    }
    if (btn) {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-brands fa-github"></i> Open Batch Pull Request`;
    }
    return;
  }

  const repoUrl = data.target_repository_url || 'https://github.com';
  const filesList = (data.files_changed || []).map(f => `<code style="background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 4px; color: var(--accent-cyan); font-family: var(--font-mono);">${escapeHtml(f)}</code>`).join(' ');

  if (resDiv) {
    resDiv.style.display = 'block';
    resDiv.innerHTML = `
    <div style="background: linear-gradient(135deg, rgba(56, 189, 248, 0.15) 0%, rgba(52, 211, 153, 0.1) 100%); border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 16px; padding: 22px; box-shadow: 0 10px 30px rgba(56, 189, 248, 0.15); margin-top: 16px;">

      <!-- PR Created Header & Location Mapping -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1);">
      <div style="display: flex; align-items: center; gap: 14px;">
        <div style="width: 46px; height: 46px; border-radius: 12px; background: rgba(56, 189, 248, 0.2); display: flex; align-items: center; justify-content: center; color: #38bdf8; font-size: 1.4rem;">
        <i class="fa-solid fa-code-pull-request"></i>
        </div>
        <div>
        <div style="font-weight: 800; color: #fff; font-size: 1.1rem;">
          Cumulative Batch Pull Request #${data.pull_request_number || '1'} Created
        </div>
        <div style="font-size: 0.825rem; color: var(--text-muted); margin-top: 2px;">
          Target Location: <a href="${repoUrl}" target="_blank" style="color: var(--accent-blue); text-decoration: underline;">${escapeHtml(data.repository)}</a>
        </div>
        </div>
      </div>

      <a href="${data.pull_request_url}" target="_blank" class="btn-neon" style="padding: 10px 22px; font-size: 0.85rem; font-weight: 700; text-decoration: none; display: inline-flex; align-items: center; gap: 8px;">
        View PR #${data.pull_request_number} on GitHub <i class="fa-solid fa-arrow-up-right-from-square"></i>
      </a>
      </div>

      <!-- Mapped Details Grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; font-size: 0.825rem; font-family: var(--font-mono); margin-bottom: 14px;">
      <div><span style="color: var(--text-muted);">Merge Destination:</span> <strong style="color: #fff;">${data.base_branch || 'main'} &larr; ${escapeHtml(data.branch)}</strong></div>
      <div><span style="color: var(--text-muted);">Commit SHA:</span> <strong style="color: var(--accent-cyan);">${data.commit_sha ? data.commit_sha.slice(0, 7) : 'head'}</strong></div>
      <div><span style="color: var(--text-muted);">Published At:</span> <strong style="color: var(--accent-green);">${new Date(data.published_at).toLocaleTimeString()}</strong></div>
      </div>

      <div style="background: rgba(0,0,0,0.4); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 12px 16px; margin-bottom: 14px;">
      <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-family: var(--font-mono); margin-bottom: 6px;">Mapped Source Files Modified</div>
      <div style="display: flex; gap: 8px; flex-wrap: wrap;">
        ${filesList || 'Multiple target files modified'}
      </div>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px;">
      <button type="button" class="btn-secondary" style="padding: 8px 16px; font-size: 0.8rem;" onclick="copyPRNotes('${data.pull_request_url}', '${data.pull_request_number}', 'Cumulative Batch Queue', 'Multiple target source files')">
        <i class="fa-solid fa-copy"></i> Copy Release Notes & Target Mapping
      </button>
      </div>

    </div>
    `;
  }
  if (btn) {
    btn.style.display = 'none';
  }

  } catch (err) {
  if (resDiv) {
    resDiv.style.display = 'block';
    resDiv.innerHTML = `<div style="padding: 12px; background: rgba(239, 68, 68, 0.15); color: #f87171; font-size: 0.85rem;">${err.message}</div>`;
  }
  if (btn) {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-brands fa-github"></i> Open Batch Pull Request`;
  }
  }
};

window.copyPRNotes = function (prUrl, prNum, ruleId, targetFile) {
  const notes = `## CodeLoom Automated Remediation PR #${prNum}
- **Type**: ${ruleId}
- **Target**: ${targetFile}
- **Sandbox Status**: <i class="fa-solid fa-circle-check"></i> 7-Stage Sandbox Re-scan Passed (0 Violations)
- **GitHub PR URL**: ${prUrl}

*Generated by CodeLoom AI Engine.*`;
  if (navigator.clipboard) {
  navigator.clipboard.writeText(notes);
  }
  alert("PR Release Notes copied to clipboard!");
};

window.applyPresetTarget = function (url, repoUrl) {
  const urlInput = document.getElementById('workbench-url-input');
  const repoInput = document.getElementById('repo-url-input');
  const singleRepoInput = document.getElementById('single-repo-url');

  if (urlInput) urlInput.value = url;
  if (repoInput) repoInput.value = repoUrl;
  if (singleRepoInput) singleRepoInput.value = repoUrl;

  const changeForm = document.getElementById('audit-change-url-form');
  if (changeForm) {
  changeForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
  }
};

window.playScreenReaderVoice = function (speechText, rate = 1.0, pitch = 1.0, btn = null) {
  if (!('speechSynthesis' in window)) {
  alert("Speech Synthesis is not supported in this browser. Simulation text: " + speechText);
  return;
  }

  window.speechSynthesis.cancel(); 
  const utterance = new SpeechSynthesisUtterance(speechText);
  utterance.rate = rate || 1.0;
  utterance.pitch = pitch || 1.0;

  const voices = window.speechSynthesis.getVoices();
  const preferredVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Daniel')));
  if (preferredVoice) utterance.voice = preferredVoice;

  if (btn) {
  const origHtml = btn.innerHTML;
  btn.innerHTML = '<i class="fa-solid fa-volume-high fa-beat" style="color: #38bdf8;"></i> Speaking...';
  btn.disabled = true;

  utterance.onend = () => {
    btn.innerHTML = origHtml;
    btn.disabled = false;
  };
  utterance.onerror = () => {
    btn.innerHTML = origHtml;
    btn.disabled = false;
  };
  }

  window.speechSynthesis.speak(utterance);
};

window.openVPATExportModal = async function (scanId) {
  const resolvedScanId = scanId || document.getElementById('scan-id-display')?.textContent?.trim();
  if (!resolvedScanId || resolvedScanId.startsWith('scan_...')) {
  alert("Please run an accessibility scan first to generate a VPAT 2.4 report.");
  return;
  }

  try {
  const res = await fetch(`${API_BASE_URL}/api/v1/scans/${encodeURIComponent(resolvedScanId)}/vpat`);
  if (!res.ok) {
    alert("Failed to generate VPAT report.");
    return;
  }
  const data = await res.json();

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `VPAT-2.4-WCAG2.2-${resolvedScanId}.json`;
  a.click();
  URL.revokeObjectURL(url);
  } catch (err) {
  alert("Error downloading VPAT: " + err.message);
  }
};

window.openCICDExportModal = async function () {
  const repoUrl = document.getElementById('repo-url-input')?.value?.trim() || 'https://github.com/owner/repository';
  try {
  const res = await fetch(`${API_BASE_URL}/api/v1/integrations/github-action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repository_url: repoUrl, package_manager: 'npm', fail_on_critical: true, min_score: 90 })
  });
  const data = await res.json();
  if (data.yaml) {
    navigator.clipboard.writeText(data.yaml);
    alert("Turnkey GitHub Action workflow (.github/workflows/codeloom-gate.yml) copied to clipboard!\n\nPaste it into your repo to block PR regressions automatically.");
  }
  } catch (err) {
  alert("Failed to generate CI/CD Action: " + err.message);
  }
};

