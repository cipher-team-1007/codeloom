"""
Phase 4 Backend Hardening Test Suite.
Tests History API, Multi-Format Exporters (JSON/HTML/CSV), WebSocket telemetry, and Cascade Deletion.
"""
import sys
from pathlib import Path
import json

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from fastapi.testclient import TestClient
from engine.api.app import app
from engine.storage.sqlite_store import store
from engine.models import Cluster, Fix, Source, Category, Severity, SimulationResult


def test_phase4_full():
    print("🚀 Starting Phase 4 Backend Hardening Test Suite...")
    client = TestClient(app)

    # 1. Setup mock scan data in SQLite
    test_scan_id = "test_phase4_scan_001"
    scores = {"accessibility": 82, "seo": 95, "performance": 88, "overall": 86}
    token_usage = {"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200}
    
    store.save_scan(
        test_scan_id,
        total_findings=4,
        deduplicated_findings=2,
        token_usage=token_usage,
        url="http://localhost:8000/demo-site/index.html",
        scores=scores,
        screenshot_ref="ref_001"
    )

    c1 = Cluster(
        cluster_id=f"{test_scan_id}__c1",
        category=Category.ACCESSIBILITY,
        rule_id="color-contrast",
        title="Insufficient Text Contrast",
        severity=Severity.SERIOUS,
        instance_count=1,
        representative_snippet="<p class='hero-subtitle'>Low contrast text</p>",
        affected_selectors=[".hero-subtitle"],
        likely_root_cause="Text element contrast ratio 2.1:1 fails WCAG AA minimum 4.5:1",
        impact="High visual impairment impact"
    )
    store.save_cluster(test_scan_id, c1)


    f1 = Fix(
        fix_id=f"{test_scan_id}__f1",
        cluster_id=c1.cluster_id,
        title="Fix Text Contrast Ratio",
        explanation="Increase font weight and adjust foreground to #ffffff",
        root_cause="Low contrast text ratio 2.1:1",
        suggested_before="color: #777;",
        suggested_after="color: #ffffff;",
        confidence=0.95,
        tier="semantic"
    )
    store.save_fix(f1)


    sim1 = SimulationResult(
        simulation_id=f"{test_scan_id}__sim1",
        fix_id=f1.fix_id,
        rule_passed=True,
        before_violations=1,
        after_violations=0,
        score_improvement=15
    )
    store.save_simulation(sim1)

    print("  ✅ Mock scan bundle persisted into SQLite.")

    # 2. Test GET /api/scans/history
    resp_hist = client.get("/api/scans/history?limit=10")
    assert resp_hist.status_code == 200
    hist_data = resp_hist.json()
    assert "items" in hist_data and "total" in hist_data
    assert hist_data["total"] >= 1
    assert any(i["scan_id"] == test_scan_id for i in hist_data["items"])
    print("  ✅ History API endpoint passed.")

    # 3. Test Search in GET /api/scans/history
    resp_search = client.get("/api/scans/history?search=demo-site")
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert len(search_data["items"]) >= 1
    print("  ✅ History search filtering passed.")

    # 4. Test GET /api/scans/{scan_id}/summary
    resp_sum = client.get(f"/api/scans/{test_scan_id}/summary")
    assert resp_sum.status_code == 200
    sum_data = resp_sum.json()
    assert sum_data["scan_id"] == test_scan_id
    assert sum_data["severities"]["serious"] == 1
    print("  ✅ Scan Summary endpoint passed.")

    # 5. Test JSON Export
    resp_json = client.get(f"/api/scans/{test_scan_id}/export/json")
    assert resp_json.status_code == 200
    assert resp_json.headers["content-type"] == "application/json"
    exported_json = resp_json.json()
    assert exported_json["scanId"] == test_scan_id
    assert exported_json["compliance"]["overall_rating"] == "NEEDS_WORK"
    assert len(exported_json["clusters"]) == 1
    print("  ✅ Multi-Format JSON Exporter passed.")

    # 6. Test HTML Export
    resp_html = client.get(f"/api/scans/{test_scan_id}/export/html")
    assert resp_html.status_code == 200
    assert "text/html" in resp_html.headers["content-type"]
    html_text = resp_html.text
    assert "CODELOOM AUTOMATED AUDIT REPORT" in html_text
    assert "Insufficient Text Contrast" in html_text
    assert ".hero-subtitle" in html_text
    print("  ✅ Multi-Format Standalone HTML Executive Exporter passed.")

    # 7. Test CSV Export
    resp_csv = client.get(f"/api/scans/{test_scan_id}/export/csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    csv_text = resp_csv.text
    assert "Scan ID,Target URL" in csv_text
    assert "color-contrast" in csv_text
    print("  ✅ Multi-Format CSV Exporter passed.")

    # 8. Test WebSocket telemetry streaming
    with client.websocket_connect(f"/ws/scans/{test_scan_id}") as ws:
        msg = ws.receive_json()
        assert "scan_id" in msg or "status" in msg
    print("  ✅ WebSocket Telemetry endpoint passed.")

    # 9. Test Cascade Scan Deletion
    resp_del = client.get(f"/api/scans/{test_scan_id}/summary")
    assert resp_del.status_code == 200
    
    resp_delete_action = client.delete(f"/api/scans/{test_scan_id}")
    assert resp_delete_action.status_code == 200
    assert resp_delete_action.json()["status"] == "deleted"

    # Verify complete cascade deletion from SQLite
    assert store.get_scan(test_scan_id) is None
    assert len(store.get_clusters_for_scan(test_scan_id)) == 0
    assert len(store.get_fixes_for_scan(test_scan_id)) == 0
    assert store.get_simulation_for_fix(f1.fix_id) is None
    print("  ✅ Cascade Scan Deletion & SQLite Transaction cleanup passed.")

    print("\n🎉 ALL PHASE 4 BACKEND HARDENING TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_phase4_full()
