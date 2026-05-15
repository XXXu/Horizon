"""V2EX scraper implementation."""

import logging
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any

import httpx

from .base import BaseScraper
from ..models import ContentItem, SourceType, V2EXConfig

logger = logging.getLogger(__name__)

V2EX_HEADERS = {
    "User-Agent": "HorizonBot/1.0 (+https://github.com/yourname/horizon)",
    "Accept": "application/json",
}


class V2EXScraper(BaseScraper):
    """Scraper for public V2EX node topics."""

    def __init__(self, config: V2EXConfig, http_client: httpx.AsyncClient):
        super().__init__(config.model_dump(), http_client)
        self.base_url = "https://www.v2ex.com/api/topics/show.json"

    async def fetch(self, since: datetime) -> list[ContentItem]:
        if not self.config.get("enabled", False):
            return []

        nodes = [node.strip() for node in self.config.get("nodes", []) if node.strip()]
        if not nodes:
            return []

        items: list[ContentItem] = []
        for node_name in nodes:
            topics = await self._fetch_node_topics(node_name)
            for topic in topics[: self.config.get("fetch_limit", 20)]:
                item = self._parse_topic(topic, node_name)
                if item is None:
                    continue
                if item.published_at < since:
                    continue
                if item.metadata.get("replies", 0) < self.config.get("min_replies", 0):
                    continue
                items.append(item)

        return items

    async def _fetch_node_topics(self, node_name: str) -> list[dict[str, Any]]:
        try:
            response = await self.client.get(
                self.base_url,
                params={"node_name": node_name},
                headers=V2EX_HEADERS,
            )
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, list) else []
        except httpx.HTTPError as exc:
            logger.warning("Error fetching V2EX node %s: %s", node_name, exc)
            return []

    def _parse_topic(self, topic: dict[str, Any], fallback_node: str) -> ContentItem | None:
        topic_id = topic.get("id")
        title = topic.get("title")
        if not topic_id or not title:
            return None

        node = topic.get("node") or {}
        member = topic.get("member") or {}
        node_name = node.get("name") or fallback_node
        node_title = node.get("title") or node_name
        url = topic.get("url") or f"https://www.v2ex.com/t/{topic_id}"
        published_at = _timestamp_to_datetime(topic.get("created"))
        content = _clean_html(topic.get("content") or topic.get("content_rendered") or "")

        return ContentItem(
            id=self._generate_id("v2ex", "topic", str(topic_id)),
            source_type=SourceType.V2EX,
            title=title,
            url=url,
            content=content,
            author=member.get("username"),
            published_at=published_at,
            metadata={
                "node": node_name,
                "node_title": node_title,
                "replies": topic.get("replies", 0),
                "last_touched": topic.get("last_touched"),
                "last_modified": topic.get("last_modified"),
                "source_url": f"https://www.v2ex.com/go/{node_name}",
            },
        )


def _timestamp_to_datetime(value: Any) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return datetime.now(timezone.utc)


def _clean_html(value: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()
