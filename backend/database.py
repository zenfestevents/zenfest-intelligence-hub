"""Database engine and ORM tables."""
import datetime
import uuid

from sqlalchemy import (Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String,
                        Text, Uuid, create_engine, text)
from sqlalchemy.orm import declarative_base, sessionmaker

import config

if not config.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy backend/.env.example to backend/.env and paste "
        "your Supabase 'Session pooler' connection string into it."
    )

engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class DBIntelFeed(Base):
    __tablename__ = "zf_intel_feed"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    entity_name = Column(String(100), nullable=False)
    primary_category = Column(String(50), nullable=False, index=True)
    region = Column(String(30), nullable=False, default="Global", index=True)
    summary = Column(Text, nullable=False)
    exact_source_quote = Column(Text, nullable=False)
    source_url = Column(Text, unique=True, nullable=False)
    source_label = Column(String(100), index=True)
    country_of_origin = Column(String(100), default="Global")
    hook_idea = Column(Text, nullable=False, default="")
    hook_score = Column(SmallInteger, nullable=False, default=1)
    relevance_score = Column(SmallInteger, nullable=False, default=1)
    visual_score = Column(SmallInteger, nullable=False, default=1)
    evergreen = Column(Boolean, nullable=False, default=False)
    brand_note = Column(Text, nullable=False, default="")
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class DBRejected(Base):
    """Items that failed the quote check or were off-topic. Kept so they are not sent to Claude again."""
    __tablename__ = "zf_rejected_items"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(Text, unique=True, nullable=False)
    reason = Column(String(100), nullable=False)
    attempted_quote = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class DBPending(Base):
    """Articles fetched and cleaned but not yet summarised. Claude works through this queue."""
    __tablename__ = "zf_pending_articles"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(Text, unique=True, nullable=False)
    source_label = Column(String(100), nullable=False)
    title = Column(Text, nullable=False, default="")
    text = Column(Text, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class DBIdea(Base):
    """A reel idea in the Idea Bank. status: Today's Pick, Idea Bank, Scripted, Posted, Outdated."""
    __tablename__ = "zf_reel_ideas"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idea_code = Column(String(20), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    hook_idea = Column(Text, nullable=False, default="")
    outline = Column(Text, nullable=False, default="")
    source_name = Column(String(150), nullable=False, default="")
    source_url = Column(Text, nullable=False, default="")
    published = Column(Date)
    date_found = Column(Date, nullable=False, default=datetime.date.today)
    category = Column(String(50), nullable=False, default="")
    region = Column(String(30), nullable=False, default="Global")
    evergreen = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="Idea Bank", index=True)
    hook_score = Column(SmallInteger, nullable=False, default=1)
    relevance_score = Column(SmallInteger, nullable=False, default=1)
    visual_score = Column(SmallInteger, nullable=False, default=1)
    freshness_score = Column(SmallInteger, nullable=False, default=1)
    brand_note = Column(Text, nullable=False, default="")
    intel_id = Column(Uuid(as_uuid=True), ForeignKey("zf_intel_feed.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=utcnow)


class DBApifyRun(Base):
    """One Apify run and what it cost (Instagram stays inside the monthly cap)."""
    __tablename__ = "zf_apify_runs"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor = Column(String(100), nullable=False)
    targets = Column(Integer, nullable=False, default=0)
    items = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Numeric(8, 4), nullable=False, default=0)
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class DBSource(Base):
    """The source list from feeds.py, rewritten by sources_sync.py each ingest run (for the web app's
    Sources page). listed=False = removed from feeds.py, kept so old items still have a region."""
    __tablename__ = "zf_sources"
    label = Column(String(100), primary_key=True)
    region = Column(String(30), nullable=False)
    kind = Column(String(30), nullable=False)
    url = Column(Text, nullable=False, default="")
    enabled = Column(Boolean, nullable=False, default=True)
    events_only = Column(Boolean, nullable=False, default=False)
    scan_only = Column(Boolean, nullable=False, default=False)
    interval_min = Column(Integer, nullable=False, default=0)
    note = Column(Text, nullable=False, default="")
    listed = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow)


def init_db() -> None:
    """Create tables. On PostgreSQL this runs schema.sql; elsewhere it uses the ORM."""
    if engine.dialect.name == "postgresql":
        sql = (config.BASE_DIR / "schema.sql").read_text(encoding="utf-8")
        with engine.begin() as conn:
            conn.execute(text(sql))
    else:
        Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print(f"Tables ready on {engine.dialect.name}.")
