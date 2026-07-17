import copy

from core.logging import get_logger
from services.quality.fact_validator import run_fact_validation
from services.quality.language_validator import run_language_validation
from services.quality.location_validator import run_location_validation, build_whitelist
from services.quality.repetition_validator import run_repetition_validation
from services.quality.story_validator import run_story_validation
from services.script.generator import ScriptGenerator

logger = get_logger()

MAX_REGENERATION_ATTEMPTS = 2


def run_all_validators(
    script_text: str,
    title: str = "",
    hook: str = "",
    facts: list[str] | None = None,
    summary: str = "",
    topic_name: str = "",
    country: str | None = None,
    research_data: dict | None = None,
) -> dict:
    facts = facts or []
    results = {}

    fact_result = run_fact_validation(script_text, facts, summary)
    results.update(fact_result)

    loc_result = run_location_validation(script_text, topic_name, country, research_data)
    results.update(loc_result)

    rep_result = run_repetition_validation(script_text)
    results.update(rep_result)

    lang_result = run_language_validation(script_text)
    results.update(lang_result)

    story_result = run_story_validation(title, hook, script_text)
    results.update(story_result)

    return results


def validation_passed(validation_results: dict) -> bool:
    checks = ["fact_grounding", "location_accuracy", "repetition_check", "language_check", "story_structure"]
    for check in checks:
        if not validation_results.get(check, {}).get("is_valid", True):
            logger.warning("content_gate_validation_failed", check=check)
            return False
    return True


def aggregate_scores(validation_results: dict) -> dict:
    hallucination_score = validation_results.get("fact_grounding", {}).get("hallucination_score", 0.0)
    grounding_score = validation_results.get("fact_grounding", {}).get("grounding_score", 100.0)
    story_score = validation_results.get("story_structure", {}).get("structure_score", 0.0)
    language_score = validation_results.get("language_check", {}).get("confidence", 0.0)
    return {
        "hallucination_score": hallucination_score,
        "grounding_score": grounding_score,
        "story_score": story_score,
        "language_score": language_score,
    }


async def validate_and_regenerate_variant(
    facts: list[str],
    summary: str,
    script_type: str,
    variant_name: str,
    topic_name: str,
    country: str | None = None,
    research_data: dict | None = None,
) -> dict:
    generator = ScriptGenerator()
    best_result = None
    best_grounding = -1.0

    for attempt in range(MAX_REGENERATION_ATTEMPTS):
        logger.info("content_gate_attempt", variant=variant_name, attempt=attempt + 1)
        result = await generator.generate(facts, summary, script_type, variant_name)
        metrics = generator._compute_review_metrics(result, facts)
        result.update(metrics)
        result["variant"] = variant_name

        script_text = result.get("script", "")
        title = result.get("title", "")
        hook = result.get("hook", "")

        validation = run_all_validators(
            script_text=script_text,
            title=title,
            hook=hook,
            facts=facts,
            summary=summary,
            topic_name=topic_name,
            country=country,
            research_data=research_data,
        )

        scores = aggregate_scores(validation)
        result.update(scores)
        result["validation_passed"] = validation_passed(validation)
        result["validation_report"] = copy.deepcopy(validation)
        result["generation_attempts"] = attempt + 1

        if result["validation_passed"]:
            result["script_status"] = "completed"
            logger.info("content_gate_passed", variant=variant_name, attempt=attempt + 1)
            return result

        grounding = scores.get("grounding_score", 0)
        if grounding >= best_grounding:
            best_grounding = grounding
            best_result = copy.deepcopy(result)

    logger.warning("content_gate_all_failed", variant=variant_name, max_attempts=MAX_REGENERATION_ATTEMPTS)
    if best_result:
        best_result["validation_passed"] = False
        best_result["script_status"] = "failed"
        return best_result

    return {
        "title": "Generation failed",
        "hook": "",
        "script": "",
        "estimated_duration_seconds": 0,
        "variant": variant_name,
        "quality_score": 0.0,
        "readability_score": 0.0,
        "engagement_score": 0.0,
        "repetition_score": 0.0,
        "hallucination_score": 100.0,
        "grounding_score": 0.0,
        "story_score": 0.0,
        "language_score": 0.0,
        "validation_passed": False,
        "validation_report": {},
        "generation_attempts": MAX_REGENERATION_ATTEMPTS,
        "script_status": "failed",
    }
