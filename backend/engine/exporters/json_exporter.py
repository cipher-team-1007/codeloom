"""
JSON Report Exporter for CodeLoom Engine.
Produces structured, standardized compliance JSON audit bundles.
"""
from typing import Dict, Any, List
import json
from engine.models import Cluster, Fix


def export_json(scan_meta: Dict[str, Any], clusters: List[Cluster], fixes: List[Fix]) -> str:
    """
    Generates a structured JSON string representation of a scan report.
    """
    scores = scan_meta.get("scores") or {}
    overall_score = scores.get("overall", 100)
    a11y_score = scores.get("accessibility", 100)

    # Determine compliance tags based on scores and critical count
    critical_count = sum(1 for c in clusters if c.severity.lower() == "critical")
    serious_count = sum(1 for c in clusters if c.severity.lower() == "serious")

    compliance_status = {
        "wcag_2_1_aa": "PASSED" if critical_count == 0 and serious_count == 0 else "NON_COMPLIANT",
        "wcag_2_2_aa": "PASSED" if critical_count == 0 and serious_count <= 1 else "NON_COMPLIANT",
        "section_508": "PASSED" if a11y_score >= 85 else "PARTIAL",
        "en_301_549": "PASSED" if a11y_score >= 85 else "PARTIAL",
        "overall_rating": "PASS" if overall_score >= 90 else ("NEEDS_WORK" if overall_score >= 70 else "FAIL")
    }

    report = {
        "$schema": "https://codeloom.ai/schemas/audit-v1.json",
        "engine": "CodeLoom Autonomous Engine v1.0.0",
        "scanId": scan_meta.get("scan_id"),
        "targetUrl": scan_meta.get("url"),
        "timestamp": scan_meta.get("created_at"),
        "scores": scores,
        "compliance": compliance_status,
        "summary": {
            "totalFindings": scan_meta.get("total_findings", 0),
            "deduplicatedFindings": scan_meta.get("deduplicated_findings", 0),
            "clustersCount": len(clusters),
            "fixesCount": len(fixes),
            "criticalCount": critical_count,
            "seriousCount": serious_count,
            "moderateCount": sum(1 for c in clusters if c.severity.lower() == "moderate"),
            "minorCount": sum(1 for c in clusters if c.severity.lower() == "minor"),
        },
        "clusters": [c.model_dump(mode="json") for c in clusters],
        "fixes": [f.model_dump(mode="json") for f in fixes],
        "tokenUsage": scan_meta.get("token_usage", {})
    }

    return json.dumps(report, indent=2)
