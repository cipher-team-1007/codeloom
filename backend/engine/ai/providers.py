"""
Multi-provider LLM adapters for Gemini, OpenAI, Anthropic, Ollama, and Mock simulation.
Includes cost calculation pricing tables.
"""
import os
from abc import ABC, abstractmethod
import json
import re
import time
import logging
from typing import Dict, Any, Optional, Tuple, List
import httpx
from pydantic import BaseModel

logger = logging.getLogger("codeloom.ai.providers")

# Standard token cost table in USD per 1,000 tokens (Input, Output)
COST_PER_1K_TOKENS = {
    # Gemini
    "gemini-1.5-flash": (0.000075, 0.0003),
    "gemini-1.5-pro": (0.00125, 0.005),
    "gemini-2.0-flash": (0.0001, 0.0004),
    # OpenAI
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.010),
    "o3-mini": (0.0011, 0.0044),
    # Anthropic
    "claude-3-5-haiku": (0.001, 0.005),
    "claude-3-5-haiku-latest": (0.001, 0.005),
    "claude-3-5-sonnet": (0.003, 0.015),
    "claude-3-5-sonnet-latest": (0.003, 0.015),
    # Ollama / Mock
    "ollama": (0.0, 0.0),
    "mock": (0.0, 0.0),
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculates estimated USD cost for a given generation call."""
    key = model.lower()
    rates = (0.0001, 0.0004) # Default fallback rate
    for m_key, m_rates in COST_PER_1K_TOKENS.items():
        if m_key in key:
            rates = m_rates
            break
    
    input_cost = (prompt_tokens / 1000.0) * rates[0]
    output_cost = (completion_tokens / 1000.0) * rates[1]
    return round(input_cost + output_cost, 6)


def extract_json_payload(content: Optional[str]) -> Dict[str, Any]:
    """Helper to cleanly extract JSON object from markdown or raw text output."""
    if not content or not isinstance(content, str) or not content.strip():
        return {}
    
    content_clean = content.strip()

    # Strip thinking/reasoning blocks (e.g. <think>...</think>)
    content_clean = re.sub(r'<think>[\s\S]*?</think>', '', content_clean).strip()

    try:
        return json.loads(content_clean, strict=False)
    except json.JSONDecodeError:
        pass

    # Strip ```json and ``` code block wrappers if present
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content_clean)
    if code_block_match:
        snippet = code_block_match.group(1).strip()
        try:
            return json.loads(snippet, strict=False)
        except json.JSONDecodeError:
            pass

    # Find first { and last }
    start = content_clean.find("{")
    end = content_clean.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = content_clean[start:end+1]
        try:
            return json.loads(snippet, strict=False)
        except json.JSONDecodeError:
            pass

    # Regex extraction fallback for unified_diff if JSON parsing fails
    diff_match = re.search(r'"unified_diff"\s*:\s*"(.*?)"(?:\s*,\s*"|\s*\})', content_clean, re.DOTALL)
    if diff_match:
        diff_val = diff_match.group(1).replace("\\n", "\n").replace('\\"', '"')
        return {"unified_diff": diff_val, "rationale": "Extracted via regex fallback."}

    return {}


def parse_api_keys(primary_key: Optional[str], env_vars: List[str]) -> List[str]:
    """
    Collects API keys from primary_key and specified env_vars.
    Supports comma-separated API key lists (e.g., GROQ_API_KEY=key1,key2,key3),
    newline-separated keys, as well as numbered env vars (GROQ_API_KEY_2).
    Deduplicates keys while preserving ordering.
    """
    raw_inputs = []
    if primary_key:
        raw_inputs.append(primary_key)
    for var in env_vars:
        val = os.environ.get(var)
        if val:
            raw_inputs.append(val)

    parsed_keys = []
    seen = set()
    for item in raw_inputs:
        if not item:
            continue
        sub_keys = [k.strip() for k in re.split(r'[,\n]', item) if k.strip()]
        for k in sub_keys:
            if k not in seen:
                seen.add(k)
                parsed_keys.append(k)
    return parsed_keys


def clean_and_normalize_unified_diff(diff_text: str) -> str:
    """
    Cleans raw unified diff strings:
    - Normalizes CRLF \r\n -> LF \n
    - Replaces escaped literal \\n -> \n and \\" -> "
    - Ensures a trailing newline at the end of the patch
    - Strips non-diff prose before '--- ' and after the last hunk
    - Ensures hunk context lines without prefix get a single leading space
    """
    if not diff_text:
        return ""
    
    text = diff_text.replace("\r\n", "\n")
    if "\\n" in text and "\n" not in text:
        text = text.replace("\\n", "\n").replace('\\"', '"')
    
    lines = text.split("\n")
    cleaned_lines = []
    in_diff = False
    in_hunk = False

    for line in lines:
        l_strip = line.strip()
        if l_strip.startswith("--- "):
            in_diff = True
            in_hunk = False
            cleaned_lines.append(l_strip)
        elif in_diff and l_strip.startswith("+++ "):
            cleaned_lines.append(l_strip)
        elif in_diff and l_strip.startswith("@@"):
            in_hunk = True
            cleaned_lines.append(l_strip)
        elif in_hunk:
            if line.startswith("-") and not line.startswith("---"):
                cleaned_lines.append(line)
            elif line.startswith("+") and not line.startswith("+++"):
                cleaned_lines.append(line)
            elif line.startswith(" ") or line.startswith("\\"):
                cleaned_lines.append(line)
            elif l_strip.startswith("-") and not l_strip.startswith("---"):
                idx = line.find("-")
                cleaned_lines.append("-" + line[idx+1:])
            elif l_strip.startswith("+") and not l_strip.startswith("+++"):
                idx = line.find("+")
                cleaned_lines.append("+" + line[idx+1:])
            elif line.startswith("!"):
                cleaned_lines.append(" " + line.lstrip("! "))
            elif l_strip == "":
                cleaned_lines.append(" ")
            elif not (l_strip.startswith("```") or l_strip.startswith("Rational") or l_strip.startswith("Note:") or l_strip.startswith("Plan") or l_strip.startswith("---") or l_strip.startswith("+++") or l_strip.startswith("@@")):
                cleaned_lines.append(" " + line)
        elif in_diff:
            cleaned_lines.append(line)

    res = "\n".join(cleaned_lines).strip()
    if res and not res.endswith("\n"):
        res += "\n"
    return res


def normalize_llm_response(content: str, parsed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Normalizes LLM output from any provider/model into a standard PatchCandidate structure:
    - Structured JSON
    - Markdown fenced JSON
    - Raw unified diff
    - Markdown fenced diff (```diff ... ```)
    - String-escaped unified_diff JSON field
    """
    result = dict(parsed) if isinstance(parsed, dict) else {}

    # If parsed dict already has a non-empty unified_diff, return normalized dict
    if "unified_diff" in result and str(result["unified_diff"]).strip():
        raw_diff = str(result["unified_diff"]).strip()
        result["unified_diff"] = clean_and_normalize_unified_diff(raw_diff)
        if "files_changed" not in result or not isinstance(result["files_changed"], list):
            result["files_changed"] = []
        if "rationale" not in result:
            result["rationale"] = "AI generated accessibility patch."
        return result

    if not content or not content.strip():
        return result

    clean_content = content.strip()

    # Attempt JSON extraction if parsed was empty
    if not result:
        result = extract_json_payload(clean_content)
        if "unified_diff" in result and str(result["unified_diff"]).strip():
            raw_diff = str(result["unified_diff"]).strip()
            result["unified_diff"] = clean_and_normalize_unified_diff(raw_diff)
            return result

    # Check for markdown fenced diffs (```diff ... ``` or ```patch ... ```)
    diff_block_match = re.search(r'```(?:diff|patch)?\s*\n?([\s\S]*?)\s*```', clean_content)
    if diff_block_match:
        snippet = diff_block_match.group(1).strip()
        if "---" in snippet and "+++" in snippet and "@@" in snippet:
            result["unified_diff"] = clean_and_normalize_unified_diff(snippet)
            result["rationale"] = result.get("rationale", "Extracted patch from code block.")
            return result

    # Check for raw unified diff pattern in full text
    diff_match = re.search(r'(--- (?:a/)?\S+[\s\S]*?\+\+\+ (?:b/)?\S+[\s\S]*?@@[\s\S]*)', clean_content)
    if diff_match:
        extracted = diff_match.group(1).strip()
        result["unified_diff"] = clean_and_normalize_unified_diff(extracted)
        result["rationale"] = result.get("rationale", "Extracted raw unified diff.")
        return result

    # Line-by-line diff fallback if headers are present
    if "---" in clean_content and "+++" in clean_content and "@@" in clean_content:
        lines = clean_content.splitlines()
        diff_lines = [
            l for l in lines 
            if l.startswith("---") or l.startswith("+++") or l.startswith("@@") or l.startswith("+") or l.startswith("-") or l.startswith(" ")
        ]
        diff_str = "\n".join(diff_lines).strip()
        if diff_str and "@@" in diff_str:
            result["unified_diff"] = clean_and_normalize_unified_diff(diff_str)
            result["rationale"] = result.get("rationale", "Extracted unified diff lines.")
            return result

    return result




