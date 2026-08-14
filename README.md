<div align="center">

# CodeLoom

### **Source-Aware Web Quality Engineering**

**Find the issue. Trace the cause. Review the fix. Verify the result.**

<br />

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-20%2B-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-AST%20Source%20Intelligence-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Browser%20Automation-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/)
[![axe-core](https://img.shields.io/badge/axe--core-Accessibility-4C4CFF)](https://github.com/dequelabs/axe-core)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)

<br />

> **Source-aware web quality engineering for developers.**
>
> CodeLoom connects runtime browser findings to source-level evidence, clusters repeated issues into likely root causes, generates reviewable remediation candidates, validates patches, and supports a verification-to-GitHub workflow.

<br />

**🌐 Website Audit** · **💻 Codebase Audit** · **🧠 Root-Cause Clustering** · **📍 AST Source Mapping** · **🧩 Patch Generation** · **🔎 Verification** · **🐙 GitHub Workflow**

</div>

---

## 📖 Table of Contents

- [Why CodeLoom?](#-why-codeloom)
- [What CodeLoom Does](#-what-codeloom-does)
- [System Architecture](#-system-architecture)
- [End-to-End Workflow](#-end-to-end-workflow)
- [Key Product Capabilities](#-key-product-capabilities)
- [Technology Stack](#-technology-stack)
- [Getting Started](#-getting-started)
- [Local Workspaces](#-local-workspaces)
- [Configuration](#-configuration)
- [Testing](#-testing)
- [Repository Structure](#-repository-structure)
- [Security Principles](#-security-principles)
- [Documentation](#-documentation)
- [Design Principles](#-design-principles)
- [Team & Credits](#-team--credits)

---

## ✨ Why CodeLoom?

Modern web-quality tools are good at telling developers **what failed**.

The harder engineering problem is:

```text
What actually caused it?
Where does that source live?
How many findings come from the same underlying pattern?
What is the smallest sensible change?
Did the change actually resolve the original issue?
```

CodeLoom is designed around that workflow:

```text
Live Website
   │
   ▼
Runtime Browser Audit
   │
   ▼
Structured Findings
   │
   ▼
Root-Cause Clustering
   │
   ▼
GitHub Repository
   │
   ▼
AST Source Intelligence
   │
   ▼
Reviewable Patch Candidate
   │
   ▼
Deterministic Validation
   │
   ▼
Sandbox / Re-scan
   │
   ▼
GitHub Delivery
```

> [!NOTE]
> **Source mapping is evidence-based.** CodeLoom can explicitly report a matched candidate, an ambiguous result, or no match. When evidence is insufficient, the system should not guess a source file.

---

## 🚀 What CodeLoom Does

| Capability | Description | Primary output |
|---|---|---|
| 🌐 **Runtime Website Audits** | Load a deployed application with Playwright and inspect rendered accessibility, SEO, performance, and structural signals. | Structured runtime findings |
| 🧠 **Root-Cause Clustering** | Deduplicate related findings and group repeated patterns into deterministic clusters. | Root-cause clusters |
| 📍 **AST Source Intelligence** | Analyze TypeScript/JavaScript source with the TypeScript Compiler API and score source candidates against runtime evidence. | Source candidates with file/line context |
| 🧩 **Reviewable Remediation** | Generate structured remediation candidates with before/after code and developer guidance. | Patch candidate |
| 🔎 **Validation & Verification** | Validate repository context, patch scope and syntax before the configured verification workflow. | Validation / verification state |
| 🐙 **GitHub Workflow** | Preserve repository/commit context and support approved delivery through GitHub. | Branch / commit / pull request |

---

## 🏗️ System Architecture

CodeLoom uses a **dual-runtime architecture** with clear ownership boundaries.

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         CodeLoom Workbench                          │
│                  Browser-based developer interface                  │
└───────────────────────────────┬─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Python FastAPI Master Engine                       │
│                           Port 8000                                 │
│                                                                     │
│  Runtime scanning        Clustering        AI / Patch workflow      │
│  Playwright + axe        Deduplication     Validation               │
│  SEO / Performance       Repository        Sandbox / Re-scan        │
│  Telemetry / Queues      GitHub            Reports / Exports        │
└───────────────────────────────┬─────────────────────────────────────┘
                │
                │ source-mapping request
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 Node.js Source Intelligence Service                 │
│                           Port 8001                                 │
│                                                                     │
│  TypeScript Compiler API                                             │
│  TS / TSX / JSX parsing                                              │
│  Source indexing                                                     │
│  Candidate generation                                                │
│  Candidate scoring                                                   │
│  Ambiguity detection                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Separation of responsibilities

| Component | Responsibility |
|---|---|
| **Python FastAPI** | Master orchestration, browser scanning, clustering, AI/remediation workflow, validation, sandbox orchestration, GitHub workflow |
| **Node.js + TypeScript** | Deterministic TypeScript/JSX AST parsing, indexing, and source candidate mapping |
| **Frontend** | Developer-facing website audit and codebase audit workbenches |

> [!IMPORTANT]
> The Node.js service is a **source-intelligence service**, not a second master backend. The Python engine remains the workflow and orchestration authority.

---

## 🔄 End-to-End Workflow

### 1. Scan the live experience

```text
URL
 ↓
Playwright Chromium
 ↓
Rendered DOM + runtime evidence
```

### 2. Analyze

```text
axe-core
SEO analyzers
Performance analyzers
Structural analyzers
```

### 3. Normalize and cluster

```text
Raw findings
 ↓
Deduplication
 ↓
Structural fingerprints
 ↓
Root-cause clusters
```

### 4. Connect the repository

```text
GitHub repository
 ↓
Repository acquisition
 ↓
Pinned revision / commit context
```

### 5. Trace runtime evidence to source

```text
Runtime selector / evidence
 ↓
TypeScript AST index
 ↓
Candidate source nodes
 ↓
Match / Ambiguous / Not Found
```

### 6. Generate a remediation candidate

```text
Root cause
 ↓
Targeted source context
 ↓
Deterministic rule OR structured AI proposal
 ↓
Patch candidate
```

### 7. Validate

Typical checks include:

- repository identity
- commit consistency
- source target
- exact target content
- patch scope
- syntax
- AST validity
- conflict and safety rules

### 8. Verify

```text
Candidate workspace
 ↓
Sandbox / application verification
 ↓
Playwright + accessibility re-scan
 ↓
Target finding comparison
 ↓
Regression comparison
```

### 9. Deliver

```text
Verified change
 ↓
Developer approval
 ↓
GitHub branch / commit / PR
```

> [!WARNING]
> **AI is not the verification authority.** A model proposing a fix does not make the fix verified. Deterministic validation and the verification workflow remain separate stages.

---

## 🧩 Key Product Capabilities

### 🌐 Website Audit

Inspect a deployed browser experience and collect structured accessibility, SEO, and performance evidence.

### 💻 Codebase Audit

Inspect repository source independently of a live site and prepare source-level context.

### 🧠 Root-Cause Clustering

Collapse related runtime findings into actionable patterns instead of treating every affected element as an unrelated task.

### 📍 Source Intelligence

Map runtime evidence to candidate TypeScript/JSX source locations using deterministic AST analysis.

### 🧩 Patch Generation

Produce structured remediation candidates with source context, before/after code, explanation, and provenance.

### 🔎 Patch Validation

Check source target, repository context, syntax, scope, and safety before a candidate moves forward.

### 🧪 Sandbox / Re-scan

Run the configured candidate verification workflow in an isolated workspace and compare the result against the baseline.

### 🐙 GitHub Integration

Keep repository and commit context attached to the remediation workflow and support approved GitHub delivery.

### 📡 Telemetry

Stream remediation workflow state to the developer-facing workbench.

### 📦 Batch Remediation

Process multiple findings through a controlled remediation queue.

### 📊 Exports

Support the project's configured report and export formats.

---

## 🛠️ Technology Stack

### Backend & Orchestration

- **Python**
- **FastAPI**
- **Pydantic / typed data models**
- **SQLite / Supabase storage adapters**
- **SSE / WebSocket telemetry**

### Browser & Web Analysis

- **Playwright**
- **axe-core**
- custom accessibility analyzers
- custom SEO analyzers
- custom performance analyzers
- structural analysis

### Source Intelligence

- **Node.js**
- **Fastify**
- **TypeScript**
- **TypeScript Compiler API**
- AST indexing and candidate scoring

### AI & Remediation

- provider abstraction
- structured LLM output
- output validation
- deterministic fallback strategies
- patch generation
- patch validation

### GitHub

- OAuth
- repository acquisition
- repository metadata
- encrypted token handling
- branch / commit / pull-request workflows

---

## 📦 Getting Started

### Prerequisites

Install:

- **Python 3.10+**
- **Node.js 20+**
- **Git**
- **npm**

### 1️⃣ Clone the repository

Replace the placeholder with the actual public repository URL before publishing:

```bash
git clone https://github.com/cipher-team-1007/codeloom.git
cd codeloom
```

### 2️⃣ Start Source Intelligence

From the repository root:

```bash
cd services/source-intelligence

npm install
npm run build
npm start
```

Expected local service:

```text
http://localhost:8001
```

If the service exposes a health endpoint, verify it before continuing.

### 3️⃣ Start the Python Engine

Open a second terminal:

```bash
cd backend
python -m venv .venv
```

#### Windows

```powershell
.\.venv\Scripts\Activate.ps1
```

#### Linux / macOS

```bash
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Install Chromium for Playwright:

```bash
playwright install chromium
```

Start FastAPI:

```bash
python -m uvicorn engine.api.app:app --host 0.0.0.0 --port 8000 --reload
```

Expected:

```text
http://localhost:8000
```

> [!TIP]
> Start the source-intelligence service before the Python engine when using source-mapping features so the master engine can reach its dependency.

---

## 🌐 Local Workspaces

| Surface | Purpose | URL |
|---|---|---|
| 🏠 **Product Home** | Landing page and product entry points | [`localhost:8000`](http://localhost:8000/) |
| 🌐 **Website Audit** | Deployed URL audit workflow | [`audit-url.html`](http://localhost:8000/audit-url.html) |
| 💻 **Codebase Audit** | GitHub/source audit workflow | [`audit-code.html`](http://localhost:8000/audit-code.html) |
| 💚 **FastAPI Health** | Backend liveness check | [`/health`](http://localhost:8000/health) |
| 📚 **FastAPI Docs** | API documentation | [`/docs`](http://localhost:8000/docs) |
| 🧠 **Source Intelligence** | Node AST service | `localhost:8001` |

> [!NOTE]
> The exact route availability is determined by the current FastAPI and Fastify route registrations. Keep this section synchronized with the running application.

---

## ⚙️ Configuration

Depending on the enabled workflow, environment configuration may include:

```dotenv
# AI
LLM_PROVIDER=
LLM_MODEL=
GEMINI_API_KEY=
OPENAI_API_KEY=
GROQ_API_KEY=
NVIDIA_API_KEY=

# GitHub
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_TOKEN_ENCRYPTION_KEY=
GITHUB_REDIRECT_URI=

# Runtime
DRY_RUN=
ALLOW_LOCALHOST_SCAN=
```

---

## 🧪 Testing

### Python engine

```bash
cd backend
pytest -q
```

### Checkpoint suite

```bash
python tests/checkpoints/check_all.py
```

### Source Intelligence

```bash
cd services/source-intelligence
npm test
npm run build
```

### Recommended verification order

```text
Unit tests
  ↓
Source-intelligence integration tests
  ↓
Backend integration tests
  ↓
Browser workflow
  ↓
Controlled fixture
  ↓
Public website smoke test
```

For source mapping, use the controlled fixtures under:

```text
experiments/source-mapping/
```

before testing against arbitrary public repositories.

---

## 📁 Repository Structure

```text
codeloom/
├── backend/               # Python master engine
│   ├── engine/
│   │   ├── ai/                    # AI gateway, context, patch generation
│   │   ├── api/                   # FastAPI routes
│   │   ├── clustering/            # Fingerprints and clustering
│   │   ├── dedup/                 # Finding deduplication
│   │   ├── github/                # GitHub integration
│   │   ├── knowledge/             # Rule / knowledge registry
│   │   ├── orchestrator/          # Master workflows
│   │   ├── repository/            # Repository acquisition
│   │   ├── sandbox/               # Sandbox execution
│   │   ├── scanner/               # Runtime scanning
│   │   ├── source_intelligence/   # Python client to Node service
│   │   ├── storage/               # Persistence adapters
│   │   └── telemetry/             # SSE / event bus
│   └── tests/                     # Unit, integration, checkpoint tests
│
├── packages/
│   └── source-intelligence/       # Node.js TypeScript AST service
│       ├── src/
│       │   ├── contracts/
│       │   ├── indexer/
│       │   ├── matcher/
│       │   ├── parser/
│       │   ├── routes/
│       │   └── services/
│       └── tests/
│
├── frontend/                      # Web product surfaces
│   ├── index.html                 # Product landing page
│   ├── audit-url.html             # Website audit workbench
│   ├── audit-code.html            # Codebase audit workbench
│   ├── script.js
│   ├── styles.css
│   └── workbench.js
│
├── experiments/
│   └── source-mapping/             # Controlled source-mapping fixtures
│
├── docs/                           # Architecture, audits and project documentation
│
├── run.md                          # Local runner notes
├── LICENSE
└── README.md
```

---

## 🔐 Security Principles

CodeLoom treats both webpages and repositories as untrusted input.

### URL scanning

The runtime scanner should protect against SSRF by validating targets and redirect destinations.

### Repository handling

Repository acquisition should guard against:

- archive traversal
- absolute paths
- excessive file sizes
- excessive file counts
- unsafe extraction paths

### Source analysis

The source-intelligence layer statically parses source and should not execute repository code during source analysis.

### Prompt injection

Repository source is untrusted data.

A comment inside a repository cannot redefine model instructions or security policy.

### Patch safety

A patch should be validated against its intended source target before application.

### GitHub credentials

GitHub credentials should remain server-side and should never be exposed to browser storage or telemetry.

---

## 📚 Documentation

Project documentation lives under:

```text
docs/
```

Recommended starting points:

- [`docs/README.md`](docs/README.md)
- [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)
- [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md)
- [`docs/SOURCE_INTELLIGENCE.md`](docs/SOURCE_INTELLIGENCE.md)
- [`docs/PATCH_PIPELINE.md`](docs/PATCH_PIPELINE.md)
- [`docs/SECURITY.md`](docs/SECURITY.md)
- [`docs/TESTING_VERIFICATION.md`](docs/TESTING_VERIFICATION.md)

---

## 🧭 Design Principles

### Deterministic where determinism matters

Source mapping, target validation, patch validation, and verification should remain system-controlled.

### AI where reasoning helps

AI is useful for remediation explanation and patch proposals—not for silently deciding which source file or commit is authoritative.

### Evidence over assumptions

A runtime finding should preserve enough evidence to explain why a cluster and source candidate were selected.

### Review before delivery

A generated patch is a proposal until it passes the configured validation and developer-review gates.

---

## 👥 Team & Credits

<div align="center">

### Built by **RECURSION**

| **Parmarth Kumar** | **Kunal Raj** |
|:---:|:---:|
| [GitHub](https://github.com/parmarth-kumar) · [LinkedIn](https://www.linkedin.com/in/parmarth-kumar/) | [GitHub](https://github.com/kunal-raj-dev) · [LinkedIn](https://www.linkedin.com/in/kunal-raj-8471b8418/) |

**Contact:** [cipher.team.1007@gmail.com](mailto:cipher.team.1007@gmail.com)

<br />

**CodeLoom v1.0.0**

*Built for developers who want to fix the cause, not just the warning.*

</div>

