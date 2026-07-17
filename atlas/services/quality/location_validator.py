import re
import unicodedata

from core.logging import get_logger

logger = get_logger()


KNOWN_PLACE_PATTERNS = [
    r"(?:में स्थित|पर स्थित|में मिलता|पर मिलता|में पाया|पर पाया|में बसा|पर बसा)\s*([\w\s]+?)(?:\s*(?:है|था|थी|थे|गया|गई|गए)[\s।!?])",
    r"(?:के|की|से)\s*([\w\s]+?)\s*(?:में|पर|के पास|के करीब)\s",
]

INDIAN_STATES = [
    "आंध्र प्रदेश", "अरुणाचल प्रदेश", "असम", "बिहार", "छत्तीसगढ़", "गोवा", "गुजरात",
    "हरियाणा", "हिमाचल प्रदेश", "झारखंड", "कर्नाटक", "केरल", "मध्य प्रदेश", "महाराष्ट्र",
    "मणिपुर", "मेघालय", "मिजोरम", "नागालैंड", "ओडिशा", "पंजाब", "राजस्थान", "सिक्किम",
    "तमिल नाडु", "तेलंगाना", "त्रिपुरा", "उत्तर प्रदेश", "उत्तराखंड", "पश्चिम बंगाल",
    "अंडमान", "लक्षद्वीप", "दिल्ली", "चंडीगढ़", "पुडुचेरी", "दादरा", "दमन", "कश्मीर",
    "लद्दाख",
]

COUNTRIES_HINDI = [
    "भारत", "इंडिया", "नेपाल", "चीन", "पाकिस्तान", "बांग्लादेश", "श्रीलंका", "जापान",
    "अमेरिका", "यूरोप", "जॉर्डन", "ईरान", "इराक", "मिस्र", "ग्रीस", "इटली", "फ्रांस",
    "जर्मनी", "ब्रिटेन", "रूस", "ऑस्ट्रेलिया", "कंबोडिया", "पेरू", "बोलीविया",
    "मेक्सिको", "तुर्की", "दुबई", "सिंगापुर", "मलेशिया", "थाईलैंड",
]


WORD_SPLIT = re.compile(r"[\s।!?？,\.\;]+")


def _whole_word_in_text(word: str, text: str) -> bool:
    word_lower = word.lower()
    tokens = WORD_SPLIT.split(text)
    if word_lower in tokens:
        return True
    word_tokens = WORD_SPLIT.split(word_lower)
    if len(word_tokens) > 1:
        for i in range(len(tokens) - len(word_tokens) + 1):
            if tokens[i:i + len(word_tokens)] == word_tokens:
                return True
    return False


def extract_locations(text: str) -> list[str]:
    text_lower = unicodedata.normalize("NFKC", text.lower())
    found = set()

    for state in INDIAN_STATES:
        if _whole_word_in_text(state, text_lower):
            found.add(state)

    for country in COUNTRIES_HINDI:
        if _whole_word_in_text(country, text_lower):
            found.add(country)

    for pattern in KNOWN_PLACE_PATTERNS:
        matches = re.findall(pattern, text_lower)
        for m in matches:
            candidate = m.strip()
            if len(candidate) > 2 and candidate not in found:
                found.add(candidate)

    return sorted(found)


def build_whitelist(topic_name: str, country: str | None, research_data: dict | None = None) -> set[str]:
    whitelist = set()
    whitelist.add(topic_name.lower())

    if country:
        whitelist.add(country.lower())
        for c in COUNTRIES_HINDI:
            if c.lower() == country.lower() or country.lower() in c.lower():
                whitelist.add(c.lower())

    if country and country.lower() == "india":
        for state in INDIAN_STATES:
            whitelist.add(state.lower())
    else:
        for state in INDIAN_STATES:
            if state.lower() in topic_name.lower() or (country and state.lower() in country.lower()):
                whitelist.add(state.lower())

    if research_data:
        wd = research_data.get("wikidata", {}) if isinstance(research_data, dict) else {}
        if isinstance(wd, dict):
            coords = wd.get("coordinates")
            if coords:
                whitelist.add(f"lat:{coords.get('latitude', '')}")
                whitelist.add(f"lon:{coords.get('longitude', '')}")
            loc = wd.get("location")
            if loc and isinstance(loc, str):
                whitelist.add(loc.lower())

    return whitelist


def run_location_validation(script_text: str, topic_name: str, country: str | None, research_data: dict | None = None) -> dict:
    locations_found = extract_locations(script_text)
    whitelist = build_whitelist(topic_name, country, research_data)

    violations = []
    hallucinated = []
    validated = 0

    for loc in locations_found:
        loc_lower = loc.lower()
        if loc_lower in whitelist or topic_name.lower() in loc_lower or loc_lower in topic_name.lower():
            validated += 1
        else:
            hallucinated.append(loc)
            violations.append({
                "location": loc,
                "expected": f"within {topic_name} ({country or 'unknown'})",
                "details": f"Location '{loc}' not found in topic whitelist",
            })

    is_valid = len(hallucinated) == 0
    total = len(locations_found)
    confidence = round(100.0 - (len(hallucinated) / max(total, 1)) * 100, 1)

    return {
        "location_accuracy": {
            "is_valid": is_valid,
            "confidence": confidence,
            "violations": violations,
            "locations_found": locations_found,
            "locations_validated": validated,
            "hallucinated_locations": hallucinated,
        }
    }
