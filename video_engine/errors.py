class VideoEngineError(Exception):
    """Base error for all video engine modules."""

    def __init__(self, message: str, module: str = "", scene_id: int = 0, hint: str = ""):
        self.module = module
        self.scene_id = scene_id
        self.hint = hint
        parts = [f"[{module}]" if module else ""]
        if scene_id:
            parts.append(f"Scene {scene_id}")
        parts.append(message)
        if hint:
            parts.append(f"→ {hint}")
        super().__init__(" ".join(parts))


class ProjectLoadError(VideoEngineError):
    """Raised when a project file cannot be loaded."""


class ProjectValidationError(VideoEngineError):
    """Raised when project data fails validation."""


class TTSGenerationError(VideoEngineError):
    """Raised when TTS audio generation fails."""


class VideoGenerationError(VideoEngineError):
    """Raised when video shot generation fails."""


class AssetSelectionError(VideoEngineError):
    """Raised when no suitable stock asset can be selected."""


class RenderError(VideoEngineError):
    """Raised when FFmpeg composition fails."""
