"""
FastAPI router for AI Provider management, connectivity testing, and prompt presets.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from engine.config import EngineConfig
from engine.ai.providers import GeminiProvider, OpenAIProvider, AnthropicProvider, GroqProvider, OllamaProvider, MockProvider
from engine.ai.prompt_templates import FRAMEWORK_DIRECTIVES, PROMPTS

logger = logging.getLogger("codeloom.api.ai")
router = APIRouter(prefix="/api/ai", tags=["ai-management"])
config = EngineConfig()


class TestConnectionRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    model: Optional[str] = None


@router.get("/providers")
async def get_providers():
    """
    Returns supported LLM providers, available models, and configured status.
    """
    gemini_key = config.get_provider_key("gemini")
    openai_key = config.get_provider_key("openai")
    anthropic_key = config.get_provider_key("anthropic")
    groq_key = config.get_provider_key("groq")

    return {
        "active_provider": config.llm_provider,
        "active_model": config.llm_model,
        "dry_run": config.dry_run,
        "providers": [
            {
                "id": "groq",
                "name": "Groq AI (Llama 3.3 70B)",
                "is_configured": bool(groq_key),
                "default_model": "llama-3.3-70b-versatile",
                "available_models": ["llama-3.3-70b-versatile", "llama3-8b-8192", "mixtral-8x7b-32768"],
                "requires_api_key": True,
            },
            {
                "id": "gemini",
                "name": "Google Gemini AI",
                "is_configured": bool(gemini_key),
                "default_model": "gemini-1.5-flash",
                "available_models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
                "requires_api_key": True,
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "is_configured": bool(openai_key),
                "default_model": "gpt-4o-mini",
                "available_models": ["gpt-4o-mini", "gpt-4o", "o3-mini"],
                "requires_api_key": True,
            },
            {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "is_configured": bool(anthropic_key),
                "default_model": "claude-3-5-haiku-latest",
                "available_models": ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest"],
                "requires_api_key": True,
            },
            {
                "id": "ollama",
                "name": "Ollama / Local LLM",
                "is_configured": True,
                "default_model": "llama3",
                "available_models": ["llama3", "mistral", "codellama", "deepseek-coder"],
                "requires_api_key": False,
            },
            {
                "id": "mock",
                "name": "Deterministic Simulation Engine",
                "is_configured": True,
                "default_model": "mock-simulation-v2",
                "available_models": ["mock-simulation-v2"],
                "requires_api_key": False,
            },
        ]
    }


@router.post("/test-connection")
async def test_connection(req: TestConnectionRequest):
    """
    Tests connectivity to an LLM provider with a lightweight prompt ping.
    """
    provider_id = req.provider.lower()
    api_key = req.api_key or config.get_provider_key(provider_id)
    model = req.model or config.llm_model

    if provider_id not in ("mock", "ollama") and not api_key:
        raise HTTPException(status_code=400, detail=f"No API key provided for {provider_id}")

    test_prompt = "Return ONLY JSON: {\"status\": \"ok\", \"message\": \"CodeLoom connection verified\"}"

    try:
        if provider_id == "groq":
            prov = GroqProvider()
            res = await prov.generate(prompt=test_prompt, model=model or "llama-3.3-70b-versatile", api_key=api_key, timeout=10.0)
        elif provider_id == "gemini":
            prov = GeminiProvider()
            res = await prov.generate(prompt=test_prompt, model=model or "gemini-1.5-flash", api_key=api_key, timeout=10.0)
        elif provider_id == "openai":
            prov = OpenAIProvider()
            res = await prov.generate(prompt=test_prompt, model=model or "gpt-4o-mini", api_key=api_key, timeout=10.0)
        elif provider_id == "anthropic":
            prov = AnthropicProvider()
            res = await prov.generate(prompt=test_prompt, model=model or "claude-3-5-haiku-latest", api_key=api_key, timeout=10.0)
        elif provider_id == "ollama":
            prov = OllamaProvider()
            res = await prov.generate(prompt=test_prompt, model=model or "llama3", api_key=api_key, timeout=10.0)
        else:
            prov = MockProvider()
            res = await prov.generate(prompt=test_prompt, model="mock", timeout=5.0)

        return {
            "success": True,
            "provider": provider_id,
            "model_used": res.model_used,
            "latency_ms": res.latency_ms,
            "message": "Connection established successfully!",
            "parsed": res.parsed,
        }
    except Exception as e:
        logger.error(f"Connection test failed for {provider_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")


@router.get("/presets")
async def get_presets():
    """
    Returns framework targets and available prompt template identifiers.
    """
    return {
        "frameworks": list(FRAMEWORK_DIRECTIVES.keys()),
        "prompt_templates": list(PROMPTS.keys()),
    }


class ScreenReaderRequest(BaseModel):
    rule_id: str
    before_code: str
    after_code: str
    target_selector: Optional[str] = None


@router.post("/screen-reader")
async def simulate_screen_reader(req: ScreenReaderRequest):
    """
    Simulates speech utterances and ARIA traits for DOM nodes before and after remediation.
    """
    from engine.ai.screen_reader import screen_reader_simulator
    res = screen_reader_simulator.simulate(
        rule_id=req.rule_id,
        before_code=req.before_code,
        after_code=req.after_code,
        target_selector=req.target_selector
    )
    return res.model_dump()


@router.get("/benchmarks")
async def run_deterministic_benchmarks():
    """
    Executes 5 canonical WCAG 2.2 benchmark fixtures against deterministic AST validator gates.
    """
    from engine.benchmarks.benchmark_runner import benchmark_runner
    return benchmark_runner.run_suite()


