from app.crawlers.baghdad import BaghdadCrawler
from app.crawlers.base import BaseCrawler
from app.crawlers.generic_html import GenericHtmlCrawler
from app.crawlers.itp_iq import ItpIqCrawler
from app.crawlers.ministry_cms import MinistryCmsCrawler
from app.crawlers.mohesr import MohesrCrawler
from app.crawlers.src import SrcCrawler
from app.domain.enums import CrawlerType


def get_crawler(crawler_type: str, base_url: str = "") -> BaseCrawler:
    normalized = (crawler_type or "").lower()
    base = (base_url or "").lower()

    mapping = {
        CrawlerType.ITP_IQ.value: ItpIqCrawler,
        "itp": ItpIqCrawler,
        CrawlerType.MOHESR.value: MohesrCrawler,
        CrawlerType.BAGHDAD.value: BaghdadCrawler,
        CrawlerType.SRC.value: SrcCrawler,
        CrawlerType.MINISTRY_CMS.value: MinistryCmsCrawler,
    }
    if normalized in mapping:
        return mapping[normalized]()

    if "itp.iq" in base:
        return ItpIqCrawler()
    if "mohesr.gov.iq" in base:
        return MohesrCrawler()
    if "baghdad.gov.iq" in base:
        return BaghdadCrawler()
    if "src.gov.iq" in base:
        return SrcCrawler()
    if any(
        x in base
        for x in (
            "moh.gov.iq",
            "moelc.gov.iq",
            "boc.oil.gov.iq",
            "mdoc.oil.gov.iq",
            "fbsa.gov.iq",
            "mot.gov.iq",
            "mod.mil.iq",
        )
    ):
        return MinistryCmsCrawler()

    return GenericHtmlCrawler()
