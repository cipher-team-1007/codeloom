# CodeLoom — Current Project State

**Status:** Current snapshot reconciliation.

## Top-level structure

```text
backend/                     Python/FastAPI master engine & tests
services/source-intelligence/ Node/TypeScript AST sidecar service
frontend/                    web UI
experiments/                 historical scratch & debug material
docs/                        project documentation
```

The supplied repository also contains historical/debug/test artifacts.

## Python engine

Observed modules inside `backend/engine/` include:

- `engine/api/`
- `engine/ai/`
- `engine/clustering/`
- `engine/dedup/`
- `engine/github/`
- `engine/knowledge/`
- `engine/models/`
- `engine/orchestrator/`
- `engine/queue/`
- `engine/repository/`
- `engine/sandbox/`
- `engine/scanner/`
- `engine/source_intelligence/`
- `engine/storage/`
- `engine/telemetry/`

This is the master application layer described by the supplied architecture docs.

## Node source-intelligence

`services/source-intelligence/` contains:

- Fastify server
- TypeScript Compiler API parser
- source indexer
- candidate matcher
- ambiguity scoring
- contracts
- integration tests

Its responsibility is source parsing and source correlation, not overall workflow orchestration.

## Frontend

The supplied tree contains:

```text
frontend/index.html
frontend/audit-url.html
frontend/audit-code.html
frontend/script.js
frontend/styles.css
frontend/workbench.js
frontend/compliance.js
frontend/preview_sandbox.js
frontend/roi_engine.js
```

Project documentation also refers to React/Vite frontend work in historical iterations. Before submission, select one canonical served frontend and make all run commands/docs match it.

## Current capability matrix

| Area | Present in snapshot | Notes |
|---|---:|---|
| Playwright scanning | Yes | Python scanner |
| axe-core | Yes | Primary automated accessibility engine |
| Runtime clustering | Yes | Deterministic DOM/structural clustering |
| Repository acquisition | Yes | Python repository layer + source-intel integration |
| Commit pinning | Yes | Documented and represented in repository flow |
| TypeScript AST parsing | Yes | Dedicated Node service |
| Python → Node source intelligence | Yes | `engine/source_intelligence/client.py` |
| AI patch generation | Yes | LLM gateway + fallback |
| Deterministic patch validation | Yes | `engine/ai/patch_validator.py` |
| Sandbox/re-scan | Present | Must be re-executed for final release claim |
| GitHub OAuth | Present | Server-side flow |
| GitHub publisher | Present | Publisher module and tests |
| SSE telemetry | Present | Event bus + API route |
| Multi-finding queue | Present | Queue/snapshot modules |
| Frontend | Present | Multiple files/iterations exist |
| Source mapping accuracy | Needs end-to-end verification | Critical trust boundary |
| Arbitrary customer repo build sandbox | Do not assume | Verify exact executor/security boundary |
| Production-ready claim | Not automatically justified | Requires release-gate verification |

## Important historical conflict

Older documents state that source mapping was regex-based and sandbox verification was simulated. Newer project material describes the dedicated TypeScript Compiler API source-intelligence service and fixture-backed end-to-end workflow.

Therefore:

> Treat the AST service as the current intended implementation, but run the actual service and integration tests before calling source mapping verified.

## MVP

The smallest complete proof of the thesis is:

1. scan a live URL;
2. cluster findings;
3. connect a public GitHub repository;
4. map one cluster to one source file with AST;
5. generate a patch;
6. display a real diff;
7. verify or explicitly label simulation.

