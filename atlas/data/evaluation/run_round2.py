"""
Evaluation Round 2 — Phase 2.6 Content Quality Engine
Runs: 3 topics x 3 variants with auto-regeneration
Saves progress incrementally to track long LLM calls.
"""
import json
import sys
import time
from pathlib import Path

import httpx
import urllib.request

API = "http://localhost:8000/api"
OUTPUT = Path(__file__).parent / "evaluation_round_2.md"
PROGRESS = Path(__file__).parent / "round2_progress.json"

TOPICS = [
    {"name": "Lonar Lake", "entity_type": "lake", "country": "India"},
    {"name": "Hampi", "entity_type": "historical_site", "country": "India"},
    {"name": "Ajanta Caves", "entity_type": "cave", "country": "India"},
]


def req(method, path, data=None, timeout=600):
    url = f"{API}{path}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(r, timeout=timeout)
    return json.loads(resp.read().decode())


def create_topic(name, etype, country):
    print(f"\n  Creating topic: {name} ... ", end="", flush=True)
    d = req("POST", "/topics", {"name": name, "entity_type": etype, "country": country, "skip_enqueue": True})
    print(f"done (id={d['topic_id'][:8]}...)", flush=True)
    return d["topic_id"]


def run_research(tid, name):
    print(f"  Researching {name} ... ", end="", flush=True)
    t0 = time.time()
    req("POST", f"/topics/{tid}/research", timeout=300)
    t = time.time() - t0
    print(f"done ({t:.0f}s)", flush=True)
    return round(t, 1)


def get_topic_data(tid):
    return req("GET", f"/topics/{tid}")


def generate_scripts(tid, name):
    print(f"  Generating scripts for {name} (this may take several minutes) ...", flush=True)
    t0 = time.time()
    d = req("POST", f"/topics/{tid}/script", {"script_type": "SHORTS_60", "max_facts": 10}, timeout=1500)
    t = time.time() - t0
    variants = d.get("variants", [])
    print(f"  done ({t:.0f}s, {len(variants)} variants)", flush=True)
    return variants, round(t, 1)


def get_report(tid):
    try:
        return req("GET", f"/topics/{tid}/script/report", timeout=30)
    except Exception:
        return None


def get_all_scripts(tid):
    """Get all scripts for a topic via the topic detail endpoint."""
    try:
        d = req("GET", f"/topics/{tid}", timeout=30)
        return d.get("scripts", [])
    except Exception:
        return []


def build_result(tid, name, cfg, research_time, gen_time, variants, report, topic_data):
    facts = topic_data.get("facts", [])
    summary = topic_data.get("summary", "")

    result = {
        "topic_id": tid,
        "topic_name": name,
        "entity_type": cfg["entity_type"],
        "country": cfg["country"],
        "research_time": research_time,
        "gen_time": gen_time,
        "research_success": bool(summary),
        "facts_count": len(facts),
        "facts_ok": len(facts) >= 5,
        "report": report,
        "variants": [],
    }

    for v in variants:
        v_result = {
            "variant": v.get("variant", "unknown"),
            "title": v.get("title", ""),
            "hook": v.get("hook", ""),
            "script_text": v.get("script_text", ""),
            "estimated_duration": v.get("estimated_duration", 0),
            "quality_score": v.get("quality_score"),
            "readability_score": v.get("readability_score"),
            "engagement_score": v.get("engagement_score"),
            "repetition_score": v.get("repetition_score"),
            "hallucination_score": v.get("hallucination_score"),
            "grounding_score": v.get("grounding_score"),
            "story_score": v.get("story_score"),
            "language_score": v.get("language_score"),
            "validation_passed": v.get("validation_passed"),
            "generation_attempts": v.get("generation_attempts"),
            "script_status": v.get("script_status"),
        }
        status = "PASS" if v_result["validation_passed"] else "FAIL"
        print(f"    [{v_result['variant']:15s}] {status} (q={v_result.get('quality_score','?')}, g={v_result.get('grounding_score','?')}, attempts={v_result.get('generation_attempts','?')})", flush=True)
        result["variants"].append(v_result)

    return result


