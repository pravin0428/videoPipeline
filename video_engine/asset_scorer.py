from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from video_engine.config import SCORE_WEIGHTS, SIMILARITY_BOOST_THRESHOLD, SIMILARITY_BOOST_FACTOR
from video_engine.models import Shot


@dataclass
class ScoreCard:
    relevance: float = 0.0
    camera_match: float = 0.0
    lighting_match: float = 0.0
    motion_match: float = 0.0
    continuity: float = 0.0
    composition: float = 0.0
    resolution: float = 0.0
    duration_fit: float = 0.0

    @property
    def total(self) -> float:
        return sum(
            getattr(self, dim) * SCORE_WEIGHTS[dim]
            for dim in SCORE_WEIGHTS
        )

    def dict(self) -> dict:
        return {
            dim: getattr(self, dim)
            for dim in SCORE_WEIGHTS
        } | {"total": round(self.total, 1)}


def _value_distance(a: str | Enum | None, b: str | Enum | None) -> float:
    if a is None or b is None:
        return 0.5
    a_str = a.value if isinstance(a, Enum) else a
    b_str = b.value if isinstance(b, Enum) else b
    return 1.0 if a_str == b_str else 0.0


def evaluate_candidate(
    candidate_metadata: dict,
    shot: Shot,
    prior_shot: Shot | None = None,
) -> ScoreCard:
    card = ScoreCard()

    query_match = 0.0
    query_keys = ["subject", "action", "environment", "focus_subject"]
    matched = 0
    for key in query_keys:
        shot_val = getattr(shot, key, "") or ""
        cand_val = candidate_metadata.get(key, "") or ""
        if shot_val.lower() in cand_val.lower() or cand_val.lower() in shot_val.lower():
            query_match += 1.0
        matched += 1
    card.relevance = query_match / max(matched, 1) * 100.0

    card.camera_match = _value_distance(
        getattr(shot, "camera_movement", None),
        candidate_metadata.get("camera_movement"),
    ) * 100.0

    card.lighting_match = _value_distance(
        getattr(shot, "time_of_day", None),
        candidate_metadata.get("time_of_day"),
    ) * 100.0

    card.motion_match = _value_distance(
        getattr(shot, "motion_intensity", None),
        candidate_metadata.get("motion_intensity"),
    ) * 100.0

    if prior_shot:
        continue_match = 0.0
        continuity_fields = ["time_of_day", "weather", "mood", "color_palette"]
        for field in continuity_fields:
            prior_val = getattr(prior_shot, field, None)
            cand_val = candidate_metadata.get(field)
            if prior_val and cand_val:
                p_str = prior_val.value if isinstance(prior_val, Enum) else prior_val
                c_str = cand_val.value if isinstance(cand_val, Enum) else cand_val
                if p_str == c_str:
                    continue_match += 1.0
        card.continuity = (continue_match / len(continuity_fields)) * 100.0

    card.composition = _value_distance(
        getattr(shot, "composition", None),
        candidate_metadata.get("composition"),
    ) * 100.0

    cand_width = candidate_metadata.get("width", 0)
    cand_height = candidate_metadata.get("height", 0)
    if cand_width > 0 and cand_height > 0:
        aspect = cand_width / cand_height
        card.resolution = 100.0 if 0.56 <= aspect <= 0.6 else 50.0
    else:
        card.resolution = 50.0

    cand_dur = candidate_metadata.get("duration", 0)
    shot_dur = shot.duration_seconds
    if cand_dur > 0 and shot_dur > 0:
        ratio = min(cand_dur, shot_dur) / max(cand_dur, shot_dur)
        card.duration_fit = ratio * 100.0
    else:
        card.duration_fit = 50.0

    return card


def select_best_clip(
    candidates: list[tuple[dict, dict]],
    shot: Shot,
    prior_shot: Shot | None = None,
) -> tuple[dict | None, ScoreCard | None]:
    best_score = -1.0
    best_candidate: dict | None = None
    best_card: ScoreCard | None = None

    for metadata, candidate in candidates:
        card = evaluate_candidate(metadata, shot, prior_shot)
        score = card.total
        if prior_shot and card.continuity > SIMILARITY_BOOST_THRESHOLD * 100:
            score *= SIMILARITY_BOOST_FACTOR
        if score > best_score:
            best_score = score
            best_candidate = candidate
            best_card = card

    return best_candidate, best_card
