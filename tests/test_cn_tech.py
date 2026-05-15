"""Tests for domestic Chinese tech sources."""

import asyncio
from datetime import datetime, timezone

import httpx

from src.models import CnTechConfig, SourceType
from src.scrapers.cn_tech import CN_TECH_SOURCES, CnTechScraper


def _rss(title: str, link: str, published: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <description>国内 AI 产品和开发者生态观察</description>
      <author>编辑部</author>
      <pubDate>{published}</pubDate>
      <category>AI</category>
    </item>
  </channel>
</rss>
"""


def test_cn_tech_fetches_rss_sources():
    seen_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(
            200,
            text=_rss(
                "国产 AI 工具开始进入独立开发者工作流",
                "https://www.36kr.com/p/example",
                "Fri, 15 May 2026 08:00:00 GMT",
            ),
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scraper = CnTechScraper(CnTechConfig(enabled=True, sources=["36kr"], fetch_limit=10), client)

    items = asyncio.run(scraper.fetch(datetime(2026, 5, 15, tzinfo=timezone.utc)))
    asyncio.run(client.aclose())

    assert seen_urls == [CN_TECH_SOURCES["36kr"].url]
    assert len(items) == 1
    assert items[0].source_type == SourceType.KR36
    assert items[0].title == "国产 AI 工具开始进入独立开发者工作流"
    assert str(items[0].url) == "https://www.36kr.com/p/example"
    assert items[0].metadata["source_key"] == "36kr"
    assert items[0].metadata["feed_url"] == CN_TECH_SOURCES["36kr"].url
    assert items[0].metadata["tags"] == ["AI"]


def test_cn_tech_fetches_juejin_articles():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "err_no": 0,
                "data": [
                    {
                        "item_info": {
                            "article_info": {
                                "article_id": "7520000000000000000",
                                "title": "用 Python 做一个 AI 产品监控工具",
                                "brief_content": "面向独立开发者的实践记录",
                                "ctime": "1778832000",
                                "view_count": 1200,
                                "digg_count": 88,
                                "comment_count": 12,
                            },
                            "author_user_info": {"user_name": "掘金作者"},
                            "category": {"category_name": "人工智能"},
                            "tags": [{"tag_name": "Python"}, {"tag_name": "AI"}],
                        }
                    }
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scraper = CnTechScraper(CnTechConfig(enabled=True, sources=["juejin"], fetch_limit=20), client)

    items = asyncio.run(scraper.fetch(datetime(2026, 5, 15, tzinfo=timezone.utc)))
    asyncio.run(client.aclose())

    assert requests[0].method == "POST"
    assert requests[0].url.path.endswith("/recommend_api/v1/article/recommend_all_feed")
    assert len(items) == 1
    assert items[0].id == "juejin:article:7520000000000000000"
    assert items[0].source_type == SourceType.JUEJIN
    assert str(items[0].url) == "https://juejin.cn/post/7520000000000000000"
    assert items[0].author == "掘金作者"
    assert items[0].metadata["category"] == "人工智能"
    assert items[0].metadata["tags"] == ["Python", "AI"]
    assert items[0].metadata["digg_count"] == 88


def test_cn_tech_filters_disabled_old_and_unknown_sources():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=_rss(
                "旧内容",
                "https://www.infoq.cn/article/old",
                "Thu, 14 May 2026 08:00:00 GMT",
            ),
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scraper = CnTechScraper(
        CnTechConfig(enabled=True, sources=["infoq_cn", "unknown"], fetch_limit=10),
        client,
    )

    items = asyncio.run(scraper.fetch(datetime(2026, 5, 15, tzinfo=timezone.utc)))
    asyncio.run(client.aclose())

    assert items == []


def test_cn_tech_http_error_degrades_to_empty_list():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scraper = CnTechScraper(CnTechConfig(enabled=True, sources=["qbitai"]), client)

    items = asyncio.run(scraper.fetch(datetime(2026, 5, 15, tzinfo=timezone.utc)))
    asyncio.run(client.aclose())

    assert items == []
