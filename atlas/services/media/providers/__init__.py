from services.media.providers.base import MediaProvider
from services.media.providers.stock_video import StockVideoProvider
from services.media.providers.ai_video import AIVideoProvider
from services.media.providers.photo import PhotoProvider
from services.media.providers.map import MapProvider
from services.media.providers.infographic import InfographicProvider
from services.media.providers.animation import ScientificAnimationProvider
from services.media.providers.historical_reconstruction import HistoricalReconstructionProvider

PROVIDER_REGISTRY: dict[str, type[MediaProvider]] = {
    "stock_video": StockVideoProvider,
    "ai_video": AIVideoProvider,
    "photo": PhotoProvider,
    "map": MapProvider,
    "infographic": InfographicProvider,
    "scientific_animation": ScientificAnimationProvider,
    "historical_reconstruction": HistoricalReconstructionProvider,
}

__all__ = [
    "MediaProvider",
    "StockVideoProvider",
    "AIVideoProvider",
    "PhotoProvider",
    "MapProvider",
    "InfographicProvider",
    "ScientificAnimationProvider",
    "HistoricalReconstructionProvider",
    "PROVIDER_REGISTRY",
]
