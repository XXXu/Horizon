import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import src.ai.analyzer as analyzer_module
from src.ai.prompts import CONTENT_ANALYSIS_SYSTEM, CONTENT_ANALYSIS_USER
from src.ai.analyzer import ContentAnalyzer
from src.models import ContentItem, SourceType


def _make_item(item_id: str) -> ContentItem:
    return ContentItem(
        id=item_id,
        source_type=SourceType.RSS,
        title=f"Item {item_id}",
        url="https://example.com/item",
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )


def test_analyze_batch_does_not_sleep_by_default(monkeypatch):
    analyzer = ContentAnalyzer(SimpleNamespace())
    items = [_make_item("rss:test:1"), _make_item("rss:test:2")]
    sleep_calls = []

    async def fake_analyze_item(item):
        item.ai_score = 8.0

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(analyzer, "_analyze_item", fake_analyze_item)
    monkeypatch.setattr(analyzer_module.asyncio, "sleep", fake_sleep)

    result = asyncio.run(analyzer.analyze_batch(items))

    assert len(result) == 2
    assert sleep_calls == []


def test_analyze_batch_sleeps_between_items_when_throttle_configured(monkeypatch):
    client = SimpleNamespace(config=SimpleNamespace(throttle_sec=1.5))
    analyzer = ContentAnalyzer(client)
    items = [_make_item("rss:test:1"), _make_item("rss:test:2"), _make_item("rss:test:3")]
    sleep_calls = []

    async def fake_analyze_item(item):
        item.ai_score = 8.0

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(analyzer, "_analyze_item", fake_analyze_item)
    monkeypatch.setattr(analyzer_module.asyncio, "sleep", fake_sleep)

    asyncio.run(analyzer.analyze_batch(items))

    assert sleep_calls == [1.5, 1.5]


def test_analyze_batch_concurrent_processing(monkeypatch):
    """Verify that higher concurrency allows overlapping item processing."""
    client = SimpleNamespace(config=SimpleNamespace(analysis_concurrency=3))
    analyzer = ContentAnalyzer(client)
    items = [_make_item(f"rss:test:{i}") for i in range(5)]
    active_count = 0
    max_active = 0

    async def fake_analyze_item(item):
        nonlocal active_count, max_active
        active_count += 1
        max_active = max(max_active, active_count)
        await asyncio.sleep(0.05)  # Small delay to allow overlap
        active_count -= 1

    monkeypatch.setattr(analyzer, "_analyze_item", fake_analyze_item)

    asyncio.run(analyzer.analyze_batch(items))

    assert max_active == 3
    assert all(item.ai_score is None for item in items)  # None because fake_analyze_item doesn't set it


def test_analyze_batch_concurrent_preserves_order(monkeypatch):
    """Verify that analyze_batch preserves input order in results."""
    client = SimpleNamespace(config=SimpleNamespace(analysis_concurrency=3))
    analyzer = ContentAnalyzer(client)
    items = [_make_item(f"rss:test:{i}") for i in range(5)]

    async def fake_analyze_item(item):
        item.ai_score = float(item.id.split(":")[-1]) * 10

    monkeypatch.setattr(analyzer, "_analyze_item", fake_analyze_item)

    result = asyncio.run(analyzer.analyze_batch(items))

    assert [item.id for item in result] == [item.id for item in items]


def test_analyze_item_sets_opportunities_and_risks() -> None:
    client = SimpleNamespace()

    async def fake_complete(**_):
        return """
        {
          "score": 8.0,
          "reason": "开发者工具需求明确。",
          "summary": "一个新的 AI 开发者工具发布。",
          "opportunities": ["围绕垂直场景做更轻量的替代品"],
          "risks": ["通用平台可能快速覆盖该能力"],
          "tags": ["ai", "developer tools"]
        }
        """

    client.complete = fake_complete
    analyzer = ContentAnalyzer(client)
    item = _make_item("rss:test:analysis")

    asyncio.run(analyzer._analyze_item(item))

    assert item.ai_score == 8.0
    assert item.ai_opportunities == ["围绕垂直场景做更轻量的替代品"]
    assert item.ai_risks == ["通用平台可能快速覆盖该能力"]


def test_content_analysis_prompt_requires_chinese_output() -> None:
    prompt_text = CONTENT_ANALYSIS_SYSTEM + CONTENT_ANALYSIS_USER

    assert "「见微」是一个面向独立开发者和 AI 产品创业者的情报筛选产品" in prompt_text
    assert "简体中文" in prompt_text
    assert "English source" in prompt_text
    assert "不要直接复制英文句子" in prompt_text
    assert "不要把「关键信号」写成" in prompt_text
    assert "不要把「摘要」写成创业建议" in prompt_text
    assert "不要把「可做机会」写成空泛建议" in prompt_text
    assert "reason: 「关键信号」" in prompt_text
    assert "summary: 「摘要」" in prompt_text
    assert "opportunities: 「可做机会」" in prompt_text
    assert "risks: 「风险提醒」" in prompt_text
    assert "tags: 「标签」" in prompt_text
