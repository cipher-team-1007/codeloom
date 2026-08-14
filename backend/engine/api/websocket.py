"""
FastAPI WebSocket router for real-time scan progress streaming.
"""
import asyncio
import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from engine.api.scan_manager import scan_manager
from engine.storage.sqlite_store import store


logger = logging.getLogger("codeloom.api.websocket")
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/scans/{scan_id}")
async def websocket_scan_progress(websocket: WebSocket, scan_id: str):
    """
    WebSocket endpoint for bi-directional live scan progress telemetry.
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected for scan {scan_id}")

    queue = asyncio.Queue()
    scan_manager.subscribe(scan_id, queue)

    try:
        # Immediately send current state if job exists or is persisted
        initial_job = scan_manager.get_job_status(scan_id)
        if initial_job:
            job_dict = initial_job.model_dump()
            await websocket.send_json(job_dict)
            if initial_job.status in ("completed", "failed"):
                return

        # Check if scan is already persisted in database
        persisted_scan = store.get_scan(scan_id)
        if persisted_scan:
            await websocket.send_json({
                "scan_id": scan_id,
                "url": persisted_scan.get("url"),
                "status": "completed",
                "progress_percent": 100,
                "current_step": "Scan completed",
                "scores": persisted_scan.get("scores")
            })
            return

        while True:
            # Wait for next status notification from scan_manager
            status_data = await queue.get()
            await websocket.send_json(status_data)

            # If scan completed or failed, finish stream after sending final status
            if status_data.get("status") in ("completed", "failed"):
                break


    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for scan {scan_id}")
    except Exception as e:
        logger.error(f"WebSocket error on scan {scan_id}: {e}", exc_info=True)
    finally:
        scan_manager.unsubscribe(scan_id, queue)
        try:
            await websocket.close()
        except Exception:
            pass
