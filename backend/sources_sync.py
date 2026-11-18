"""Copy the source list in feeds.py into the zf_sources table (2026-11-18).

The web app shows it at /admin/intelligence/sources (every Zenfest team login), joined with how many
items each source brought in. ingest.py calls sync_sources() at the start of every run, so the page
follows feeds.py within 30 minutes of a push. Run by hand: python sources_sync.py

Sources removed from feeds.py stay in the table with listed=False (their old items keep a region).
The private RSSHub address is never stored: RSSHub sources keep only their path.
"""
import logging
from typing import Dict, List

from sqlalchemy import text

from database import SessionLocal, utcnow
from feeds import FEEDS, INSTAGRAM_ACCOUNTS, INSTAGRAM_HASHTAGS, RSSHUB_URL

logger = logging.getLogger(__name__)


def _kind_and_url(url: str):
    if RSSHUB_URL and url.startswith(RSSHUB_URL):
        return "rsshub", url[len(RSSHUB_URL):] or "/"
    if url.startswith("/"):  # RSSHub off: rsshub() returned the bare path
        return "rsshub", url
    if "bing.com/news" in url:
        return "search", url
    return "rss", url


def source_rows() -> List[Dict]:
    rows: List[Dict] = []
    for f in FEEDS:
        kind, url = _kind_and_url(f.url)
        rows.append(dict(label=f.label, region=f.group, kind=kind, url=url, enabled=f.enabled,
                         events_only=f.events_only, scan_only=f.scan_only, interval_min=f.interval_min,
                         note=f.note))
    for region, handles in INSTAGRAM_ACCOUNTS.items():
        for h in handles:
            rows.append(dict(label=f"Instagram @{h}", region=region, kind="instagram_account",
                             url=f"https://www.instagram.com/{h}/", enabled=True, events_only=False,
                             scan_only=False, interval_min=2 * 24 * 60, note="Read through Apify every 2 days."))
    for region, tags in INSTAGRAM_HASHTAGS.items():
        for t in tags:
            rows.append(dict(label=f"Instagram #{t}", region=region, kind="instagram_hashtag",
                             url=f"https://www.instagram.com/explore/tags/{t}/", enabled=True,
                             events_only=False, scan_only=False, interval_min=7 * 24 * 60,
                             note="Read through Apify on Mondays."))
    return rows


def sync_sources() -> int:
    rows = source_rows()
    now = utcnow()
    with SessionLocal() as session:
        session.execute(text("UPDATE zf_sources SET listed = FALSE"))
        for r in rows:
            session.execute(
                text("""
                    INSERT INTO zf_sources (label, region, kind, url, enabled, events_only, scan_only,
                                            interval_min, note, listed, updated_at)
                    VALUES (:label, :region, :kind, :url, :enabled, :events_only, :scan_only,
                            :interval_min, :note, TRUE, :now)
                    ON CONFLICT (label) DO UPDATE SET
                        region = EXCLUDED.region, kind = EXCLUDED.kind, url = EXCLUDED.url,
                        enabled = EXCLUDED.enabled, events_only = EXCLUDED.events_only,
                        scan_only = EXCLUDED.scan_only, interval_min = EXCLUDED.interval_min,
                        note = EXCLUDED.note, listed = TRUE, updated_at = EXCLUDED.updated_at
                """),
                {**r, "now": now},
            )
        session.commit()
    return len(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"{sync_sources()} sources written to zf_sources.")
