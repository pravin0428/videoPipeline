#!/usr/bin/env python3
"""Seed script to test the Atlas pipeline with sample topics."""

import asyncio
import uuid

import httpx

BASE_URL = "http://localhost:8000/api"

SAMPLE_TOPICS = [
    {"name": "Ajanta Caves", "entity_type": "landmark", "country": "India"},
    {"name": "Taj Mahal", "entity_type": "landmark", "country": "India"},
    {"name": "Mount Everest", "entity_type": "mountain", "country": "Nepal"},
    {"name": "Amazon River", "entity_type": "river"},
    {"name": "Varanasi", "entity_type": "city", "country": "India"},
]


async def seed() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        for topic in SAMPLE_TOPICS:
            print(f"\n--- Processing: {topic['name']} ---")

            resp = await client.post("/topics", json=topic)
            if resp.status_code != 201:
                print(f"  Failed to create topic: {resp.text}")
                continue
            topic_id = resp.json()["topic_id"]
            print(f"  Created topic ID: {topic_id}")

            resp = await client.post(f"/topics/{topic_id}/research")
            if resp.status_code != 200:
                print(f"  Research failed: {resp.text}")
                continue
            print(f"  Research status: {resp.json()['status']}")

            resp = await client.get(f"/topics/{topic_id}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"  Summary: {data['summary'][:100]}...")
                print(f"  Facts: {len(data['facts'])}")
                for f in data["facts"]:
                    print(f"    - [{f['confidence_score']}] {f['fact'][:80]}")


if __name__ == "__main__":
    asyncio.run(seed())
