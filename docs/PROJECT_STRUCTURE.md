# CodeLoom — Project Structure

```text
codeloom/
├── frontend/
├── backend/
│   ├── engine/
│   ├── tests/
│   ├── demo-site/
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── README.md
├── services/
│   └── source-intelligence/
├── docs/
├── experiments/
├── scripts/
├── README.md
├── LICENSE
├── .gitignore
└── run.md
```

## `backend/`

### `backend/engine/api/`

FastAPI route handlers:

- `app.py`
- `clusters.py`
- `fixes.py`
- `github.py`
- `history.py`
- `queues.py`
- `remediations.py`
- `scan_manager.py`
- `simulations.py`
- `websocket.py`

### `backend/engine/scanner/`

Runtime scanning and analyzers:

```text
axe_scanner.py
comprehensive_scanner.py
static_scanner.py
score_calculator.py
url_validator.py
analyzers/
  aria_validator.py
  contrast_analyzer.py
  keyboard_auditor.py
  performance_analyzer.py
  seo_analyzer.py
  structure_analyzer.py
```

### `backend/engine/clustering/`

- `clusterer.py`
- `fingerprint.py`
- `enrichment.py`

### `backend/engine/dedup/`

Finding deduplication/rule mapping.

### `backend/engine/ai/`

- context builder
- LLM gateway
- providers
- patch generator
- patch validator
- output validator
- fallback
- prompt templates
- screen-reader/DataForSEO helpers

### `backend/engine/orchestrator/`

Master workflow state machine and report builder.

### `backend/engine/repository/`

Repository acquisition and metadata.

### `backend/engine/source_intelligence/`

Python client to the Node source-intelligence service.

### `backend/engine/sandbox/`

Candidate workspace/sandbox execution.

### `backend/engine/github/`

Authentication, secure credential vault, GitHub API client, publisher.

### `backend/engine/queue/`

Multi-finding remediation queues and snapshot evolution.

### `backend/engine/telemetry/`

Event bus and SSE telemetry.

### `backend/engine/storage/`

SQLite/Supabase adapters.

### `backend/tests/`

Master test suite (checkpoints, unit, integration).

## `services/source-intelligence/`

```text
src/
  server.ts
  config/
  contracts/
  indexer/
  matcher/
  parser/
  routes/
  services/
tests/
package.json
tsconfig.json
```

### Parser

TypeScript Compiler API AST parsing.

### Indexer

Repository source node indexing.

### Matcher

Candidate generation and ambiguity handling.

### Routes

Source-mapping API.

## `frontend/`

Current supplied UI files:

```text
index.html
audit-url.html
audit-code.html
script.js
styles.css
workbench.js
compliance.js
preview_sandbox.js
roi_engine.js
```

## `experiments/`

Controlled React/Vite fixtures (`experiments/source-mapping/`), debug scripts (`experiments/debug/`), and historical scratch artifacts (`experiments/scratch2/`).

Do not make release behavior depend on these files.

