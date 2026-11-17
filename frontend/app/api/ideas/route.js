import { clampInt, db, respond } from "@/lib/db";

export const dynamic = "force-dynamic";

const STATUSES = ["Today's Pick", "Idea Bank", "Scripted", "Posted", "Outdated"];

/** Reel ideas from the Idea Bank: today's pick first, then newest. Filters: status, region. */
export async function GET(request) {
  return respond(async () => {
    const params = new URL(request.url).searchParams;
    const where = [];
    const values = [];
    const status = params.get("status");
    if (status && STATUSES.includes(status)) {
      values.push(status);
      where.push(`status = $${values.length}`);
    } else {
      where.push(`status <> 'Outdated'`);
    }
    const region = params.get("region");
    if (region && region !== "All") {
      values.push(region);
      where.push(`region = $${values.length}`);
    }
    values.push(clampInt(params.get("limit"), 60, 1, 300));
    const { rows } = await db().query(
      `SELECT id, idea_code, title, hook_idea, outline, source_name, source_url, published, date_found,
              category, region, evergreen, status, hook_score, relevance_score, visual_score, freshness_score,
              (hook_score + relevance_score + visual_score + freshness_score) AS total, brand_note
         FROM zf_reel_ideas
        WHERE ${where.join(" AND ")}
        ORDER BY (status = 'Today''s Pick') DESC, date_found DESC, total DESC
        LIMIT $${values.length}`,
      values
    );
    return rows;
  });
}
