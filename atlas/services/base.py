from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResult:
    source: str
    data: dict


class BaseProvider(ABC):
    @abstractmethod
    async def fetch(self, topic: str, entity_type: str, **kwargs) -> ProviderResult:
        ...
