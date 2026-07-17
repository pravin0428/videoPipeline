from __future__ import annotations

from typing import Optional

from video_engine.providers.base_provider import BaseProvider, VideoAsset


class HailuoProvider(BaseProvider):
    """Hailuo AI video generation by MiniMax (not yet integrated).

    TODO: Implementation guide
    ──────────────────────────
    Authentication:
      - Requires MiniMax/Hailuo API key.
      - Set in config["hailuo_api_key"] or HAILUO_API_KEY env var.
      - Header: "Authorization: Bearer {api_key}"

    Request flow:
      1. POST https://api.minimax.chat/v1/video_generation
         Body: {
           "model": "video-01",
           "prompt": prompt,
           "duration": options.get("duration", 5),
           "negative_prompt": options.get("negative_prompt", "")
         }
      2. Response contains a task_id:
         {"base_resp": {"status_code": 0}, "task_id": "..."}

    Polling:
      - Poll GET https://api.minimax.chat/v1/query/video_generation?task_id={task_id}
        every 5s until "status" is "Success".
      - On success, response includes "file_id" for the generated video.

    Download:
      - Use GET https://api.minimax.chat/v1/files/{file_id} to download.
      - Save to local_path.

    Response mapping → VideoAsset:
      - local_path: local file after download
      - duration: from generation parameters
      - width/height: from response or config default
      - metadata: full API response JSON
      - quality_score: default 75.0
    """
    provider_name = "hailuo"

    def initialize(self) -> None:
        raise NotImplementedError(
            "Hailuo (MiniMax) is not yet integrated. "
            "See class docstring for implementation guide."
        )

    def health_check(self) -> bool:
        raise NotImplementedError("Hailuo not integrated")

    def generate(self, prompt: str, options: Optional[dict] = None) -> VideoAsset:
        raise NotImplementedError(
            "Hailuo (MiniMax) is not yet integrated.\n"
            "Steps to implement:\n"
            "  1. Get API key from MiniMax developer portal.\n"
            "  2. Set HAILUO_API_KEY in config or env.\n"
            "  3. POST /v1/video_generation with the prompt.\n"
            "  4. Poll /v1/query/video_generation until Success.\n"
            "  5. Download video using the file_id.\n"
            "  6. Return a VideoAsset with local_path set."
        )