def compute_stats(results):
    n = len(results)
    variants = [v for r in results for v in r["variants"]]
    nv = len(variants)

    research_ok = sum(1 for r in results if r["research_success"])
    facts_ok = sum(1 for r in results if r["facts_ok"])
    validated = [v for v in variants if v.get("validation_passed") is True]

    def avg(key, seq):
        vals = [v.get(key) for v in seq if v.get(key) is not None]
        return round(sum(vals) / max(len(vals), 1), 1) if vals else 0.0

    return {
        "total_topics": n,
        "total_variants": nv,
        "research_success_rate": round(research_ok / max(n, 1) * 100, 1),
        "facts_success_rate": round(facts_ok / max(n, 1) * 100, 1),
        "validation_pass_rate": round(len(validated) / max(nv, 1) * 100, 1),
        "validated_count": len(validated),
        "avg_quality_score": avg("quality_score", variants),
        "avg_engagement_score": avg("engagement_score", variants),
        "avg_grounding_score": avg("grounding_score", variants),
        "avg_story_score": avg("story_score", variants),
        "avg_language_score": avg("language_score", variants),
        "avg_hallucination_score": avg("hallucination_score", variants),
        "avg_readability_score": avg("readability_score", variants),
        "avg_repetition_score": avg("repetition_score", variants),
    }


def find_best_variant(results):
    variants = [v for r in results for v in r["variants"]]
    scored = sorted(variants, key=lambda v: v.get("quality_score", 0) or 0, reverse=True)
    return scored[0] if scored else {}


def variant_type_avg_scores(results):
    variants = [v for r in results for v in r["variants"]]
    by_type = {}
    for v in variants:
        vt = v.get("variant", "unknown")
        by_type.setdefault(vt, []).append(v)

    def avg_score(vlist, key):
        vals = [v.get(key) for v in vlist if v.get(key) is not None]
        return round(sum(vals) / max(len(vals), 1), 1) if vals else 0.0

    return {
        vt: {
            "count": len(vlist),
            "avg_quality": avg_score(vlist, "quality_score"),
            "avg_grounding": avg_score(vlist, "grounding_score"),
            "avg_engagement": avg_score(vlist, "engagement_score"),
            "avg_story": avg_score(vlist, "story_score"),
            "avg_language": avg_score(vlist, "language_score"),
            "avg_hallucination": avg_score(vlist, "hallucination_score"),
            "pass_count": sum(1 for v in vlist if v.get("validation_passed") is True),
        }
        for vt, vlist in by_type.items()
    }


