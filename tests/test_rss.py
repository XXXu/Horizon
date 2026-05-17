"""Tests for generic RSS sources."""

import asyncio
from datetime import datetime, timezone

import httpx

from src.models import RSSSourceConfig
from src.scrapers.rss import RSSScraper


def test_rss_item_id_is_stable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>Stable RSS ID</title>
      <link>https://example.com/stable-rss-id</link>
      <pubDate>Fri, 16 May 2026 07:29:15 GMT</pubDate>
    </item>
  </channel>
</rss>
""",
        )

    async def fetch_once() -> str:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        scraper = RSSScraper(
            [
                RSSSourceConfig(
                    name="Example",
                    url="https://example.com/feed.xml",
                    category="test",
                )
            ],
            client,
        )
        items = await scraper.fetch(datetime(2026, 5, 16, tzinfo=timezone.utc))
        await client.aclose()
        return items[0].id

    first_id = asyncio.run(fetch_once())
    second_id = asyncio.run(fetch_once())

    assert first_id == second_id
    assert first_id.startswith("rss:example.com_feed.xml:")
