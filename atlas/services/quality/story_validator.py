import re
import unicodedata

from core.logging import get_logger

logger = get_logger()

CURIOSITY_MARKERS = [
    "क्या आप", "जानते हैं", "जानती हैं", "पता है", "सोचिए", "सोचो",
    "हैरत", "अद्भुत", "गजब", "रहस्य", "अनोखा", "कमाल",
    "आखिर", "क्यों", "कैसे", "कहां", "कब",
    "नहीं", "होगा", "होगी", "होंगे", "सकता", "सकती", "सकते",
    "देखना", "सुनना", "जानना", "समझना",
    "बताइए", "बताओ", "क्या हो", "क्या है",
    "तैयार हैं", "जानना चाहते",
]

HOOK_MARKERS = [
    "क्या आप", "जानते हैं", "हैरत", "गजब", "अद्भुत", "कल्पना",
    "सोचिए", "सोचो", "कभी", "आज", "देखिए",
    "रहस्य", "आकर्षित", "अनोखा", "हैरतंगेज", "कमाल",
]

FACT_MARKERS = [
    "साल", "वर्ष", "शताब्दी", "मीटर", "किलोमीटर",
    "लाख", "करोड़", "अरब", "%", "प्रतिशत",
    "ईसा", "बी॰सी॰", "बीसी", "एडी", "ई॰",
    "किमी", "°", "डिग्री",
]


def run_story_validation(title: str, hook: str, script_text: str) -> dict:
    combined = f"{title} {hook} {script_text}"
    combined_lower = unicodedata.normalize("NFKC", combined.lower())

    sentences = [s.strip() for s in re.split(r"[।!?？\n]+", script_text) if s.strip() and len(s.strip()) > 5]

    elements_found = {
        "hook": False,
        "context": False,
        "fact_section": False,
        "curiosity_ending": False,
    }
    violations = []

    if hook and len(hook) > 5:
        hook_lower = unicodedata.normalize("NFKC", hook.lower())
        is_hook = any(marker in hook_lower for marker in HOOK_MARKERS) or "?" in hook
        if is_hook:
            elements_found["hook"] = True
        else:
            violations.append({
                "element": "hook",
                "details": f"Hook present but may not be engaging: '{hook[:60]}'",
            })
    else:
        violations.append({
            "element": "hook",
            "details": "No hook found",
        })

    if len(sentences) >= 2:
        elements_found["context"] = True

    if len(sentences) >= 3:
        fact_sentences = 0
        for sent in sentences:
            sent_lower = unicodedata.normalize("NFKC", sent.lower())
            if any(marker in sent_lower for marker in FACT_MARKERS):
                fact_sentences += 1
        if fact_sentences >= 1:
            elements_found["fact_section"] = True
        else:
            violations.append({
                "element": "fact_section",
                "details": "No fact sentences found (dates, measurements, statistics)",
            })
    else:
        violations.append({
            "element": "fact_section",
            "details": f"Only {len(sentences)} sentences, need at least 3 for proper structure",
        })

    if sentences:
        last_sent = unicodedata.normalize("NFKC", sentences[-1].lower())
        is_curiosity = any(marker in last_sent for marker in CURIOSITY_MARKERS) or "?" in last_sent
        if is_curiosity:
            elements_found["curiosity_ending"] = True
        else:
            violations.append({
                "element": "curiosity_ending",
                "details": f"Last sentence may not engage curiosity: '{sentences[-1][:60]}'",
            })
    else:
        violations.append({
            "element": "curiosity_ending",
            "details": "No sentences to evaluate",
        })

    found_count = sum(1 for v in elements_found.values() if v)
    structure_score = round((found_count / 4) * 100, 1)

    is_valid = found_count >= 3
    confidence = round(structure_score, 1)

    return {
        "story_structure": {
            "is_valid": is_valid,
            "confidence": confidence,
            "violations": violations,
            "elements_found": elements_found,
            "structure_score": structure_score,
        }
    }