def generate_report(results, stats, best, variant_scores):
    lines = []
    def w(s=""): lines.append(s)

    w("# Evaluation Round 2 — Phase 2.6 Content Quality Engine")
    w()
    w("**Date:** 2026-06-20")
    w(f"**Topics:** {', '.join(r['topic_name'] for r in results)}")
    w("**Engine:** Phase 2.6 with 5 validators + auto-regeneration (max 3 attempts)")
    w()

    w("## Summary Statistics")
    w()
    w("| Metric | Value |")
    w("|--------|-------|")
    w(f"| Total Topics | {stats['total_topics']} |")
    w(f"| Total Scripts Generated | {stats['total_variants']} |")
    w(f"| Research Success Rate | {stats['research_success_rate']}% |")
    w(f"| Fact Extraction Success Rate | {stats['facts_success_rate']}% |")
    w(f"| Validation Pass Rate | {stats['validation_pass_rate']}% |")
    w(f"| Average Quality Score | {stats['avg_quality_score']} |")
    w(f"| Average Engagement Score | {stats['avg_engagement_score']} |")
    w(f"| Average Grounding Score | {stats['avg_grounding_score']} |")
    w(f"| Average Story Score | {stats['avg_story_score']} |")
    w(f"| Average Language Score | {stats['avg_language_score']} |")
    w(f"| Average Hallucination Score | {stats['avg_hallucination_score']} |")
    w(f"| Average Readability Score | {stats['avg_readability_score']} |")
    w(f"| Average Repetition Score | {stats['avg_repetition_score']} |")
    w()

    w("## Per-Topic Details")
    w()
    for r in results:
        w(f"### {r['topic_name']}")
        w()
        w(f"- **Topic ID:** `{r['topic_id']}`")
        w(f"- **Research Time:** {r['research_time']}s")
        w(f"- **Generation Time:** {r['gen_time']}s")
        w(f"- **Research Success:** {'Yes' if r['research_success'] else 'No'}")
        w(f"- **Facts Extracted:** {r['facts_count']}")
        w()

        w("| Variant | Title | Quality | Engagement | Grounding | Story | Language | Hallucination | Validated | Attempts | Status |")
        w("|---------|-------|---------|------------|-----------|-------|----------|---------------|-----------|----------|--------|")
        for v in r["variants"]:
            w(f"| {v['variant']} | {v['title'][:30]} | {v.get('quality_score', '-')} | {v.get('engagement_score', '-')} | {v.get('grounding_score', '-')} | {v.get('story_score', '-')} | {v.get('language_score', '-')} | {v.get('hallucination_score', '-')} | {'✓' if v.get('validation_passed') else '✗'} | {v.get('generation_attempts', '-')} | {v.get('script_status', '-')} |")
        w()

    w("## Script Details")
    w()
    for r in results:
        for v in r["variants"]:
            w(f"### {r['topic_name']} — {v['variant']}")
            w()
            w(f"- **Title:** {v.get('title', '')}")
            w(f"- **Hook:** {v.get('hook', '')}")
            w(f"- **Script:** {v.get('script_text', '')}")
            w(f"- **Quality Score:** {v.get('quality_score', '-')}")
            w(f"- **Engagement Score:** {v.get('engagement_score', '-')}")
            w(f"- **Grounding Score:** {v.get('grounding_score', '-')}")
            w(f"- **Story Score:** {v.get('story_score', '-')}")
            w(f"- **Language Score:** {v.get('language_score', '-')}")
            w(f"- **Hallucination Score:** {v.get('hallucination_score', '-')}")
            w(f"- **Validation Passed:** {'Yes' if v.get('validation_passed') else 'No'}")
            w(f"- **Generation Attempts:** {v.get('generation_attempts', '-')}")
            w(f"- **Script Status:** {v.get('script_status', '-')}")
            w()

    w("## Variant Type Comparison")
    w()
    w("| Variant | Count | Avg Quality | Avg Grounding | Avg Engagement | Avg Story | Avg Language | Avg Hallucination | Pass Rate |")
    w("|---------|-------|-------------|---------------|----------------|-----------|--------------|-------------------|-----------|")
    for vt, scores in sorted(variant_scores.items()):
        pr = f"{scores['pass_count']}/{scores['count']} ({round(scores['pass_count']/max(scores['count'],1)*100)}%)"
        w(f"| {vt} | {scores['count']} | {scores['avg_quality']} | {scores['avg_grounding']} | {scores['avg_engagement']} | {scores['avg_story']} | {scores['avg_language']} | {scores['avg_hallucination']} | {pr} |")
    w()

    w("## Round 1 vs Round 2 Comparison")
    w()
    w("| Metric | Round 1 | Round 2 | Delta |")
    w("|--------|---------|---------|-------|")
    w(f"| Validation Pass Rate | 75.0% | {stats['validation_pass_rate']}% | {stats['validation_pass_rate'] - 75.0:+.1f}% |")
    w(f"| Average Quality Score | 68.0* | {stats['avg_quality_score']} | {stats['avg_quality_score'] - 68.0:+.1f} |")
    w(f"| Average Engagement Score | 49.5* | {stats['avg_engagement_score']} | {stats['avg_engagement_score'] - 49.5:+.1f} |")
    w(f"| Average Grounding Score | — | {stats['avg_grounding_score']} | — |")
    w(f"| Average Story Score | — | {stats['avg_story_score']} | — |")
    w(f"| Average Language Score | — | {stats['avg_language_score']} | — |")
    w(f"| Average Hallucination Score | — | {stats['avg_hallucination_score']} | — |")
    w(f"| Average Readability Score | — | {stats['avg_readability_score']} | — |")
    w(f"| Average Repetition Score | — | {stats['avg_repetition_score']} | — |")
    w()
    w("_*Round 1 metrics are estimated from available data. Round 1 did not have structured grounding/story/language/hallucination scoring._")
    w()

    w("## Improvements from Phase 2.6")
    w()
    w("- Structured 5-validator pipeline ensures every script is checked for fact accuracy, location correctness, repetition, Hindi language ratio, and story structure")
    w("- Auto-regeneration loop retries failed scripts up to 3 times before marking as `failed`")
    w("- Mystery prompt now has 10 strict rules preventing hallucination and enforcing fact-grounding")
    w("- Every script is scored on hallucination, grounding, story, and language")
    w("- Report endpoint (`GET /topics/{id}/script/report`) provides full validation trace")
    w()

    w("## Remaining Weaknesses")
    w()
    w("- Fact validator uses keyword overlap (not semantic matching) — may miss subtle hallucinations or flag valid paraphrases")
    w("- Location validator whitelist depends on research data completeness")
    w("- Story validator is heuristic-based (marker words, sentence position)")
    w("- Engagement scoring remains rule-based (questions + exclamation marks + emotional words)")
    w("- LLM generation speed (~55s per call) limits practical auto-regeneration throughput")
    w()

    if best and best.get("title"):
        w("## Best Script Overall")
        w()
        best_topic = "?"
        for r in results:
            for v in r["variants"]:
                if v is best:
                    best_topic = r["topic_name"]
        w(f"**{best.get('title', 'N/A')}** ({best.get('variant', 'N/A')} — {best_topic})")
        for k in ["quality_score", "grounding_score", "story_score", "language_score", "engagement_score", "hallucination_score"]:
            w(f"- {k}: {best.get(k, '-')}")
        w()

    if variant_scores:
        best_vt = max(variant_scores.items(), key=lambda x: x[1]["avg_quality"])
        w(f"## Best Variant Type: **{best_vt[0]}**")
        w(f"  (Avg Quality: {best_vt[1]['avg_quality']}, Pass Rate: {best_vt[1]['pass_count']}/{best_vt[1]['count']} = {round(best_vt[1]['pass_count']/max(best_vt[1]['count'],1)*100)}%)")
        w()
    else:
        w("## Best Variant Type: N/A (no variants generated)")
        w()

    w("## Recommendation")
    w()
    if stats["validation_pass_rate"] >= 80:
        w("### Ready for Video Generation")
        w()
        w("The Content Quality Engine has validated scripts with a pass rate above 80%.")
        w("Fact-grounding, language purity, and story structure are consistently meeting thresholds.")
        w("Proceed to TTS synthesis and video rendering pipeline.")
    elif stats["validation_pass_rate"] >= 50:
        w("### Conditional — Proceed with Monitoring")
        w()
        w(f"Pass rate is {stats['validation_pass_rate']}% (between 50-80%). Many scripts validate, but some need attention.")
        w("Recommend proceeding to video generation for validated scripts only.")
        w("Continue monitoring hallucination scores and consider additional fact-checking for borderline scripts.")
    else:
        w("### Needs Another Content Iteration")
        w()
        w(f"Pass rate is {stats['validation_pass_rate']}% (below 50%).")
        w("The Content Quality Engine is catching issues but regeneration is not producing sufficiently validated scripts.")
        w("Recommended improvements before video generation:")
        w("- Enhance fact validator with LLM-based semantic claim checking")
        w("- Improve LLM prompt engineering for each variant type")
        w("- Consider fine-tuning the model on validated script examples")
    w()

    return "\n".join(lines)


