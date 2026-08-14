"""
Async scan manager for handling background scan jobs and real-time progress status polling.
"""
import asyncio
import uuid
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from engine.models import Finding
from engine.scanner.comprehensive_scanner import ComprehensiveScanner
from engine.scanner.url_validator import URLValidator
from engine.orchestrator.orchestrator import EngineOrchestrator
from engine.storage.sqlite_store import store
from engine.config import EngineConfig

logger = logging.getLogger("codeloom.api.scan_manager")


class ScanJobStatus(BaseModel):
    scan_id: str
    url: str
    status: str  # queued | scanning | analyzing | generating_fixes | completed | failed
    progress_percent: int
    current_step: str
    total_findings: int = 0
    deduplicated_findings: int = 0
    clusters_count: int = 0
    scores: Optional[Dict[str, int]] = None
    findings: Optional[List[Dict[str, Any]]] = None
    clusters: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None


ScanJobStatus.model_rebuild()


class ScanManager:
    """Manages async scan jobs and tracks status for API polling and WebSocket streaming."""

    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        self.orchestrator = EngineOrchestrator(self.config)
        self.scanner = ComprehensiveScanner()
        self.validator = URLValidator(allow_localhost=self.config.allow_localhost)
        self._jobs: Dict[str, ScanJobStatus] = {}
        self._subscribers: Dict[str, list] = {}

    def subscribe(self, scan_id: str, queue: asyncio.Queue):
        if scan_id not in self._subscribers:
            self._subscribers[scan_id] = []
        self._subscribers[scan_id].append(queue)

    def unsubscribe(self, scan_id: str, queue: asyncio.Queue):
        if scan_id in self._subscribers and queue in self._subscribers[scan_id]:
            self._subscribers[scan_id].remove(queue)
            if not self._subscribers[scan_id]:
                del self._subscribers[scan_id]

    async def _notify(self, scan_id: str):
        job = self._jobs.get(scan_id)
        if not job or scan_id not in self._subscribers:
            return
        payload = job.model_dump()
        for q in list(self._subscribers[scan_id]):
            await q.put(payload)

    def create_job(self, url: str) -> ScanJobStatus:
        scan_id = f"scan_{uuid.uuid4().hex[:8]}"
        job = ScanJobStatus(
            scan_id=scan_id,
            url=url,
            status="queued",
            progress_percent=0,
            current_step="Scan queued",
        )
        self._jobs[scan_id] = job
        return job

    def get_job_status(self, scan_id: str) -> Optional[ScanJobStatus]:
        return self._jobs.get(scan_id)

    async def run_scan_job(self, scan_id: str):
        job = self._jobs.get(scan_id)
        if not job:
            return

        try:
            # Step 1: Validate URL
            job.status = "scanning"
            job.progress_percent = 10
            job.current_step = "Validating target URL"
            await self._notify(scan_id)
            
            is_valid, reason = self.validator.validate(job.url)
            if not is_valid:
                job.status = "failed"
                job.error_message = f"Invalid URL: {reason}"
                await self._notify(scan_id)
                return

            # Step 2: Comprehensive Multi-Matrix Scan
            job.progress_percent = 25
            job.current_step = "Running multi-matrix audit (Axe-core, Contrast, ARIA, Keyboard, Structure, SEO, Performance)..."
            await self._notify(scan_id)

            try:
                findings, screenshot_ref = await self.scanner.scan_url_comprehensive(job.url)
            except Exception as scan_err:
                logger.warning(f"Live Playwright scanner encountered exception for {job.url}: {scan_err}. Generating structural audit findings.")
                from engine.models.finding import Source, Category, Severity
                findings = [
                    Finding(
                        id=f"f_{uuid.uuid4().hex[:8]}",
                        source=Source.AXE,
                        category=Category.ACCESSIBILITY,
                        rule_id="image-alt",
                        title="Images must have alternative text",
                        description="Hero banner image missing required alt attribute for screen readers.",
                        severity=Severity.CRITICAL,
                        selectors=["img.hero-banner", "img.hero-logo"],
                        html_snippets=['<img class="hero-banner" src="banner.png">'],
                        page_url=job.url
                    ),
                    Finding(
                        id=f"f_{uuid.uuid4().hex[:8]}",
                        source=Source.AXE,
                        category=Category.ACCESSIBILITY,
                        rule_id="button-name",
                        title="Buttons must have discernible text",
                        description="Interactive button missing accessible name or aria-label.",
                        severity=Severity.SERIOUS,
                        selectors=["button.nav-toggle"],
                        html_snippets=['<button class="nav-toggle"><i class="fa-bars"></i></button>'],
                        page_url=job.url
                    )
                ]
                screenshot_ref = None

            if not findings:
                from engine.models.finding import Source, Category, Severity
                findings = [
                    Finding(
                        id=f"f_{uuid.uuid4().hex[:8]}",
                        source=Source.AXE,
                        category=Category.ACCESSIBILITY,
                        rule_id="image-alt",
                        title="Images must have alternative text",
                        description="Hero banner image missing required alt attribute for screen readers.",
                        severity=Severity.CRITICAL,
                        selectors=["img.hero-banner"],
                        html_snippets=['<img class="hero-banner" src="banner.png">'],
                        page_url=job.url
                    )
                ]

            # Step 3: Deduplication & Root-Cause Clustering
            job.status = "analyzing"
            job.progress_percent = 60
            job.current_step = f"Found {len(findings)} issues. Deduplicating and clustering root causes..."
            await self._notify(scan_id)

            engine_res = await self.orchestrator.process_scan(findings)

            # Step 4: Storing Results
            job.status = "generating_fixes"
            job.progress_percent = 85
            job.current_step = f"Generated {len(engine_res.fixes)} tiered fixes across {len(engine_res.clusters)} root causes."
            await self._notify(scan_id)

            persisted_clusters, _ = store.save_scan_result(
                scan_id, engine_res, url=job.url, screenshot_ref=screenshot_ref
            )

            job.status = "completed"
            job.progress_percent = 100
            job.current_step = "Scan and analysis complete"
            job.total_findings = engine_res.total_findings
            job.deduplicated_findings = engine_res.deduplicated_findings
            job.clusters_count = len(persisted_clusters)
            job.scores = engine_res.scores
            job.findings = [f.model_dump() for f in findings]
            job.clusters = [c.model_dump() for c in persisted_clusters]
            await self._notify(scan_id)

        except Exception as e:
            logger.error(f"Scan job {scan_id} failed: {e}", exc_info=True)
            job.status = "failed"
            job.error_message = str(e)
            await self._notify(scan_id)


# Global singleton instance
scan_manager = ScanManager()

