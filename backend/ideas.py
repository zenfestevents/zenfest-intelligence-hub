"""Step 3 of the pipeline: the Idea Bank. Turns verified event news into reel ideas.

Replaces the Notion "Zenfest Idea Bank" (owner, 2026-11-17). Used by the daily Claude task:

  python ideas.py candidates [DAYS]   verified items from the last DAYS days (default 3) not yet
                                      used as ideas, best first, plus today's region mix so far
  python ideas.py picks               feed items the owner tapped "Reel idea" on in the website admin
                                      that are not ideas yet (add them with "picked": true)
  python ideas.py add FILE            save Claude's chosen ideas (JSON list); exactly one may be
                                      "today_pick": true. Gives each an idea code ZF-YYYYMMDD-NN.
  python ideas.py tidy                news ideas older than 14 days -> Outdated (never touches
                                      Scripted or Posted)
  python ideas.py import-notion FILE  one-time import of the old Notion Idea Bank export
  python ideas.py status              counts by status and region

The region mix rule (owner, 2026-11-17): every day's ideas mix Tamil Nadu, India and the world
(Global, East Asia, Middle East). See MIX_TARGET.
"""
import datetime
import json
import sys
import uuid
from typing import Any, Dict, List

from sqlalchemy import func

from database import DBFeedMark, DBIdea, DBIntelFeed, SessionLocal

STATUSES = ("Today's Pick", "Idea Bank", "Scripted", "Posted", "Outdated")
# How many ideas a day, per region (the daily task aims for this, never forces a weak one).
MIX_TARGET = {"Tamil Nadu": 2, "India": 2, "Global": 1, "East Asia": 1, "Middle East": 1}
NEWS_SHELF_LIFE_DAYS = 14


def freshness(published: datetime.date, today: datetime.date) -> int:
    if not published:
        return 1
    age = (today - published).days
    return 5 if age <= 3 else 4 if age <= 7 else 3 if age <= 14 else 2 if age <= 60 else 1


def _today() -> datetime.date:
    # India date: the day starts at midnight IST, not UTC.
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date()


def candidates(days: int) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        used = {u for (u,) in db.query(DBIdea.source_url).all()}
        rows = (
            db.query(DBIntelFeed)
            .filter(DBIntelFeed.created_at >= since)
            .order_by((DBIntelFeed.hook_score + DBIntelFeed.relevance_score + DBIntelFeed.visual_score).desc(),
                      DBIntelFeed.published_at.desc())
            .limit(150)
            .all()
        )
        today = _today()
        mix_today = dict(
            db.query(DBIdea.region, func.count()).filter(DBIdea.date_found == today).group_by(DBIdea.region).all()
        )
        return {
            "today": today.isoformat(),
            "mix_target": MIX_TARGET,
            "already_added_today": mix_today,
            "items": [
                {
                    "intel_id": str(r.id),
                    "title": r.title,
                    "summary": r.summary,
                    "region": r.region,
                    "category": r.primary_category,
                    "source": r.source_label,
                    "source_url": r.source_url,
                    "published": r.published_at.date().isoformat(),
                    "hook_idea": r.hook_idea,
                    "scores": {"hook": r.hook_score, "relevance": r.relevance_score, "visual": r.visual_score,
                               "freshness": freshness(r.published_at.date(), today)},
                    "evergreen": r.evergreen,
                    "brand_note": r.brand_note,
                }
                for r in rows
                if r.source_url not in used
            ],
        }
    finally:
        db.close()


def picks() -> Dict[str, Any]:
    """Feed items the owner tapped "Reel idea" on (zf_feed_marks kind='reel') that are not ideas yet.
    An owner pick that already is an idea just gets picked=True. Add the rest with "picked": true."""
    db = SessionLocal()
    try:
        marked = (
            db.query(DBIntelFeed)
            .join(DBFeedMark, DBFeedMark.intel_id == DBIntelFeed.id)
            .filter(DBFeedMark.kind == "reel")
            .all()
        )
        today = _today()
        items = []
        flagged = 0
        for r in marked:
            existing = db.query(DBIdea).filter((DBIdea.intel_id == r.id) | (DBIdea.source_url == r.source_url)).first()
            if existing:
                if not existing.picked:
                    existing.picked = True
                    flagged += 1
                continue
            items.append({
                "intel_id": str(r.id), "title": r.title, "summary": r.summary,
                "plain_story": r.plain_story, "example": r.example,
                "region": r.region, "category": r.primary_category, "source": r.source_label,
                "source_url": r.source_url, "published": r.published_at.date().isoformat(),
                "hook_idea": r.hook_idea,
                "scores": {"hook": r.hook_score, "relevance": r.relevance_score, "visual": r.visual_score,
                           "freshness": freshness(r.published_at.date(), today)},
                "evergreen": r.evergreen, "brand_note": r.brand_note,
            })
        db.commit()
        return {"already_ideas_flagged": flagged, "items": items}
    finally:
        db.close()


def _next_codes(db, today: datetime.date, n: int) -> List[str]:
    prefix = f"ZF-{today:%Y%m%d}-"
    last = (db.query(func.max(DBIdea.idea_code)).filter(DBIdea.idea_code.like(prefix + "%")).scalar() or "")
    start = int(last[-2:]) + 1 if last else 1
    return [f"{prefix}{i:02d}" for i in range(start, start + n)]


def _uuid(v):
    try:
        return uuid.UUID(str(v)) if v else None
    except ValueError:
        return None