class ProviderResult(BaseModel):
    content: str
    parsed: Dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    model_used: str
    provider_name: str
    estimated_cost_usd: float


class BaseLLMProvider(ABC):
    """Abstract interface for LLM execution engine."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> ProviderResult:
        pass


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM Integration."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> ProviderResult:
        start_time = time.time()
        selected_model = model if (model and "gemini" in model.lower()) else "gemini-1.5-flash"
        if not api_key:
            raise ValueError("Gemini API key is missing.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }

        contents = []
        if system_prompt:
            prompt = f"System Instruction: {system_prompt}\n\nTask:\n{prompt}"
            
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        client_timeout = httpx.Timeout(timeout, connect=10.0)
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start_time) * 1000.0
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini API returned empty candidates.")
            
        content = candidates[0]["content"]["parts"][0].get("text") or ""
        parsed = extract_json_payload(content)
        
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", len(prompt) // 4)
        completion_tokens = usage.get("candidatesTokenCount", len(content) // 4)
        total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)
        cost = calculate_cost(selected_model, prompt_tokens, completion_tokens)

        return ProviderResult(
            content=content,
            parsed=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency, 2),
            model_used=selected_model,
            provider_name="gemini",
            estimated_cost_usd=cost,
        )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider (GPT-4o, GPT-4o-mini, o3-mini)."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> ProviderResult:
        start_time = time.time()
        selected_model = model if (model and "gpt" in model.lower()) else "gpt-4o-mini"
        if not api_key:
            raise ValueError("OpenAI API key is missing.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": selected_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        client_timeout = httpx.Timeout(timeout, connect=10.0)
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start_time) * 1000.0
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("OpenAI API returned empty choices.")
            
        content = choices[0].get("message", {}).get("content") or ""
        parsed = extract_json_payload(content)

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
        completion_tokens = usage.get("completion_tokens", len(content) // 4)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        cost = calculate_cost(selected_model, prompt_tokens, completion_tokens)

        return ProviderResult(
            content=content,
            parsed=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency, 2),
            model_used=selected_model,
            provider_name="openai",
            estimated_cost_usd=cost,
        )


class GroqProvider(BaseLLMProvider):
    """Groq API Provider (Llama 3.3 70B, Llama 3 8B)."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 15.0,
    ) -> ProviderResult:
        start_time = time.time()
        keys = parse_api_keys(api_key, ["GROQ_API_KEY", "GROQ_API_KEYS", "GROQ_API_KEY_2", "GROQ_API_KEY_3", "GROQ_API_KEY_4", "GROQ_API_KEY_5"])
        
        if not keys:
            raise ValueError("Groq API key is missing.")

        models_to_try = [
            model if (model and "llama" in model.lower()) else "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
        ]

        messages = []
        sys_msg = (system_prompt or "") + "\nYou MUST respond with a valid JSON object."
        messages.append({"role": "system", "content": sys_msg.strip()})
        messages.append({"role": "user", "content": prompt})

        last_exc = None
        data = None
        used_model = models_to_try[0]

        client_timeout = httpx.Timeout(timeout, connect=5.0)
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            for k in keys:
                for m in models_to_try:
                    try:
                        headers = {
                            "Authorization": f"Bearer {k}",
                            "Content-Type": "application/json",
                        }
                        payload = {
                            "model": m,
                            "messages": messages,
                            "response_format": {"type": "json_object"},
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        }
                        resp = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            used_model = m
                            break
                        elif resp.status_code == 429:
                            logger.info(f"Groq key ...{k[-6:]} rate-limited for model {m}. Trying next key/model...")
                            continue
                        else:
                            resp.raise_for_status()
                    except Exception as exc:
                        last_exc = exc
                        continue
                if data:
                    break

        if not data:
            raise last_exc or ValueError("All Groq keys and models exhausted.")

        latency = (time.time() - start_time) * 1000.0
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("Groq API returned empty choices.")
            
        content = choices[0].get("message", {}).get("content") or ""
        parsed = extract_json_payload(content)

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
        completion_tokens = usage.get("completion_tokens", len(content) // 4)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        cost = calculate_cost(used_model, prompt_tokens, completion_tokens)

        return ProviderResult(
            content=content,
            parsed=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency, 2),
            model_used=used_model,
            provider_name="groq",
            estimated_cost_usd=cost,
        )


