"""Phase 14 — Human Director Score.

Every video receives scores for:
- Visual Storytelling
- Documentary Feel
- Visual Diversity
- Cinematic Quality
- Emotional Flow
- Educational Value
- Viewer Retention Prediction
- Overall Production Score
"""

from services.director.models import DirectorScore as DirectorScoreModel


class DirectorScoreCalculator:
    def calculate(self, video_path: str, scenes: list[dict], quality_checks: dict) -> DirectorScoreModel:
        score = DirectorScoreModel()

        checks = quality_checks.get("checks", {})

        camera_diversity_score = 0.0
        emotion_diversity_score = 0.0
        media_diversity_score = 0.0

        if "camera_diversity" in checks:
            camera_diversity_score = 1.0 if checks["camera_diversity"]["passed"] else 0.4
        if "emotional_diversity" in checks:
            emotion_diversity_score = 1.0 if checks["emotional_diversity"]["passed"] else 0.4
        if "media_diversity" in checks:
            media_diversity_score = 1.0 if checks["media_diversity"]["passed"] else 0.5

        score.visual_diversity = (camera_diversity_score + media_diversity_score) / 2.0 * 10

        scene_count = len(scenes)
        shots_count = sum(s.get("shots", 1) for s in scenes)
        total_assets = sum(s.get("assets", 0) for s in scenes)

        score.visual_storytelling = min(10.0, (shots_count / max(scene_count, 1)) * 2.5)

        score.emotional_flow = emotion_diversity_score * 10

        all_passed = quality_checks.get("passed", False)
        passed_count = sum(1 for c in checks.values() if c.get("passed", False))
        total_count = max(len(checks), 1)

        score.cinematic_quality = (passed_count / total_count) * 10

        score.educational_value = 7.0

        score.retention_prediction = (
            score.visual_storytelling * 0.3 +
            score.emotional_flow * 0.25 +
            score.cinematic_quality * 0.25 +
            score.visual_diversity * 0.2
        )

        score.overall = (
            score.visual_storytelling * 0.15 +
            score.documentary_feel * 0.10 +
            score.visual_diversity * 0.15 +
            score.cinematic_quality * 0.20 +
            score.emotional_flow * 0.15 +
            score.educational_value * 0.10 +
            score.retention_prediction * 0.15
        )

        return score
