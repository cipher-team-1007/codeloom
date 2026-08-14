# CodeLoom Backend Engine 🚀

> **Canonical System Knowledge Bible**: [`docs/ACCESSIFIX_PROJECT_BIBLE.md`](file:///c:/Users/kunal/Downloads/lexical%20ai%20-%20parmarth/lexical-ai/docs/ACCESSIFIX_PROJECT_BIBLE.md)  
> **PDF Version Available**: [`docs/ACCESSIFIX_PROJECT_BIBLE.pdf`](file:///c:/Users/kunal/Downloads/lexical%20ai%20-%20parmarth/lexical-ai/docs/ACCESSIFIX_PROJECT_BIBLE.pdf)  

Specialized AI Accessibility Engineering Engine that transforms raw accessibility, SEO, and performance scan reports into **actionable, deduplicated, clustered root-cause fixes** with proof in a sandbox browser.

---

## 🏗️ Architecture Overview

```
Scan Findings (30+ items)
     │
     ▼
[M1: Deduplication Engine] (Removes duplicate axe-core/Lighthouse findings)
     │
     ▼
[M2: Root-Cause Clustering] (12 button violations → 1 actionable cluster)
     │
     ▼
[M3 & M4: Knowledge Base & Domain Specialists]
   ├── Accessibility Specialist (WCAG 2.1 AA)
   ├── SEO Specialist (Metadata & Discoverability)
   └── Performance Specialist (Core Web Vitals)
     │
     ▼
[M5: Orchestrator & Token Budget Manager]
   ├── Tier 1: Template Fixes (0 tokens consumed, instantaneous)
   ├── Tier 2: Light AI (~350 tokens, strict schema)
   └── Tier 3: Full AI (~1200 tokens, deep reasoning)
     │
     ▼
[M6: Sandbox Proof Simulator] (Applies DOM patches & validates delta in Playwright)
     │
     ▼
[M7: FastAPI REST Endpoints] (Plugs seamlessly into frontend and scanner)
```

---

## 🏃 Running Verification Checkpoints

Run the master verification runner to test every module sequentially:

```bash
cd backend
python tests/checkpoints/check_all.py
```

Or run individual checkpoints:

```bash
python tests/checkpoints/check_m0_models.py      # Data Models & Mock Data
python tests/checkpoints/check_m1_dedup.py       # Deduplication Engine
python tests/checkpoints/check_m2_cluster.py     # Root-Cause Clustering
python tests/checkpoints/check_m3_knowledge.py   # Knowledge Base & Tier System
python tests/checkpoints/check_m4_specialists.py # Domain Specialists
python tests/checkpoints/check_m5_orchestrator.py # AI Pipeline & Orchestrator
python tests/checkpoints/check_m6_simulator.py   # Sandbox Simulator
python tests/checkpoints/check_m7_api.py         # FastAPI Endpoints
```

---

## 🌐 Launching the application

```bash
..\.venv\Scripts\python.exe -m uvicorn engine.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000` for the live audit interface. The FastAPI server also
serves `landing-page-v2`, so there is no separate frontend process to start.

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`

### Optional AI configuration

Template remediations work without a model. Context-dependent recommendations are
shown as manual-review items unless an LLM is configured. Create an `.env` file in
`backend` with the provider credentials you intend to use:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
LLM_MODEL=gpt-4o-mini
DRY_RUN=false
```

The engine never invents an AI-generated fix when credentials are absent.

### Browser runtime

Live audits use Playwright Chromium. Install it once after installing requirements:

```bash
..\.venv\Scripts\playwright install chromium
```

---

## 🔌 API Endpoints

- `GET /health` — Health check
- `GET /api/scans/{scanId}/clusters` — Returns grouped clusters and root causes
- `POST /api/clusters/{clusterId}/generate-fix` — Generates a code remediation
- `POST /api/fixes/{fixId}/simulate` — Applies sandbox DOM patch and proves score improvement

