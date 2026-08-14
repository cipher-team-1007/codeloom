"""
CSV Audit Report Exporter for CodeLoom Engine.
Produces RFC 4180 compliant CSV tabular reports for Jira/Linear/Excel triage.
"""
from typing import Dict, Any, List
import csv
import io
from engine.models import Cluster, Fix


def export_csv(scan_meta: Dict[str, Any], clusters: List[Cluster], fixes: List[Fix]) -> str:
    """
    Generates a CSV string representation of a scan report.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Write CSV Header
    writer.writerow([
        "Scan ID",
        "Target URL",
        "Scan Date",
        "Cluster ID",
        "Category",
        "Severity",
        "Rule ID",
        "Title",
        "Explanation",
        "Instance Count",
        "Target Selectors",
        "Remediation Type",
        "Remediation Code / Patch",
        "AI Confidence"
    ])

    scan_id = scan_meta.get("scan_id", "")
    target_url = scan_meta.get("url", "")
    scan_date = scan_meta.get("created_at", "")

    fix_map = {f.cluster_id: f for f in fixes}

    for c in clusters:
        selectors = getattr(c, 'affected_selectors', getattr(c, 'selectors', []))
        selectors_str = " | ".join(selectors)
        explanation = getattr(c, 'explanation', getattr(c, 'likely_root_cause', c.title))
        associated_fix = fix_map.get(c.cluster_id)
        
        fix_type = getattr(associated_fix, 'tier', getattr(associated_fix, 'fix_type', 'N/A')) if associated_fix else "N/A"
        fix_code = getattr(associated_fix, 'suggested_after', getattr(associated_fix, 'code_diff', getattr(associated_fix, 'explanation', ''))) if associated_fix else ""
        confidence = f"{associated_fix.confidence:.2f}" if associated_fix else "N/A"


        writer.writerow([
            scan_id,
            target_url,
            scan_date,
            c.cluster_id,
            c.category,
            c.severity,
            c.rule_id,
            c.title,
            explanation,
            c.instance_count,

            selectors_str,
            fix_type,
            fix_code,
            confidence
        ])

    return output.getvalue()