class XAIProvider(BaseLLMProvider):
    """xAI (Grok) API Provider supporting Grok-2 and Grok-2-mini."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 15.0,
    ) -> ProviderResult:
        start_time = time.time()
        keys = parse_api_keys(api_key, ["XAI_API_KEY", "XAI_API_KEYS", "GROK_API_KEY"])

        if not keys:
            raise ValueError("xAI API key is missing.")

        models_to_try = [
            model if (model and "grok" in model.lower()) else "grok-2-latest",
            "grok-2-mini",
            "grok-build-0.1",
            "grok-4.6",
            "grok-4.5",
            "grok-4.20",
            "grok-beta"
        ]

        messages = []
        sys_msg = (system_prompt or "") + "\nYou MUST respond ONLY with a valid JSON object."
        messages.append({"role": "system", "content": sys_msg.strip()})
        messages.append({"role": "user", "content": prompt})

        last_exc = None
        data = None
        used_model = models_to_try[0]

        client_timeout = httpx.Timeout(timeout, connect=5.0)
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            for k in keys:
                for m in models_to_try:
                    try:
                        headers = {
                            "Authorization": f"Bearer {k}",
                            "Content-Type": "application/json",
                        }
                        payload = {
                            "model": m,
                            "messages": messages,
                            "response_format": {"type": "json_object"},
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        }
                        resp = await client.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            used_model = m
                            break
                        elif resp.status_code == 429:
                            logger.info(f"xAI key ...{k[-6:]} rate-limited for model {m}. Trying next key/model...")
                            continue
                        else:
                            resp.raise_for_status()
                    except Exception as exc:
                        last_exc = exc
                        continue
                if data:
                    break

        if not data:
            raise last_exc or ValueError("All xAI API keys and models exhausted.")

        latency = (time.time() - start_time) * 1000.0
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("xAI API returned empty choices.")

        content = choices[0].get("message", {}).get("content") or ""
        parsed = extract_json_payload(content)

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
        completion_tokens = usage.get("completion_tokens", len(content) // 4)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        cost = calculate_cost(used_model, prompt_tokens, completion_tokens)

        return ProviderResult(
            content=content,
            parsed=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency, 2),
            model_used=used_model,
            provider_name="xai",
            estimated_cost_usd=cost,
        )


class NVIDIAProvider(BaseLLMProvider):
    """NVIDIA NIM API Provider (Nemotron, Llama 3.3, Llama 3.1)."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 10.0,
    ) -> ProviderResult:
        start_time = time.time()
        # Valid active models on NVIDIA NIM integrate.api.nvidia.com
        selected_model = model or "meta/llama-3.3-70b-instruct"
        if "/" not in selected_model:
            selected_model = "meta/llama-3.3-70b-instruct"
        elif "nemotron" in selected_model.lower() and "70b" not in selected_model.lower():
            selected_model = "meta/llama-3.3-70b-instruct"
        elif "ultra" in selected_model.lower() or "550b" in selected_model.lower():
            selected_model = "meta/llama-3.3-70b-instruct"

        keys = parse_api_keys(api_key, ["NVIDIA_API_KEY", "NVIDIA_API_KEYS", "NVIDIA_API_KEY_2", "NVIDIA_API_KEY_3", "NVIDIA_API_KEY_4", "NVIDIA_API_KEY_5", "NVAPI_KEY"])

        if not keys:
            raise ValueError("NVIDIA API key is missing.")

        endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
        messages = []
        sys_msg = (system_prompt or "") + "\nYou MUST respond ONLY with a valid JSON object."
        messages.append({"role": "system", "content": sys_msg.strip()})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        client_timeout = httpx.Timeout(timeout, connect=15.0)
        data = None
        last_exc = None

        async with httpx.AsyncClient(timeout=client_timeout) as client:
            for k in keys:
                try:
                    headers = {
                        "Authorization": f"Bearer {k}",
                        "Content-Type": "application/json",
                    }
                    resp = await client.post(endpoint, headers=headers, json=payload)
                    
                    # Automatic fallback if model ID is unavailable
                    if resp.status_code in (404, 400):
                        logger.warning(f"NVIDIA model '{selected_model}' returned {resp.status_code}. Retrying with 'meta/llama-3.3-70b-instruct'...")
                        selected_model = "meta/llama-3.3-70b-instruct"
                        payload["model"] = selected_model
                        resp = await client.post(endpoint, headers=headers, json=payload)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        break
                    elif resp.status_code == 429:
                        logger.info(f"NVIDIA key ...{k[-6:]} rate-limited. Rotating to next key...")
                        continue
                    else:
                        resp.raise_for_status()
                except Exception as exc:
                    last_exc = exc
                    continue

        if not data:
            raise last_exc or ValueError("All NVIDIA NIM keys exhausted.")

        latency = (time.time() - start_time) * 1000.0
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("NVIDIA API returned empty choices.")

        content = choices[0].get("message", {}).get("content") or ""
        parsed = extract_json_payload(content)

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
        completion_tokens = usage.get("completion_tokens", len(content) // 4)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        cost = calculate_cost(selected_model, prompt_tokens, completion_tokens)

        return ProviderResult(
            content=content,
            parsed=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency, 2),
            model_used=selected_model,
            provider_name="nvidia",
            estimated_cost_usd=cost,
        )


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter API Provider supporting free and premium multi-model routing."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 45.0,
    ) -> ProviderResult:
        start_time = time.time()
        selected_model = model or "google/gemini-2.0-flash-001"
        keys = parse_api_keys(api_key, ["OPENROUTER_API_KEY", "OPENROUTER_API_KEYS", "OPENROUTER_API_KEY_2", "OPENROUTER_API_KEY_3"])

        if not keys:
            raise ValueError("OpenRouter API key is missing.")

        active_key = keys[0]
        endpoint = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {active_key}",
            "HTTP-Referer": "https://codeloom.ai",
            "X-Title": "CodeLoom Engine",
            "Content-Type": "application/json",
        }

        messages = []
        sys_msg = (system_prompt or "") + "\nYou MUST respond ONLY with a valid JSON object."
        messages.append({"role": "system", "content": sys_msg.strip()})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": selected_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        client_timeout = httpx.Timeout(timeout, connect=15.0)

        async with httpx.AsyncClient(timeout=client_timeout) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            if resp.status_code in (404, 400):
                payload["model"] = "meta-llama/llama-3.3-70b-instruct"
                resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start_time) * 1000.0
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("OpenRouter API returned empty choices.")

        content = choices[0].get("message", {}).get("content") or ""
        parsed = extract_json_payload(content)

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
        completion_tokens = usage.get("completion_tokens", len(content) // 4)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        cost = calculate_cost(selected_model, prompt_tokens, completion_tokens)

        return ProviderResult(
            content=content,
            parsed=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency, 2),
            model_used=selected_model,
            provider_name="openrouter",
            estimated_cost_usd=cost,
        )


