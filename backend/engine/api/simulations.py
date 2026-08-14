"""
FastAPI router for browser simulation and proof verification.
"""
import logging
from fastapi import APIRouter, HTTPException
from engine.models import Fix, Cluster
from engine.simulator import SandboxSimulator
from engine.storage.sqlite_store import store

logger = logging.getLogger("codeloom.api.simulations")
router = APIRouter(prefix="/api", tags=["simulations"])
simulator = SandboxSimulator()


@router.post("/fixes/{fix_id}/simulate")
async def simulate_fix(fix_id: str):
    """
    Applies the fix in the sandbox DOM and returns before/after violation deltas.
    """
    target_fix = store.get_fix(fix_id)
    target_cluster = None

    if not target_fix:
        raise HTTPException(status_code=404, detail=f"Fix {fix_id} not found")
    else:
        target_cluster = store.get_cluster(target_fix.cluster_id)
        if not target_cluster:
            raise HTTPException(status_code=404, detail=f"Cluster {target_fix.cluster_id} not found")

    logger.info(f"Running simulation for fix {fix_id}")
    res = await simulator.simulate(target_fix, target_cluster)
    
    # Save the simulation result
    store.save_simulation(res)
    
    return res.model_dump()
