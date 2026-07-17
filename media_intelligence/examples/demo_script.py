"""
Demo: Media Intelligence Engine with a full documentary script.
Processes a complete narration script sentence-by-sentence
and produces a structured production plan.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from media_intelligence.engine import MediaIntelligenceEngine
from media_intelligence.models import MediaType


# ── Documentary script: "The Temples of Khajuraho" ──
SCRIPT = [
    "The Khajuraho temples are located in the Madhya Pradesh region of central India, nestled between the Vindhya mountain range and the dense forests of Bundelkhand.",
    "Built between 950 and 1050 AD by the Chandela dynasty, these temples represent the pinnacle of medieval Indian architecture.",
    "Of the original 85 temples, only about 25 have survived the passage of time, making it one of the most concentrated temple complexes in the world.",
    "The temples are divided into three main groups: the Western, Eastern, and Southern clusters, each with its own distinct character.",
    "As the Chandela kings expanded their empire, they commissioned more and more temples, each one more ornate than the last.",
    "The intricate carvings on the temple walls depict celestial dancers in graceful poses, frozen in stone for over a thousand years.",
    "These dancers, known as apsaras, represent the divine beauty that the sculptors sought to capture in every curve and contour.",
    "The temple architecture follows the shikhara style, where the central spire rises like a mountain peak toward the heavens.",
    "This design was not merely aesthetic but symbolic, representing Mount Meru, the mythical axis of the universe in Hindu cosmology.",
    "The concept of spiritual ascent is embedded in every aspect of the temple design, guiding the devotee from the material world toward the divine.",
    "Every evening, the priests perform the ancient ritual of aarti, waving lamps in circular motions before the deity as bells ring through the courtyard.",
    "The warm glow of the oil lamps illuminates the dark sanctum, creating an atmosphere of profound devotion that has remained unchanged for centuries.",
    "For the millions of visitors who come each year, Khajuraho is not merely a historical monument but a living testament to India's cultural heritage.",
]


def demo():
    engine = MediaIntelligenceEngine()

    # ── Process each sentence ──
    plans = []
    media_counts = {}

    for i, sentence in enumerate(SCRIPT, 1):
        print(f"\n{'─'*60}")
        print(f"Sentence {i}: {sentence}")
        print(f"{'─'*60}")

        plan = engine.plan(sentence)
        plans.append(plan)

        # Track counts
        mt = plan.media_type.value
        media_counts[mt] = media_counts.get(mt, 0) + 1

        # Print summary
        print(f"  Media:     {plan.media_type.label} ({plan.confidence:.0%})")
        print(f"  Goal:      {plan.visual_goal}")
        print(f"  Search:    {plan.search_prompt}")
        print(f"  Duration:  {plan.suggested_duration:.1f}s")
        print(f"  Fallback:  {' → '.join(m.label for m in plan.fallback_order)}")

    # ── Summary ──
    print(f"\n\n{'='*60}")
    print(f"PRODUCTION PLAN SUMMARY")
    print(f"{'='*60}")
    print(f"Total sentences: {len(SCRIPT)}")
    print(f"\nMedia type distribution:")
    for mt, count in sorted(media_counts.items(), key=lambda x: -x[1]):
        pct = count / len(SCRIPT) * 100
        label = MediaType(mt).label
        print(f"  {label:35s} {count:2d} scenes ({pct:4.0f}%)")

    # Estimate total duration
    total_dur = sum(p.suggested_duration for p in plans)
    print(f"\nEstimated total duration: {total_dur:.0f}s ({total_dur/60:.1f} min)")

    # ── Save full plan ──
    output = {
        "script": SCRIPT,
        "scenes": [p.to_dict() for p in plans],
        "statistics": {
            "total_sentences": len(SCRIPT),
            "media_distribution": media_counts,
            "estimated_duration_s": round(total_dur, 1),
        },
    }

    output_path = Path(__file__).parent / "khajuraho_production_plan.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nFull production plan saved: {output_path}")

    # ── Print per-media-type breakdown ──
    print(f"\n{'='*60}")
    print(f"SCENE-BY-SCENE MEDIA PLAN")
    print(f"{'='*60}")
    for i, plan in enumerate(plans, 1):
        d = plan.to_dict()
        print(f"\nScene {i:2d}: {d['media_type'].upper():25s} [{d['confidence']:.0%}]")
        print(f"       Sentence: {d['sentence'][:70]}...")
        print(f"       Search:   {d['search_prompt']}")
        print(f"       Camera:   {d['camera_style'][:40]}")


if __name__ == "__main__":
    demo()
