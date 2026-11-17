import { db, respond } from "@/lib/db";

export const dynamic = "force-dynamic";

// Enabled feeds in backend/feeds.py (with RSSHub on). Update when that list changes:
//   python -c "import feeds; print(len(feeds.ENABLED_FEEDS))"
const SOURCES_ENABLED = 71;
const INSTAGRAM_TARGETS = 34; // 29 accounts + 5 hashtags (feeds.py INSTAGRAM_*)
// The poller runs every 30 minutes; treat it as active if it wrote anything recently.
const ACTIVE_WINDOW_MS = 3 * 60 * 60 * 1000;

export async function GET() {
  return respond(async () => {
    const { rows } = await db().query(`
      SELECT
        (SELECT COUNT(*)::int FROM zf_intel_feed WHERE created_at >= NOW() - INTERVAL '24 hours') AS verified_last_24h,
        (SELECT COUNT(*)::int FROM zf_intel_feed) AS verified_total,
        (SELECT COUNT(*)::int FROM zf_pending_articles) AS waiting_total,
        (SELECT COUNT(*)::int FROM zf_reel_ideas WHERE status IN ('Today''s Pick', 'Idea Bank')) AS ideas_open,
        (SELECT COALESCE(SUM(cost_usd), 0)::float FROM zf_apify_runs
           WHERE created_at >= date_trunc('month', NOW())) AS apify_month_usd,
        GREATEST(
          (SELECT MAX(created_at) FROM zf_intel_feed),
          (SELECT MAX(created_at) FROM zf_rejected_items),
          (SELECT MAX(created_at) FROM zf_pending_articles)
        ) AS last_poll_at
    `);
    const regions = await db().query(
      `SELECT region, COUNT(*)::int AS count FROM zf_intel_feed
        WHERE created_at >= NOW() - INTERVAL '7 days' GROUP BY region`
    );
    const stats = rows[0];
    return {
      ...stats,
      regions_7d: Object.fromEntries(regions.rows.map((r) => [r.region, r.count])),
      sources_enabled: SOURCES_ENABLED,
      instagram_targets: INSTAGRAM_TARGETS,
      polling_active: Boolean(stats.last_poll_at) && Date.now() - new Date(stats.last_poll_at).getTime() < ACTIVE_WINDOW_MS,
    };
  });
}
