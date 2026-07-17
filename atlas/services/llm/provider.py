import asyncio
import json

import httpx

from core.config import settings
from core.logging import get_logger
from schemas.llm import LLMResponse

logger = get_logger()

SYSTEM_PROMPT = """You are a knowledge extraction engine.

Your task is to analyze the provided source data.

Rules:
1. Use ONLY provided information.
2. Never invent facts.
3. Remove duplicates.
4. Ignore speculation.
5. Extract 5-10 factual statements.
6. Create a concise summary.

Return ONLY JSON.

Schema:
{
  "summary": "",
  "facts": [""]
}"""


class LLMProvider:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def extract_knowledge(self, merged_content: dict) -> LLMResponse:
        prompt = self._build_prompt(merged_content)
        raw = await self._query_ollama_with_retry(prompt)
        return self._parse_response(raw)

    async def _query_ollama_with_retry(self, prompt: str) -> str:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return await self._query_ollama(prompt)
            except httpx.HTTPError as e:
                last_error = e
                logger.warning("llm_request_retry", attempt=attempt + 1, error=str(e))
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        logger.error("llm_request_failed_all_retries", error=str(last_error))
        return json.dumps({"summary": "LLM extraction failed.", "facts": []})

    def _build_prompt(self, content: dict) -> str:
        sections = []
        for source, data in content.items():
            if data:
                sections.append(f"=== {source.upper()} ===\n{json.dumps(data, indent=2)}")
        return "\n\n".join(sections)

    async def _query_ollama(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "stream": False,
            "format": "json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            result = resp.json()
            return result.get("response", "{}")

    def _parse_response(self, raw: str) -> LLMResponse:
        try:
            data = json.loads(raw)
            return LLMResponse(
                summary=data.get("summary", ""),
                facts=data.get("facts", []),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("llm_parse_failed", raw=raw[:200], error=str(e))
            return LLMResponse(summary="Failed to parse LLM response.", facts=[])
