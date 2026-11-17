"""Daily headline scan: every enabled source, nothing skipped silently.

Lists what each source published in the last 24 hours, grouped by region (Tamil Nadu, India,
Global, East Asia, Middle East), so the day's reel can be picked from all of it and the mix can
be balanced. Uses no LLM, no Apify and writes nothing to the database, so it costs nothing.
Instagram is covered by instagram_ingest.py on its own budgeted schedule, not here.

  python daily_scan.py            every feed, last 24 hours
  python daily_scan.py --hours 48 look further back

Every source ends in one of three states, all written to the report:
  FRESH  has items inside the window
  QUIET  loaded fine, nothing new (the age of its newest item is shown)
  FAILED could not be loaded after three tries (the reason is shown)

General news feeds (events_only) list only items that mention an event word.
The report goes to work/headlines_YYYY-MM-DD.txt (not committed).
"""
import datetime
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

import config
from feeds import ENABLED_FEEDS, REGIONS, RSSHUB_URL, is_event_item
from sources import entry_date, fetch_entries

TRIES = 3
OUT_DIR = config.BASE_DIR.parent / "work"


def wake_rsshub() -> str:
    """The free Render server sleeps when idle; the first request can take a minute to wake it."""
    if not RSSHUB_URL:
        return "not configured"
    err = ""
    for _ in range(TRIES):
        try:
            httpx.get(RSSHUB_URL + "/", timeout=150).raise_for_status()
            return "awake"
        except Exception as e:
            err = str(e)[:80]
            time.sleep(10)
    return f"did not wake: {err}"


def scan(feed, hours: float, now: datetime.datetime) -> dict:
    err = ""
    for attempt in range(TRIES):
        try:
            entries = fetch_entries(feed)
            break
        except Exception as e:
            err = str(e).splitlines()[0][:90]
            time.sleep(5 * (attempt + 1))
    else:
        return {"feed": feed, "state": "FAILED", "why": err, "items": []}

    if feed.events_only:
        entries = [e for e in entries if is_event_item(e)]
    items, newest = [], None
    for e in entries:
        title, link = (e.get("title") or "").strip()[:140], e.get("link")
        if not link:
            continue
        if not (e.get("published_parsed") or e.get("updated_parsed")):
            # Listings without dates (e.g. AllEvents): everything on the list is current.
            items.append((None, title, link))
            continue
        age = (now - entry_date(e)).total_seconds() / 3600
        newest = age if newest is None else min(newest, age)
        if -1 <= age <= hours:
            items.append((max(age, 0.0), title, link))
    return {"feed": feed, "state": "FRESH" if items else "QUIET", "newest": newest, "items": items,
            "total": len(entries)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.disable(logging.CRITICAL)
    hours = float(sys.argv[sys.argv.index("--hours") + 1]) if "--hours" in sys.argv else 24.0
    now = datetime.datetime.now(datetime.timezone.utc)

    rsshub_state = wake_rsshub()
    hub = [f for f in ENABLED_FEEDS if RSSHUB_URL and f.url.startswith(RSSHUB_URL)]
    rest = [f for f in ENABLED_FEEDS if f not in hub]
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda f: scan(f, hours, now), rest))
    # One at a time: the small RSSHub server times out when asked for several feeds at once.
    results += [scan(f, hours, now) for f in hub]

    fresh = [r for r in results if r["state"] == "FRESH"]
    quiet = [r for r in results if r["state"] == "QUIET"]
    failed = [r for r in results if r["state"] == "FAILED"]
    dated = [(age, r["feed"].group, r["feed"].label, t, l) for r in fresh for age, t, l in r["items"] if age is not None]
    undated = [(r["feed"].group, r["feed"].label, t, l) for r in fresh for age, t, l in r["items"] if age is None]

    out = [
        f"Zenfest headline scan {now:%Y-%m-%d %H:%M} UTC, last {hours:g} hours",
        f"Feeds: {len(results)} checked | {len(fresh)} fresh | {len(quiet)} quiet | {len(failed)} failed | "
        f"{len(dated)} dated headlines | RSSHub: {rsshub_state}",
        "Per region: " + " | ".join(f"{g}: {sum(1 for d in dated if d[1] == g)}" for g in REGIONS),
    ]

    out.append("\n== FAILED (not covered today) ==")
    out += [f"{r['feed'].group} | {r['feed'].label} | {r['why']}" for r in failed] or ["none"]

    for region in REGIONS:
        rows = sorted(d for d in dated if d[1] == region)
        out.append(f"\n== {region.upper()}, newest first ==")
        out += [f"{age:4.1f}h | {lab} | {t} | {l}" for age, _, lab, t, l in rows] or ["nothing new"]

    out.append("\n== LISTINGS WITHOUT DATES ==")
    out += [f"{g} | {lab} | {t} | {l}" for g, lab, t, l in undated] or ["none"]

    out.append("\n== QUIET (loaded, nothing new) ==")
    for r in sorted(quiet, key=lambda r: (r["feed"].group, r["feed"].label)):
        n = r["newest"]
        newest = "no dated items" if n is None else f"newest {n / 24:.1f} days old" if n >= 48 else f"newest {n:.0f}h old"
        out.append(f"{r['feed'].group} | {r['feed'].label} | {r['total']} items | {newest}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"headlines_{now:%Y-%m-%d}.txt"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[:3]))
    print(f"Report: {path}")


if __name__ == "__main__":
    main()
