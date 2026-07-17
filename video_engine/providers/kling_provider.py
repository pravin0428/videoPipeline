from __future__ import annotations

from typing import Optional

from video_engine.providers.base_provider import BaseProvider, VideoAsset


class KlingProvider(BaseProvider):
    """Kling AI video generation by Kuaishou (not yet integrated).

    TODO: Implementation guide
    ──────────────────────────
    Authentication:
      - Requires API key from the Kling developer portal.
      - Set in config["kling_api_key"] or KLING_API_KEY env var.
      - Header: "Authorization: Bearer {api_key}"

    Request flow:
      1. POST https://api.klingai.com/v1/videos/generate
         Body: {
           "model_name": "kling-v1",
           "prompt": prompt,
           "duration": options.get("duration", 5),
           "negative_prompt": options.get("negative_prompt", ""),
           "cfg_scale": 7.0
         }
      2. Response contains a task_id:
         {"code": 0, "data": {"task_id": "..."}}

    Polling:
      - Poll GET https://api.klingai.com/v1/videos/{task_id}
        every 5s until "status" is "succeeded".
      - On success, response includes video URL.

    Download:
      - Download video from the returned URL to local_path.

    Response mapping → VideoAsset:
      - local_path: local file after download
      - duration: from generation parameters
      - width/height: from response or config default (1080x1920)
      - metadata: full API response JSON
      - quality_score: default 75.0
    """
    provider_name = "kling"

    def initialize(self) -> None:
        raise NotImplementedError(
            "Kling AI is not yet integrated. "
            "See class docstring for implementation guide."
        )

    def health_check(self) -> bool:
        raise NotImplementedError("Kling AI not integrated")

    def generate(self, prompt: str, options: Optional[dict] = None) -> VideoAsset:
        raise NotImplementedError(
            "Kling AI is not yet integrated.\n"
            "Steps to implement:\n"
            "  1. Register at https://klingai.com and get API key.\n"
            "  2. Set KLING_API_KEY in config or env.\n"
            "  3. POST /v1/videos/generate with the prompt.\n"
            "  4. Poll /v1/videos/{task_id} until succeeded.\n"
            "  5. Download the resulting video.\n"
            "  6. Return a VideoAsset with local_path set."
        )