class AnthropicProvider(BaseLLMProvider):

    """Anthropic Claude API Provider (Claude 3.5 Sonnet / Haiku)."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> ProviderResult:
        start_time = time.time()
        selected_model = model or "claude-3-5-haiku-latest"
        if not api_key:
            raise ValueError("Anthropic API key is missing.")

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        payload = {
            "model": selected_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start_time) * 1000.0
        content = data["content"][0]["text"]
        parsed = extract_json_payload(content)

        usage = data.get("usage", {})
        prompt_tokens = usage.get("input_tokens", len(prompt) // 4)
        completion_tokens = usage.get("output_tokens", len(content) // 4)
        total_tokens = prompt_tokens + completion_tokens
        cost = calculate_cost(selected_model, prompt_tokens, completion_tokens)

        return ProviderResult(
            content=content,
            parsed=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency, 2),
            model_used=selected_model,
            provider_name="anthropic",
            estimated_cost_usd=cost,
        )


class OllamaProvider(BaseLLMProvider):
    """Local Ollama / OpenAI-compatible local model integration."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> ProviderResult:
        start_time = time.time()
        selected_model = model or "llama3"
        base_url = api_key if (api_key and api_key.startswith("http")) else "http://localhost:11434/v1"
        endpoint = f"{base_url.rstrip('/')}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start_time) * 1000.0
        content = data["choices"][0]["message"]["content"]
        parsed = extract_json_payload(content)

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
        completion_tokens = usage.get("completion_tokens", len(content) // 4)
        total_tokens = prompt_tokens + completion_tokens

        return ProviderResult(
            content=content,
            parsed=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency, 2),
            model_used=selected_model,
            provider_name="ollama",
            estimated_cost_usd=0.0,
        )


