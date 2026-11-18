"""Queues new Instagram posts from event pages and hashtags, using Apify (Instagram has no free feed).

Takes the place of the AI Hub's x_ingest.py. Two official Apify actors, pay per result:
  apify/instagram-profile-scraper  $0.0026 per profile (comes with its ~12 latest posts)
  apify/instagram-hashtag-scraper  $0.0026 per post

The accounts and hashtags are in feeds.py (INSTAGRAM_ACCOUNTS / INSTAGRAM_HASHTAGS).
Budget (owner, 2026-11-17): stay inside Apify's free $5 a month. So:
  - profiles run every 2 days (~31 profiles x 15 runs = about $1.20 a month)
  - hashtags run once a week (5 tags x 10 posts x ~4.3 = about $0.56 a month)
  - before every run the script asks Apify how much this month has used; if the run could push it
    past APIFY_MONTHLY_CAP_USD (default $4.50) it does not start
  - each run also carries Apify's own hard limit (maxTotalChargeUsd), so one run can never overspend
Only public posts are read, logged out. The script never logs in to Instagram.
Posts are used as topic ideas only: we never repost anyone's photos or videos.

Usage: python instagram_ingest.py profiles            run the accounts
       python instagram_ingest.py hashtags            run the hashtags
       python instagram_ingest.py profiles --dry-run  show what would run and its cost, spend nothing
       python instagram_ingest.py budget              show this month's Apify usage
"""
import datetime
import json
import logging
import sys
from typing import Dict, List, Tuple

import httpx

import config
from feeds import INSTAGRAM_ACCOUNTS, INSTAGRAM_HASHTAGS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hub.instagram")

API = "https://api.apify.com/v2"
PROFILE_ACTOR = "apify~instagram-profile-scraper"
HASHTAG_ACTOR = "apify~instagram-hashtag-scraper"
PRICE_PER_RESULT = 0.0026  # free-tier price for both actors (checked 2026-11-17)
POSTS_PER_HASHTAG = 10
# Posts older than this are ignored (profiles return their ~12 latest posts, some weeks old).
MAX_POST_AGE_DAYS = 7
# Captions shorter than this cannot hold a 40-character verbatim quote plus context.
MIN_TEXT_CHARS = 80


def _headers() -> Dict[str, str]:
    if not config.APIFY_TOKEN:
        raise RuntimeError("APIFY_TOKEN is not set in backend/.env (or as a GitHub secret)")
    return {"Authorization": f"Bearer {config.APIFY_TOKEN}"}


def month_usage_usd() -> float:
    """What the Apify account has used so far this billing month, from Apify itself."""
    r = httpx.get(f"{API}/users/me/limits", headers=_headers(), timeout=30)
    r.raise_for_status()
    return float(r.json()["data"]["current"]["monthlyUsageUsd"])


def plan(kind: str) -> Tuple[str, dict, int, float]:
    """Returns (actor, input, targets, worst-case cost) for a run kind."""
    if kind == "profiles":
        names = [h for handles in INSTAGRAM_ACCOUNTS.values() for h in handles]
        return PROFILE_ACTOR, {"usernames": names}, len(names), len(names) * PRICE_PER_RESULT
    if kind == "hashtags":
        tags = [t for ts in INSTAGRAM_HASHTAGS.values() for t in ts]
        inp = {"hashtags": tags, "resultsType": "posts", "resultsLimit": POSTS_PER_HASHTAG}
        return HASHTAG_ACTOR, inp, len(tags), len(tags) * POSTS_PER_HASHTAG * PRICE_PER_RESULT
    raise SystemExit("Say 'profiles' or 'hashtags'.")


def run_actor(actor: str, actor_input: dict, max_charge: float) -> Tuple[List[dict], float]:
    """Runs an actor, waits for it, returns (items, real cost in USD)."""
    r = httpx.post(
        f"{API}/acts/{actor}/runs",
        params={"waitForFinish": 240, "maxTotalChargeUsd": round(max_charge, 2)},
        headers=_headers(),
        json=actor_input,
        timeout=300,
    )
    r.raise_for_status()
    run = r.json()["data"]
    # A long run may still be going after the wait; poll a few more times.
    for _ in range(10):
        if run.get("status") in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        r = httpx.get(f"{API}/actor-runs/{run['id']}", params={"waitForFinish": 60}, headers=_headers(), timeout=90)
        r.raise_for_status()
        run = r.json()["data"]
    items = httpx.get(
        f"{API}/datasets/{run['defaultDatasetId']}/items", params={"clean": "true"}, headers=_headers(), timeout=120
    ).json()
    cost = float(run.get("usageTotalUsd") or 0)
    logger.info(f"{actor}: status {run.get('status')}, {len(items)} items, cost ${cost:.4f}")
    return items, cost


