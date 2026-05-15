import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from src.models import SourceType, V2EXConfig
from src.scrapers.v2ex import V2EX_HEADERS, V2EXScraper


def test_v2ex_default_nodes_use_existing_ai_related_node() -> None:
    config = V2EXConfig()

    assert "openai" in config.nodes
    assert "ai" not in config.nodes


def _topic_payload(created: datetime | None = None, replies: int = 3) -> list[dict]:
    created_at = created or datetime.now(timezone.utc)
    return [
        {
            "id": 123,
            "title": "有没有适合独立开发者的 AI 工具方向？",
            "url": "https://www.v2ex.com/t/123",
            "content_rendered": "<p>想听听大家最近遇到的真实需求。</p>",
            "created": int(created_at.timestamp()),
            "replies": replies,
            "member": {"username": "maker"},
            "node": {"name": "create", "title": "分享创造"},
            "last_touched": int(created_at.timestamp()),
        }
    ]


def test_v2ex_fetches_node_topics() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_topic_payload())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scraper = V2EXScraper(
        V2EXConfig(enabled=True, nodes=["create"], fetch_limit=10, min_replies=0),
        client,
    )

    items = asyncio.run(scraper.fetch(datetime.now(timezone.utc) - timedelta(hours=1)))
    asyncio.run(client.aclose())

    assert len(items) == 1
    assert requests[0].url.params["node_name"] == "create"
    assert requests[0].headers["user-agent"] == V2EX_HEADERS["User-Agent"]
    assert items[0].source_type == SourceType.V2EX
    assert items[0].id == "v2ex:topic:123"
    assert items[0].title == "有没有适合独立开发者的 AI 工具方向？"
    assert items[0].author == "maker"
    assert items[0].metadata["node"] == "create"
    assert items[0].metadata["replies"] == 3
    assert "真实需求" in (items[0].content or "")


def test_v2ex_filters_old_or_low_reply_topics() -> None:
    old_time = datetime.now(timezone.utc) - timedelta(days=3)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_topic_payload(created=old_time, replies=0))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scraper = V2EXScraper(
        V2EXConfig(enabled=True, nodes=["create"], fetch_limit=10, min_replies=1),
        client,
    )

    items = asyncio.run(scraper.fetch(datetime.now(timezone.utc) - timedelta(hours=24)))
    asyncio.run(client.aclose())

    assert items == []


def test_v2ex_http_error_degrades_to_empty_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="blocked")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scraper = V2EXScraper(V2EXConfig(enabled=True, nodes=["ai"]), client)

    items = asyncio.run(scraper.fetch(datetime.now(timezone.utc) - timedelta(hours=1)))
    asyncio.run(client.aclose())

    assert items == []


def test_v2ex_http_error_logs_status_and_body(caplog) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Object Not Found"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scraper = V2EXScraper(V2EXConfig(enabled=True, nodes=["ai"]), client)

    items = asyncio.run(scraper.fetch(datetime.now(timezone.utc) - timedelta(hours=1)))
    asyncio.run(client.aclose())

    assert items == []
    assert "status=404" in caplog.text
    assert "Object Not Found" in caplog.text
