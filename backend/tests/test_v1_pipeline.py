"""
V1 End-to-end verification script.
Tests URL validation, score calculation, demo site scanning simulation, and API endpoints.
"""
import sys
from pathlib import Path
import asyncio

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from engine.scanner.url_validator import URLValidator
from engine.scanner.score_calculator import ScoreCalculator
from engine.models import Finding, Source, Category, Severity
from engine.orchestrator.orchestrator import EngineOrchestrator
from engine.api.scan_manager import scan_manager
from fastapi.testclient import TestClient
from engine.api.app import app


from engine.scanner.analyzers import (
    ContrastAnalyzer, KeyboardAuditor, ARIAValidator,
    StructureAnalyzer, SEOAnalyzer, PerformanceAnalyzer
)


def test_url_validator():
    print("Testing URLValidator...")
    val_strict = URLValidator(allow_localhost=False)
    val_local = URLValidator(allow_localhost=True)

    # Valid URLs
    assert val_strict.validate("https://google.com")[0] == True
    assert val_strict.validate("http://example.com/page")[0] == True

    # Invalid URLs (SSRF / Bad protocol)
    assert val_strict.validate("file:///etc/passwd")[0] == False
    assert val_strict.validate("ftp://server.com")[0] == False
    assert val_strict.validate("http://localhost:8000")[0] == False
    assert val_strict.validate("http://192.168.1.1")[0] == False

    # Localhost allowed mode
    assert val_local.validate("http://localhost:8000")[0] == True
    assert val_local.validate("http://127.0.0.1:9090")[0] == True
    print("✅ URLValidator passed!")


def test_score_calculator():
    print("Testing ScoreCalculator...")
    calc = ScoreCalculator()
    findings = [
        Finding(
            source=Source.AXE,
            category=Category.ACCESSIBILITY,
            rule_id="button-name",
            title="Missing button name",
            description="Button lacks accessible name",
            severity=Severity.CRITICAL,
            selectors=[".btn-1"]
        ),
        Finding(
            source=Source.AXE,
            category=Category.ACCESSIBILITY,
            rule_id="image-alt",
            title="Missing alt",
            description="Image lacks alt text",
            severity=Severity.CRITICAL,
            selectors=[".img-1"]
        ),
    ]
    scores = calc.calculate(findings)
    assert scores.accessibility < 100
    assert scores.seo == 100
    assert scores.performance == 100
    print(f"✅ ScoreCalculator passed! Scores: {scores.model_dump()}")


def test_analyzers_import():
    print("Testing Analyzers import...")
    c = ContrastAnalyzer()
    k = KeyboardAuditor()
    a = ARIAValidator()
    s = StructureAnalyzer()
    seo = SEOAnalyzer()
    p = PerformanceAnalyzer()
    assert c is not None and k is not None and a is not None and s is not None and seo is not None and p is not None
    print("✅ All 6 Multi-Matrix Analyzers loaded successfully!")


def test_api_endpoints():
    print("Testing API endpoints...")
    client = TestClient(app)

    # Health
    r = client.get("/health")
    assert r.status_code == 200

    # Invalid URL rejection
    r_bad = client.post("/api/scan-url", json={"url": "ftp://invalid-url.com"})
    assert r_bad.status_code == 400

    # Async scan creation
    r_scan = client.post("/api/scans", json={"url": "http://localhost:8000"})
    assert r_scan.status_code == 200
    scan_id = r_scan.json()["scan_id"]

    # Poll status
    r_status = client.get(f"/api/scans/{scan_id}/status")
    assert r_status.status_code == 200

    # Populate findings via process endpoint for deterministic report verification
    findings_payload = [
        {
            "source": "axe",
            "category": "accessibility",
            "rule_id": "image-alt",
            "title": "Images must have alternate text",
            "description": "Image missing alt text",
            "severity": "critical",
            "selectors": [".img-hero"],
            "html_snippets": ["<img src='hero.png'>"]
        },
        {
            "source": "custom",
            "category": "seo",
            "rule_id": "document-title",
            "title": "Page missing title",
            "description": "No title element found in head",
            "severity": "serious",
            "selectors": ["head"]
        }
    ]
    r_proc = client.post(f"/api/scans/{scan_id}/process", json=findings_payload)
    assert r_proc.status_code == 200

    # Test report endpoint
    r_rep = client.get(f"/api/scans/{scan_id}/report")
    assert r_rep.status_code == 200
    rep = r_rep.json()
    assert "matrices" in rep and len(rep["matrices"]) > 0

    # Test clusters endpoint
    r_clust = client.get(f"/api/scans/{scan_id}/clusters")
    assert r_clust.status_code == 200
    clusters_data = r_clust.json()
    assert "clusters" in clusters_data and len(clusters_data["clusters"]) > 0

    cluster_id = clusters_data["clusters"][0]["cluster_id"]
    r_fix = client.post(f"/api/clusters/{cluster_id}/generate-fix")
    assert r_fix.status_code == 200
    fix_data = r_fix.json()
    assert "fix_id" in fix_data

    fix_id = fix_data["fix_id"]
    r_sim = client.post(f"/api/fixes/{fix_id}/simulate")
    assert r_sim.status_code == 200
    sim_data = r_sim.json()
    assert "simulation_id" in sim_data
    assert "score_improvement" in sim_data

    print(f"✅ All API endpoints passed! Scan ID: {scan_id}, Clusters: {len(clusters_data['clusters'])}, Score Delta: +{sim_data.get('score_improvement', 0)}")


def main():
    test_url_validator()
    test_score_calculator()
    test_analyzers_import()
    test_api_endpoints()
    print("\n🎉 ALL V1 & V2 MULTI-MATRIX VERIFICATION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
