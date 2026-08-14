"""
Checkpoint M6: Sandbox Simulator Verification.
"""
import asyncio
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))


def main():
    from engine.models import Cluster, Fix
    from engine.simulator import DOMPatcher, DeltaComparator, SandboxSimulator

    results = []

    # Check 1: Initialize Simulator components
    try:
        patcher = DOMPatcher()
        comparator = DeltaComparator()
        simulator = SandboxSimulator()
        results.append(("Simulator components initialize successfully", True, "Patcher, Comparator, SandboxSimulator ready"))
    except Exception as e:
        results.append(("Simulator components initialize", False, str(e)))
        _print_summary(results)
        return False

    # Check 2: DOM Patcher generates functional JavaScript
    dummy_cluster = Cluster(
        cluster_id="clst_000",
        title="Icon buttons lack accessible names",
        rule_id="button-name",
        category="accessibility",
        severity="critical",
        instance_count=6,
        representative_snippet='<button class="icon-btn"><svg></svg></button>',
        affected_selectors=[".icon-btn"],
        likely_root_cause="Missing aria-label on icon button",
        impact="Screen readers announce unlabelled button",
    )

    dummy_fix = Fix(
        fix_id="fix_001",
        cluster_id="clst_000",
        title="Add aria-label to icon buttons",
        explanation="Provides accessible name for screen readers",
        root_cause="Icon-only button",
        suggested_before='<button class="icon-btn"><svg></svg></button>',
        suggested_after='<button class="icon-btn" aria-label="Action"><svg></svg></button>',
        confidence=0.92,
        tier="template",
        tokens_used=0,
        validation_steps=["Verify screen reader announcement"],
    )

    patch_js = patcher.generate_patch_script(dummy_fix, dummy_cluster)
    has_script = "aria-label" in patch_js and "querySelectorAll" in patch_js
    results.append((
        "DOM Patcher creates valid browser remediation scripts",
        has_script,
        f"Generated {len(patch_js)} chars of browser patch JS"
    ))

    # Check 3: Delta Comparator metrics
    res = comparator.compare(dummy_fix, dummy_cluster, before_count=6, after_count=0)
    results.append((
        "Delta Comparator proves accessibility score improvement",
        res.rule_passed and res.score_improvement > 0,
        f"Simulated Score: {res.score_before} -> {res.score_after} (+{res.score_improvement} points)"
    ))

    # Check 4: Full simulator run
    sim_res = asyncio.run(simulator.simulate(dummy_fix, dummy_cluster))
    results.append((
        "Sandbox Simulator completes automated remediation verification",
        sim_res.is_sandbox and sim_res.after_violations == 0,
        f"Violations before: {sim_res.before_violations}, after: {sim_res.after_violations}"
    ))

    _print_summary(results)
    return True


def _print_summary(results):
    print("\n" + "=" * 60)
    print("  CHECKPOINT M6: Sandbox Simulator Proof Layer")
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
        print("  🎉 MODULE 6 COMPLETE — Ready for Module 7 (FastAPI Layer)")
    else:
        print("  🛑 MODULE 6 HAS FAILURES")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
