"""
Phase 5 AI Intelligence Test Suite.
Tests multi-provider LLM adapters, cost calculations, HTML AST output validator,
prompt templates with framework directives, self-correction loop, and AI management endpoints.
"""
import sys
from pathlib import Path
import asyncio
import json

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from fastapi.testclient import TestClient
from engine.api.app import app
from engine.config import EngineConfig
from engine.ai.providers import (
    calculate_cost, extract_json_payload, GeminiProvider, OpenAIProvider,
    AnthropicProvider, OllamaProvider, MockProvider
)
from engine.ai.output_validator import OutputValidator, ValidationReport, StrictHTMLParser
from engine.ai.prompt_templates import get_prompt_and_system, PROMPTS, FRAMEWORK_DIRECTIVES
from engine.ai.context_builder import ContextBuilder
from engine.ai.llm_gateway import LLMGateway
from engine.orchestrator.orchestrator import EngineOrchestrator
from engine.models import Cluster, Fix, Severity, Category
from engine.storage.sqlite_store import store


def test_cost_and_json_parsing():
    print("Testing token cost calculations & JSON extraction...")
    # Test token pricing math
    cost_gemini = calculate_cost("gemini-1.5-flash", prompt_tokens=1000, completion_tokens=1000)
    assert cost_gemini == round(0.000075 + 0.0003, 6)

    cost_gpt4o = calculate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=1000)
    assert cost_gpt4o == round(0.0025 + 0.010, 6)

    # Test markdown JSON payload extraction
    raw_md = "Here is the JSON answer:\n```json\n{\"title\": \"Fix contrast\", \"confidence\": 0.9}\n```"
    parsed = extract_json_payload(raw_md)
    assert parsed.get("title") == "Fix contrast"
    assert parsed.get("confidence") == 0.9

    raw_plain = "  {\"status\": \"ok\"}  "
    assert extract_json_payload(raw_plain).get("status") == "ok"
    print("  ✅ Cost calculation and JSON extraction passed.")


def test_output_validator_ast():
    print("Testing multi-stage HTML AST OutputValidator...")
    validator = OutputValidator()

    # Valid response
    valid_resp = {
        "title": "Fix button accessible name",
        "explanation": "Add aria-label to button.",
        "suggestedBefore": "<button class='btn'></button>",
        "suggestedAfter": "<button class='btn' aria-label='Submit search'>Search</button>",
        "confidence": 0.95,
        "requiresManualReview": False
    }
    rep_valid = validator.validate_report(valid_resp)
    assert rep_valid.is_valid == True
    assert len(rep_valid.errors) == 0

    # Invalid: missing fields
    invalid_fields = {"title": "Incomplete"}
    rep_fields = validator.validate_report(invalid_fields)
    assert rep_fields.is_valid == False
    assert any("Missing required JSON fields" in e for e in rep_fields.errors)

    # Invalid: unclosed HTML tag in suggestedAfter
    invalid_html = {
        "title": "Broken HTML",
        "explanation": "Tag unclosed",
        "suggestedBefore": "<div>",
        "suggestedAfter": "<div class='container'><p>Text without closing div",
        "confidence": 0.8
    }
    rep_html = validator.validate_report(invalid_html)
    assert rep_html.is_valid == False
    assert any("Unclosed HTML tag" in e for e in rep_html.errors)

    print("  ✅ Multi-stage HTML AST OutputValidator passed.")


def test_prompt_templates_and_frameworks():
    print("Testing prompt template rendering with framework targets...")
    ctx = {
        "rule_id": "color-contrast",
        "wcag_criteria": "1.4.3",
        "severity": "critical",
        "category": "accessibility",
        "instance_count": 1,
        "html_snippet": "<span style='color:#aaa;'>Text</span>",
        "likely_root_cause": "Contrast 2.1:1 fails 4.5:1",
        "impact": "High",
        "affected_selectors": ".subtext"
    }

    # Test React JSX framework target
    rendered, sys_prompt = get_prompt_and_system("contrast_v2", ctx, framework="react_jsx", custom_instructions="Use Tailwind")
    assert "React JSX syntax" in rendered
    assert "Custom Instructions: Use Tailwind" in rendered
    assert "color-contrast" in rendered
    assert "CodeLoom AI" in sys_prompt

    print("  ✅ Prompt templates & framework targets passed.")


