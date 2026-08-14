"""
Provider-agnostic LLM gateway with multi-provider routing, retry logic, and telemetry.
"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engine.config import EngineConfig
from engine.ai.providers import (
    BaseLLMProvider, GeminiProvider, OpenAIProvider, AnthropicProvider,
    OllamaProvider, GroqProvider, XAIProvider, NVIDIAProvider, OpenRouterProvider, MockProvider, ProviderResult
)

logger = logging.getLogger("codeloom.ai.llm_gateway")


class LLMResponse(BaseModel):
    content: str
    parsed: Dict[str, Any]
    tokens_used: int
    model: str
    tier: str
    provider_used: str = "mock"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    prompt_sent: str = ""
    system_prompt_sent: str = ""


class LLMGateway:
    """Interacts with LLM APIs with provider fallback, retry, and mock support."""

    def __init__(self, config: EngineConfig):
        self.config = config
        self.providers: Dict[str, BaseLLMProvider] = {
            "groq": GroqProvider(),
            "xai": XAIProvider(),
            "nvidia": NVIDIAProvider(),
            "openrouter": OpenRouterProvider(),
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "ollama": OllamaProvider(),
            "mock": MockProvider(),
        }


    async def generate(
        self,
        prompt_template: str,
        context: Dict[str, Any],
        tier: str,
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None,
        api_key_override: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """
        Formats prompt with context and calls designated LLM provider with fallback & retries.
        """
        # Fill formatting defaults for prompt templates if missing
        safe_ctx = {
            "framework_directive": "Output standard Vanilla HTML/CSS markup.",
            "custom_instructions_block": "",
            "html_snippet_escaped": context.get("html_snippet", "").replace('"', '\\"'),
            "category": "accessibility",
            "search_engine_impact": "Medium search impact",
            "core_web_vital": "LCP",
            "estimated_time_savings_ms": 100,
            **context
        }
        try:
            formatted_prompt = prompt_template.format(**safe_ctx)
        except Exception:
            formatted_prompt = prompt_template

        target_provider = (provider_override or self.config.llm_provider).lower()
        target_model = model_override or self.config.llm_model

        # Build prioritized failover provider list with support for explicit LLM_PROVIDERS env control
        import os
        allowed_env = os.environ.get("LLM_PROVIDERS") or os.environ.get("ALLOWED_PROVIDERS")
        if allowed_env and allowed_env.strip().lower() != "all":
            allowed_providers = [p.strip().lower() for p in allowed_env.split(",") if p.strip()]
            provider_chain = [p for p in allowed_providers if p in self.providers]
            if not provider_chain:
                provider_chain = [target_provider]
        else:
            provider_chain = [target_provider]
            for p in ["groq", "xai", "gemini", "nvidia", "openrouter", "openai", "anthropic", "ollama"]:
                if p not in provider_chain:
                    p_key = self.config.get_provider_key(p)
                    if (p != "mock" and p != "ollama" and p_key and not self.config.dry_run):
                        provider_chain.append(p)

        if "mock" not in provider_chain:
            provider_chain.append("mock")

        last_error = None
        max_attempts = self.config.retry_attempts

        for current_provider in provider_chain:
            key = api_key_override or self.config.get_provider_key(current_provider)

            if current_provider not in ("mock", "ollama") and (self.config.dry_run or not key):
                logger.info(f"Skipping provider {current_provider}: missing API key or dry_run enabled.")
                continue

            provider_impl = self.providers.get(current_provider, self.providers["mock"])

            # If provider supports multi-key pool (groq, nvidia), let the provider rotate unless override is given
            passed_key = api_key_override if api_key_override else (None if current_provider in ("groq", "nvidia") else key)

            for attempt in range(max_attempts):
                try:
                    res: ProviderResult = await provider_impl.generate(
                        prompt=formatted_prompt,
                        system_prompt=system_prompt,
                        model=target_model if current_provider == target_provider else None,
                        api_key=passed_key,
                        temperature=temperature,
                        max_tokens=1500 if tier == "full_ai" else 600,
                        timeout=self.config.timeout_seconds,
                    )

                    return LLMResponse(
                        content=res.content,
                        parsed=res.parsed,
                        tokens_used=res.total_tokens,
                        model=res.model_used,
                        tier=tier,
                        provider_used=res.provider_name,
                        prompt_tokens=res.prompt_tokens,
                        completion_tokens=res.completion_tokens,
                        latency_ms=res.latency_ms,
                        estimated_cost_usd=res.estimated_cost_usd,
                        prompt_sent=formatted_prompt,
                        system_prompt_sent=system_prompt or "",
                    )

                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed for provider {current_provider}: {err_str[:150]}")
                    # Fast failover on rate-limits, unconfigured/unpaid endpoints, or timeouts
                    if any(k in err_str for k in ["429", "Too Many Requests", "Rate limit", "402", "Payment Required", "404", "Not Found", "timeout", "Timed out"]):
                        logger.info(f"Provider {current_provider} encountered unrecoverable status ({err_str[:60]}). Immediately failing over.")
                        break
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(0.1)

            logger.warning(f"Provider {current_provider} exhausted retries. Attempting failover to next available provider...")

        # Final guarantee fallback
        mock_res = await self.providers["mock"].generate(
            prompt=formatted_prompt,
            system_prompt=system_prompt,
        )
        return LLMResponse(
            content=mock_res.content,
            parsed=mock_res.parsed,
            tokens_used=mock_res.total_tokens,
            model="mock-fallback",
            tier=tier,
            provider_used="mock",
            prompt_tokens=mock_res.prompt_tokens,
            completion_tokens=mock_res.completion_tokens,
            latency_ms=mock_res.latency_ms,
            estimated_cost_usd=0.0,
            prompt_sent=formatted_prompt,
            system_prompt_sent=system_prompt or "",
        )

        raise RuntimeError(f"LLM generation failed: {str(last_error)}")
