"""
Batch evaluation script for Atlas content validation experiment.
Runs research + script generation for 10 topics, collects metrics, writes report.
"""
import asyncio
import json
import os
import sys
from datetime import datetime

import httpx

API_BASE = "http://localhost:8000/api"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "evaluation")

TOPICS = {
    "Ajanta Caves": "landmark",
    "Ellora Caves": "landmark",
    "Lonar Lake": "natural",
    "Hampi": "landmark",
    "Petra": "landmark",
    "Machu Picchu": "landmark",
    "Mount Everest": "natural",
    "Varanasi": "city",
    "Angkor Wat": "landmark",
    "Salar de Uyuni": "natural",
}


def log(msg: str) -> None:
    ts = datetime.now().isoformat()[:19]
    print(f"[{ts}] {msg}", flush=True)


async def create_topic(client: httpx.AsyncClient, name: str) -> str | None:
    entity_type = TOPICS[name]
    try:
        resp = await client.post(
            f"{API_BASE}/topics",
            json={"name": name, "entity_type": entity_type, "skip_enqueue": True},
            timeout=30,
        )
        if resp.status_code == 201:
            tid = resp.json()["topic_id"]
            log(f"  Created topic: {name} -> {tid}")
            return tid
        else:
            log(f"  FAILED to create topic {name}: {resp.status_code}")
            return None
    except Exception as e:
        log(f"  ERROR creating topic {name}: {e}")
        return None


async def run_research(client: httpx.AsyncClient, topic_id: str, name: str) -> bool:
    for attempt in range(2):
        try:
            resp = await client.post(f"{API_BASE}/topics/{topic_id}/research", timeout=600)
            if resp.status_code == 200:
                log(f"  Research OK: {name}")
                return True
            else:
                log(f"  Research FAILED ({resp.status_code}): {name} - {resp.text[:100]}")
                return False
        except Exception as e:
            log(f"  Research ERROR (attempt {attempt+1}): {name} - {e}")
            if attempt == 0:
                await asyncio.sleep(5)
    return False


async def get_topic_data(client: httpx.AsyncClient, topic_id: str) -> dict:
    try:
        resp = await client.get(f"{API_BASE}/topics/{topic_id}", timeout=30)
        if resp.status_code == 200:
            return resp.json()
        return {}
    except Exception:
        return {}


async def generate_scripts(client: httpx.AsyncClient, topic_id: str, name: str) -> dict | None:
    try:
        resp = await client.post(
            f"{API_BASE}/topics/{topic_id}/script",
            json={"script_type": "SHORTS_60", "max_facts": 10},
            timeout=600,
        )
        if resp.status_code == 200:
            data = resp.json()
            log(f"  Scripts OK: {name} ({len(data.get('variants', []))} variants)")
            return data
        else:
            log(f"  Scripts FAILED ({resp.status_code}): {name} - {resp.text[:200]}")
            return None
    except Exception as e:
        log(f"  Scripts ERROR: {name} - {e}")
        return None


def avg(scores: list) -> float:
    return sum(scores) / len(scores) if scores else 0.0


