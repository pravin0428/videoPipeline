"""
Media Intelligence Engine
Receives one sentence at a time and produces a structured MediaPlan
with the optimal media type, prompts, fallback chain, and quality criteria.
"""
import json
from typing import Optional
from .models import MediaType, SentenceFeatures, MediaPlan, FALLBACK_CHAINS
from .analyzers.sentence_analyzer import SentenceAnalyzer
from .analyzers.media_matcher import MediaMatcher
from .planners.prompt_builder import PromptBuilder


class MediaIntelligenceEngine:
    """Main orchestrator: sentence → structured media plan."""

    def __init__(self):
        self.analyzer = SentenceAnalyzer()
        self.matcher = MediaMatcher()
        self.prompt_builder = PromptBuilder()

    def plan(self, sentence: str) -> MediaPlan:
        features = self.analyzer.analyze(sentence)
        media_type, confidence, reasoning = self.matcher.match(features)
        prompt_data = self.prompt_builder.build_for(sentence, features, media_type)

        plan = MediaPlan(
            sentence=sentence,
            media_type=media_type,
            confidence=confidence,
            reasoning=reasoning,
            visual_elements=prompt_data.get("visual_elements", []),
            search_prompt=prompt_data.get("search_prompt", ""),
            generation_prompt=prompt_data.get("generation_prompt", ""),
            negative_prompt=prompt_data.get("negative_prompt", ""),
            fallback_order=FALLBACK_CHAINS.get(media_type, list(MediaType)),
            quality_criteria=prompt_data.get("quality_criteria", []),
            suggested_duration=prompt_data.get("suggested_duration", 5.0),
            camera_style=prompt_data.get("camera_style", ""),
            visual_goal=prompt_data.get("visual_goal", ""),
        )
        return plan

    def analyze(self, sentence: str) -> SentenceFeatures:
        return self.analyzer.analyze(sentence)


def print_plan(plan: MediaPlan):
    """Pretty-print a MediaPlan."""
    d = plan.to_dict()
    print(f"\n{'='*60}")
    print(f"Sentence: {d['sentence'][:80]}{'...' if len(d['sentence']) > 80 else ''}")
    print(f"{'='*60}")
    print(f"Media Type:    {plan.media_type.label} (confidence: {d['confidence']:.0%})")
    print(f"Reasoning:     {d['reasoning']}")
    print(f"Visual Goal:   {d['visual_goal']}")
    print(f"Duration:      {d['suggested_duration']:.1f}s")
    print(f"Camera:        {d['camera_style'][:60]}...")
    print(f"Search Query:  {d['search_prompt']}")
    print(f"Gen Prompt:    {d['generation_prompt'][:80]}...")
    print(f"Fallback:      {' → '.join(m.label for m in plan.fallback_order)}")
    print(f"Quality:       {'; '.join(d['quality_criteria'])}")
    print()


def plan_script(sentences: list[str]) -> list[MediaPlan]:
    """Plan visuals for an entire script."""
    engine = MediaIntelligenceEngine()
    return [engine.plan(s) for s in sentences]


if __name__ == "__main__":
    import sys

    engine = MediaIntelligenceEngine()

    if len(sys.argv) > 1:
        sentence = " ".join(sys.argv[1:])
        plan = engine.plan(sentence)
        print_plan(plan)
        print(json.dumps(plan.to_dict(), indent=2))
    else:
        # Interactive demo
        print("Media Intelligence Engine — Ctrl+D to exit")
        print("Enter a documentary narration sentence:\n")
        for line in sys.stdin:
            line = line.strip()
            if line:
                plan = engine.plan(line)
                print_plan(plan)
            print("Enter next sentence (Ctrl+D to exit):\n")
