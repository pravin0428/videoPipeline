import re
import unicodedata

from core.logging import get_logger

logger = get_logger()

NUMERIC_PATTERN = re.compile(r"\d+(?:\.\d+)?")


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text.strip().lower())


def extract_numbers_all(text: str) -> set[str]:
    return set(NUMERIC_PATTERN.findall(text))


def extract_key_proper_nouns(text: str) -> list[str]:
    """Extract capitalized words or transliterated names from English text."""
    words = re.findall(r"[A-Z][a-z]+", text)
    return [w.lower() for w in words if len(w) > 2]


def check_numbers_in_sentence(sentence: str, fact_numbers: set[str]) -> bool:
    nums = extract_numbers_all(sentence)
    if not nums:
        return True
    for n in nums:
        if n not in fact_numbers:
            logger.debug("fact_number_unverified", number=n)
            return False
    return True


def check_proper_nouns_in_sentence(sentence: str, proper_nouns: list[str]) -> bool:
    sent_lower = normalize_text(sentence)
    for pn in proper_nouns:
        if pn in sent_lower:
            return True
    return False


def check_claim_against_facts(sentence: str, facts: list[str], summary: str = "") -> dict:
    all_text = " ".join(facts) + " " + summary
    fact_numbers = extract_numbers_all(all_text)
    proper_nouns = extract_key_proper_nouns(all_text)

    sentence_nums = extract_numbers_all(sentence)
    nums_ok = check_numbers_in_sentence(sentence, fact_numbers)
    pn_found = check_proper_nouns_in_sentence(sentence, proper_nouns)

    has_fact_keyword = False
    for fact in facts:
        fact_lower = normalize_text(fact)
        for token in fact_lower.split():
            if len(token) > 3 and token in normalize_text(sentence):
                has_fact_keyword = True
                break
        if has_fact_keyword:
            break

    if not sentence_nums and not has_fact_keyword and not pn_found:
        return {"supported": True, "score": 1.0, "detail": "no specific claims to verify"}

    if not nums_ok:
        return {"supported": False, "score": 0.0, "detail": "numbers in script not found in facts"}

    if has_fact_keyword or pn_found:
        return {"supported": True, "score": 0.8, "detail": "keywords/proper nouns match facts"}

    if sentence_nums:
        return {"supported": True, "score": 0.6, "detail": "numbers match facts"}

    return {"supported": False, "score": 0.0, "detail": "no verification possible"}


def run_fact_validation(script_text: str, facts: list[str], summary: str = "") -> dict:
    sentences = [s.strip() for s in re.split(r"[।!?？\n]+", script_text) if s.strip() and len(s.strip()) > 5]

    violations = []
    supported_count = 0
    unsupported_count = 0

    for sent in sentences:
        result = check_claim_against_facts(sent, facts, summary)
        if result["supported"]:
            supported_count += 1
        else:
            unsupported_count += 1
            violations.append({
                "claim": sent[:100],
                "severity": "high",
                "details": f"Unverified claim: numbers in script not found in source facts. {result.get('detail', '')}",
            })

    total = supported_count + unsupported_count
    grounding_score = round((supported_count / max(total, 1)) * 100, 1)
    hallucination_score = round(100.0 - grounding_score, 1)

    is_valid = hallucination_score < 40.0
    confidence = round(max(0.0, 100.0 - hallucination_score * 1.5), 1)

    return {
        "fact_grounding": {
            "is_valid": is_valid,
            "confidence": confidence,
            "hallucination_score": hallucination_score,
            "grounding_score": grounding_score,
            "violations": violations,
            "supported_claims": supported_count,
            "unsupported_claims": unsupported_count,
            "total_claims_checked": total,
        }
    }