def report(all_results: list[dict]) -> str:
    out = []
    out.append("# Atlas Content Validation Report\n")
    out.append(f"**Date**: {datetime.now().isoformat()[:19]}")
    out.append(f"**Model**: qwen3:8b (Ollama)")
    out.append(f"**Total Topics**: {len(all_results)}\n")
    out.append("---\n")

    completed = [r for r in all_results if r["status"] == "completed"]
    partial = [r for r in all_results if r["status"] == "partial"]
    failed = [r for r in all_results if r["status"] == "failed"]
    total = len(all_results)

    # Collect all scored scripts
    scored = []
    for r in completed + partial:
        for v in r.get("variants", []):
            q = v.get("quality_score") or 0
            rd = v.get("readability_score") or 0
            e = v.get("engagement_score") or 0
            rp = v.get("repetition_score") or 0
            overall = (q + rd + e + rp) / 4.0
            scored.append({
                **v,
                "topic": r["topic"],
                "overall": round(overall, 1),
            })

    scored.sort(key=lambda x: x["overall"], reverse=True)

    # --- 1. Success Rate ---
    out.append("## 1. Success Rate\n")
    rate = (len(completed) + 0.5 * len(partial)) / total * 100
    out.append("| Metric | Value |")
    out.append("|--------|-------|")
    out.append(f"| Total Topics | {total} |")
    out.append(f"| Fully Completed (3/3 variants) | {len(completed)} |")
    out.append(f"| Partially Completed | {len(partial)} |")
    out.append(f"| Failed | {len(failed)} |")
    out.append(f"| **Success Rate** | **{rate:.1f}%** |")
    out.append(f"| Total Scripts Generated | {len(scored)} |\n")
    out.append("---\n")

    # --- 2. Failed Topics ---
    out.append("## 2. Failed Topics\n")
    if failed:
        for r in failed:
            err = "; ".join(r.get("errors", ["Unknown"]))
            out.append(f"- **{r['topic']}**: {err}")
    else:
        out.append("None.\n")
    out.append("\n---\n")

    # --- 3. Best 5 ---
    out.append("## 3. Best 5 Scripts\n")
    for i, s in enumerate(scored[:5], 1):
        out.append(f"### {i}. {s['topic']} — *{s.get('variant', '?')}*")
        out.append(f"- **Title**: {s.get('title', '')}")
        out.append(f"- **Hook**: {s.get('hook', '')}")
        out.append(f"- **Script**: {s.get('script_text', '')[:200]}...")
        out.append(f"- **Duration**: {s.get('estimated_duration', 0)}s")
        out.append(f"- Quality={s.get('quality_score')}, Readability={s.get('readability_score')}, "
                   f"Engagement={s.get('engagement_score')}, Repetition={s.get('repetition_score')}, "
                   f"**Overall={s['overall']}**\n")
    out.append("---\n")

    # --- 4. Worst 5 ---
    out.append("## 4. Worst 5 Scripts\n")
    worst = scored[-5:] if len(scored) >= 5 else scored
    for i, s in enumerate(worst, 1):
        out.append(f"### {i}. {s['topic']} — *{s.get('variant', '?')}*")
        out.append(f"- **Title**: {s.get('title', '')}")
        out.append(f"- **Hook**: {s.get('hook', '')}")
        out.append(f"- **Script**: {s.get('script_text', '')[:200]}...")
        out.append(f"- **Duration**: {s.get('estimated_duration', 0)}s")
        out.append(f"- Quality={s.get('quality_score')}, Readability={s.get('readability_score')}, "
                   f"Engagement={s.get('engagement_score')}, Repetition={s.get('repetition_score')}, "
                   f"**Overall={s['overall']}**\n")
    out.append("---\n")

    # --- 5. Best variant ---
    out.append("## 5. Best-Performing Variant Type\n")
    var_scores: dict[str, list[float]] = {}
    for s in scored:
        v = s.get("variant", "unknown")
        var_scores.setdefault(v, []).append(s["overall"])
    out.append("| Variant | Avg Score | Count |")
    out.append("|---------|-----------|-------|")
    best_var = "N/A"
    best_avg = 0
    for v_name in ["documentary", "mystery", "travel"]:
        vals = var_scores.get(v_name, [])
        a = avg(vals)
        out.append(f"| **{v_name}** | {a:.1f} | {len(vals)} |")
        if a > best_avg:
            best_avg = a
            best_var = v_name
    out.append(f"\n**Best variant**: {best_var} ({best_avg:.1f})\n")
    out.append("---\n")

    # --- 6. Weaknesses ---
    out.append("## 6. Common Weaknesses\n")
    n = len(scored)
    if n == 0:
        out.append("No scripts generated.\n")
    else:
        low_q = sum(1 for s in scored if (s.get("quality_score") or 0) < 50)
        low_r = sum(1 for s in scored if (s.get("readability_score") or 0) < 40)
        low_e = sum(1 for s in scored if (s.get("engagement_score") or 0) < 30)
        low_rp = sum(1 for s in scored if (s.get("repetition_score") or 0) < 50)
        if low_q: out.append(f"- Quality < 50: {low_q}/{n}")
        if low_r: out.append(f"- Readability < 40: {low_r}/{n}")
        if low_e: out.append(f"- Engagement < 30: {low_e}/{n}")
        if low_rp: out.append(f"- Repetition < 50: {low_rp}/{n}")
        if not (low_q or low_r or low_e or low_rp):
            out.append("- No major weaknesses detected.")
    out.append("\n---\n")

    # --- 7. Recommendations ---
    out.append("## 7. Recommendations\n")
    recs = [
        "1. **Prompt refinement**: If engagement is low, strengthen hook/emotional language requirements in prompts.",
        "2. **Facts quality filter**: Aim for 8+ facts before generating; low-fact scripts are repetitive.",
        "3. **Duration calibration**: Adjust target word count in prompts if durations drift from 45-60s.",
        "4. **Location repetition**: Add explicit anti-repetition rules for topic/location names.",
        "5. **Variant selection**: Use the highest-scoring variant as the production default.",
        "6. **Human review gate**: Add manual approval for scripts scoring below 60 overall before video generation.",
    ]
    out.extend(recs)
    out.append("\n---\n")

    # --- Per-topic details ---
    out.append("## Detailed Results Per Topic\n")
    for r in all_results:
        out.append(f"### {r['topic']} — *{r['status']}*\n")
        out.append(f"**Summary**: {r.get('research_summary', 'N/A')}\n")
        out.append(f"**Facts** ({len(r.get('facts', []))}):\n")
        for f in r.get("facts", []):
            out.append(f"- {f}")
        out.append("")
        for v in r.get("variants", []):
            out.append(f"**{v.get('variant', '?').upper()}**")
            out.append(f"- Title: {v.get('title', '')}")
            out.append(f"- Hook: {v.get('hook', '')}")
            out.append(f"- Script: {v.get('script_text', '')}")
            out.append(f"- Duration: {v.get('estimated_duration', 0)}s")
            out.append(f"- Q:{v.get('quality_score')} R:{v.get('readability_score')} E:{v.get('engagement_score')} Rep:{v.get('repetition_score')}\n")
        if r.get("errors"):
            out.append(f"**Errors**: {'; '.join(r['errors'])}\n")
    return "\n".join(out)


