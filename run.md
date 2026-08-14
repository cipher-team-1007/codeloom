# 🏗️ System Architecture Overview

CodeLoom uses a canonical **three-tier architecture with a Node.js AST sidecar**:

```text
FRONTEND (Static Web UI)
  ↓
PYTHON FASTAPI MASTER ENGINE (Port 8000)
  ↓
NODE/TYPESCRIPT SOURCE-INTELLIGENCE SIDECAR (Port 8001)
```

1. **Frontend**: HTML5/CSS3/JavaScript Developer Workbench served directly by FastAPI.
2. **Python FastAPI Master Engine** (`backend/` on Port `8000`): Owns browser scanning, violation normalization, root-cause clustering, AI/remediation workflow, patch validation, sandbox proof simulation, GitHub PR generation, and telemetry.
3. **Node/TypeScript Source-Intelligence Sidecar** (`services/source-intelligence/` on Port `8001`): Owns TypeScript/JSX AST parsing, source indexing, candidate generation, candidate scoring, ambiguity detection, and file/line provenance.

---

## 🛠️ Step 1: Initial Prerequisites & Installation

Make sure you have **Node.js** (v20+) and **Python** (v3.10+) installed.

### Terminal 1 — Setup Node.js AST Sidecar

```bash
# 1. Navigate to the source-intelligence service directory
cd services/source-intelligence

# 2. Install Node dependencies
npm install

# 3. Build TypeScript files into dist/
npm run build
```

### Terminal 2 — Setup Python Master Engine

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Playwright browser dependencies
playwright install chromium
```

---

## 🚀 Step 2: Running the Project (Launching Services)

You will open **two separate terminal windows**:

### Terminal 1: Launch Node.js Source Intelligence Sidecar

```bash
cd services/source-intelligence
npm start
```

> **Expected Output:**
> `Source Intelligence service running at http://0.0.0.0:8001`

---

## 🚀 Terminal 2: Launch Python Master Backend & Serve Frontend

```bash
cd backend
python -m uvicorn engine.api.app:app --host 127.0.0.1 --port 8000 --reload
```

> **Expected Output:**
> `INFO: Uvicorn running on http://0.0.0.0:8000`

---

## 🌐 Step 3: Accessing the Application

Once both terminals are running, open your web browser:

- 📊 **URL Audit & Inspection Workbench**: [http://localhost:8000/audit-url.html](http://localhost:8000/audit-url.html)
- 💻 **Code Audit & Remediation Studio**: [http://localhost:8000/audit-code.html](http://localhost:8000/audit-code.html)
- 🏠 **Product Marketing Home**: [http://localhost:8000/](http://localhost:8000/)
- 💚 **Backend Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🔄 Step 4: Core User Workflow in the UI

1. **Preflight Inspection**:

   - Open `http://localhost:8000/audit-url.html`.
   - Enter target inspection address (e.g. `https://fitness-form-flow-studio.vercel.app/`).
   - Click **"Run Preflight Inspection"**.
2. **Run Full Scanner**:

   - Click **"Launch Full Scan Job"**. Playwright will scan the page with `axe-core` and display root-cause DOM clusters.
3. **Link GitHub Repository**:

   - Enter your target GitHub Repository URL (e.g. `https://github.com/my-org/my-app`) and branch (`main`).
   - Click **"Link & Correlate Repository"**.
4. **Execute AI Remediation & Sandbox Verification**:

   - Scroll down to **Remediation Studio**.
   - Click **"Run Remediation Workflow"**.
   - Watch the **7-stage real-time telemetry stream** as CodeLoom maps the TSX component, generates a patch, validates syntax, boots an isolated sandbox, re-scans the application, and proves the WCAG violation is resolved!
5. **Publish Pull Request**:

   - Click **"Connect GitHub"** $\rightarrow$ **"Publish Verified Pull Request"** to open an automated PR on GitHub!

