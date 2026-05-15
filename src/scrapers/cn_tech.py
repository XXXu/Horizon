"""Domestic Chinese tech source scraper implementation."""

import calendar
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, List

import feedparser
import httpx

from .base import BaseScraper
from ..models import CnTechConfig, ContentItem, SourceType

logger = logging.getLogger(__name__)


CN_TECH_HEADERS = {
    "User-Agent": "HorizonBot/1.0 (+https://github.com/yourname/horizon)",
    "Accept": "application/rss+xml,application/atom+xml,application/json,text/xml,*/*",
}

JUEJIN_API_URL = "https://api.juejin.cn/recommend_api/v1/article/recommend_all_feed"


@dataclass(frozen=True)
class CnTechSource:
    """Definition for one domestic tech source."""

    key: str
    name: str
    url: str
    source_type: SourceType
    category: str
    kind: str = "rss"


CN_TECH_SOURCES: dict[str, CnTechSource] = {
    "36kr": CnTechSource(
        key="36kr",
        name="36氪",
        url="https://36kr.com/feed",
        source_type=SourceType.KR36,
        category="business-tech",
    ),
    "infoq_cn": CnTechSource(
        key="infoq_cn",
        name="InfoQ 中文",
        url="https://feed.infoq.com/cn",
        source_type=SourceType.INFOQ_CN,
        category="software-engineering",
    ),
    "juejin": CnTechSource(
        key="juejin",
        name="掘金",
        url=JUEJIN_API_URL,
        source_type=SourceType.JUEJIN,
        category="developer-community",
        kind="juejin",
    ),
    "geekpark": CnTechSource(
        key="geekpark",
        name="极客公园",
        url="https://www.geekpark.net/rss",
        source_type=SourceType.GEEKPARK,
        category="product-innovation",
    ),
    "qbitai": CnTechSource(
        key="qbitai",
        name="量子位",
        url="https://www.qbitai.com/feed",
        source_type=SourceType.QBITAI,
        category="ai",
    ),
}


class CnTechScraper(BaseScraper):
    """Scraper for domestic Chinese tech media and developer sources."""

    def __init__(self, config: CnTechConfig, http_client: httpx.AsyncClient):
        super().__init__(config, http_client)

    async def fetch(self, since: datetime) -> List[ContentItem]:
        """Fetch domestic tech source items."""

        if not self.config.enabled:
            return []

        items: list[ContentItem] = []
        for source_key in self.config.sources:
            source = CN_TECH_SOURCES.get(source_key)
            if source is None:
                logger.warning("Unknown cn_tech source: %s", source_key)
                continue

            if source.kind == "juejin":
                source_items = await self._fetch_juejin(source, since)
            else:
                source_items = await self._fetch_rss_source(source, since)
            items.extend(source_items[: self.config.fetch_limit])

        return items

    async def _fetch_rss_source(
        self, source: CnTechSource, since: datetime
    ) -> list[ContentItem]:
        """Fetch one RSS/Atom source."""

        try:
            response = await self.client.get(
                source.url,
                follow_redirects=True,
                headers=CN_TECH_HEADERS,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Error fetching %s feed: %s", source.name, exc)
            return []

        feed = feedparser.parse(response.text)
        items: list[ContentItem] = []
        for entry in feed.entries:
            published_at = self._parse_feed_date(entry)
            if not published_at or published_at < since:
                continue

            entry_id = entry.get("id", entry.get("guid", entry.get("link", "")))
            url = entry.get("link", source.url)
            item = ContentItem(
                id=self._generate_id(source.source_type.value, "article", str(hash(entry_id))),
                source_type=source.source_type,
                title=entry.get("title", "Untitled"),
                url=url,
                content=self._extract_feed_content(entry),
                author=entry.get("author", source.name),
                published_at=published_at,
                metadata={
                    "source_key": source.key,
                    "source_name": source.name,
                    "feed_url": source.url,
                    "category": source.category,
                    "tags": [tag.term for tag in entry.get("tags", [])],
                },
            )
            items.append(item)

        return items

    async def _fetch_juejin(self, source: CnTechSource, since: datetime) -> list[ContentItem]:
        """Fetch Juejin recommended articles through its public web API."""

        payload = {
            "id_type": 2,
            "client_type": 2608,
            "sort_type": 200,
            "cursor": "0",
            "limit": self.config.fetch_limit,
        }
        try:
            response = await self.client.post(
                source.url,
                json=payload,
                follow_redirects=True,
                headers=CN_TECH_HEADERS,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Error fetching %s articles: %s", source.name, exc)
            return []

        if data.get("err_no") not in (0, None):
            logger.warning("Error response from %s: %s", source.name, data.get("err_msg"))
            return []

        items: list[ContentItem] = []
        for raw_item in data.get("data", []):
            item = self._parse_juejin_item(source, raw_item)
            if item and item.published_at >= since:
                items.append(item)
        return items

    def _parse_juejin_item(
        self, source: CnTechSource, raw_item: dict[str, Any]
    ) -> ContentItem | None:
        """Parse one Juejin API item."""

        item_info = raw_item.get("item_info", raw_item)
        article = item_info.get("article_info") or raw_item.get("article_info")
        if not article:
            return None

        article_id = str(article.get("article_id") or "")
        if not article_id:
            return None

        published_at = self._parse_timestamp(article.get("ctime") or article.get("mtime"))
        tags = [
            tag.get("tag_name")
            for tag in item_info.get("tags", [])
            if isinstance(tag, dict) and tag.get("tag_name")
        ]
        author_info = item_info.get("author_user_info", {})
        category_info = item_info.get("category", {})

        return ContentItem(
            id=self._generate_id(source.source_type.value, "article", article_id),
            source_type=source.source_type,
            title=article.get("title", "Untitled"),
            url=f"https://juejin.cn/post/{article_id}",
            content=article.get("brief_content") or article.get("mark_content") or "",
            author=author_info.get("user_name") or source.name,
            published_at=published_at,
            metadata={
                "source_key": source.key,
                "source_name": source.name,
                "api_url": source.url,
                "category": category_info.get("category_name") or source.category,
                "tags": tags,
                "view_count": article.get("view_count", 0),
                "digg_count": article.get("digg_count", 0),
                "comment_count": article.get("comment_count", 0),
                "collect_count": article.get("collect_count", 0),
            },
        )

    def _parse_feed_date(self, entry: dict[str, Any]) -> datetime | None:
        """Parse date from RSS/Atom entry."""

        for field in ("published", "updated", "created"):
            parsed_field = f"{field}_parsed"
            if parsed_field in entry and entry[parsed_field]:
                return datetime.fromtimestamp(calendar.timegm(entry[parsed_field]), tz=timezone.utc)
            if field in entry:
                try:
                    parsed = parsedate_to_datetime(entry[field])
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return parsed
                except (TypeError, ValueError):
                    continue
        return None

    def _parse_timestamp(self, value: Any) -> datetime:
        """Parse Unix timestamp values from APIs."""

        try:
            timestamp = int(value)
        except (TypeError, ValueError):
            return datetime.now(timezone.utc)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def _extract_feed_content(self, entry: dict[str, Any]) -> str:
        """Extract text content from feed entry."""

        if entry.get("summary"):
            return entry.summary
        if entry.get("description"):
            return entry.description
        if entry.get("content"):
            return entry.content[0].get("value", "")
        return ""