class MockProvider(BaseLLMProvider):
    """High-fidelity mock provider for zero-token local testing."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> ProviderResult:
        start_time = time.time()
        time.sleep(0.05) # Simulate minor non-blocking delay

        # Extract rule from prompt context if possible
        rule_match = re.search(r'Rule:\s*([^\n\r]+)', prompt)
        rule_id = rule_match.group(1).strip() if rule_match else "wcag-rule"

        # Check if patch generation is requested
        if "patch plan" in prompt.lower() or "unified_diff" in prompt.lower() or "generate the patch" in prompt.lower():
            file_match = re.search(r'File:\s*([^\n\r]+)', prompt)
            target_file = file_match.group(1).strip() if file_match else "src/components/PrimaryButton.tsx"
            
            # Extract source context to make a valid mock diff
            context_match = re.search(r'Untrusted Source Context\n```\n(.*?)\n```', prompt, re.DOTALL)
            if context_match and context_match.group(1).strip():
                source_context = context_match.group(1).strip()
                # Find the first non-empty line
                lines = [line for line in source_context.split('\n') if line.strip()]
                if lines:
                    target_line = lines[0]
                    # strip line numbers if they exist (e.g., "12: <div...")
                    clean_line = re.sub(r'^\d+:\s*', '', target_line)
                    # mock replace
                    diff = f"--- a/{target_file}\n+++ b/{target_file}\n@@ -1,3 +1,3 @@\n-{clean_line}\n+{clean_line} /* mock patch */\n"
                else:
                    diff = f"--- a/{target_file}\n+++ b/{target_file}\n@@ -1,3 +1,3 @@\n- old\n+ new\n"
            else:
                diff = f"--- a/{target_file}\n+++ b/{target_file}\n@@ -1,3 +1,3 @@\n export const Component = () => {{\n-  return <img className=\"hero-logo\" src=\"/logo.png\" />;\n+  return <img className=\"hero-logo\" src=\"/logo.png\" alt=\"Accessibility hero logo\" />;\n }};"
            
            parsed = {
                "files_changed": [target_file],
                "unified_diff": diff,
                "rationale": f"Added mock patch to {target_file} based on source context."
            }
            logger.warning(f"MockProvider generated a fake patch for {target_file}. Real LLM is required for valid fixes.")
        # Generate intelligent mock response tailored to rule
        elif "color-contrast" in rule_id.lower():

            parsed = {
                "title": "Enhance text contrast ratio to WCAG 2.1 AA (4.5:1)",
                "explanation": "The current text color provides insufficient contrast against its background, degrading readability for low-vision users.",
                "rootCause": "Contrast ratio 2.1:1 fails minimum 4.5:1 threshold.",
                "suggestedBefore": "<p style=\"color: #999;\">Low contrast caption</p>",
                "suggestedAfter": "<p style=\"color: #111827;\">High contrast caption</p>",
                "confidence": 0.95,
                "requiresManualReview": False,
                "validationSteps": ["Inspect in dev tools", "Verify 4.5:1 ratio with color picker"],
                "wcagLink": "https://www.w3.org/WAI/WCAG21/quickref/#contrast-minimum"
            }
        elif "image-alt" in rule_id.lower() or "alt" in rule_id.lower():
            parsed = {
                "title": "Add descriptive alternate text to image",
                "explanation": "Images without alt text cannot be communicated to screen reader users.",
                "rootCause": "Missing alt attribute on informative image.",
                "suggestedBefore": "<img src=\"hero.jpg\">",
                "suggestedAfter": "<img src=\"hero.jpg\" alt=\"CodeLoom dashboard overview showing scan metrics\">",
                "confidence": 0.92,
                "requiresManualReview": True,
                "validationSteps": ["Verify image purpose", "Check screen reader announcement"],
                "wcagLink": "https://www.w3.org/WAI/WCAG21/quickref/#non-text-content"
            }
        else:
            parsed = {
                "title": f"Remediate {rule_id} accessibility violation",
                "explanation": f"Structural fix to satisfy WCAG guidelines for {rule_id}.",
                "rootCause": "Element lacks required accessibility markup.",
                "suggestedBefore": "<div>Clickable element</div>",
                "suggestedAfter": "<button type=\"button\" class=\"btn-primary\">Clickable element</button>",
                "confidence": 0.90,
                "requiresManualReview": False,
                "validationSteps": ["Verify keyboard focus", "Check screen reader role"],
                "wcagLink": "https://www.w3.org/WAI/WCAG21/quickref/"
            }

        content = json.dumps(parsed, indent=2)
        latency = (time.time() - start_time) * 1000.0

        return ProviderResult(
            content=content,
            parsed=parsed,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(content) // 4,
            total_tokens=(len(prompt) + len(content)) // 4,
            latency_ms=round(latency, 2),
            model_used=model or "mock-simulation-engine",
            provider_name="mock",
            estimated_cost_usd=0.0,
        )