def _clamp(v, lo=1, hi=5) -> int:
    try:
        return max(lo, min(hi, int(v)))
    except Exception:
        return lo


def add(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Each item: intel_id (optional), title, hook_idea, outline, source_name, source_url, published
    (YYYY-MM-DD), category, region, evergreen, hook/relevance/visual scores, brand_note, today_pick."""
    today = _today()
    picks = [i for i in items if i.get("today_pick")]
    if len(picks) > 1:
        raise SystemExit("Only one idea may be today_pick.")
    db = SessionLocal()
    try:
        known = {u for (u,) in db.query(DBIdea.source_url).all()}
        fresh = [i for i in items if i.get("source_url") and i["source_url"] not in known]
        if picks and fresh:
            db.query(DBIdea).filter(DBIdea.status == "Today's Pick").update({"status": "Idea Bank"})
        codes = _next_codes(db, today, len(fresh))
        for code, i in zip(codes, fresh):
            published = None
            if i.get("published"):
                try:
                    published = datetime.date.fromisoformat(str(i["published"])[:10])
                except ValueError:
                    published = None
            db.add(DBIdea(
                idea_code=code,
                title=str(i.get("title", ""))[:255],
                hook_idea=i.get("hook_idea", ""),
                outline=i.get("outline", ""),
                source_name=str(i.get("source_name", ""))[:150],
                source_url=i["source_url"],
                published=published,
                date_found=today,
                category=str(i.get("category", ""))[:50],
                region=i.get("region", "Global"),
                evergreen=bool(i.get("evergreen")),
                status="Today's Pick" if i.get("today_pick") else "Idea Bank",
                hook_score=_clamp(i.get("hook_score")),
                relevance_score=_clamp(i.get("relevance_score")),
                visual_score=_clamp(i.get("visual_score")),
                freshness_score=freshness(published, today),
                brand_note=i.get("brand_note", ""),
                picked=bool(i.get("picked")),
                intel_id=_uuid(i.get("intel_id")),
            ))
        db.commit()
        return {"added": len(fresh), "skipped_duplicates": len(items) - len(fresh), "codes": codes}
    finally:
        db.close()


def tidy() -> Dict[str, int]:
    db = SessionLocal()
    try:
        cutoff = _today() - datetime.timedelta(days=NEWS_SHELF_LIFE_DAYS)
        n = (
            db.query(DBIdea)
            .filter(DBIdea.status == "Idea Bank", DBIdea.evergreen.is_(False), DBIdea.published < cutoff)
            .update({"status": "Outdated"}, synchronize_session=False)
        )
        db.commit()
        return {"moved_to_outdated": n}
    finally:
        db.close()


def import_notion(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """One-time: the old Notion Idea Bank (exported as JSON rows with Notion's column names)."""
    category_map = {
        "Industry News (India)": "Industry News", "Tip/Hack": "Tips & Trends", "Décor Trend": "Décor & Design",
        "Corporate/Experiential": "Corporate & MICE", "Event Tech/Experiential": "Event Tech",
        "Viral Moment": "Viral Moment", "Festival/Cultural": "Culture & Celebrations", "Wedding": "Wedding",
    }
    db = SessionLocal()
    added = skipped = 0
    try:
        have = {c for (c,) in db.query(DBIdea.idea_code).all()}
        for r in rows:
            code = r.get("Idea ID")
            if not code or code in have:
                skipped += 1
                continue

            def num(k):
                return _clamp(r.get(k))

            def day(v):
                try:
                    return datetime.date.fromisoformat(str(v)[:10])
                except Exception:
                    return None

            db.add(DBIdea(
                idea_code=code, title=(r.get("Title") or "")[:255], hook_idea=r.get("Hook Idea") or "",
                source_name=(r.get("Source Name") or "")[:150], source_url=r.get("Source URL") or "",
                published=day(r.get("Published")), date_found=day(r.get("found")) or _today(),
                category=category_map.get(r.get("Category"), r.get("Category") or ""),
                region=r.get("Region") or "Global", evergreen=r.get("Evergreen") == "__YES__",
                status=r.get("Status") if r.get("Status") in STATUSES else "Idea Bank",
                hook_score=num("Hook"), relevance_score=num("Relevance"), visual_score=num("Visual"),
                freshness_score=num("Freshness"), brand_note=r.get("Brand Note") or "",
            ))
            added += 1
        db.commit()
        return {"imported": added, "skipped": skipped}
    finally:
        db.close()


def status() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        by_status = dict(db.query(DBIdea.status, func.count()).group_by(DBIdea.status).all())
        by_region = dict(db.query(DBIdea.region, func.count()).group_by(DBIdea.region).all())
        return {"by_status": by_status, "by_region": by_region}
    finally:
        db.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
    if cmd == "candidates":
        print(json.dumps(candidates(int(args[0]) if args else 3), ensure_ascii=False))
    elif cmd == "picks":
        print(json.dumps(picks(), ensure_ascii=False))
    elif cmd == "add":
        print(json.dumps(add(json.load(open(args[0], encoding="utf-8")))))
    elif cmd == "tidy":
        print(json.dumps(tidy()))
    elif cmd == "import-notion":
        print(json.dumps(import_notion(json.load(open(args[0], encoding="utf-8")))))
    elif cmd == "status":
        print(json.dumps(status(), ensure_ascii=False))
    else:
        print(__doc__)
