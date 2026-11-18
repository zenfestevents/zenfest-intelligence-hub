"""Step 1 of the pipeline: fetch sources and queue new articles. Uses no LLM and needs no API key.

Claude works through the queue afterwards (see claude_queue.py).

Manual run:  python ingest.py              (all enabled feeds)
             python ingest.py "EventFAQs"  (one feed by label)
"""
import logging
import sys
from typing import Optional

import config
from database import DBIntelFeed, DBPending, DBRejected, SessionLocal
from feeds import ENABLED_FEEDS, Feed, is_event_item
from sources import entry_date, fetch_entries
from textutil import get_image, get_text, resolve_link

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hub.ingest")

# Stop queueing when this many articles are already waiting for Claude.
MAX_PENDING = 300


def _seen(db, url: str) -> bool:
    return bool(
        db.query(DBIntelFeed.id).filter(DBIntelFeed.source_url == url).first()
        or db.query(DBRejected.id).filter(DBRejected.source_url == url).first()
        or db.query(DBPending.id).filter(DBPending.source_url == url).first()
    )


def ingest_feed(feed: Feed) -> int:
    """Queue new articles from one source. Returns how many were queued."""
    queued = 0
    logger.info(f"Scanning: {feed.label}")
    try:
        entries = fetch_entries(feed)
    except Exception as e:
        logger.error(f"Source unavailable: {feed.label}: {e}")
        return 0

    entries = entries[: feed.max_entries or config.ENTRIES_PER_FEED]
    if feed.events_only:
        entries = [e for e in entries if is_event_item(e)]

    db = SessionLocal()
    try:
        for entry in entries:
            link = entry.get("link")
            if not link:
                continue
            try:
                if db.query(DBPending).count() >= MAX_PENDING:
                    logger.warning("Queue is full, stopping.")
                    return queued
                if _seen(db, link):
                    continue
                url = resolve_link(link)
                if url != link and _seen(db, url):
                    continue
                text = get_text(feed, entry, url)
                if len(text) < 200:
                    logger.info(f"Skipped (too little text): {url}")
                    continue
                db.add(
                    DBPending(
                        source_url=url,
                        source_label=feed.label[:100],
                        title=(entry.get("title") or "").strip(),
                        text=text,
                        image_url=get_image(entry, url)[:2000],
                        published_at=entry_date(entry),
                    )
                )
                db.commit()
                queued += 1
                logger.info(f"Queued: {url}")
            except Exception as e:
                db.rollback()
                logger.error(f"Error on {link}: {e}")
    finally:
        db.close()
    return queued


def run(only: Optional[str] = None) -> int:
    if not only:
        # Keep the web app's Sources page in step with feeds.py. Never let it stop collecting.
        try:
            from sources_sync import sync_sources
            logger.info(f"Source list synced: {sync_sources()} sources")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Source list sync failed (collecting anyway): {exc}")
    total = 0
    for feed in ENABLED_FEEDS:
        if feed.scan_only:
            continue
        if only and feed.label.lower() != only.lower():
            continue
        total += ingest_feed(feed)
    logger.info(f"Ingest done: {total} new articles queued")
    return total


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
