import asyncio
import json
import math
import re

import httpx

from core.config import settings
from core.logging import get_logger

logger = get_logger()

VARIANT_SYSTEM_PROMPTS = {
    "documentary": """You are an expert Hindi documentary writer for YouTube Shorts.

IMPORTANT RULES — Follow EVERY rule strictly:
1. NEVER invent facts, names, dates, locations, or numbers. Only use facts provided below.
2. Every claim in the script MUST be traceable to the provided facts.
3. If you don't know something from the facts, DO NOT make it up. Skip it.
4. Do NOT add imaginary places, people, or events.
5. All content MUST be factually grounded in the provided facts.
6. Do NOT repeat sentences. Each sentence must add new information.
7. Use conversational Hindi (Hinglish where natural). Keep Hindi ratio above 80%.
8. Do NOT use the topic's location name more than 2 times.
9. Use storytelling structure: curiosity hook → context → facts → ending question.
10. Do NOT write like an encyclopedia. Be engaging, conversational, and informative.

Return ONLY valid JSON with no extra text.

Schema:
{
  "title": "Hindi title (max 10 words)",
  "hook": "Opening hook (1 sentence, max 20 words)",
  "script": "Full script (60-120 words, conversational Hindi, 80%+ Hindi)",
  "estimated_duration_seconds": 55
}""",

    "mystery": """You are an expert Hindi mystery storyteller for YouTube Shorts.

IMPORTANT RULES — Follow EVERY rule strictly:
1. NEVER invent facts, names, dates, locations, or numbers. Only use facts provided below.
2. Every claim in the script MUST be traceable to the provided facts.
3. If you don't know something from the facts, DO NOT make it up. Skip it.
4. Do NOT add imaginary places, people, or events.
5. All content MUST be factually grounded in the provided facts.
6. Do NOT repeat sentences. Each sentence must add new information.
7. Use conversational Hindi (Hinglish where natural). Keep Hindi ratio above 80%.
8. Do NOT use the topic's location name more than 2 times.
9. Use storytelling structure: mystery hook → clue 1 → clue 2 → revelation ending with question.
10. Do NOT write like an encyclopedia. Be engaging, conversational, and mysterious.

Return ONLY valid JSON with no extra text.

Schema:
{
  "title": "Hindi title (max 10 words)",
  "hook": "Opening hook (1 sentence, max 20 words)",
  "script": "Full script (60-120 words, conversational Hindi, 80%+ Hindi)",
  "estimated_duration_seconds": 45
}""",

    "travel": """You are an expert Hindi travel storyteller for YouTube Shorts.

IMPORTANT RULES — Follow EVERY rule strictly:
1. NEVER invent facts, names, dates, locations, or numbers. Only use facts provided below.
2. Every claim in the script MUST be traceable to the provided facts.
3. If you don't know something from the facts, DO NOT make it up. Skip it.
4. Do NOT add imaginary places, people, or events.
5. All content MUST be factually grounded in the provided facts.
6. Do NOT repeat sentences. Each sentence must add new information.
7. Use conversational Hindi (Hinglish where natural). Keep Hindi ratio above 80%.
8. Do NOT use the topic's location name more than 2 times.
9. Use storytelling structure: exciting hook → arrival → discovery → invitation question.
10. Do NOT write like an encyclopedia. Be engaging, immersive, and conversational.

Return ONLY valid JSON with no extra text.

Schema:
{
  "title": "Hindi title (max 10 words)",
  "hook": "Opening hook (1 sentence, max 20 words)",
  "script": "Full script (60-120 words, conversational Hindi, 80%+ Hindi)",
  "estimated_duration_seconds": 55
}""",
}


