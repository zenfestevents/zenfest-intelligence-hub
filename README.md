# Zenfest Intelligence Hub

The Zenfest copy of the AI Intelligent Hub (owner, 2026-11-17). It collects event news from
Tamil Nadu, India and the world (East Asia and the Gulf too, where event tech shows up first),
has Claude check and summarise it, and turns it into daily reel ideas for @zenfest_events.

Nothing here makes videos or spends paid credits except Apify for Instagram, capped at the free
$5 a month. Nothing is produced until the owner approves a script.

## How it works (plain words)

| Step | What happens | Where it runs | Cost |
| --- | --- | --- | --- |
| 1. Collect | `backend/ingest.py` reads 71 free news feeds every 30 minutes and puts new event stories in a waiting queue | GitHub Actions | free |
| 1b. Instagram | `backend/instagram_ingest.py` reads 29 event pages (every 2 days) and 5 hashtags (Mondays) through Apify | GitHub Actions | inside Apify's free $5/month; stops itself at $4.50 |
| 2. Check | Claude reads the queue, writes a summary, a reel hook and a brand-safety note, and copies one sentence word for word. Plain Python checks that sentence really is in the article; if not, the item is thrown away | scheduled Claude task `hub-summarise-queue` (this PC) | Claude plan |
| 3. Ideas | Every morning Claude picks 7-8 ideas mixing Tamil Nadu, India, Global, East Asia and Middle East, and marks one Today's Pick | scheduled Claude task `hub-daily-ideas` (this PC) | Claude plan |
| 4. Look | The dashboard shows the ideas, the verified feed by region, Instagram finds and the queue | Vercel | free |

`backend/daily_scan.py` is a free one-shot headline list of every source for the last 24 hours,
grouped by region (report in `work/`). Use it any time.

### The sources

All in `backend/feeds.py`, grouped by region:

- **Tamil Nadu:** The Hindu (Tamil Nadu, Chennai, Coimbatore, Madurai, Tiruchi), DT Next, Hindu Tamil Thisai, Dinamani, Vikatan (Tamil, Claude translates), Mylapore Times, The Madras Day, AllEvents Chennai, and news searches for Tamil Nadu weddings and Chennai / Coimbatore / Madurai events.
- **India:** EventFAQs, WeddingSutra, Wedding Affair, MediaNews4U, TravTalk, Exhibition Showcase, news searches for WedMeGood, exchange4media and wedding trends.
- **Global:** BizBash, Skift Meetings, TTGmice, TSNN, Exhibition News, Access All Areas, TPi, Festival Insights, Pollstar, Smart Meetings, PCMA, ICCA, MIX, mice.net.au, blooloop, DroneXL, Designboom, My Modern Met, ILEA, news searches for Event Industry News, Event Marketer, décor trends and event technology.
- **East Asia:** Entertainment Technology Asia, Korea Herald, Korea Times, Japan Times, d'strict, news searches for China drone shows, Japan projection mapping and Korea media art, and Chinese-language sources through RSSHub (36Kr searches for drone shows, light shows, immersive and weddings; The Paper; Zaobao).
- **Middle East:** Gulf News, Khaleej Times, Arab News, Arabian Business, Global Village Dubai, news searches for Riyadh Season, Dubai events and Saudi festivals.
- **Instagram (Apify):** 7 Tamil Nadu décor and wedding pages, 9 India, 9 Global, 1 East Asia, 3 Middle East; hashtags #chennaiweddingdecor, #tamilwedding, #mandapdecor, #southindianwedding, #eventdecor.

General newspapers are filtered by event words in the headline (English, Tamil, Chinese), so
politics and cricket scores don't fill the queue.

Deliberately not used: LinkedIn (its rules ban scraping), Reddit (needs API approval),
Douyin / Xiaohongshu / Weibo (block automated reading; China comes through Chinese news sites instead).

## One-time setup (owner)

1. **Supabase: shared with the AI Hub (owner, 2026-11-17).** No new project. Zenfest uses the AI Hub's
   database (`DATABASE_URL` copied from `D:\AI Intelligent Hub\backend\.env`) with its own tables, all
   named `zf_…` (`zf_intel_feed`, `zf_pending_articles`, `zf_rejected_items`, `zf_reel_ideas`,
   `zf_apify_runs`), so the two hubs never mix. Never rename them to the AI Hub's names.
2. **Apify:** in the new Zenfest Apify account, Console → Settings → API & Integrations → copy the token.
   Also set a hard monthly limit of $5 in Apify's billing settings, as a second safety net.
3. Copy `backend/.env.example` to `backend/.env` and paste both values (RSSHUB_URL is already filled in;
   it shares the AI Hub's RSSHub server on Render).
4. Create the tables and import the old Notion ideas:
   ```bash
   backend\.venv\Scripts\python.exe backend\database.py
   ```
   ```bash
   cd backend && .venv\Scripts\python.exe ideas.py import-notion data\notion_idea_bank_2026-11-17.json
   ```
5. **GitHub:** create a private repo, push this folder, then Settings → Secrets and variables → Actions:
   add `DATABASE_URL`, `APIFY_TOKEN` and `RSSHUB_URL`. Open Actions → "Zenfest poller" → Run workflow to test.
6. **Vercel:** Add New → Project → this repo, Root Directory `frontend`, environment variable `DATABASE_URL`.
7. **Claude tasks: on since 2026-11-17.** `hub-summarise-queue` (about 06:15 daily) and `hub-daily-ideas`
   (about 07:45 daily) run in the Claude desktop app while it is open (a missed run happens at the next
   launch). Until the GitHub poller is set up, the summarise job first runs `ingest.py` itself.
   The live prompts are in `C:\Users\kumar\.claude\scheduled-tasks\`; `tasks/*.md` are the first drafts.

## Run on this PC

From `backend` (the venv is already set up):

| Command | What it does |
| --- | --- |
| `.venv\Scripts\python.exe check_feeds.py` | Which sources are reachable. Needs no keys. |
| `.venv\Scripts\python.exe daily_scan.py` | Free headline list of the last 24 hours by region, to `work/`. |
| `.venv\Scripts\python.exe ingest.py` | One collection pass over all feeds. |
| `.venv\Scripts\python.exe instagram_ingest.py profiles --dry-run` | Shows the Instagram run and its cost without spending. |
| `.venv\Scripts\python.exe instagram_ingest.py budget` | Apify spend this month. |
| `.venv\Scripts\python.exe claude_queue.py status` | How many items are waiting for Claude. |
| `.venv\Scripts\python.exe ideas.py status` | Idea Bank counts by status and region. |
| `.venv\Scripts\python.exe probe_source.py <url>` | Finds a working feed for a new website. |
| `.venv\Scripts\python.exe -m pytest tests -q` | Tests for the quote checker. |

Dashboard, from `frontend` (needs `frontend/.env.local` with the `DATABASE_URL` line): `npm run dev`.
