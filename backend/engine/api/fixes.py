"""
FastAPI router for generating, regenerating, and inspecting AI fixes.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from engine.models import Cluster, Fix
from engine.orchestrator.orchestrator import EngineOrchestrator
from engine.storage.sqlite_store import store

logger = logging.getLogger("codeloom.api.fixes")
router = APIRouter(prefix="/api", tags=["fixes"])
orchestrator = EngineOrchestrator()


class FixGenerationRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    framework: Optional[str] = "vanilla"
    custom_instructions: Optional[str] = ""


class FixRegenerateRequest(BaseModel):
    custom_instructions: str
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    framework: Optional[str] = "vanilla"


@router.post("/clusters/{cluster_id}/generate-fix")
async def generate_fix(cluster_id: str, req: Optional[FixGenerationRequest] = Body(None)):
    """
    Generates an AI fix for an individual cluster on-demand.
    Accepts custom provider, framework target, and prompt instructions.
    """
    target_cluster = store.get_cluster(cluster_id)

    if not target_cluster:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")

    provider = req.provider if req else None
    model = req.model if req else None
    api_key = req.api_key if req else None
    framework = req.framework if req else "vanilla"
    custom_instructions = req.custom_instructions if req else ""

    logger.info(f"Generating fix for cluster {cluster_id} (provider={provider}, framework={framework})")
    fix = await orchestrator._generate_fix(
        cluster=target_cluster,
        provider=provider,
        model=model,
        api_key=api_key,
        framework=framework,
        custom_instructions=custom_instructions
    )
    
    if fix:
        store.save_fix(fix)
        return fix.model_dump()
        
    raise HTTPException(status_code=500, detail="Failed to generate fix")


@router.post("/fixes/{fix_id}/regenerate")
async def regenerate_fix(fix_id: str, req: FixRegenerateRequest):
    """
    Regenerates an existing fix with user refinement instructions.
    """
    existing_fix = store.get_fix(fix_id)
    if not existing_fix:
        raise HTTPException(status_code=404, detail=f"Fix {fix_id} not found")

    cluster = store.get_cluster(existing_fix.cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail=f"Associated cluster {existing_fix.cluster_id} not found")

    logger.info(f"Regenerating fix {fix_id} with instructions: {req.custom_instructions}")
    new_fix = await orchestrator._generate_fix(
        cluster=cluster,
        provider=req.provider,
        model=req.model,
        api_key=req.api_key,
        framework=req.framework or "vanilla",
        custom_instructions=req.custom_instructions
    )

    if new_fix:
        # Retain original fix_id so UI updates smoothly
        new_fix.fix_id = existing_fix.fix_id
        store.save_fix(new_fix)
        return new_fix.model_dump()

    raise HTTPException(status_code=500, detail="Failed to regenerate fix")


@router.get("/fixes/{fix_id}/debug-prompt")
async def debug_prompt(fix_id: str):
    """
    Returns full prompt debug inspection info for a generated fix.
    """
    fix = store.get_fix(fix_id)
    if not fix:
        raise HTTPException(status_code=404, detail=f"Fix {fix_id} not found")

    cluster = store.get_cluster(fix.cluster_id)
    
    # Re-build context for debug visualization
    base_ctx = orchestrator.context_builder.build(cluster if cluster else Cluster(
        cluster_id="debug", category="accessibility", rule_id="preview", title="preview", severity="serious"
    ))

    return {
        "fix_id": fix.fix_id,
        "cluster_id": fix.cluster_id,
        "specialist": fix.specialist,
        "prompt_version": fix.prompt_version,
        "tier": fix.tier,
        "tokens_used": fix.tokens_used,
        "confidence": fix.confidence,
        "validation_steps": fix.validation_steps,
        "context_packet": base_ctx,
        "wcag_link": fix.wcag_link,
    }