class ScriptGenerator:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def generate_all(self, facts: list[str], summary: str, script_type: str = "SHORTS_60") -> list[dict]:
        variants = []
        for variant in ["documentary", "mystery", "travel"]:
            result = await self.generate(facts, summary, script_type, variant)
            metrics = self._compute_review_metrics(result, facts)
            result.update(metrics)
            result["variant"] = variant
            variants.append(result)
        return variants

    async def generate(self, facts: list[str], summary: str, script_type: str = "SHORTS_60", variant: str = "documentary") -> dict:
        prompt = self._build_prompt(facts, summary, script_type, variant)
        raw = await self._query_ollama_with_retry(prompt)
        parsed = self._parse_response(raw)
        quality_score = self._score_quality(parsed, facts)
        parsed["quality_score"] = quality_score
        return parsed

    async def _query_ollama_with_retry(self, prompt: str) -> str:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return await self._query_ollama(prompt)
            except httpx.HTTPError as e:
                last_error = e
                logger.warning("script_llm_retry", attempt=attempt + 1, error=str(e))
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        logger.error("script_llm_failed_all_retries", error=str(last_error))
        return json.dumps({
            "title": "Script generation failed",
            "hook": "",
            "script": "स्क्रिप्ट जनरेशन विफल रहा। कृपया पुनः प्रयास करें।",
            "estimated_duration_seconds": 0,
        })

    def _build_prompt(self, facts: list[str], summary: str, script_type: str, variant: str) -> str:
        facts_text = "\n".join(f"- {f}" for f in facts)
        target_duration = 60

        duration_seconds = re.search(r"SHORTS_(\d+)", script_type)
        if duration_seconds:
            target_duration = int(duration_seconds.group(1))

        return f"""Topic Summary: {summary}

Facts to use:
{facts_text}

Target duration: {target_duration} seconds.

Generate a {variant} style Hindi YouTube Shorts script following the JSON schema exactly."""

    async def _query_ollama(self, prompt: str) -> str:
        system_prompt = self._get_system_prompt(prompt)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "format": "json",
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            result = resp.json()
            return result.get("response", "{}")

    def _get_system_prompt(self, prompt: str) -> str:
        for variant_key in VARIANT_SYSTEM_PROMPTS:
            if variant_key in prompt:
                return VARIANT_SYSTEM_PROMPTS[variant_key]
        return VARIANT_SYSTEM_PROMPTS["documentary"]

    def _parse_response(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
            return {
                "title": data.get("title", ""),
                "hook": data.get("hook", ""),
                "script": data.get("script", ""),
                "estimated_duration_seconds": data.get("estimated_duration_seconds", 45),
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("script_parse_failed", raw=raw[:200], error=str(e))
            return {
                "title": "Parsing failed",
                "hook": "",
                "script": "",
                "estimated_duration_seconds": 0,
            }

    def _score_quality(self, script: dict, facts: list[str]) -> float:
        score = 40.0

        title = script.get("title", "")
        hook = script.get("hook", "")
        body = script.get("script", "")
        duration = script.get("estimated_duration_seconds", 0)

        if title and len(title) >= 5:
            score += 10.0

        if hook and len(hook) >= 10:
            score += 15.0

        word_count = len(body.split()) if body else 0
        if 60 <= word_count <= 110:
            score += 10.0
        elif 40 <= word_count < 60 or 110 < word_count <= 140:
            score += 5.0

        if 45 <= duration <= 60:
            score += 10.0
        elif 30 <= duration < 45:
            score += 5.0

        used_facts = 0
        for fact in facts:
            fact_keywords = set(fact.lower().split()[:5])
            body_lower = body.lower()
            if any(kw in body_lower for kw in fact_keywords):
                used_facts += 1

        fact_ratio = used_facts / len(facts) if facts else 0
        score += fact_ratio * 15.0

        return round(min(score, 100.0), 1)

    def _compute_review_metrics(self, script: dict, facts: list[str]) -> dict:
        body = script.get("script", "")
        title = script.get("title", "")
        hook = script.get("hook", "")

        combined = f"{title} {hook} {body}"

        hindi_vowels = len(re.findall(r"[ािीुूृेैोौंँः]", combined))
        total_chars = len(combined.strip())
        readability = round(min(100.0, (hindi_vowels / max(total_chars, 1)) * 200), 1)

        questions = len(re.findall(r"[?？]", combined))
        exclamations = len(re.findall(r"[!！]", combined))
        emotional_words = len(re.findall(r"(अद्भुत|गजब|शानदार|हैरत|रहस्य|अनोखा|बेहतरीन|खोज|चौंकाने|कमाल|लाजवाब|दिलचस्प)", combined))
        engagement = round(min(100.0, (questions * 15 + exclamations * 10 + emotional_words * 8)), 1)

        location_repeats = len(re.findall(r"(अजंता|एलोरा|लोनार|हम्पी|पेट्रा|महाराष्ट्र|कर्नाटक|जॉर्डन)", combined))
        repetition_penalty = min(location_repeats * 5, 40)
        repetition = round(max(0.0, 100.0 - repetition_penalty), 1)

        return {
            "readability_score": readability,
            "engagement_score": engagement,
            "repetition_score": repetition,
        }
