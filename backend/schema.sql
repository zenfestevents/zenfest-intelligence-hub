-- Zenfest Intelligence Hub schema (PostgreSQL / Supabase). Safe to run more than once.
-- Applied by: python database.py. Adapted from the AI Intelligent Hub (2026-11-17).
-- gen_random_uuid() is built into PostgreSQL 13+, so no extension is needed.

-- Verified event news: Claude's summary + a quote that Python found word for word in the source.
CREATE TABLE IF NOT EXISTS zf_intel_feed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    entity_name VARCHAR(100) NOT NULL,
    primary_category VARCHAR(50) NOT NULL,
    region VARCHAR(30) NOT NULL DEFAULT 'Global',
    summary TEXT NOT NULL,
    exact_source_quote TEXT NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    source_label VARCHAR(100),
    country_of_origin VARCHAR(100) DEFAULT 'Global',
    hook_idea TEXT NOT NULL DEFAULT '',
    hook_score SMALLINT NOT NULL DEFAULT 1,
    relevance_score SMALLINT NOT NULL DEFAULT 1,
    visual_score SMALLINT NOT NULL DEFAULT 1,
    evergreen BOOLEAN NOT NULL DEFAULT FALSE,
    brand_note TEXT NOT NULL DEFAULT '',
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Items that failed the quote check or were not about events, so they are not sent to Claude again.
CREATE TABLE IF NOT EXISTS zf_rejected_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url TEXT NOT NULL UNIQUE,
    reason VARCHAR(100) NOT NULL,
    attempted_quote TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Queue of fetched articles and Instagram posts waiting for Claude.
CREATE TABLE IF NOT EXISTS zf_pending_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url TEXT NOT NULL UNIQUE,
    source_label VARCHAR(100) NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- The Idea Bank (replaces the Notion "Zenfest Idea Bank"). One row per reel idea.
-- status: Today's Pick | Idea Bank | Scripted | Posted | Outdated
CREATE TABLE IF NOT EXISTS zf_reel_ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_code VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    hook_idea TEXT NOT NULL DEFAULT '',
    outline TEXT NOT NULL DEFAULT '',
    source_name VARCHAR(150) NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    published DATE,
    date_found DATE NOT NULL DEFAULT CURRENT_DATE,
    category VARCHAR(50) NOT NULL DEFAULT '',
    region VARCHAR(30) NOT NULL DEFAULT 'Global',
    evergreen BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'Idea Bank',
    hook_score SMALLINT NOT NULL DEFAULT 1,
    relevance_score SMALLINT NOT NULL DEFAULT 1,
    visual_score SMALLINT NOT NULL DEFAULT 1,
    freshness_score SMALLINT NOT NULL DEFAULT 1,
    brand_note TEXT NOT NULL DEFAULT '',
    intel_id UUID REFERENCES zf_intel_feed(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Every Apify run, with what it really cost, so Instagram stays inside the monthly cap.
CREATE TABLE IF NOT EXISTS zf_apify_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor VARCHAR(100) NOT NULL,
    targets INTEGER NOT NULL DEFAULT 0,
    items INTEGER NOT NULL DEFAULT 0,
    cost_usd NUMERIC(8, 4) NOT NULL DEFAULT 0,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- The source list (feeds.py), rewritten by sources_sync.py at the start of every ingest run, so the
-- web app's /admin/intelligence/sources page shows exactly what is being collected (2026-11-18).
-- kind: rss | search | rsshub | instagram_account | instagram_hashtag
CREATE TABLE IF NOT EXISTS zf_sources (
    label VARCHAR(100) PRIMARY KEY,
    region VARCHAR(30) NOT NULL,
    kind VARCHAR(30) NOT NULL,
    url TEXT NOT NULL DEFAULT '',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    events_only BOOLEAN NOT NULL DEFAULT FALSE,
    scan_only BOOLEAN NOT NULL DEFAULT FALSE,
    interval_min INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    listed BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_zf_pending_published_at ON zf_pending_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_zf_intel_published_at ON zf_intel_feed(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_zf_intel_region ON zf_intel_feed(region);
CREATE INDEX IF NOT EXISTS idx_zf_intel_category ON zf_intel_feed(primary_category);
CREATE INDEX IF NOT EXISTS idx_zf_intel_source_label ON zf_intel_feed(source_label);
CREATE INDEX IF NOT EXISTS idx_zf_ideas_status ON zf_reel_ideas(status);
CREATE INDEX IF NOT EXISTS idx_zf_ideas_date_found ON zf_reel_ideas(date_found DESC);

-- The backend connects with the database password, which bypasses row level security.
-- RLS on with no policies blocks Supabase's public REST API (anon key) from every table.
ALTER TABLE zf_intel_feed ENABLE ROW LEVEL SECURITY;
ALTER TABLE zf_rejected_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE zf_pending_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE zf_reel_ideas ENABLE ROW LEVEL SECURITY;
ALTER TABLE zf_apify_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE zf_sources ENABLE ROW LEVEL SECURITY;
