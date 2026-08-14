"""
Checkpoint M0: Data Models and Mock Dataset Verification.
"""
import json
import sys
from pathlib import Path

# Add backend root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))


def main():
    results = []

    # Check 1: Import all models
    try:
        from engine.models import Finding, Cluster, Fix, SimulationResult, Source, Category, Severity
        results.append(("Import all models", True, "Finding, Cluster, Fix, SimulationResult, Enums OK"))
    except Exception as e:
        results.append(("Import all models", False, str(e)))

    # Check 2: Create Finding from dict
    try:
        f = Finding(
            source=Source.AXE,
            category=Category.ACCESSIBILITY,
            rule_id="button-name",
            title="Discernible text required",
            description="Ensures buttons have accessible names",
            severity=Severity.CRITICAL,
            selectors=[".btn-primary"],
            html_snippets=["<button class='btn-primary'><svg/></button>"]
        )
        assert f.id.startswith("f_")
        results.append(("Create Finding from dict", True, f"Auto-generated ID: {f.id}"))
    except Exception as e:
        results.append(("Create Finding from dict", False, str(e)))

    # Check 3: Create Cluster with default status
    try:
        c = Cluster(
            cluster_id="clst_001",
            title="Buttons missing accessible names",
            rule_id="button-name",
            category="accessibility",
            severity="critical",
            instance_count=5,
            finding_ids=["f_1", "f_2"],
            representative_snippet="<button/>",
            affected_selectors=[".btn-primary"],
            likely_root_cause="Shared button component missing label",
            impact="Screen reader users cannot identify action",
        )
        assert c.fix_status == "pending"
        results.append(("Create Cluster model", True, f"Default status: {c.fix_status}"))
    except Exception as e:
        results.append(("Create Cluster model", False, str(e)))

    # Check 4: Create Fix with default zero tokens
    try:
        fix = Fix(
            fix_id="fix_001",
            cluster_id="clst_001",
            title="Add aria-label to buttons",
            explanation="Allows screen readers to announce purpose",
            root_cause="Icon-only button without text",
            suggested_before="<button/>",
            suggested_after="<button aria-label='Action'/>",
            confidence=0.92,
            tier="template",
            tokens_used=0,
            validation_steps=["Inspect accessibility tree"],
        )
        assert fix.tokens_used == 0
        results.append(("Create Fix model", True, f"Tokens used: {fix.tokens_used}, Tier: {fix.tier}"))
    except Exception as e:
        results.append(("Create Fix model", False, str(e)))

    # Check 5: Mock data file exists
    mock_file = root_dir / "tests" / "mock_data" / "findings.json"
    try:
        with open(mock_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        assert len(raw_data) >= 20
        results.append(("Mock data file exists", True, f"Loaded {len(raw_data)} findings from disk"))
    except Exception as e:
        results.append(("Mock data file exists", False, str(e)))

    # Check 6: Parse all mock findings into Pydantic models
    try:
        with open(mock_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        findings = [Finding(**item) for item in raw_data]
        assert len(findings) == len(raw_data)
        results.append(("Parse all findings into models", True, f"All {len(findings)} findings validated"))
    except Exception as e:
        results.append(("Parse all findings into models", False, str(e)))

    # Print summary
    print("\n" + "=" * 60)
    print("  CHECKPOINT M0: Data Models & Mock Dataset")
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
        print("  🎉 MODULE 0 COMPLETE — Ready for Module 1 (Deduplication)")
    else:
        print("  🛑 MODULE 0 HAS FAILURES")
    print("=" * 60 + "\n")
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
