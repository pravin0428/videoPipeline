from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://atlas:atlas@localhost:5432/atlas"
    database_url_sync: str = "postgresql://atlas:atlas@localhost:5432/atlas"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    log_level: str = "INFO"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    geonames_username: str = "demo"
    app_data_dir: str = str(Path.home() / ".atlas")
    tts_default_voice: str = "hi-IN-SwaraNeural"
    tts_default_rate: str = "+0%"
    tts_default_pitch: str = "+0Hz"

    pexels_api_key: str = ""
    pixabay_api_key: str = ""
    unsplash_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
