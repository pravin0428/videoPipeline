from __future__ import annotations

from typing import Optional

from video_engine.providers.base_provider import BaseProvider, VideoAsset


class RunwayProvider(BaseProvider):
    """Runway Gen-3 / Gen-2 video generation (not yet integrated).

    TODO: Implementation guide
    ──────────────────────────
    Authentication:
      - Requires Runway API key from the Runway developer console.
      - Set in config["runway_api_key"] or RUNWAY_API_KEY env var.
      - Header: "X-Runway-Api-Key: {api_key}"

    Request flow:
      1. POST https://api.runwayml.com/v1/generations
         Body: {
           "model": "gen-3",
           "prompt": prompt,
           "duration": options.get("duration", 5),
           "resolution": options.get("resolution", "1080x1920"),
           "negative_prompt": options.get("negative_prompt", "")
         }
      2. Response contains a generation ID:
         {"id": "gen_...", "status": "pending"}

    Polling:
      - Poll GET https://api.runwayml.com/v1/generations/{id}
        every 10s until "status" is "completed".
      - On completion, response includes "output" with video URLs.

    Download:
      - Download video from the first output URL to local_path.

    Response mapping → VideoAsset:
      - local_path: local file after download
      - duration: from generation parameters
      - width/height: from response metadata
      - metadata: full API response JSON
      - quality_score: default 85.0 (Gen-3 quality is excellent)
    """
    provider_name = "runway"

    def initialize(self) -> None:
        raise NotImplementedError(
            "Runway is not yet integrated. "
            "See class docstring for implementation guide."
        )

    def health_check(self) -> bool:
        raise NotImplementedError("Runway not integrated")

    def generate(self, prompt: str, options: Optional[dict] = None) -> VideoAsset:
        raise NotImplementedError(
            "Runway is not yet integrated.\n"
            "Steps to implement:\n"
            "  1. Get API key from Runway developer console.\n"
            "  2. Set RUNWAY_API_KEY in config or env.\n"
            "  3. POST /v1/generations with the prompt.\n"
            "  4. Poll /v1/generations/{id} until completed.\n"
            "  5. Download video from the output URL.\n"
            "  6. Return a VideoAsset with local_path set."
        )
