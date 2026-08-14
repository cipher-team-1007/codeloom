import pytest
import httpx
import os
from pathlib import Path

from engine.source_intelligence.client import SourceIntelligenceClient
from engine.source_intelligence.models import SourceMappingRequest, RuntimeEvidence
from engine.source_intelligence.exceptions import SourceIntelligenceConnectionError, SourceIntelligenceAPIError, SourceIntelligenceTimeoutError

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "experiments" / "source-mapping" / "fixture" / "src"
# Assume the node service is running locally for integration tests
os.environ["SOURCE_INTELLIGENCE_URL"] = "http://127.0.0.1:8002"

@pytest.fixture
def client():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', 8002)) != 0:
            pytest.skip("Source intelligence Node service not running on port 8002")
    return SourceIntelligenceClient(base_url="http://127.0.0.1:8002", timeout=5.0)

@pytest.mark.asyncio
async def test_case_1_exact_match(client):
    request = SourceMappingRequest(
        repositoryPath=str(FIXTURE_PATH),
        commitSha="mock-sha",
        runtimeEvidence=RuntimeEvidence(
            ruleId="image-alt",
            targetSelector="img.product-image",
            htmlSnippet='<img class="product-image" src="/placeholder1.jpg">'
        )
    )
    
    result = await client.map_source(request)
    assert result.status == "MATCHED"
    assert len(result.candidates) > 0
    assert result.candidates[0].file.endswith("ProductCard.tsx")
    assert result.candidates[0].score == 3

@pytest.mark.asyncio
async def test_case_2_exact_match(client):
    request = SourceMappingRequest(
        repositoryPath=str(FIXTURE_PATH),
        commitSha="mock-sha",
        runtimeEvidence=RuntimeEvidence(
            ruleId="button-name",
            targetSelector="button.btn-primary",
            htmlSnippet='<button class="btn-primary">Add to Cart</button>'
        )
    )
    
    result = await client.map_source(request)
    assert result.status == "MATCHED"
    assert len(result.candidates) > 0
    assert result.candidates[0].file.endswith("PrimaryButton.tsx")

@pytest.mark.asyncio
async def test_case_3_similar_elements(client):
    # Depending on how exact matching ranks, it should find the button with class add-item
    request = SourceMappingRequest(
        repositoryPath=str(FIXTURE_PATH),
        commitSha="mock-sha",
        runtimeEvidence=RuntimeEvidence(
            ruleId="button-name",
            targetSelector="button.btn-secondary",
            htmlSnippet='<button class="btn-secondary"><i class="icon-cart"></i></button>'
        )
    )
    result = await client.map_source(request)
    assert result.status == "MATCHED"
    assert len(result.candidates) > 0
    assert result.candidates[0].file.endswith("SecondaryButton.tsx")

@pytest.mark.asyncio
async def test_case_4_dynamic_match(client):
    request = SourceMappingRequest(
        repositoryPath=str(FIXTURE_PATH),
        commitSha="mock-sha",
        runtimeEvidence=RuntimeEvidence(
            ruleId="link-name",
            targetSelector="a.nav-link.active",
            htmlSnippet='<a class="nav-link active" href="/products">Products</a>'
        )
    )
    result = await client.map_source(request)
    assert result.status == "MATCHED"
    assert len(result.candidates) > 0
    assert result.candidates[0].file.endswith("DynamicLink.tsx")

@pytest.mark.asyncio
async def test_case_5_ambiguous(client):
    request = SourceMappingRequest(
        repositoryPath=str(FIXTURE_PATH),
        commitSha="mock-sha",
        runtimeEvidence=RuntimeEvidence(
            ruleId="image-alt",
            targetSelector="img.ambiguous-image",
            htmlSnippet='<img class="ambiguous-image" src="/profile.jpg">'
        )
    )
    result = await client.map_source(request)
    assert result.status == "AMBIGUOUS"
    assert len(result.candidates) > 1

@pytest.mark.asyncio
async def test_node_unavailable():
    bad_client = SourceIntelligenceClient(base_url="http://127.0.0.1:9999", timeout=1.0)
    request = SourceMappingRequest(
        repositoryPath=str(FIXTURE_PATH),
        commitSha="mock-sha",
        runtimeEvidence=RuntimeEvidence(
            ruleId="image-alt",
            targetSelector="img",
            htmlSnippet='<img>'
        )
    )
    with pytest.raises(SourceIntelligenceTimeoutError):
        await bad_client.map_source(request)

@pytest.mark.asyncio
async def test_invalid_request(client):
    request = SourceMappingRequest(
        repositoryPath="/invalid/path",
        commitSha="mock-sha",
        runtimeEvidence=RuntimeEvidence(
            ruleId="image-alt",
            targetSelector="img",
            htmlSnippet='<img>'
        )
    )
    with pytest.raises(SourceIntelligenceAPIError) as exc_info:
        await client.map_source(request)
    assert exc_info.value.status_code in [400, 403]
