import re
import unicodedata

from core.logging import get_logger

logger = get_logger()

SIMILARITY_THRESHOLD = 0.90


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text.lower())
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    raw = re.split(r"[।!?？\n]+", text)
    return [s.strip() for s in raw if len(s.strip()) > 5]


def jaccard_similarity(a: str, b: str) -> float:
    tokens_a = set(normalize_text(a).split())
    tokens_b = set(normalize_text(b).split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def run_repetition_validation(script_text: str) -> dict:
    sentences = split_sentences(script_text)

    if len(sentences) < 2:
        return {
            "repetition_check": {
                "is_valid": True,
                "confidence": 100.0,
                "violations": [],
                "total_sentences": len(sentences),
                "duplicate_pairs": 0,
                "max_similarity": 0.0,
            }
        }

    violations = []
    max_similarity = 0.0
    duplicate_pairs = 0

    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            sim = jaccard_similarity(sentences[i], sentences[j])
            if sim > max_similarity:
                max_similarity = sim
            if sim >= SIMILARITY_THRESHOLD:
                duplicate_pairs += 1
                violations.append({
                    "sentence1": sentences[i][:80],
                    "sentence2": sentences[j][:80],
                    "similarity": round(sim, 3),
                    "details": f"Sentences {i+1} and {j+1} are {sim:.1%} similar (threshold {SIMILARITY_THRESHOLD:.0%})",
                })

    is_valid = max_similarity < SIMILARITY_THRESHOLD
    confidence = round(max(0.0, 100.0 - (max_similarity * 100 - 80) * 2), 1) if max_similarity >= 0.5 else 100.0

    return {
        "repetition_check": {
            "is_valid": is_valid,
            "confidence": confidence,
            "violations": violations,
            "total_sentences": len(sentences),
            "duplicate_pairs": duplicate_pairs,
            "max_similarity": round(max_similarity, 3),
        }
    }
