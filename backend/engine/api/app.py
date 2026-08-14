import sys
import asyncio
import logging
from pathlib import Path

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from engine.api.clusters import router as clusters_router
from engine.api.fixes import router as fixes_router
from engine.api.simulations import router as simulations_router
from engine.api.history import router as history_router
from engine.api.exports import router as exports_router
from engine.api.websocket import router as websocket_router
from engine.api.ai import router as ai_router
from engine.api.remediations import router as remediations_router
from engine.api.github import router as github_router
from engine.api.queues import router as queues_router
from engine.api.patch_control import router as patch_control_router

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("codeloom.api")

app = FastAPI(
    title="CodeLoom Accessibility Engine",
    version="1.0.0",
    description="Domain specialist accessibility engine providing tiered, verified remediations."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

app.add_middleware(GZipMiddleware, minimum_size=500)

class PerformanceStaticMiddleware(BaseHTTPMiddleware):
    """Enables fast caching with ETag revalidation for sub-millisecond local static asset delivery."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.endswith(('.js', '.css', '.html', '.svg', '.png', '.woff2')):
            response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        return response

app.add_middleware(PerformanceStaticMiddleware)

app.include_router(history_router)
app.include_router(clusters_router)
app.include_router(fixes_router)
app.include_router(simulations_router)
app.include_router(exports_router)
app.include_router(websocket_router)
app.include_router(ai_router)
app.include_router(remediations_router)
app.include_router(github_router)
app.include_router(queues_router)
app.include_router(patch_control_router)
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "engine": "CodeLoom Engine",
        "version": "1.0.0",
        "service": "active"
    }


# Mount canonical frontend directory
root_workspace = Path(__file__).resolve().parents[3]
canonical_frontend_dir = root_workspace / "frontend"
if not canonical_frontend_dir.is_dir() or not (canonical_frontend_dir / "index.html").is_file():
    raise RuntimeError(f"Canonical frontend directory missing or invalid: {canonical_frontend_dir}")

assets_dir = canonical_frontend_dir / "assets"
if assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
app.mount("/", StaticFiles(directory=canonical_frontend_dir, html=True), name="frontend")


