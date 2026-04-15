from abc import ABC, abstractmethod
from core.models import Job


class BaseSource(ABC):
    name: str = "unknown"

    @abstractmethod
    async def fetch(self) -> list[Job]:
        """Fetch jobs from this source. Returns list of Job objects."""
        pass
