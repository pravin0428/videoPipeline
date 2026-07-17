from typing import Optional
from ..models import MediaType, SentenceFeatures, CAMERA_STYLES
from ..analyzers import sentence_analyzer as sa


class PromptBuilder:

    def build_for(
        self,
        sentence: str,
        features: SentenceFeatures,
        media_type: MediaType,
    ) -> dict:
        return {
            "search_prompt": self._build_search_prompt(sentence, features, media_type),
            "generation_prompt": self._build_generation_prompt(sentence, features, media_type),
            "negative_prompt": self._build_negative_prompt(media_type),
            "quality_criteria": self._build_quality_criteria(media_type, features),
            "camera_style": self._select_camera_style(features),
            "visual_goal": self._build_visual_goal(sentence, features, media_type),
            "visual_elements": self._extract_visual_elements(features),
            "suggested_duration": self._suggest_duration(sentence, features, media_type),
        }

    def _build_search_prompt(
        self, sentence: str, features: SentenceFeatures, media_type: MediaType
    ) -> str:
        parts = []
        nouns = features.key_nouns[:5]
        if nouns:
            parts.extend(n.lower() for n in nouns)
        if features.location_terms:
            parts.append(features.location_terms[0].lower())
        adjs = features.key_adjectives[:2]
        if adjs:
            parts = adjs + parts
        if features.has_historical_ref:
            parts.append("ancient")
        if features.has_natural_phenomenon:
            parts.append("nature")

        if media_type == MediaType.MAP:
            loc = features.location_terms[0] if features.location_terms else "world"
            return f"{loc} map geography topography"

        if media_type == MediaType.INFOGRAPHIC:
            top_nouns = [n for n in features.key_nouns[:3] if n.lower() not in {"india", "world"}]
            subject = top_nouns[0] if top_nouns else "data"
            return f"{subject} infographic chart data visualization statistics"

        if media_type == MediaType.SCIENTIFIC_ANIMATION:
            top_nouns = features.key_nouns[:3]
            if top_nouns:
                return f"{' '.join(top_nouns)} science nature process"
            return "science nature time lapse"

        query = " ".join(parts[:6]) if parts else " ".join(sentence.split()[:6])
        query = " ".join(query.split()[:8])
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "in", "on",
            "at", "to", "for", "of", "with", "by", "from", "as", "and",
            "or", "but", "its", "their", "this", "that", "these", "those",
        }
        query = " ".join(w for w in query.split() if w.lower() not in stop_words)
        return query.strip()

    def _build_generation_prompt(
        self, sentence: str, features: SentenceFeatures, media_type: MediaType
    ) -> str:
        camera = self._select_camera_style(features)
        mood = self._detect_mood(features)
        subject = self._extract_subject(features)
        setting = self._extract_setting(features)

        if media_type == MediaType.AI_VIDEO:
            prompt_parts = [
                f"Cinematic {mood} shot of {subject}",
                f"Set in {setting}" if setting else "",
                camera,
                "Cinematic lighting, atmospheric, documentary quality",
                "National Geographic style, 4K, shallow depth of field",
                "Slow camera movement, professional composition",
            ]
        elif media_type == MediaType.SCIENTIFIC_ANIMATION:
            prompt_parts = [
                f"Scientific visualization of {subject}",
                "Educational animation style, clean graphics",
                "Smooth motion, labeled elements, clear visual hierarchy",
                "Blue and teal color scheme, professional scientific illustration",
            ]
        elif media_type == MediaType.INFOGRAPHIC:
            prompt_parts = [
                f"Clean infographic visualization of {subject}",
                "Modern data visualization style, clear typography",
                "Minimalist design, professional color palette",
                "Suitable for documentary, educational context",
            ]
        elif media_type == MediaType.MAP:
            prompt_parts = [
                f"Geographic map of {subject}" if subject else "Geographic map",
                "Topographic style with elevation detail" if features.has_geological_ref
                else "Political map with clear boundaries",
                "Professional cartography, documentary quality",
            ]
        else:
            prompt_parts = [
                f"Cinematic documentary shot of {subject}" if subject else "Cinematic documentary shot",
                f"In {setting}" if setting else "",
                camera,
                "Natural lighting, realistic textures, authentic atmosphere",
                "National Geographic documentary quality, 4K resolution",
            ]

        return " | ".join(p for p in prompt_parts if p)

    def _build_negative_prompt(self, media_type: MediaType) -> str:
        negatives = {
            MediaType.AI_VIDEO: (
                "blurry, low quality, distorted, ugly, deformed, watermark, "
                "text, signature, cartoon, anime, oversaturated, unrealistic, "
                "artifacts, glitch, noise, grainy, dark, underexposed"
            ),
            MediaType.SCIENTIFIC_ANIMATION: (
                "text, watermark, low quality, blurry, cartoon, childish, "
                "oversimplified, incorrect, misleading, noisy"
            ),
            MediaType.INFOGRAPHIC: (
                "cluttered, messy, hard to read, small text, low contrast, "
                "ugly colors, blurry, low resolution, watermarked"
            ),
            MediaType.MAP: (
                "inaccurate, cartoony, childish, low resolution, blurry, "
                "watermark, text, labels"
            ),
            MediaType.STOCK_VIDEO: (
                "watermark, text, logo, blurry, low quality, shaky, "
                "overexposed, underexposed"
            ),
            MediaType.STOCK_PHOTO: (
                "watermark, text, logo, blurry, low resolution, "
                "overexposed, underexposed"
            ),
        }
        return negatives.get(media_type, "low quality, blurry, watermark, text")

    def _build_quality_criteria(
        self, media_type: MediaType, features: SentenceFeatures
    ) -> list[str]:
        criteria = {
            MediaType.MAP: [
                "Clearly shows the geographic location",
                "Legible boundaries and labels",
                "Matches the described region",
                "Suitable for documentary context",
            ],
            MediaType.INFOGRAPHIC: [
                "Data is clearly visualized",
                "Easy to read at a glance",
                "Professional design aesthetic",
                "Matches educational tone",
            ],
            MediaType.SCIENTIFIC_ANIMATION: [
                "Accurately represents the process",
                "Clear visual explanation",
                "Smooth animation",
                "Professionally styled",
            ],
            MediaType.STOCK_VIDEO: [
                "Matches the described scene",
                "Smooth motion, no shakiness",
                "Cinematic quality",
                "Authentic, not staged-looking",
                "Good lighting and composition",
            ],
            MediaType.STOCK_PHOTO: [
                "High resolution",
                "Matches the described scene",
                "Good composition for Ken Burns pan",
                "Cinematic lighting",
            ],
            MediaType.AI_VIDEO: [
                "Visually coherent frames",
                "Matches the described mood",
                "Minimal artifacts or distortion",
                "Cinematic quality",
                "Realistic enough for documentary",
            ],
        }
        return criteria.get(media_type, ["Matches the narration context"])

    def _select_camera_style(self, features: SentenceFeatures) -> str:
        if features.has_emotion and features.has_sensory_detail:
            return CAMERA_STYLES["awe"]
        if features.has_abstract_concept:
            return CAMERA_STYLES["wonder"]
        if features.has_historical_ref:
            return CAMERA_STYLES["historical"]
        if features.has_scale:
            return CAMERA_STYLES["epic"]
        if features.has_architectural_ref:
            return CAMERA_STYLES["educational"]
        if features.has_cultural_ref or features.has_ritual:
            return CAMERA_STYLES["intimate"]
        return CAMERA_STYLES["neutral"]

    def _build_visual_goal(
        self, sentence: str, features: SentenceFeatures, media_type: MediaType
    ) -> str:
        dq = features.dominant_quality
        goals = {
            "location": "Establish geographic context for the viewer",
            "data": "Make the statistic comprehensible at a glance",
            "process": "Reveal the mechanism behind the phenomenon",
            "visual": "Immerse the viewer in the described scene",
            "abstract": "Visualize an intangible concept",
            "historical": "Evoke the atmosphere of the historical period",
            "science": "Explain the scientific principle visually",
            "cultural": "Showcase the cultural practice or artifact",
        }
        return goals.get(dq, "Support the narration with relevant visuals")

    def _extract_visual_elements(self, features: SentenceFeatures) -> list[str]:
        elements = []
        for noun in features.key_nouns:
            if noun.lower() in sa.CONCRETE_VISUAL_NOUNS:
                elements.append(noun)
        if features.location_terms:
            elements.append(f"Location: {features.location_terms[0]}")
        if features.key_adjectives:
            elements.append(f"Mood: {features.key_adjectives[0]}")
        return elements[:8]

    def _suggest_duration(
        self, sentence: str, features: SentenceFeatures, media_type: MediaType
    ) -> float:
        word_count = len(sentence.split())
        if media_type in (MediaType.MAP, MediaType.INFOGRAPHIC):
            return max(6.0, word_count * 0.3)
        if media_type == MediaType.SCIENTIFIC_ANIMATION:
            return max(8.0, word_count * 0.4)
        if media_type == MediaType.AI_VIDEO:
            return max(5.0, word_count * 0.3)
        return min(max(4.0, word_count * 0.2), 6.0)

    def _detect_mood(self, features: SentenceFeatures) -> str:
        if features.has_emotion:
            return "atmospheric"
        if features.has_historical_ref:
            return "period-evoking"
        if features.has_natural_phenomenon:
            return "natural"
        if features.has_abstract_concept:
            return "contemplative"
        return "documentary"

    def _extract_subject(self, features: SentenceFeatures) -> str:
        candidates = []
        for noun in features.key_nouns:
            if noun.lower() in sa.CONCRETE_VISUAL_NOUNS:
                candidates.append(noun)
        if features.location_terms:
            candidates.append(features.location_terms[0])
        if candidates:
            return ", ".join(candidates[:3])
        return "the described subject"

    def _extract_setting(self, features: SentenceFeatures) -> str:
        parts = []
        if features.key_adjectives:
            parts.extend(features.key_adjectives[:2])
        if features.location_terms:
            parts.extend(features.location_terms[:2])
        return ", ".join(parts) if parts else ""
