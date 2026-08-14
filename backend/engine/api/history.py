"""
FastAPI router for Scan History management.
"""
import logging
import secrets
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from engine.storage.sqlite_store import store

logger = logging.getLogger("codeloom.api.history")
router = APIRouter(prefix="/api", tags=["history"])


@router.get("/scans/history")
async def get_scan_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None)
):
    """
    Returns paginated scan history items with aggregate metrics.
    """
    try:
        res = store.get_all_scans(limit=limit, offset=offset, search=search)
        return res
    except Exception as e:
        logger.error(f"Error fetching scan history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve scan history")


@router.get("/scans/{scan_id}/summary")
async def get_scan_summary(scan_id: str):
    """
    Returns quick scorecard summary for a scan item.
    """
    scan_meta = store.get_scan(scan_id)
    if not scan_meta:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    
    clusters = store.get_clusters_for_scan(scan_id)
    return {
        "scan_id": scan_id,
        "url": scan_meta["url"],
        "created_at": scan_meta["created_at"],
        "scores": scan_meta["scores"],
        "total_findings": scan_meta["total_findings"],
        "deduplicated_findings": scan_meta["deduplicated_findings"],
        "clusters_count": len(clusters),
        "severities": {
            "critical": sum(1 for c in clusters if c.severity.lower() == "critical"),
            "serious": sum(1 for c in clusters if c.severity.lower() == "serious"),
            "moderate": sum(1 for c in clusters if c.severity.lower() == "moderate"),
            "minor": sum(1 for c in clusters if c.severity.lower() == "minor"),
        }
    }


@router.delete("/scans/{scan_id}")
async def delete_scan(scan_id: str):
    """
    Deletes a scan item and all its associated clusters, fixes, and simulations.
    """
    deleted = store.delete_scan(scan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    return {"status": "success", "message": f"Scan {scan_id} deleted successfully"}


# ── Project Management Endpoints (Chunk 4) ──
@router.get("/projects")
async def get_projects():
    """Returns all tracked projects and scan statistics."""
    try:
        return {"projects": store.get_all_projects()}
    except Exception as e:
        logger.error(f"Error retrieving projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve projects")


@router.post("/projects")
async def create_project(data: dict):
    """Links/creates a new project in SQLite store."""
    project_id = data.get("project_id") or f"proj_{secrets.token_hex(4)}"
    name = data.get("name") or "Unnamed Project"
    repository_url = data.get("repository_url")
    default_branch = data.get("default_branch") or "main"

    if not repository_url:
        raise HTTPException(status_code=400, detail="repository_url is required")

    try:
        project = store.save_project(project_id, name, repository_url, default_branch)
        return {"status": "success", "project": project}
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create project")


@router.get("/remediations/history")
async def get_remediation_history(limit: int = Query(default=50, ge=1, le=200)):
    """Returns persistent verified remediations and GitHub PR links."""
    try:
        return {"remediations": store.get_all_remediations(limit=limit)}
    except Exception as e:
        logger.error(f"Error retrieving remediations history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve remediation history")
