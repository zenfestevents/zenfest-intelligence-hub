import { clampInt, db, respond } from "@/lib/db";

export const dynamic = "force-dynamic";

const FILTERS = {
  category: "primary_category",
  region: "region",
  source: "source_label",
};

export async function GET(request) {
  return respond(async () => {
    const params = new URL(request.url).searchParams;
    const where = [];
    const values = [];
    for (const [param, column] of Object.entries(FILTERS)) {
      const value = params.get(param);
      if (value && value !== "All") {
        values.push(value);
        where.push(`${column} = $${values.length}`);
      }
    }
    values.push(clampInt(params.get("limit"), 60, 1, 200));
    const { rows } = await db().query(
      `SELECT id, title, entity_name, primary_category, region, summary, exact_source_quote, source_url,
              source_label, country_of_origin, hook_idea, hook_score, relevance_score, visual_score,
              evergreen, brand_note, published_at
         FROM zf_intel_feed
        ${where.length ? "WHERE " + where.join(" AND ") : ""}
        ORDER BY published_at DESC
        LIMIT $${values.length}`,
      values
    );
    return rows;
  });
}
