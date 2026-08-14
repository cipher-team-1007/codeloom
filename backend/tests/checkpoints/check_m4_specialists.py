"""
Checkpoint M4: Domain Specialists Verification.
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
    from engine.knowledge.registry import KnowledgeRegistry
    from engine.specialists.accessibility import AccessibilitySpecialist
    from engine.specialists.seo import SEOSpecialist
    from engine.specialists.performance import PerformanceSpecialist

    mock_file = root_dir / "tests" / "mock_data" / "findings.json"
    with open(mock_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    findings = [Finding(**item) for item in raw_data]

    dedup_res = Deduplicator().deduplicate(findings)
    clusters = ClusterEngine().cluster(dedup_res.findings)
    knowledge = KnowledgeRegistry()

    a11y = AccessibilitySpecialist(knowledge)
    seo = SEOSpecialist(knowledge)
    perf = PerformanceSpecialist(knowledge)

    specialists = {"accessibility": a11y, "seo": seo, "performance": perf}
    results = []

    # Check 1: Domain identifiers
    correct_domains = (a11y.domain() == "accessibility" and seo.domain() == "seo" and perf.domain() == "performance")
    results.append((
        "Specialist domain routing tags correct",
        correct_domains,
        f"A11y: {a11y.domain()}, SEO: {seo.domain()}, Perf: {perf.domain()}"
    ))

    # Check 2: Accessibility context enrichment
    a11y_c = next((c for c in clusters if c.category == "accessibility"), None)
    if a11y_c:
        ctx = a11y.enhance_context(a11y_c)
        results.append((
            "Accessibility Specialist adds WCAG criteria & assistive tech context",
            "wcag_criteria" in ctx and "affected_users" in ctx,
            f"Enriched keys: {list(ctx.keys())}"
        ))

    # Check 3: Deterministic template fix generation
    lang_c = next((c for c in clusters if c.rule_id == "html-has-lang"), None)
    if lang_c:
        fix = a11y.generate_template_fix(lang_c)
        results.append((
            "Zero-token template fix generated for 'html-has-lang'",
            fix is not None and fix.tokens_used == 0,
            f"Fix title: '{fix.title if fix else 'None'}', Tokens: {fix.tokens_used if fix else 'N/A'}"
        ))

    # Check 4: SEO context enhancement
    seo_c = next((c for c in clusters if c.category == "seo"), None)
    if seo_c:
        seo_ctx = seo.enhance_context(seo_c)
        results.append((
            "SEO Specialist adds search impact and meta heuristics",
            "search_engine_impact" in seo_ctx,
            f"Search impact: {seo_ctx.get('search_engine_impact')}"
        ))

    # Check 5: Performance context enhancement
    perf_c = next((c for c in clusters if c.category == "performance"), None)
    if perf_c:
        perf_ctx = perf.enhance_context(perf_c)
        results.append((
            "Performance Specialist adds Core Web Vital associations",
            "core_web_vital" in perf_ctx,
            f"Target CWV: {perf_ctx.get('core_web_vital')}"
        ))

    # Check 6: Priority scoring
    scores = []
    for c in clusters:
        spec = specialists.get(c.category)
        if spec:
            s = spec.get_priority_score(c)
            scores.append((c.rule_id, s))
    all_scores_valid = all(0.0 <= s <= 1.0 for _, s in scores)
    results.append((
        "Domain priority scores correctly normalized [0.0 - 1.0]",
        all_scores_valid,
        f"Top priorities: {[(r, round(s, 2)) for r, s in scores[:4]]}"
    ))

    # Check 7: Count free template fixes
    template_fixes = []
    for c in clusters:
        spec = specialists.get(c.category)
        if spec:
            f_res = spec.generate_template_fix(c)
            if f_res:
                template_fixes.append((c.rule_id, f_res.title))

    results.append((
        f"Generated {len(template_fixes)} instantaneous template fixes across all domains",
        len(template_fixes) >= 2,
        f"Zero-token fix rules: {[r for r, _ in template_fixes]}"
    ))

    print("\n" + "=" * 60)
    print("  CHECKPOINT M4: Domain Specialists")
    print("=" * 60)
    all_passed = True
    for title, passed, detail in results:
        status_icon = "✅" if passed else "❌"
        print(f"  {status_icon} {title}")
        print(f"     {detail}")
        if not passed:
            all_passed = False

    print("\n  🆓 Free Tier 1 Remediations Generated (0 Tokens):")
    for r_id, title in template_fixes:
        print(f"     • {r_id}: {title}")

    print("\n" + "=" * 60)
    if all_passed:
        print("  🎉 MODULE 4 COMPLETE — Ready for Module 5 (AI Pipeline)")
    else:
        print("  🛑 MODULE 4 HAS FAILURES")
    print("=" * 60 + "\n")
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
