"""
FastAPI router for Multi-Format Report Exporters (JSON, HTML, CSV, VPAT, CI/CD Gate).
"""
import json
import logging
from fastapi import APIRouter, HTTPException, Response, Body
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from engine.storage.sqlite_store import store
from engine.exporters.json_exporter import export_json
from engine.exporters.html_exporter import export_html
from engine.exporters.csv_exporter import export_csv
from engine.compliance.vpat_generator import vpat_generator
from engine.integrations.cicd_generator import cicd_generator

logger = logging.getLogger("codeloom.api.exports")
router = APIRouter(prefix="/api", tags=["exports"])


class ActionGenRequest(BaseModel):
    repository_url: str = "https://github.com/owner/repository"
    package_manager: str = "npm"
    fail_on_critical: bool = True
    min_score: int = 90


def _get_bundle_or_404(scan_id: str):
    bundle = store.get_scan_bundle(scan_id)
    if not bundle or not bundle.get("meta"):
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    return bundle


@router.get("/scans/{scan_id}/export/json")
@router.get("/v1/scans/{scan_id}/export/json")
async def download_json_report(scan_id: str):
    """Returns downloadable JSON audit report."""
    bundle = _get_bundle_or_404(scan_id)
    json_str = export_json(bundle["meta"], bundle["clusters"], bundle["fixes"])
    filename = f"codeloom-report-{scan_id}.json"
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/scans/{scan_id}/export/html", response_class=HTMLResponse)
@router.get("/v1/scans/{scan_id}/export/html", response_class=HTMLResponse)
async def download_html_report(scan_id: str, download: bool = False):
    """Returns standalone HTML executive audit report."""
    bundle = _get_bundle_or_404(scan_id)
    html_str = export_html(bundle["meta"], bundle["clusters"], bundle["fixes"])
    headers = {}
    if download:
        filename = f"codeloom-report-{scan_id}.html"
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return HTMLResponse(content=html_str, headers=headers)


@router.get("/scans/{scan_id}/export/csv")
@router.get("/v1/scans/{scan_id}/export/csv")
async def download_csv_report(scan_id: str):
    """Returns downloadable CSV audit report formatted for Jira / Linear / Excel."""
    bundle = _get_bundle_or_404(scan_id)
    csv_str = export_csv(bundle["meta"], bundle["clusters"], bundle["fixes"])
    filename = f"codeloom-report-{scan_id}.csv"
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/scans/{scan_id}/vpat")
@router.get("/v1/scans/{scan_id}/vpat")
async def get_vpat_report(scan_id: str, download: bool = False):
    """
    Generates standard VPAT 2.4 (WCAG Edition) Accessibility Conformance Report (ACR).
    """
    bundle = _get_bundle_or_404(scan_id)
    vpat = vpat_generator.generate_vpat(
        scan_id=scan_id,
        scan_meta=bundle["meta"],
        clusters=bundle["clusters"],
        fixes=bundle.get("fixes", [])
    )
    
    if download:
        filename = f"VPAT-2.4-WCAG-CodeLoom-{scan_id}.json"
        return Response(
            content=vpat.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    return vpat.model_dump()


@router.post("/integrations/github-action")
@router.post("/v1/integrations/github-action")
async def generate_github_action(req: ActionGenRequest):
    """
    Generates turnkey .github/workflows/codeloom-gate.yml workflow YAML.
    """
    yaml_text = cicd_generator.generate_workflow(
        repo_url=req.repository_url,
        package_manager=req.package_manager,
        fail_on_critical=req.fail_on_critical,
        min_score=req.min_score
    )
    return {
        "status": "success",
        "filename": ".github/workflows/codeloom-gate.yml",
        "yaml": yaml_text
    }
