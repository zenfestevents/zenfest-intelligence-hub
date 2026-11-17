"""Turns any source in the catalog into a list of feed-like entries (all RSS/Atom so far)."""
import calendar
import datetime

import feedparser
import httpx

import config
from feeds import RSSHUB_URL, Feed

HEADERS = {"User-Agent": config.USER_AGENT}


def _get(url: str) -> httpx.Response:
    # The self-hosted RSSHub runs on a small free server that sleeps when idle and builds
    # each feed on request, so it needs far longer than an ordinary feed.
    timeout = 120 if RSSHUB_URL and url.startswith(RSSHUB_URL) else 20
    r = httpx.get(url, headers=HEADERS, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return r


def fetch_entries(feed: Feed) -> list:
    """Downloads a source and returns its entries (newest first). Raises on network errors."""
    return feedparser.parse(_get(feed.url).content).entries


def entry_date(entry) -> datetime.datetime:
    """When a feed entry was published (falls back to now). Needs no database, so daily_scan can use it."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.datetime.fromtimestamp(calendar.timegm(t), tz=datetime.timezone.utc)
    return datetime.datetime.now(datetime.timezone.utc)
