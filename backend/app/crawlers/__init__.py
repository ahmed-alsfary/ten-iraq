from app.crawlers.base import BaseCrawler, CrawlResult, DiscoveredItem
from app.crawlers.factory import get_crawler
from app.crawlers.generic_html import GenericHtmlCrawler
from app.crawlers.itp_iq import ItpIqCrawler

__all__ = [
    "BaseCrawler",
    "CrawlResult",
    "DiscoveredItem",
    "GenericHtmlCrawler",
    "ItpIqCrawler",
    "get_crawler",
]
