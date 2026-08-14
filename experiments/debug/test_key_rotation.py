import asyncio
import json
from engine.ai.providers import NVIDIAProvider, GroqProvider
from engine.ai.llm_gateway import LLMGateway
from engine.config import EngineConfig

async def main():
    print("--- 1. Testing NVIDIA NIM Key Pool ---")
    nv = NVIDIAProvider()
    res_nv = await nv.generate(prompt="Respond with a JSON object: {\"status\": \"ok\", \"provider\": \"nvidia\"}")
    print(f"NVIDIA: {res_nv.parsed} | Model: {res_nv.model_used} | Time: {res_nv.latency_ms}ms")

    print("\n--- 2. Testing Groq Key Pool ---")
    gq = GroqProvider()
    res_gq = await gq.generate(prompt="Respond with a JSON object: {\"status\": \"ok\", \"provider\": \"groq\"}")
    print(f"Groq: {res_gq.parsed} | Model: {res_gq.model_used} | Time: {res_gq.latency_ms}ms")

    print("\n--- 3. Testing LLM Gateway Automatic Fallback Chain ---")
    cfg = EngineConfig()
    gw = LLMGateway(cfg)
    resp = await gw.generate(
        prompt_template="Generate JSON: {{\"fix\": \"image-alt-added\", \"target\": \"img\"}}",
        context={},
        tier="full_ai"
    )
    print(f"Gateway Primary Choice: Provider={resp.provider_used} | Model={resp.model} | Tokens={resp.tokens_used} | Time={resp.latency_ms}ms")

if __name__ == "__main__":
    asyncio.run(main())
