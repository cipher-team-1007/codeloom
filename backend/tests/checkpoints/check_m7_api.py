"""
Checkpoint M7: FastAPI Endpoints Verification.
"""
import sys
import json
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))


def main():
    from fastapi.testclient import TestClient
    from engine.api.app import app

    client = TestClient(app)
    results = []
    mock_path = root_dir / "tests" / "mock_data" / "findings.json"
    findings = json.loads(mock_path.read_text(encoding="utf-8"))
    scan_id = "checkpoint_api_scan"

    try:
        r = client.post(f"/api/scans/{scan_id}/process", json=findings)
        processed = r.status_code == 200
        results.append(("POST /api/scans/{scanId}/process persists submitted findings", processed,
                        f"HTTP {r.status_code}"))
    except Exception as e:
        results.append(("Process scan endpoint error", False, str(e)))

    # Check 1: Health endpoint
    try:
        r = client.get("/health")
        data = r.json()
        results.append((
            "API Health endpoint responds with active status",
            r.status_code == 200 and data.get("status") == "healthy",
            f"HTTP {r.status_code} | Engine: {data.get('engine')}"
        ))
    except Exception as e:
        results.append(("Health endpoint error", False, str(e)))

    # Check 2: Clusters endpoint
    try:
        r = client.get(f"/api/scans/{scan_id}/clusters")
        data = r.json()
        clusters_ok = r.status_code == 200 and len(data.get("clusters", [])) > 0
        results.append((
            "GET /api/scans/{scanId}/clusters returns clustered root-cause data",
            clusters_ok,
            f"HTTP {r.status_code} | Found {len(data.get('clusters', []))} clusters"
        ))
    except Exception as e:
        results.append(("Clusters endpoint error", False, str(e)))

    # Check 3: Fix generation endpoint
    try:
        cluster_id = data["clusters"][0]["cluster_id"]
        r = client.post(f"/api/clusters/{cluster_id}/generate-fix")
        data = r.json()
        fix_ok = r.status_code == 200 and "fix_id" in data and "suggested_after" in data
        results.append((
            "POST /api/clusters/{clusterId}/generate-fix delivers actionable code fix",
            fix_ok,
            f"HTTP {r.status_code} | Fix: '{data.get('title')}' | Tier: {data.get('tier')}"
        ))
    except Exception as e:
        results.append(("Fix generation endpoint error", False, str(e)))

    # Check 4: Simulation verification endpoint
    try:
        fix_id = data["fix_id"]
        r = client.post(f"/api/fixes/{fix_id}/simulate")
        data = r.json()
        sim_ok = r.status_code == 200 and "score_improvement" in data
        results.append((
            "POST /api/fixes/{fixId}/simulate returns sandbox proof and score deltas",
            sim_ok,
            f"HTTP {r.status_code} | Score delta: +{data.get('score_improvement')} points"
        ))
    except Exception as e:
        results.append(("Simulation endpoint error", False, str(e)))

    print("\n" + "=" * 60)
    print("  CHECKPOINT M7: FastAPI Endpoints & Contracts")
    print("=" * 60)
    all_passed = True
    for title, passed, detail in results:
        status_icon = "✅" if passed else "❌"
        print(f"  {status_icon} {title}")
        print(f"     {detail}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("  🎉 MODULE 7 COMPLETE — Full Engine Ready for Frontend Integration!")
    else:
        print("  🛑 MODULE 7 HAS FAILURES")
    print("=" * 60 + "\n")
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