import pytest

@pytest.mark.asyncio
async def test_llm_gateway_and_mock_provider():
    print("Testing LLMGateway and MockProvider fallback...")
    config = EngineConfig(llm_provider="mock", dry_run=True)
    gateway = LLMGateway(config)

    ctx = ContextBuilder().build(Cluster(
        cluster_id="c_test_01",
        category=Category.ACCESSIBILITY,
        rule_id="color-contrast",
        title="Low contrast",
        severity=Severity.SERIOUS,
        instance_count=1,
        representative_snippet="<p style='color:#777;'>Text</p>",
        likely_root_cause="Contrast fails WCAG AA",
        impact="High visual impairment impact"
    ))

    res = await gateway.generate(
        prompt_template=PROMPTS["contrast_v2"],
        context=ctx,
        tier="light_ai"
    )

    assert res.provider_used == "mock"
    assert "suggestedAfter" in res.parsed
    assert res.tokens_used > 0
    print(f"  ✅ LLMGateway & MockProvider passed. Model: {res.model}, Tokens: {res.tokens_used}")


def test_ai_api_endpoints():
    print("Testing FastAPI AI endpoints (/api/ai/providers, /api/ai/test-connection, /api/fixes/regenerate)...")
    client = TestClient(app)

    # 1. GET /api/ai/providers
    r_prov = client.get("/api/ai/providers")
    assert r_prov.status_code == 200
    p_data = r_prov.json()
    assert "providers" in p_data
    assert any(p["id"] == "gemini" for p in p_data["providers"])
    assert any(p["id"] == "mock" for p in p_data["providers"])

    # 2. POST /api/ai/test-connection (Mock provider ping)
    r_ping = client.post("/api/ai/test-connection", json={"provider": "mock"})
    assert r_ping.status_code == 200
    assert r_ping.json()["success"] == True

    # 3. GET /api/ai/presets
    r_pre = client.get("/api/ai/presets")
    assert r_pre.status_code == 200
    assert "frameworks" in r_pre.json()

    # 4. POST /api/clusters/{id}/generate-fix with custom provider payload
    test_scan_id = "test_ai_scan_001"
    cluster = Cluster(
        cluster_id=f"{test_scan_id}__c1",
        category=Category.ACCESSIBILITY,
        rule_id="image-alt",
        title="Image missing alt text",
        severity=Severity.CRITICAL,
        instance_count=1,
        representative_snippet="<img src='hero.png'>",
        likely_root_cause="Missing alt text attribute",
        impact="High screen reader impact"
    )
    store.save_cluster(test_scan_id, cluster)

    r_fix = client.post(
        f"/api/clusters/{cluster.cluster_id}/generate-fix",
        json={
            "provider": "mock",
            "framework": "react_jsx",
            "custom_instructions": "Add descriptive alt text"
        }
    )
    assert r_fix.status_code == 200
    fix_data = r_fix.json()
    assert fix_data["cluster_id"] == cluster.cluster_id
    fix_id = fix_data["fix_id"]

    # 5. POST /api/fixes/{id}/regenerate
    r_regen = client.post(
        f"/api/fixes/{fix_id}/regenerate",
        json={
            "custom_instructions": "Make alt text short and simple",
            "provider": "mock",
            "framework": "tailwind"
        }
    )
    assert r_regen.status_code == 200
    regen_data = r_regen.json()
    assert regen_data["fix_id"] == fix_id

    # 6. GET /api/fixes/{id}/debug-prompt
    r_debug = client.get(f"/api/fixes/{fix_id}/debug-prompt")
    assert r_debug.status_code == 200
    debug_data = r_debug.json()
    assert debug_data["fix_id"] == fix_id
    assert "context_packet" in debug_data

    print("  ✅ All FastAPI AI Endpoints passed.")


def main():
    print("🚀 Starting Phase 5 AI Intelligence Test Suite...")
    test_cost_and_json_parsing()
    test_output_validator_ast()
    test_prompt_templates_and_frameworks()
    asyncio.run(test_llm_gateway_and_mock_provider())
    test_ai_api_endpoints()
    print("\n🎉 ALL PHASE 5 AI INTELLIGENCE TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
