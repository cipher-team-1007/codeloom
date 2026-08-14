"""
Checkpoint M2: Root-Cause Clustering Engine Verification.
"""
import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))


def main():
    from engine.models import Finding
    from engine.dedup.deduplicator import Deduplicator
    from engine.clustering.clusterer import ClusterEngine

    mock_file = root_dir / "tests" / "mock_data" / "findings.json"
    with open(mock_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    findings = [Finding(**item) for item in raw_data]

    dedup_res = Deduplicator().deduplicate(findings)
    clusterer = ClusterEngine()
    clusters = clusterer.cluster(dedup_res.findings)

    results = []

    # Check 1: Created clusters
    results.append((
        f"Generated {len(clusters)} clusters from {len(dedup_res.findings)} deduplicated findings",
        len(clusters) > 0,
        "Clusters populated"
    ))

    # Check 2: Dramatic grouping ratio
    results.append((
        "Clustering collapses finding count (>50% reduction)",
        len(clusters) < len(dedup_res.findings) * 0.5,
        f"{len(dedup_res.findings)} findings -> {len(clusters)} actionable clusters"
    ))

    # Check 3: 12 button findings collapsed into 1 cluster
    btn_clusters = [c for c in clusters if c.rule_id == "button-name"]
    btn_count = sum(c.instance_count for c in btn_clusters)
    results.append((
        "12 icon buttons grouped into 1 root-cause cluster",
        len(btn_clusters) == 1 and btn_count == 12,
        f"Found {len(btn_clusters)} cluster(s) with {btn_count} total button instances"
    ))

    # Check 4: 5 image-alt findings collapsed into 1 cluster
    img_clusters = [c for c in clusters if c.rule_id == "image-alt"]
    img_count = sum(c.instance_count for c in img_clusters)
    results.append((
        "5 missing alt-text instances grouped into 1 cluster",
        len(img_clusters) == 1 and img_count == 5,
        f"Found {len(img_clusters)} cluster(s) with {img_count} total image instances"
    ))

    # Check 5: Critical severity prioritized first
    first_sev = clusters[0].severity if clusters else "none"
    results.append((
        "Clusters correctly sorted by severity (Critical first)",
        first_sev == "critical",
        f"Top cluster severity: {first_sev}"
    ))

    # Check 6: Required fields presence
    required_fields = ["cluster_id", "title", "rule_id", "severity", "instance_count", "likely_root_cause", "impact", "representative_snippet"]
    all_fields = all(all(getattr(c, field, None) is not None for field in required_fields) for c in clusters)
    results.append((
        "All clusters contain complete schema metadata",
        all_fields,
        f"Checked {len(required_fields)} fields across {len(clusters)} clusters"
    ))

    # Check 7: Multiple categories present
    cats = set(c.category for c in clusters)
    results.append((
        "Multi-domain categories categorized (Accessibility, SEO, Performance)",
        len(cats) >= 3,
        f"Categories: {list(cats)}"
    ))

    print("\n" + "=" * 60)
    print("  CHECKPOINT M2: Clustering Engine")
    print("=" * 60)
    all_passed = True
    for title, passed, detail in results:
        status_icon = "✅" if passed else "❌"
        print(f"  {status_icon} {title}")
        print(f"     {detail}")
        if not passed:
            all_passed = False

    print("\n  📋 Cluster Summary Breakdown:")
    print(f"  {'ID':<10} {'Rule ID':<22} {'Severity':<10} {'Count':<6} {'Category':<15}")
    print(f"  {'-'*10} {'-'*22} {'-'*10} {'-'*6} {'-'*15}")
    for c in clusters:
        print(f"  {c.cluster_id:<10} {c.rule_id:<22} {c.severity:<10} {c.instance_count:<6} {c.category:<15}")

    print("\n" + "=" * 60)
    if all_passed:
        print("  🎉 MODULE 2 COMPLETE — Ready for Module 3 (Knowledge Base)")
    else:
        print("  🛑 MODULE 2 HAS FAILURES")
    print("=" * 60 + "\n")
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
