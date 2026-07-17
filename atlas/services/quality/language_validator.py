import re
import unicodedata

from core.logging import get_logger

logger = get_logger()

HINDI_RATIO_THRESHOLD = 0.80

DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F\uA8E0-\uA8FF\u1CD0-\u1CFF]")
ENGLISH_PATTERN = re.compile(r"[a-zA-Z]")
HINDI_STOP_WORDS = {
    "का", "की", "के", "में", "से", "को", "पर", "है", "हैं", "था", "थी", "थे",
    "और", "या", "एक", "यह", "वह", "इस", "उस", "कि", "ने", "भी", "तक", "द्वारा",
    "लिए", "दिया", "गया", "गई", "गए", "कर", "हो", "रहा", "रही", "रहे",
    "सकता", "सकती", "सकते", "चाहिए", "बहुत", "अपने", "अपनी", "अपना",
}


def extract_english_words(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]+", text)
    return [w for w in words if len(w) > 2 and w.lower() not in {"the", "and", "for", "are", "but", "not", "you", "all", "can", "has", "was", "its", "out", "did", "get", "got", "how", "why", }]


def run_language_validation(script_text: str) -> dict:
    text = unicodedata.normalize("NFKC", script_text)

    total_chars = len(text.strip())
    hindi_chars = len(DEVANAGARI_PATTERN.findall(text))
    english_chars = len(ENGLISH_PATTERN.findall(text))

    letter_chars = hindi_chars + english_chars
    hindi_ratio = round(hindi_chars / max(letter_chars, 1), 3) if letter_chars > 0 else 0.0

    english_words = extract_english_words(text)

    violations = []
    if hindi_ratio < HINDI_RATIO_THRESHOLD:
        violations.append({
            "issue": "low_hindi_ratio",
            "details": f"Hindi ratio is {hindi_ratio:.1%} (threshold {HINDI_RATIO_THRESHOLD:.0%}). Found {len(english_words)} English words: {', '.join(english_words[:10])}",
        })

    if english_words:
        violations.append({
            "issue": "english_leakage",
            "details": f"Found {len(english_words)} English words: {', '.join(english_words[:15])}",
        })

    is_valid = hindi_ratio >= HINDI_RATIO_THRESHOLD
    confidence = round(min(100.0, (hindi_chars / max(total_chars, 1) / HINDI_RATIO_THRESHOLD) * 100), 1)

    return {
        "language_check": {
            "is_valid": is_valid,
            "confidence": confidence,
            "violations": violations,
            "hindi_ratio": hindi_ratio,
            "total_chars": total_chars,
            "hindi_chars": hindi_chars,
            "english_chars": english_chars,
            "english_words_found": english_words,
        }
    }