def save_progress(results):
    PROGRESS.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


# ---- MAIN ----
def main():
    results = []
    report_file = None

    for tc in TOPICS:
        name = tc["name"]
        print(f"\n{'='*60}", flush=True)
        print(f"  TOPIC: {name}", flush=True)
        print(f"{'='*60}", flush=True)

        try:
            tid = create_topic(name, tc["entity_type"], tc["country"])
            research_time = run_research(tid, name)
            topic_data = get_topic_data(tid)
            variants, gen_time = generate_scripts(tid, name)
            report = get_report(tid)
            result = build_result(tid, name, tc, research_time, gen_time, variants, report, topic_data)
            results.append(result)
            save_progress(results)
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            results.append({
                "topic_id": "ERROR",
                "topic_name": name,
                "entity_type": tc["entity_type"],
                "country": tc["country"],
                "research_time": 0, "gen_time": 0,
                "research_success": False, "facts_count": 0, "facts_ok": False,
                "report": None, "variants": [],
            })
            save_progress(results)

    stats = compute_stats(results)
    best = find_best_variant(results)
    variant_scores = variant_type_avg_scores(results)

    report_md = generate_report(results, stats, best, variant_scores)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(report_md, encoding="utf-8")

    print(f"\n{'='*60}", flush=True)
    print(f"  REPORT: {OUTPUT}", flush=True)
    print(f"  Topics: {stats['total_topics']}, Variants: {stats['total_variants']}", flush=True)
    print(f"  Validated: {stats['validated_count']}/{stats['total_variants']} ({stats['validation_pass_rate']}%)", flush=True)
    print(f"  Avg Quality: {stats['avg_quality_score']}", flush=True)
    print(f"  Avg Grounding: {stats['avg_grounding_score']}", flush=True)
    print(f"  Avg Hallucination: {stats['avg_hallucination_score']}", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
