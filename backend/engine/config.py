"""
Configuration management for CodeLoom Engine.
"""
import os
from pathlib import Path
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    # Load .env file from engine parent directory or workspace root
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        load_dotenv(override=True)
except ImportError:
    pass


class EngineConfig(BaseModel):
    max_tokens_per_scan: int = Field(default=50000, description="Max token budget per single full audit scan")
    llm_provider: str = Field(default="groq", description="Default provider: groq | nvidia | openrouter | gemini | openai | anthropic | ollama | mock")
    llm_model: str = Field(default="llama-3.3-70b-versatile", description="Default model ID")
    llm_api_key: str = Field(default="", description="General API key or token for LLM calls")
    gemini_api_key: str = Field(default="", description="Google Gemini API Key")
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    anthropic_api_key: str = Field(default="", description="Anthropic API Key")
    groq_api_key: str = Field(default="", description="Groq API Key")
    xai_api_key: str = Field(default="", description="xAI Grok API Key")
    nvidia_api_key: str = Field(default="", description="NVIDIA API Key")
    openrouter_api_key: str = Field(default="", description="OpenRouter API Key")
    ollama_base_url: str = Field(default="http://localhost:11434/v1", description="Ollama / Local LLM Base URL")
    dry_run: bool = Field(default=False, description="When true, uses template/mock generation without remote API calls")
    playwright_headless: bool = Field(default=True, description="Run Playwright in headless mode")
    allow_localhost: bool = Field(default=True, description="Allow local dev scanning (e.g. http://localhost)")
    retry_attempts: int = Field(default=2, description="Max retry attempts for LLM calls")
    timeout_seconds: float = Field(default=30.0, description="LLM call timeout in seconds")

    def __init__(self, **data):
        super().__init__(**data)
        
        # Load environment keys
        self.gemini_api_key = data.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY") or ""
        self.openai_api_key = data.get("openai_api_key") or os.environ.get("OPENAI_API_KEY") or ""
        self.anthropic_api_key = data.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY") or ""
        self.groq_api_key = data.get("groq_api_key") or os.environ.get("GROQ_API_KEY") or ""
        self.xai_api_key = data.get("xai_api_key") or os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY") or ""
        self.nvidia_api_key = data.get("nvidia_api_key") or os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVAPI_KEY") or ""
        self.openrouter_api_key = data.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY") or ""
        self.ollama_base_url = data.get("ollama_base_url") or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434/v1"

        api_key = os.environ.get("LLM_API_KEY") or self.groq_api_key or self.nvidia_api_key or self.openrouter_api_key or self.gemini_api_key or self.openai_api_key or self.anthropic_api_key
        if api_key:
            self.llm_api_key = api_key
        provider = os.environ.get("LLM_PROVIDER")
        if "llm_provider" in data:
            self.llm_provider = data["llm_provider"]
        elif provider:
            self.llm_provider = provider
        elif self.groq_api_key:
            self.llm_provider = "groq"
        elif self.nvidia_api_key:
            self.llm_provider = "nvidia"
        elif self.openrouter_api_key:
            self.llm_provider = "openrouter"
        elif self.gemini_api_key:
            self.llm_provider = "gemini"

        model = os.environ.get("LLM_MODEL") or os.environ.get("AI_MODEL")
        if model:
            self.llm_model = model

        dry_run_env = os.environ.get("DRY_RUN")
        if dry_run_env is not None:
            self.dry_run = dry_run_env.lower() in ("true", "1", "yes")
        elif "dry_run" in data:
            self.dry_run = data["dry_run"]
        elif self.llm_provider == "mock" or not (self.groq_api_key or self.nvidia_api_key or self.openrouter_api_key or self.gemini_api_key or self.openai_api_key or self.anthropic_api_key):
            self.dry_run = True
        else:
            self.dry_run = False

        allow_loc = os.environ.get("ALLOW_LOCALHOST_SCAN")
        if allow_loc is not None:
            self.allow_localhost = allow_loc.lower() in ("true", "1", "yes")

    def get_provider_key(self, provider: str) -> str:
        prov = (provider or self.llm_provider).lower()
        if prov == "nvidia":
            return self.nvidia_api_key
        elif prov == "gemini":
            return self.gemini_api_key
        elif prov == "openai":
            return self.openai_api_key
        elif prov == "anthropic":
            return self.anthropic_api_key
        elif prov == "groq":
            return self.groq_api_key
        elif prov in ("xai", "grok"):
            return self.xai_api_key
        elif prov == "openrouter":
            return self.openrouter_api_key
        return self.llm_api_key


