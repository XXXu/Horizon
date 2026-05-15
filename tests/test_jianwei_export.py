from datetime import datetime, timezone

from src.integrations.jianwei import (
    artifact_date_for_display_timezone,
    build_jianwei_artifact,
    export_jianwei_artifacts,
)
from src.models import ContentItem, SourceType


def _make_item() -> ContentItem:
    item = ContentItem(
        id="rss:example:1",
        source_type=SourceType.RSS,
        title="AI Product Signal",
        url="https://example.com/item",
        content="A useful AI product signal.",
        author="Example",
        published_at=datetime(2026, 5, 13, 8, 0, tzinfo=timezone.utc),
        metadata={
            "feed_name": "Example Feed",
            "feed_url": "https://example.com/feed.xml",
            "category": "ai",
        },
    )
    item.ai_score = 8.5
    item.ai_summary = "一个值得关注的 AI 产品信号。"
    item.ai_reason = "它说明垂直 AI 工具仍有机会。"
    item.ai_opportunities = ["做一个垂直 AI 工作流工具"]
    item.ai_risks = ["大厂可能快速跟进"]
    item.ai_tags = ["ai", "product"]
    return item


def test_build_jianwei_artifact() -> None:
    artifact = build_jianwei_artifact(_make_item(), persona_slug="indie-maker", model="test-model")

    assert artifact["source"]["type"] == "rss"
    assert artifact["source"]["name"] == "Example Feed"
    assert artifact["source"]["url"] == "https://example.com/feed.xml"
    assert artifact["item"]["external_id"] == "rss:example:1"
    assert artifact["analysis"]["persona_slug"] == "indie-maker"
    assert artifact["analysis"]["score"] == 8.5
    assert artifact["analysis"]["opportunities"] == ["做一个垂直 AI 工作流工具"]
    assert artifact["analysis"]["risks"] == ["大厂可能快速跟进"]
    assert artifact["analysis"]["tags"] == ["ai", "product"]


def test_export_jianwei_artifacts(tmp_path) -> None:
    paths = export_jianwei_artifacts(
        [_make_item()],
        output_dir=tmp_path,
        persona_slug="indie-maker",
        model="test-model",
    )

    assert len(paths) == 1
    assert paths[0].exists()
    assert paths[0].read_text(encoding="utf-8").count("AI Product Signal") == 1


def test_artifact_date_uses_china_timezone() -> None:
    utc_evening = datetime(2026, 5, 15, 17, 30, tzinfo=timezone.utc)

    assert artifact_date_for_display_timezone(utc_evening) == "2026-05-16"
