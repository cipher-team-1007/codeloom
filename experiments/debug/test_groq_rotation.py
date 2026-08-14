import asyncio
from engine.ai.providers import GroqProvider

async def main():
    print("Testing Groq Multi-Key Pool Rotation...")
    gq = GroqProvider()
    res = await gq.generate(
        prompt="Respond ONLY with a JSON object: {\"status\": \"ok\", \"fix\": \"added-alt-tag\"}",
        system_prompt="You are an accessibility code fix engine."
    )
    print(f"Success! Model: {res.model_used} | Latency: {res.latency_ms}ms | Parsed: {res.parsed}")

if __name__ == "__main__":
    asyncio.run(main())
