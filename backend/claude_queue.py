"""Step 2 of the pipeline: Claude summarises queued articles; Python checks the quote.

Claude (running as a scheduled task) does two things:

  python claude_queue.py next 15        -> prints up to 15 queued articles as JSON
  python claude_queue.py submit FILE    -> reads Claude's answers (JSON list) and saves them
  python claude_queue.py status         -> shows how many articles are waiting
  python claude_queue.py plain next 30  -> published items still missing the simple-English text
  python claude_queue.py plain submit FILE -> saves [{id, plain_headline, plain_story, example}]

Each answer must contain the fields of models.VerifiedIntelExtraction plus "source_url".
The quote check is plain Python: if the quote is not word for word in the article, the item is
thrown away and never reaches the dashboard. Articles in Tamil or Chinese keep the quote in the
original language; the title, summary and hook are written in English.
"""
import json
import sys
import uuid
from typing import Any, Dict, List

from pydantic import ValidationError

from database import DBIntelFeed, DBPending, DBRejected, SessionLocal
from feeds import KEEP_ALL_LABELS, REGION_OF
from models import CATEGORIES, REGIONS, VerifiedIntelExtraction
from verifier import verify_quote

# Claude only sees this many characters of each article (keeps a run inside the plan's limits).
CLAUDE_VIEW_CHARS = 6000
MAX_ATTEMPTS = 3


def next_batch(limit: int) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = (
            db.query(DBPending)
            .filter(DBPending.attempts < MAX_ATTEMPTS)
            .order_by(DBPending.published_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "source_url": r.source_url,
                "source": r.source_label,
                "source_region": REGION_OF.get(r.source_label, "Global"),
                "title": r.title,
                "always_keep": r.source_label in KEEP_ALL_LABELS,
                "text": r.text[:CLAUDE_VIEW_CHARS],
            }
            for r in rows
        ]
    finally:
        db.close()


def process_one(db, item: Dict[str, Any]) -> str:
    """Handle one answer from Claude. Returns 'saved', 'rejected', 'not_relevant' or an error tag."""
    url = (item.get("source_url") or "").strip()
    pending = db.query(DBPending).filter(DBPending.source_url == url).first()
    if not pending:
        return "unknown_url"
    try:
        extracted = VerifiedIntelExtraction.model_validate({k: v for k, v in item.items() if k != "source_url"})
    except ValidationError:
        pending.attempts += 1
        db.commit()
        return "invalid_answer"

    if not extracted.is_relevant and pending.source_label not in KEEP_ALL_LABELS:
        db.add(DBRejected(source_url=url, reason="not_relevant"))
        db.delete(pending)
        db.commit()
        return "not_relevant"

    ok, reason = verify_quote(pending.text, extracted.exact_source_quote)
    if not ok:
        db.add(DBRejected(source_url=url, reason=reason, attempted_quote=extracted.exact_source_quote[:1000]))
        db.delete(pending)
        db.commit()
        return "rejected"

    db.add(
        DBIntelFeed(
            title=extracted.title[:255],
            entity_name=extracted.entity_name[:100],
            primary_category=extracted.primary_category,
            region=extracted.region,
            summary=extracted.summary,
            exact_source_quote=extracted.exact_source_quote.strip(),
            source_url=url,
            source_label=pending.source_label,
            country_of_origin=(extracted.country_of_origin or "Global")[:100],
            hook_idea=extracted.hook_idea,
            hook_score=extracted.hook_score,
            relevance_score=extracted.relevance_score,
            visual_score=extracted.visual_score,
            evergreen=extracted.evergreen,
            brand_note=extracted.brand_note,
            plain_headline=extracted.plain_headline,
            plain_story=extracted.plain_story,
            example=extracted.example,
            image_url=pending.image_url or "",
            published_at=pending.published_at,
        )
    )
    db.delete(pending)
    db.commit()
    return "saved"


def submit(items: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    db = SessionLocal()
    try:
        for item in items:
            try:
                outcome = process_one(db, item)
            except Exception as e:  # keep going if one row fails (e.g. duplicate URL)
                db.rollback()
                outcome = f"error:{type(e).__name__}"
            counts[outcome] = counts.get(outcome, 0) + 1
    finally:
        db.close()
    return counts


PLAIN_FIELDS = ("plain_headline", "plain_story", "example")


def plain_next(limit: int) -> List[Dict[str, Any]]:
    """Published items that still lack the simple-English text, newest first (for the catch-up step)."""
    db = SessionLocal()
    try:
        rows = (
            db.query(DBIntelFeed)
            .filter(DBIntelFeed.plain_headline == "")
            .order_by(DBIntelFeed.published_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {"id": str(r.id), "title": r.title, "summary": r.summary, "quote": r.exact_source_quote,
             "source": r.source_label, "region": r.region, "category": r.primary_category}
            for r in rows
        ]
    finally:
        db.close()


def plain_submit(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """Saves Claude's simple-English rewrite: [{id, plain_headline, plain_story, example}]."""
    counts = {"saved": 0, "skipped": 0}
    db = SessionLocal()
    try:
        for item in items:
            values = {k: str(item.get(k) or "").strip() for k in PLAIN_FIELDS}
            try:
                row = db.get(DBIntelFeed, uuid.UUID(str(item.get("id"))))
            except (ValueError, TypeError):
                row = None
            if not row or not values["plain_headline"] or not values["plain_story"]:
                counts["skipped"] += 1
                continue
            for k, v in values.items():
                setattr(row, k, v)
            db.commit()
            counts["saved"] += 1
    finally:
        db.close()
    counts["still_missing"] = len(plain_next(10000))
    return counts


def status() -> Dict[str, int]:
    db = SessionLocal()
    try:
        return {
            "waiting": db.query(DBPending).filter(DBPending.attempts < MAX_ATTEMPTS).count(),
            "stuck": db.query(DBPending).filter(DBPending.attempts >= MAX_ATTEMPTS).count(),
            "published": db.query(DBIntelFeed).count(),
        }
    finally:
        db.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy code page
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "next":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
        print(json.dumps({"categories": CATEGORIES, "regions": REGIONS, "articles": next_batch(n)}, ensure_ascii=False))
    elif cmd == "submit":
        path = sys.argv[2] if len(sys.argv) > 2 else None
        raw = open(path, encoding="utf-8").read() if path else sys.stdin.read()
        print(json.dumps(submit(json.loads(raw))))
    elif cmd == "status":
        print(json.dumps(status()))
    elif cmd == "plain" and len(sys.argv) > 2 and sys.argv[2] == "next":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        print(json.dumps({"items": plain_next(n)}, ensure_ascii=False))
    elif cmd == "plain" and len(sys.argv) > 3 and sys.argv[2] == "submit":
        print(json.dumps(plain_submit(json.loads(open(sys.argv[3], encoding="utf-8").read()))))
    else:
        print(__doc__)
