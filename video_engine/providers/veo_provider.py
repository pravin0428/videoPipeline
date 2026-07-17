from __future__ import annotations

from typing import Optional

from video_engine.providers.base_provider import BaseProvider, VideoAsset


class VeoProvider(BaseProvider):
    """Google Veo AI video generation (not yet integrated).

    TODO: Implementation guide
    ──────────────────────────
    Authentication:
      - Requires Google Cloud service account with Veo API enabled.
      - Set up OAuth2 via google-auth library:
          credentials = service_account.Credentials.from_service_account_file(
              os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
          )
      - Store credentials path in config["google_credentials"] or
        GOOGLE_APPLICATION_CREDENTIALS env var.

    Request flow:
      1. POST https://aistudio.googleapis.com/v1/projects/{project}/models/veo:predict
         Body: {
           "instances": [{"prompt": prompt}],
           "parameters": {"durationSeconds": options.get("duration", 5)}
         }
      2. Response contains an async operation name:
         {"name": "projects/{project}/operations/{op_id}"}

    Polling:
      - Poll GET https://aistudio.googleapis.com/v1/{operation_name}
        every 10s until "done": true.
      - On completion, response contains "videoUri" or "gcsUri".

    Download:
      - Download video from the returned URI to local_path.
      - Use google-cloud-storage if the URI is a GCS path.

    Response mapping → VideoAsset:
      - local_path: local file after download
      - duration: from generation parameters or response metadata
      - width/height: from response or config default
      - metadata: full API response JSON
      - quality_score: default 80.0 (Veo quality is generally high)
    """
    provider_name = "veo"

    def initialize(self) -> None:
        raise NotImplementedError(
            "Google Veo is not yet integrated. "
            "See class docstring for implementation guide."
        )

    def health_check(self) -> bool:
        raise NotImplementedError("Google Veo not integrated")

    def generate(self, prompt: str, options: Optional[dict] = None) -> VideoAsset:
        raise NotImplementedError(
            "Google Veo is not yet integrated.\n"
            "Steps to implement:\n"
            "  1. Install google-cloud-aiplatform.\n"
            "  2. Create a service account with Veo API access.\n"
            "  3. Set GOOGLE_APPLICATION_CREDENTIALS or pass credentials in config.\n"
            "  4. Call POST /v1/projects/{project}/models/veo:predict with the prompt.\n"
            "  5. Poll the returned operation until complete.\n"
            "  6. Download video from returned URI.\n"
            "  7. Return a VideoAsset with local_path set."
        )
