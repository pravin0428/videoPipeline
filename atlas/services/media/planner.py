import re

from core.logging import get_logger
from services.media.providers.base import MediaPlan

logger = get_logger()

GEOGRAPHY_KEYWORDS = [
    "जिला", "district", "राज्य", "state", "प्रदेश", "देश", "country",
    "मानचित्र", "map", "स्थित", "located", "उत्तर", "दक्षिण", "पूर्व", "पश्चिम",
    "north", "south", "east", "west", "सीमा", "border", "क्षेत्र", "region",
]

POPULATION_KEYWORDS = [
    "जनसंख्या", "population", "लोग", "people", "निवासी", "residents",
    "करोड़", "million", "अरब", "billion", "हज़ार", "thousand",
]

DATA_KEYWORDS = [
    "किमी", "km", "मीटर", "meter", "feet", "फीट", "height", "ऊँचाई",
    "distance", "दूरी", "लंबाई", "length", "गहराई", "depth",
    "प्रतिशत", "percent", "संख्या", "number",
]

SCIENCE_KEYWORDS = [
    "फंगस", "fungus", "गुरुत्वाकर्षण", "gravity", "ज्वालामुखी", "volcano",
    "सौर", "solar", "डीएनए", "DNA", "जड़", "root", "roots",
    "नेटवर्क", "network", "सूक्ष्म", "micro", "कोशिका", "cell",
    "परमाणु", "atom", "ग्रह", "planet", "तारा", "star",
    "विकास", "evolution", "जीवाश्म", "fossil", "जलवायु", "climate",
]

HISTORY_KEYWORDS = [
    "इतिहास", "history", "प्राचीन", "ancient", "साल पहले", "years ago",
    "शताब्दी", "century", "साम्राज्य", "empire", "राजा", "king",
    "रानी", "queen", "युद्ध", "war", "क्रांति", "revolution",
]

UNDERGROUND_KEYWORDS = [
    "नीचे", "underground", "जड़", "root", "गुफा", "cave",
    "भूमिगत", "subterranean", "मिट्टी", "soil", "भूगर्भ", "subsurface",
]

DATE_PATTERN = re.compile(r"\d{3,4}\s*(ईसा|ई\.|बीसी|AD|BC|सन|सदी|शताब्दी)")


class MediaPlanner:
    def __init__(self):
        self._concept_pool = self._build_concept_map()

    @staticmethod
    def _build_concept_map() -> dict[str, str]:
        return {
            "population": "infographic", "जनसंख्या": "infographic",
            "percent": "infographic", "प्रतिशत": "infographic",
            "km": "infographic", "किमी": "infographic",
            "meter": "infographic", "मीटर": "infographic",
            "map": "map", "मानचित्र": "map", "district": "map",
            "जिला": "map", "state": "map", "राज्य": "map",
            "fungus": "scientific_animation", "फंगस": "scientific_animation",
            "gravity": "scientific_animation", "गुरुत्वाकर्षण": "scientific_animation",
            "volcano": "scientific_animation", "ज्वालामुखी": "scientific_animation",
            "solar": "scientific_animation", "सौर": "scientific_animation",
            "dna": "scientific_animation", "डीएनए": "scientific_animation",
            "root": "scientific_animation", "जड़": "scientific_animation",
            "cell": "scientific_animation", "कोशिका": "scientific_animation",
            "network": "scientific_animation", "नेटवर्क": "scientific_animation",
            "ancient": "historical_reconstruction", "प्राचीन": "historical_reconstruction",
            "history": "historical_reconstruction", "इतिहास": "historical_reconstruction",
            "century": "historical_reconstruction", "शताब्दी": "historical_reconstruction",
            "empire": "historical_reconstruction", "साम्राज्य": "historical_reconstruction",
            "cave": "scientific_animation", "गुफा": "scientific_animation",
            "underground": "scientific_animation", "भूमिगत": "scientific_animation",
            "river": "map", "नदी": "map",
            "mountain": "map", "पहाड़": "map",
        }

    def plan(self, scene_number: int, narration: str, visual_goal: str = "", duration: float = 6.0) -> MediaPlan:
        combined = (narration + " " + visual_goal).lower()
        text_lower = combined

        media_type, reason = self._classify(text_lower, narration)

        return MediaPlan(
            scene_number=scene_number,
            media_type=media_type,
            reason=reason,
            narrative_context=narration[:200],
            duration=duration,
        )

    def _classify(self, text_lower: str, narration: str) -> tuple[str, str]:
        if DATE_PATTERN.search(narration):
            for kw in HISTORY_KEYWORDS:
                if kw in text_lower:
                    return ("historical_reconstruction",
                            f"Historical content detected: '{kw}' in narration.")

        for kw in UNDERGROUND_KEYWORDS:
            if kw in text_lower:
                return ("scientific_animation",
                        f"Underground/root concept detected: '{kw}'. Needs scientific visualization.")

        for kw in SCIENCE_KEYWORDS:
            if kw in text_lower:
                return ("scientific_animation",
                        f"Scientific concept detected: '{kw}'. Best explained with animation.")

        for kw in GEOGRAPHY_KEYWORDS:
            if kw in text_lower:
                return ("map",
                        f"Geographic reference detected: '{kw}'. Map will orient the viewer.")

        for kw in POPULATION_KEYWORDS:
            if kw in text_lower:
                return ("infographic",
                        f"Data/numeric reference detected: '{kw}'. Infographic overlay best.")

        for kw in DATA_KEYWORDS:
            if kw in text_lower:
                return ("infographic",
                        f"Measurement reference: '{kw}'. Animated infographic suitable.")

        return ("stock_video",
                "General documentary scene. Stock video provides authentic visual context.")