async def main() -> None:
    log("=" * 60)
    log("Atlas Content Validation Experiment")
    log(f"Topics: {len(TOPICS)}")
    log(f"Output: {OUTPUT_DIR}")
    log("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        # Phase 1: create all topics
        log("\n--- Phase 1: Creating topics ---")
        topic_ids = {}
        for name in TOPICS:
            tid = await create_topic(client, name)
            if tid:
                topic_ids[name] = tid
            await asyncio.sleep(0.5)

        log(f"Created {len(topic_ids)}/{len(TOPICS)} topics")

        # Phase 2: run research sequentially
        log("\n--- Phase 2: Running research ---")
        research_ok = {}
        for name, tid in topic_ids.items():
            ok = await run_research(client, tid, name)
            research_ok[name] = ok

        log(f"Research success: {sum(1 for v in research_ok.values() if v)}/{len(research_ok)}")

        # Phase 3: get topic data and check facts
        log("\n--- Phase 3: Checking facts ---")
        topic_data = {}
        for name, tid in topic_ids.items():
            if research_ok.get(name):
                data = await get_topic_data(client, tid)
                topic_data[name] = data
                log(f"  {name}: {len(data.get('facts', []))} facts")

        # Phase 4: generate scripts for topics with enough facts
        log("\n--- Phase 4: Generating scripts ---")
        all_results = []
        for name in TOPICS:
            result = {
                "topic": name,
                "status": "failed",
                "research_summary": "",
                "facts": [],
                "variants": [],
                "errors": [],
            }
            tid = topic_ids.get(name)
            if not tid:
                result["errors"].append("Topic creation failed")
                all_results.append(result)
                continue

            if not research_ok.get(name):
                result["errors"].append("Research failed")
                all_results.append(result)
                continue

            data = topic_data.get(name, {})
            facts = data.get("facts", [])
            result["research_summary"] = data.get("summary", "")
            result["facts"] = [f["fact"] for f in facts]

            if len(facts) < 5:
                result["errors"].append(f"Insufficient facts ({len(facts)})")
                result["status"] = "partial"
                all_results.append(result)
                continue

            scripts = await generate_scripts(client, tid, name)
            if scripts and scripts.get("variants"):
                result["variants"] = scripts["variants"]
                result["status"] = "completed" if len(scripts["variants"]) == 3 else "partial"
            else:
                result["errors"].append("Script generation returned no variants")
                result["status"] = "partial"

            all_results.append(result)

    # Generate report
    log("\n--- Generating report ---")
    report_md = report(all_results)
    rpath = os.path.join(OUTPUT_DIR, "evaluation_report.md")
    with open(rpath, "w", encoding="utf-8") as f:
        f.write(report_md)
    log(f"Report: {rpath} ({len(report_md)} chars)")

    # Summary
    c = sum(1 for r in all_results if r["status"] == "completed")
    p = sum(1 for r in all_results if r["status"] == "partial")
    ff = sum(1 for r in all_results if r["status"] == "failed")
    rate = (c + 0.5 * p) / len(all_results) * 100
    total_s = sum(len(r.get("variants", [])) for r in all_results)
    log(f"\nSummary:")
    log(f"  Completed: {c} | Partial: {p} | Failed: {ff}")
    log(f"  Success Rate: {rate:.1f}%")
    log(f"  Total scripts: {total_s}")
    log("Done!")


if __name__ == "__main__":
    asyncio.run(main())
