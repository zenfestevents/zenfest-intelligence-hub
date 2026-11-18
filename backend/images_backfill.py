"""Fill image_url for feed items saved before pictures were collected (2026-11-18).

Downloads each article page once and reads its main picture (og:image, the one WhatsApp shows).
Free: plain HTTP, no LLM, no Apify. Instagram posts are skipped (their pictures come from Apify).
Run: python images_backfill.py [limit]
"""
import sys
from concurrent.futures import ThreadPoolExecutor

from database import DBIntelFeed, SessionLocal
from textutil import fetch_page_image


def run(limit: int = 500) -> dict:
    db = SessionLocal()
    try:
        rows = (
            db.query(DBIntelFeed.id, DBIntelFeed.source_url)
            .filter(DBIntelFeed.image_url == "")
            .filter(~DBIntelFeed.source_label.like("Instagram%"))
            .order_by(DBIntelFeed.published_at.desc())
            .limit(limit)
            .all()
        )
        with ThreadPoolExecutor(max_workers=6) as pool:
            images = list(pool.map(lambda r: fetch_page_image(r.source_url), rows))
        found = 0
        for (row_id, _), image in zip(rows, images):
            if image:
                db.query(DBIntelFeed).filter(DBIntelFeed.id == row_id).update({"image_url": image[:2000]})
                found += 1
        db.commit()
        return {"checked": len(rows), "pictures_found": found}
    finally:
        db.close()


if __name__ == "__main__":
    print(run(int(sys.argv[1]) if len(sys.argv) > 1 else 500))
