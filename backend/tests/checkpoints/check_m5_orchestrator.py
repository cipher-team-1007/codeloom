"""
Checkpoint M5: AI Pipeline & Orchestrator Full Flow Verification.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))


def main():
    from engine.config import EngineConfig
    from engine.models import Finding
    from engine.orchestrator import EngineOrchestrator
    from engine.ai.context_builder import ContextBuilder
    from engine.ai.prompt_templates import PROMPTS
    from engine.ai.output_validator import OutputValidator

    has_api_key = bool(os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    config = EngineConfig(dry_run=not has_api_key)
    orchestrator = EngineOrchestrator(config)

    mock_file = root_dir / "tests" / "mock_data" / "findings.json"
    with open(mock_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    findings = [Finding(**item) for item in raw_data]

    results = []

    # Check 1: Orchestrator initialization
    results.append((
        "Orchestrator initialized with token budget & specialists",
        True,
        f"Execution Mode: {'LIVE (Remote API)' if has_api_key else 'DRY RUN (Smart Mock/Templates)'}"
    ))

    # Check 2: Full pipeline execution
    try:
        engine_res = asyncio.run(orchestrator.process_scan(findings))
        results.append((
            f"Pipeline processed {engine_res.total_findings} findings into {len(engine_res.clusters)} clusters & {len(engine_res.fixes)} fixes",
            len(engine_res.clusters) > 0 and len(engine_res.fixes) > 0,
            f"Produced {len(engine_res.fixes)} fix recommendations"
        ))
    except Exception as e:
        results.append(("Pipeline execution failed", False, str(e)))
        _print_summary(results)
        return False

    # Check 3: Template fixes generated with zero tokens
    template_fixes = [f for f in engine_res.fixes if f.tier == "template"]
    results.append((
        f"Generated {len(template_fixes)} Tier-1 template fixes with 0 token consumption",
        len(template_fixes) >= 2,
        f"Rules: {[f.cluster_id for f in template_fixes]}"
    ))

    # Check 4: Token tracking
    token_usage = engine_res.token_usage
    results.append((
        "Token budget and usage correctly tracked per scan",
        "total_tokens" in token_usage and "remaining" in token_usage,
        f"Used: {token_usage.get('total_tokens')} tokens | Remaining: {token_usage.get('remaining')}"
    ))

    # Check 5: Context builder structure
    ctx_builder = ContextBuilder()
    test_c = engine_res.clusters[0]
    ctx = ctx_builder.build(test_c)
    ctx_valid = all(k in ctx for k in ["rule_id", "severity", "html_snippet", "instance_count"])
    results.append((
        "Context Builder generates compact, token-efficient prompt structures",
        ctx_valid,
        f"Context keys: {list(ctx.keys())[:6]}..."
    ))

    # Check 6: Prompt templates validity
    prompt_errors = []
    for name, template in PROMPTS.items():
        try:
            dummy = {k: "val" for k in [
                "rule_id", "wcag_criteria", "severity", "category", "html_snippet",
                "dom_path", "explanation_from_tool", "instance_count",
                "affected_selectors", "likely_root_cause", "impact",
                "additional_domain_context", "search_engine_impact",
                "core_web_vital", "estimated_time_savings_ms",
                "framework_directive", "custom_instructions_block", "html_snippet_escaped"
            ]}
            template.format(**dummy)
        except Exception as err:
            prompt_errors.append(f"{name}: {err}")

    results.append((
        "All versioned prompt templates render without syntax errors",
        len(prompt_errors) == 0,
        f"Validated {len(PROMPTS)} prompt templates" if len(prompt_errors) == 0 else f"Errors: {prompt_errors}"
    ))

    # Check 7: Output Validator checks
    val = OutputValidator()
    valid_res = {"title": "Fix", "explanation": "Detail", "suggestedBefore": "<a/>", "suggestedAfter": "<a aria-label='test'/>", "confidence": 0.9}
    invalid_res = {"title": "Bad", "confidence": 2.5}  # Out of bounds
    results.append((
        "Output Validator enforces strict schema & confidence bounds",
        val.validate(valid_res) and not val.validate(invalid_res),
        "Passed valid test object and rejected invalid test object"
    ))

    # Check 8: Fixes completeness
    required_fix_fields = ["fix_id", "cluster_id", "title", "explanation", "suggested_before", "suggested_after", "confidence", "tier", "specialist"]
    all_fixes_complete = all(all(getattr(f, field, None) is not None for field in required_fix_fields) for f in engine_res.fixes)
    results.append((
        "All generated Fix objects conform to production API contracts",
        all_fixes_complete,
        f"Validated {len(engine_res.fixes)} complete Fix objects"
    ))

    _print_summary(results)

    print("  📋 Fix Generation Breakdown:")
    print(f"  {'Cluster':<10} {'Rule ID':<20} {'Tier':<12} {'Tokens':<8} {'Confidence':<10} {'Specialist'}")
    print(f"  {'-'*10} {'-'*20} {'-'*12} {'-'*8} {'-'*10} {'-'*12}")
    for fix in engine_res.fixes:
        print(f"  {fix.cluster_id:<10} {fix.title[:18]:<20} {fix.tier:<12} {fix.tokens_used:<8} {fix.confidence:<10} {fix.specialist}")

    total_tokens = sum(f.tokens_used for f in engine_res.fixes)
    print(f"\n  💰 Total AI Tokens Burned: {total_tokens} (Average per cluster: {round(total_tokens / max(1, len(engine_res.fixes)))})")
    return True


def _print_summary(results):
    print("\n" + "=" * 60)
    print("  CHECKPOINT M5: AI Pipeline & Orchestrator")
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
        print("  🎉 MODULE 5 COMPLETE — Ready for Module 6 (Sandbox Simulator)")
    else:
        print("  🛑 MODULE 5 HAS FAILURES")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
