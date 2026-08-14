import pytest
import os
from engine.ai.patch_generator import PatchGenerator
from engine.ai.llm_gateway import LLMGateway
from engine.config import EngineConfig
from engine.models.patch_plan import (
    PatchGenerationRequest, PatchPlan, PatchTarget, RemediationIntent, PatchConstraint
)

@pytest.mark.asyncio
async def test_real_llm_patch_generation():
    # Only run if internet tests are explicitly enabled and an API key is available
    if os.environ.get("RUN_INTERNET_TESTS") != "1":
        pytest.skip("Skipping real LLM test. Set RUN_INTERNET_TESTS=1 to run.")
        
    config = EngineConfig()
    
    # We need a real provider. Anthropic Claude 3.5 Sonnet or OpenAI GPT-4o-mini is preferred for structured code tasks.
    # The gateway falls back to MockProvider if no key is found, but we want to assert we actually used a real one.
    
    if not (config.anthropic_api_key or config.openai_api_key or config.gemini_api_key):
        pytest.skip("Skipping real LLM test. No API keys configured.")
        
    gateway = LLMGateway(config)
    
    plan = PatchPlan(
        plan_id="plan-integration-1",
        repository_identity="test-repo",
        commit_sha="abcd1234",
        target=PatchTarget(
            file_path="src/components/ProductCard.tsx",
            element_type="img",
            start_line=15
        ),
        intent=RemediationIntent(
            rule_id="image-alt",
            root_cause="Image is missing alternative text.",
            instruction="Add meaningful alternative text using the existing product context."
        ),
        constraints=PatchConstraint(
            allowed_files=["src/components/ProductCard.tsx"],
            max_lines_changed=10
        )
    )
    
    request = PatchGenerationRequest(
        plan=plan,
        source_context='<img className="product-image" src={product.image} />'
    )
    
    generator = PatchGenerator(gateway)
    candidate = await generator.generate_patch(request)
    
    # Verify the LLM produced a valid result
    assert candidate.status == "GENERATED"
    assert candidate.base_commit_sha == "abcd1234"
    assert "ProductCard.tsx" in candidate.files_changed
    assert "alt=" in candidate.unified_diff
