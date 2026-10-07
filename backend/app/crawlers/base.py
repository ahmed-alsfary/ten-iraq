from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DiscoveredItem:
    url: str
    title: str | None = None
    published_at: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class CrawlResult:
    source_id: str
    discovered: list[DiscoveredItem]
    pages_scanned: int = 0
    errors: list[str] = field(default_factory=list)


class BaseCrawler(ABC):
    """Adapter interface for all source crawlers (HTML, RSS, API, custom)."""

    @abstractmethod
    def crawl(self, source_id: str, base_url: str, selectors: dict | None = None) -> CrawlResult:
        raise NotImplementedError
