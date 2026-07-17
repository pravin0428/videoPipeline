"""
MediaMatcher: Decision tree that maps SentenceFeatures to the best MediaType.
Prioritizes educational clarity > visual storytelling > viewer retention.
"""
from ..models import MediaType, SentenceFeatures, FALLBACK_CHAINS


class MediaMatcher:
    """Maps sentence features to the optimal media type using a decision tree."""

    def match(self, features: SentenceFeatures) -> tuple[MediaType, float, str]:
        text = features.text.lower()

        # ═══════════════════════════════════════════════════════════
        # PRIORITY 1: Educational Clarity
        # ═══════════════════════════════════════════════════════════

        # ── MAP: named place + direction/boundaries OR explicit geographic framing ──
        has_geo_framing = any(w in text for w in
            {"located", "situated", "region of", "province of", "state of",
             "borders", "lies in", "nestled", "flows", "flowing",
             "travel from", "travels from", "traveling from",
             "flew from", "migrate from", "migrates from"})

        if (features.has_named_place or has_geo_framing) and \
           (features.has_direction or features.has_boundaries):
            return (MediaType.MAP, 0.90,
                    f"Named place with geographic direction — map establishes "
                    f"spatial context for educational grounding.")

        # ── INFOGRAPHIC: statistics, data, comparisons ──
        # Check BEFORE weak MAP (named place alone) — data needs visualization
        if features.has_statistics or (features.has_numbers and features.has_comparison):
            nums = features.numbers_found[:3]
            return (MediaType.INFOGRAPHIC, 0.85,
                    f"Statistical data ({', '.join(nums)}) — infographic makes "
                    f"numbers comprehensible at a glance.")

        if features.has_named_place and not features.has_movement and \
           not features.has_concrete_visual:
            return (MediaType.MAP, 0.80,
                    f"Named place introduced — map provides geographic "
                    f"orientation before moving to visuals.")

        # ── SCIENTIFIC ANIMATION: process, mechanism, cause-effect ──
        if features.has_process and features.has_cause_effect:
            return (MediaType.SCIENTIFIC_ANIMATION, 0.90,
                    f"Process with cause-effect relationships — animation "
                    f"reveals the underlying mechanism.")

        if features.has_process and features.has_steps:
            return (MediaType.SCIENTIFIC_ANIMATION, 0.85,
                    f"Multi-step process described — animation shows "
                    f"each stage in sequence.")

        if (features.has_biological_ref or features.has_geological_ref) and \
           features.has_process:
            return (MediaType.SCIENTIFIC_ANIMATION, 0.80,
                    f"Scientific subject with process — animation explains "
                    f"the mechanism visually.")

        if features.has_natural_phenomenon and features.has_cause_effect:
            return (MediaType.SCIENTIFIC_ANIMATION, 0.80,
                    f"Natural phenomenon with causal explanation — "
                    f"animation reveals invisible forces.")

        # ═══════════════════════════════════════════════════════════
        # PRIORITY 2: Visual Storytelling
        # ═══════════════════════════════════════════════════════════

        # ── MAP (weak): explicit geo-framing without named place or direction ──
        if has_geo_framing and not features.has_concrete_visual:
            return (MediaType.MAP, 0.65,
                    f"Geographic framing detected — map provides context.")

        # ── STOCK VIDEO: concrete scene with movement ──
        if features.has_concrete_visual and features.has_movement \
           and not features.has_abstract_concept:
            return (MediaType.STOCK_VIDEO, 0.85,
                    f"Concrete visual scene with movement — stock video "
                    f"provides immersive realism for documentary.")

        # ── STOCK VIDEO: concrete scene with rich sensory detail ──
        if features.has_concrete_visual and features.has_sensory_detail:
            return (MediaType.STOCK_VIDEO, 0.75,
                    f"Rich sensory detail in a concrete scene — stock video "
                    f"captures the atmosphere better than other media.")

        # ── STOCK PHOTO: concrete but static ──
        if features.has_concrete_visual and not features.has_movement:
            return (MediaType.STOCK_PHOTO, 0.70,
                    f"Concrete but static scene — high-quality photo with "
                    f"Ken Burns pan creates visual interest without requiring "
                    f"motion that doesn't exist.")

        # ═══════════════════════════════════════════════════════════
        # PRIORITY 3: Abstract / Intangible
        # ═══════════════════════════════════════════════════════════

        # ── AI VIDEO: abstract concepts without concrete reference ──
        if features.has_abstract_concept and not features.has_concrete_visual:
            return (MediaType.AI_VIDEO, 0.65,
                    f"Abstract concept with no visual reference — AI generation "
                    f"can visualize the intangible.")

        # ── AI VIDEO: ritual/emotion without concrete scene ──
        if features.has_emotion and not features.has_concrete_visual:
            return (MediaType.AI_VIDEO, 0.55,
                    f"Emotion-driven content without concrete scene — "
                    f"AI video can evoke the feeling through atmospheric imagery.")

        # ═══════════════════════════════════════════════════════════
        # PRIORITY 4: Default fallbacks
        # ═══════════════════════════════════════════════════════════

        # Historical + architecture → archival photo
        if features.has_historical_ref and features.has_architectural_ref:
            return (MediaType.STOCK_PHOTO, 0.65,
                    f"Historical architecture — archival photo with "
                    f"Ken Burns evokes the period atmosphere.")

        # MAP (very weak): any location mention without stronger signal
        if features.has_location and not features.has_concrete_visual \
           and not features.has_movement:
            return (MediaType.MAP, 0.55,
                    f"Location mentioned without strong visual — "
                    f"map provides geographic reference.")

        # Catch-all: stock video (most versatile for documentary)
        return (MediaType.STOCK_VIDEO, 0.50,
                "General documentary narration — stock video provides "
                "versatile visual support for the spoken content.")

    def get_fallback_order(self, media_type: MediaType) -> list[MediaType]:
        return FALLBACK_CHAINS.get(media_type, list(MediaType))
