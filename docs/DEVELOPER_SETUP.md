# CodeLoom — Developer Setup

## Prerequisites

- Python 3.10+
- Node.js 20+
- npm
- Git
- Chromium via Playwright

## Python engine

```bash
cd backend
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Node source-intelligence

```bash
cd services/source-intelligence
npm install
npm run build
npm start
```

Expected documented port:

```text
8001
```

## Python FastAPI

From `backend/` run Uvicorn:

```bash
python -m uvicorn engine.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Before committing docs, verify the actual module path because historical run documents contain more than one command.

## Local endpoints

```text
http://localhost:8000/
http://localhost:8000/audit-url.html
http://localhost:8000/audit-code.html
http://localhost:8000/health
http://localhost:8000/docs
http://localhost:8000/redoc
```

Source intelligence is documented on port 8001.

## Environment

Documented configuration includes:

```dotenv
LLM_PROVIDER=
LLM_MODEL=
NVIDIA_API_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OLLAMA_BASE_URL=
DRY_RUN=
ALLOW_LOCALHOST_SCAN=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_TOKEN_ENCRYPTION_KEY=
GITHUB_REDIRECT_URI=
GITHUB_FRONTEND_REDIRECT_URL=
```

Never commit real secrets.

## Correct startup order

1. Python dependencies.
2. Chromium.
3. Node source-intelligence service.
4. Python FastAPI master engine.
5. health checks.
6. frontend.
7. controlled fixture test.

