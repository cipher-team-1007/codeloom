"""
Checkpoint M1: Deduplication Engine Verification.
"""
import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))


def main():
    from engine.models import Finding
    from engine.dedup.deduplicator import Deduplicator

    mock_file = root_dir / "tests" / "mock_data" / "findings.json"
    with open(mock_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    findings = [Finding(**item) for item in raw_data]

    deduplicator = Deduplicator()
    result = deduplicator.deduplicate(findings)

    results = []

    # Check 1: Input count matches mock data
    results.append((
        f"Input count ({result.original_count}) matches raw dataset",
        result.original_count == len(raw_data),
        f"Loaded {len(raw_data)} findings"
    ))

    # Check 2: Duplicates were removed
    results.append((
        f"Removed {result.removed_count} redundant finding(s)",
        result.removed_count >= 2,
        f"Duplicates removed: {result.removed_count}"
    ))

    # Check 3: Output count is lower than input
    results.append((
        f"Deduplicated count: {result.deduped_count} (down from {result.original_count})",
        result.deduped_count < result.original_count,
        "Redundancy successfully pruned"
    ))

    # Check 4: Removed items are from Lighthouse (axe prioritized)
    all_removed_are_lh = all(getattr(f.source, "value", str(f.source)) == "lighthouse" for f in result.removed)
    results.append((
        "Axe-core prioritized over Lighthouse for overlaps",
        all_removed_are_lh,
        f"Removed sources: {[getattr(f.source, 'value', str(f.source)) for f in result.removed]}"
    ))

    # Check 5: SEO and Performance findings preserved
    seo_items = [f for f in result.findings if getattr(f.category, "value", str(f.category)) == "seo"]
    perf_items = [f for f in result.findings if getattr(f.category, "value", str(f.category)) == "performance"]
    results.append((
        "Lighthouse unique domains (SEO + Performance) preserved",
        len(seo_items) >= 2 and len(perf_items) >= 2,
        f"Preserved: {len(seo_items)} SEO, {len(perf_items)} Performance findings"
    ))

    print("\n" + "=" * 60)
    print("  CHECKPOINT M1: Deduplication Engine")
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
        print("  🎉 MODULE 1 COMPLETE — Ready for Module 2 (Clustering)")
    else:
        print("  🛑 MODULE 1 HAS FAILURES")
    print("=" * 60 + "\n")
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