def _when(value) -> datetime.datetime:
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(datetime.timezone.utc)
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc)


def posts_from(kind: str, items: List[dict]) -> List[dict]:
    """Flattens Apify output into posts: url, label, author, text, published_at."""
    posts = []
    if kind == "profiles":
        for profile in items:
            handle = profile.get("username") or ""
            for p in profile.get("latestPosts") or []:
                posts.append({"url": p.get("url"), "label": f"Instagram @{handle}", "author": handle,
                              "text": p.get("caption") or "", "published_at": _when(p.get("timestamp")),
                              "image": p.get("displayUrl") or ""})
    else:
        tag_of = {}
        for ts in INSTAGRAM_HASHTAGS.values():
            tag_of.update({t.lower(): t for t in ts})
        for p in items:
            tag = (p.get("inputUrl") or "").rstrip("/").split("/")[-1].lower()
            label = f"Instagram #{tag_of.get(tag, tag or 'hashtag')}"
            posts.append({"url": p.get("url"), "label": label, "author": p.get("ownerUsername") or "",
                          "text": p.get("caption") or "", "published_at": _when(p.get("timestamp")),
                          "image": p.get("displayUrl") or ""})
    return [p for p in posts if p["url"]]


def run(kind: str, dry_run: bool = False) -> int:
    actor, actor_input, targets, worst = plan(kind)
    used = month_usage_usd() if config.APIFY_TOKEN else 0.0
    print(f"{kind}: {targets} targets, worst case ${worst:.3f}. Apify used this month: ${used:.2f} "
          f"of the ${config.APIFY_MONTHLY_CAP_USD:.2f} cap.")
    if dry_run:
        print(json.dumps({"actor": actor, "input": actor_input}, indent=2))
        return 0
    if used + worst > config.APIFY_MONTHLY_CAP_USD:
        logger.warning("Skipped: this run could go over the monthly cap. Nothing was spent.")
        return 0

    from database import DBApifyRun, DBIntelFeed, DBPending, DBRejected, SessionLocal

    items, cost = run_actor(actor, actor_input, worst * 1.2)
    posts = posts_from(kind, items)
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=MAX_POST_AGE_DAYS)
    queued = 0
    db = SessionLocal()
    try:
        db.add(DBApifyRun(actor=actor, targets=targets, items=len(items), cost_usd=cost))
        db.commit()
        for p in posts:
            url, text = p["url"], " ".join(p["text"].split())
            if p["published_at"] < cutoff or len(text) < MIN_TEXT_CHARS:
                continue
            seen = (db.query(DBIntelFeed.id).filter(DBIntelFeed.source_url == url).first()
                    or db.query(DBRejected.id).filter(DBRejected.source_url == url).first()
                    or db.query(DBPending.id).filter(DBPending.source_url == url).first())
            if seen:
                continue
            try:
                db.add(DBPending(
                    source_url=url,
                    source_label=p["label"][:100],
                    title=f"@{p['author']} on Instagram",
                    text=f"@{p['author']} posted on Instagram:\n\n{text}"[: config.MAX_ARTICLE_CHARS],
                    image_url=(p.get("image") or "")[:2000],
                    published_at=p["published_at"],
                ))
                db.commit()
                queued += 1
            except Exception as e:
                db.rollback()
                logger.error(f"Error on {url}: {e}")
    finally:
        db.close()
    logger.info(f"Instagram {kind} done: {queued} posts queued, cost ${cost:.4f}")
    return queued


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if args[:1] == ["budget"]:
        print(f"Apify used this month: ${month_usage_usd():.2f} (cap ${config.APIFY_MONTHLY_CAP_USD:.2f})")
    else:
        run(args[0] if args else "", dry_run="--dry-run" in args)
