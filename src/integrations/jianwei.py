"""Export Horizon items as Jianwei import artifacts."""

import argparse
import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from rich.console import Console

from src.models import Config, ContentItem
from src.orchestrator import HorizonOrchestrator
from src.storage.manager import StorageManager

console = Console()


def build_jianwei_artifact(item: ContentItem, *, persona_slug: str, model: str) -> dict[str, Any]:
    """Convert one Horizon item into the JSON shape expected by Jianwei."""
    return {
        "source": {
            "type": item.source_type.value,
            "name": _source_name(item),
            "url": _source_url(item),
            "config": _source_config(item),
        },
        "item": {
            "external_id": item.id,
            "title": item.title,
            "url": str(item.url),
            "content": item.content,
            "author": item.author,
            "published_at": item.published_at.isoformat(),
            "metadata": item.metadata,
        },
        "analysis": {
            "persona_slug": persona_slug,
            "score": float(item.ai_score or 0),
            "summary": item.ai_summary or item.title,
            "why_it_matters": item.ai_reason or item.ai_summary or item.title,
            "opportunities": [],
            "risks": [],
            "tags": item.ai_tags,
            "model": model,
        },
    }


def export_jianwei_artifacts(
    items: list[ContentItem],
    *,
    output_dir: Path,
    persona_slug: str,
    model: str,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, item in enumerate(items, start=1):
        artifact = build_jianwei_artifact(item, persona_slug=persona_slug, model=model)
        filename = f"{index:03d}-{_slugify(item.title)}.json"
        path = output_dir / filename
        path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(path)
    return paths


async def run_export(args: argparse.Namespace) -> list[Path]:
    load_dotenv()
    storage = StorageManager(data_dir="data")
    config = storage.load_config()
    orchestrator = HorizonOrchestrator(config, storage)

    since = orchestrator._determine_time_window(args.hours)
    console.print(f"📅 Fetching content since: {since.strftime('%Y-%m-%d %H:%M:%S')}")

    fetched_items = await orchestrator.fetch_all_sources(since)
    console.print(f"📥 Fetched {len(fetched_items)} items")
    if not fetched_items:
        return []

    merged_items = orchestrator.merge_cross_source_duplicates(fetched_items)
    analyzed_items = await orchestrator._analyze_content(merged_items)
    important_items = _filter_items(analyzed_items, config, args.min_score)
    important_items = important_items[: args.limit]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_dir = Path(args.output_dir) / today / args.persona_slug
    paths = export_jianwei_artifacts(
        important_items,
        output_dir=output_dir,
        persona_slug=args.persona_slug,
        model=config.ai.model,
    )
    console.print(f"💾 Exported {len(paths)} Jianwei artifacts to: {output_dir}")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Horizon results for Jianwei import")
    parser.add_argument("--hours", type=int, default=None, help="Fetch from last N hours")
    parser.add_argument("--persona-slug", default="indie-maker", help="Target Jianwei persona slug")
    parser.add_argument("--output-dir", default="data/jianwei_artifacts", help="Artifact output root")
    parser.add_argument("--limit", type=int, default=20, help="Maximum artifacts to export")
    parser.add_argument("--min-score", type=float, default=None, help="Override AI score threshold")
    args = parser.parse_args()
    asyncio.run(run_export(args))


def _filter_items(items: list[ContentItem], config: Config, min_score: float | None) -> list[ContentItem]:
    threshold = min_score if min_score is not None else config.filtering.ai_score_threshold
    important_items = [item for item in items if item.ai_score and item.ai_score >= threshold]
    important_items.sort(key=lambda item: item.ai_score or 0, reverse=True)
    return important_items


def _source_name(item: ContentItem) -> str:
    return (
        item.metadata.get("feed_name")
        or item.metadata.get("subreddit")
        or item.metadata.get("channel")
        or item.metadata.get("repo")
        or item.source_type.value
    )


def _source_url(item: ContentItem) -> str:
    return (
        item.metadata.get("feed_url")
        or item.metadata.get("discussion_url")
        or item.metadata.get("repo_url")
        or str(item.url)
    )


def _source_config(item: ContentItem) -> dict[str, Any]:
    config = dict(item.metadata)
    config.pop("feed_name", None)
    config.pop("feed_url", None)
    return config


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value).strip("-").lower()
    return slug[:80] or "item"


if __name__ == "__main__":
    main()
