"""Turning a feed entry into clean article text. No LLM, no database.

Moved out of the AI Hub's worker.py (whose Gemini path this project does not use).
"""
import html
import logging
import re
from typing import Optional

import httpx
import trafilatura

import config
from feeds import Feed

logger = logging.getLogger("hub.text")
_TAGS = re.compile(r"<[^>]+>")


def html_to_text(fragment: str) -> str:
    text = _TAGS.sub(" ", fragment or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def entry_body(entry) -> str:
    """Text carried inside the feed entry itself."""
    parts = [c.get("value", "") for c in entry.get("content", [])] or [entry.get("summary", "")]
    body = html_to_text(" ".join(parts))
    title = entry.get("title", "").strip()
    return f"{title}\n\n{body}" if body else ""


def resolve_link(url: str) -> str:
    """Bing News links are click-trackers that redirect to the article. Store the real address,
    so the same story is recognised as already seen and the dashboard links to the publisher."""
    if "bing.com/news/apiclick" not in url:
        return url
    try:
        r = httpx.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=20, follow_redirects=True)
        return str(r.url)
    except Exception as e:
        logger.warning(f"Could not resolve {url[:80]}: {e}")
        return url


# Main picture (og:image) of each page fetched in this run, for the owner's feed (2026-11-18).
_PAGE_IMAGES: dict = {}


def _clean_image(src) -> str:
    src = (src or "").strip()
    return src if src.startswith("https://") or src.startswith("http://") else ""


def page_image_from_html(downloaded: str) -> str:
    try:
        meta = trafilatura.extract_metadata(downloaded)
        return _clean_image(getattr(meta, "image", "") if meta else "")
    except Exception:  # noqa: BLE001
        return ""


def fetch_page_text(url: str) -> Optional[str]:
    """Downloads a web page and returns its main text (and remembers its main picture)."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            _PAGE_IMAGES[url] = page_image_from_html(downloaded)
            return trafilatura.extract(downloaded, include_comments=False, include_tables=True)
    except Exception as e:
        logger.error(f"Error fetching URL {url}: {e}")
    return None


def fetch_page_image(url: str) -> str:
    """Downloads a page only for its main picture (used by images_backfill.py)."""
    try:
        downloaded = trafilatura.fetch_url(url)
        return page_image_from_html(downloaded) if downloaded else ""
    except Exception:  # noqa: BLE001
        return ""


def get_image(entry, url: str) -> str:
    """The article's main picture: the page's og:image if we downloaded it, else one inside the feed entry."""
    found = _PAGE_IMAGES.pop(url, "")
    if found:
        return found
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key) or []:
            src = _clean_image(m.get("url"))
            if src:
                return src
    for link in entry.get("links") or []:
        if (link.get("type") or "").startswith("image/"):
            src = _clean_image(link.get("href"))
            if src:
                return src
    return ""


def get_text(feed: Feed, entry, url: str) -> str:
    text = ""
    if feed.text_from == "page":
        text = fetch_page_text(url) or ""
    if len(text) < 200:
        text = entry_body(entry)
    return text[: config.MAX_ARTICLE_CHARS]
