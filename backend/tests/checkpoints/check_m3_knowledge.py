"""
Checkpoint M3: Knowledge Base and Tier Classification Verification.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))


def main():
    from engine.knowledge.registry import KnowledgeRegistry

    registry = KnowledgeRegistry()
    stats = registry.stats()

    results = []

    # Check 1: Loaded rules
    results.append((
        f"Loaded {stats['total_rules']} domain rules from YAML",
        stats["total_rules"] >= 10,
        f"Parsed YAML rule count: {stats['total_rules']}"
    ))

    # Check 2: Template fixes available
    results.append((
        f"Identified {stats['with_templates']} rules with deterministic templates",
        stats["with_templates"] >= 5,
        "Template metadata verified"
    ))

    # Check 3: Deterministic zero-token rules exist
    results.append((
        f"{stats['deterministic_fixes']} rules are fully deterministic (ZERO token cost)",
        stats["deterministic_fixes"] >= 2,
        "Instant zero-token remediations available"
    ))

    # Check 4: Specific rule query
    btn_rule = registry.get_rule("button-name")
    results.append((
        "Lookup WCAG metadata for 'button-name'",
        btn_rule is not None and btn_rule.get("wcag_criteria") == "4.1.2",
        f"WCAG Criterion: {btn_rule.get('wcag_criteria') if btn_rule else 'None'}"
    ))

    # Check 5: Tier selection classification
    expected_tiers = {
        "html-has-lang": "template",
        "button-name": "light_ai",
        "color-contrast": "full_ai",
    }
    actual_tiers = {r: registry.get_tier(r) for r in expected_tiers}
    all_tiers_match = actual_tiers == expected_tiers
    results.append((
        "Tier classification adheres to cost-saving strategy",
        all_tiers_match,
        f"Classifications: {actual_tiers}"
    ))

    # Check 6: Unknown rules default to full AI
    unknown_tier = registry.get_tier("non-existent-custom-rule")
    results.append((
        "Unregistered rules route to full AI reasoning",
        unknown_tier == "full_ai",
        f"Unknown rule tier: {unknown_tier}"
    ))

    # Check 7: Template structural validation
    templated_rules = [r for r in registry.get_all_rule_ids() if registry.has_template(r)]
    valid_templates = True
    for r_id in templated_rules:
        r = registry.get_rule(r_id)
        tmpl = r.get("fix_template", {})
        if not all(k in tmpl for k in ["title", "explanation", "root_cause", "confidence", "validation_steps"]):
            valid_templates = False
            break

    results.append((
        "All templates have complete fields and verification steps",
        valid_templates,
        f"Validated {len(templated_rules)} templates"
    ))

    print("\n" + "=" * 60)
    print("  CHECKPOINT M3: Knowledge Base & Tier System")
    print("=" * 60)
    all_passed = True
    for title, passed, detail in results:
        status_icon = "✅" if passed else "❌"
        print(f"  {status_icon} {title}")
        print(f"     {detail}")
        if not passed:
            all_passed = False

    print(f"\n  📊 Token Optimization Strategy Distribution:")
    print(f"     🟢 Tier 1: Template (0 Tokens):     {stats['deterministic_fixes']} rules")
    print(f"     🟡 Tier 2: Light AI (~350 Tokens):  {stats['needs_light_ai']} rules")
    print(f"     🔴 Tier 3: Full AI (~1200 Tokens):  {stats['needs_full_ai']} rules")

    print("\n" + "=" * 60)
    if all_passed:
        print("  🎉 MODULE 3 COMPLETE — Ready for Module 4 (Specialists)")
    else:
        print("  🛑 MODULE 3 HAS FAILURES")
    print("=" * 60 + "\n")
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
