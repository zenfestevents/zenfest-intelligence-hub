# Rules for Claude in the Zenfest Intelligence Hub

The business rules are in `D:\Zenfest Events Projects\CLAUDE.md` (Tamil Nadu company, never "a
Chennai company"; brand safety; real numbers only; nothing produced until the owner approves a
script; no paid credits without asking). This file covers the hub itself. See README.md for setup.

## What this is
A copy of the AI Intelligent Hub (`D:\AI Intelligent Hub`) for events, built 2026-11-17 at the
owner's request: same pipeline (feeds → queue → Claude summary + verbatim quote → Python quote
check → dashboard), with a daily Idea Bank on top. It replaced the two Notion scheduled tasks
(`zenfest-source-discovery`, `zenfest-daily-idea-fetch`, switched off since 2026-11-13); the 98
Notion ideas are in `backend/data/` for import.

## Owner's choices (2026-11-17)
- Exact copy of the AI Hub: own GitHub repo and own Vercel dashboard; the AI Hub's RSSHub server on
  Render **and the AI Hub's Supabase database** are shared. Every Zenfest table is prefixed `zf_` so it
  never touches the AI Hub's `intel_feed` / `pending_articles` / `rejected_items` / `startups_directory`.
  A new table must get the prefix too (and its indexes `idx_zf_…`, since `CREATE INDEX IF NOT EXISTS`
  silently skips a name the AI Hub already uses).
- **Apify: free $5 a month only.** `instagram_ingest.py` refuses a run that could take the month past
  `APIFY_MONTHLY_CAP_USD` (4.50) and passes Apify's own `maxTotalChargeUsd` per run. Never raise the
  cap, add accounts beyond the budget, or run Apify outside the schedule without asking.
- **China through Chinese news sites** (RSSHub routes + Bing News), not Douyin/Xiaohongshu/Weibo.
- **Every day's ideas mix regions:** Tamil Nadu, India, Global, East Asia, Middle East
  (`MIX_TARGET` in `ideas.py`). Event tech often appears first in China, Korea, Japan and the Gulf.

## Easy to get wrong
- Never scrape LinkedIn. Reddit stays off until API approval. Never log in to Instagram or give a
  scraper cookies; Instagram posts are ideas only, never reposted.
- General news feeds use `events_only=True` (headline must contain an event word, `EVENT_WORDS`,
  whole-word match for English). Add words there, not per feed. Sources whose every item is event
  news (trade titles, `site:` searches) don't need it.
- Bing News links are click-trackers; `textutil.resolve_link` stores the real article URL.
- Quotes stay in the original language (Tamil, Chinese); titles, summaries and hooks are English.
- Brand safety runs in two places: the summariser writes `brand_note` per item and the daily idea
  task extends it. Still run the `brand-safety-check` skill before any script or prompt.
- When `feeds.py` changes, update `SOURCES_ENABLED` / `INSTAGRAM_TARGETS` in `frontend/app/api/stats/route.js`.
- Commit or push only when the owner asks.
