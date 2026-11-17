"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, Check, ShieldAlert } from "lucide-react";

// Must match backend/models.py.
const REGIONS = ["All", "Tamil Nadu", "India", "Global", "East Asia", "Middle East"];
const CATEGORIES = [
  "All",
  "Wedding",
  "Family Function",
  "Décor & Design",
  "Event Tech",
  "Corporate & MICE",
  "Concerts & Festivals",
  "Culture & Celebrations",
  "Industry News",
  "Tips & Trends",
  "Viral Moment",
];
const IDEA_STATUSES = ["All open", "Today's Pick", "Idea Bank", "Scripted", "Posted", "Outdated"];
const TABS = [
  { id: "ideas", label: "Reel ideas" },
  { id: "feed", label: "Live feed" },
  { id: "instagram", label: "Instagram" },
  { id: "queue", label: "Waiting queue" },
];
const QUEUE_PAGE = 100;
const REFRESH_MS = 60000;

async function getJson(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function timeAgo(iso) {
  if (!iso) return "never";
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  return `${Math.floor(seconds / 86400)} d ago`;
}

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/* ---------- small building blocks ---------- */

function FilterBar({ label, options, value, onChange }) {
  return (
    <div className="flex flex-wrap items-center gap-x-1 gap-y-2" role="group" aria-label={label}>
      <span className="label mr-3">{label}</span>
      {options.map((opt) => {
        const active = value === opt;
        return (
          <button
            key={opt}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(opt)}
            className={`border px-3 py-1.5 text-[11px] uppercase tracking-[0.08em] transition-colors ${
              active
                ? "border-hazard bg-hazard text-crt"
                : "border-line text-dim hover:border-hazard hover:text-phosphor"
            }`}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

function Notice({ title, children, alert = false }) {
  return (
    <div className={`border p-6 ${alert ? "border-hazard" : "border-line"}`} role={alert ? "alert" : "status"}>
      <p className={`text-xs uppercase tracking-[0.1em] ${alert ? "text-hazard" : "text-phosphor"}`}>{title}</p>
      {children && <p className="mt-2 max-w-[70ch] text-[14px] leading-relaxed text-dim">{children}</p>}
    </div>
  );
}

function Scores({ hook, relevance, visual, freshness }) {
  const parts = [
    ["Hook", hook],
    ["Fit", relevance],
    ["Visual", visual],
  ];
  if (freshness) parts.push(["Fresh", freshness]);
  return (
    <p className="label flex flex-wrap gap-x-3">
      {parts.map(([k, v]) => (
        <span key={k}>
          {k} <span className="text-phosphor">{v}/5</span>
        </span>
      ))}
    </p>
  );
}

function BrandNote({ text }) {
  if (!text) return null;
  return (
    <p className="flex gap-2 text-[12px] leading-relaxed text-dim">
      <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-hazard" aria-hidden="true" />
      <span>{text}</span>
    </p>
  );
}

function SourceLink({ href, children }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-[12px] uppercase tracking-[0.08em] text-hazard underline decoration-line underline-offset-4 hover:decoration-hazard"
    >
      {children}
      <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
    </a>
  );
}

function IntelCard({ item }) {
  return (
    <article className="cell flex flex-col gap-4 p-5">
      <header className="flex items-start justify-between gap-4">
        <p className="label text-hazard">
          {item.region} · {item.primary_category}
        </p>
        <p className="label shrink-0 text-right">
          <time dateTime={item.published_at}>{timeAgo(item.published_at)}</time>
        </p>
      </header>

      <h3 className="font-display text-[20px] font-medium uppercase leading-tight text-phosphor">{item.title}</h3>
      <p className="text-[14px] leading-relaxed text-dim">{item.summary}</p>

      {item.hook_idea && (
        <p className="border-l-2 border-hazard pl-3 text-[14px] leading-relaxed text-phosphor">
          <span className="label mb-1 block text-hazard">Reel hook</span>
          {item.hook_idea}
        </p>
      )}

      <figure className="border-l-2 border-signal pl-3">
        <figcaption className="mb-1 flex items-center gap-1.5 text-[11px] uppercase tracking-[0.1em] text-signal">
          <Check className="h-3.5 w-3.5" aria-hidden="true" />
          Quote found in source
        </figcaption>
        <blockquote className="text-[13px] leading-relaxed text-phosphor">&ldquo;{item.exact_source_quote}&rdquo;</blockquote>
      </figure>

      <BrandNote text={item.brand_note} />

      <footer className="mt-auto flex flex-wrap items-end justify-between gap-3 border-t border-line pt-3">
        <Scores hook={item.hook_score} relevance={item.relevance_score} visual={item.visual_score} />
        <SourceLink href={item.source_url}>{item.source_label || hostOf(item.source_url)}</SourceLink>
      </footer>
    </article>
  );
}

function IdeaCard({ idea }) {
  const pick = idea.status === "Today's Pick";
  return (
    <article className={`cell flex flex-col gap-4 p-5 ${pick ? "outline outline-2 -outline-offset-2 outline-hazard" : ""}`}>
      <header className="flex items-start justify-between gap-4">
        <p className="label text-hazard">
          {pick ? "Today's pick · " : ""}
          {idea.region} · {idea.category || "Idea"}
        </p>
        <p className="label shrink-0 text-right">
          {idea.idea_code} · <span className="text-phosphor">{idea.total}/20</span>
        </p>
      </header>
      <h3 className="font-display text-[20px] font-medium uppercase leading-tight text-phosphor">{idea.title}</h3>
      {idea.hook_idea && (
        <p className="border-l-2 border-hazard pl-3 text-[15px] leading-relaxed text-phosphor">{idea.hook_idea}</p>
      )}
      {idea.outline && <p className="whitespace-pre-line text-[13px] leading-relaxed text-dim">{idea.outline}</p>}
      <BrandNote text={idea.brand_note} />
      <footer className="mt-auto flex flex-wrap items-end justify-between gap-3 border-t border-line pt-3">
        <span className="label">
          {idea.status} · found {idea.date_found?.slice(0, 10)}
          {idea.evergreen ? " · evergreen" : ""}
        </span>
        {idea.source_url && <SourceLink href={idea.source_url}>{idea.source_name || hostOf(idea.source_url)}</SourceLink>}
      </footer>
    </article>
  );
}

function Grid({ state, emptyHint, render }) {
  if (state.error) {
    return (
      <Notice title="Cannot reach the database" alert>
        The dashboard could not load data ({state.error}). Check DATABASE_URL.
      </Notice>
    );
  }
  if (state.loading && state.items.length === 0) return <Notice title="Loading" />;
  if (state.items.length === 0) return <Notice title="Nothing here yet">{emptyHint}</Notice>;
  return <div className="gridlines md:grid-cols-2 2xl:grid-cols-3">{state.items.map(render)}</div>;
}

/* ---------- data hook ---------- */

function useList(path, params, active) {
  const [state, setState] = useState({ items: [], loading: true, error: null });
  const key = JSON.stringify(params);

  const load = useCallback(async () => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(JSON.parse(key))) if (v && v !== "All" && v !== "All open") qs.set(k, v);
    try {
      const items = await getJson(`${path}?${qs}`);
      setState({ items, loading: false, error: null });
    } catch (err) {
      setState((s) => ({ ...s, loading: false, error: err.message }));
    }
  }, [path, key]);

  useEffect(() => {
    if (!active) return undefined;
    setState((s) => ({ ...s, loading: true }));
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [load, active]);

  return state;
}

/* ---------- waiting queue (same as the AI Hub) ---------- */

function QueueTab() {
  const [source, setSource] = useState("All");
  const [limit, setLimit] = useState(QUEUE_PAGE);
  const [state, setState] = useState({ data: null, loading: true, error: null });

  const load = useCallback(async () => {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (source !== "All") qs.set("source", source);
    try {
      const data = await getJson(`/api/queue?${qs}`);
      setState({ data, loading: false, error: null });
    } catch (err) {
      setState((s) => ({ ...s, loading: false, error: err.message }));
    }
  }, [source, limit]);

  useEffect(() => {
    setState((s) => ({ ...s, loading: true }));
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  if (state.error) {
    return (
      <Notice title="Cannot reach the database" alert>
        The waiting queue could not load ({state.error}).
      </Notice>
    );
  }
  const data = state.data;
  if (!data) return <Notice title="Loading" />;
  if (data.waiting === 0) {
    return <Notice title="Queue is empty">Every fetched article has been summarised or rejected.</Notice>;
  }

  const shownTotal = source === "All" ? data.waiting : data.sources.find((s) => s.source === source)?.count ?? 0;
  const summary = [
    ["Waiting", data.waiting],
    ["Sources waiting", data.sources.length],
    ["Published in last 24h", data.last_24h],
    ["Stuck (3 failed tries)", data.stuck, data.stuck > 0],
    ["Oldest item", timeAgo(data.oldest)],
  ];

  return (
    <div className="space-y-8">
      <p className="max-w-[70ch] text-[14px] leading-relaxed text-dim">
        Articles and Instagram posts fetched but not yet read by the daily Claude run. They are not checked and have
        no summary yet.
      </p>
      <dl className="gridlines grid-cols-2 md:grid-cols-5" aria-label="Queue status">
        {summary.map(([name, value, warn]) => (
          <div key={name} className="cell p-4">
            <dt className="label">{name}</dt>
            <dd className={`mt-1 font-display text-2xl uppercase ${warn ? "text-hazard" : "text-phosphor"}`}>{value}</dd>
          </div>
        ))}
      </dl>
      <div>
        <h2 className="label mb-3">By source</h2>
        <div className="gridlines grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {[{ source: "All", count: data.waiting, newest: null }, ...data.sources].map((s) => {
            const active = source === s.source;
            return (
              <button
                key={s.source}
                type="button"
                aria-pressed={active}
                onClick={() => {
                  setSource(s.source);
                  setLimit(QUEUE_PAGE);
                }}
                className={`cell flex min-w-0 items-center justify-between gap-3 p-3 text-left transition-colors ${
                  active ? "!bg-hazard text-crt" : "text-phosphor hover:text-hazard"
                }`}
              >
                <span className="min-w-0">
                  <span className="block truncate text-[12px] uppercase tracking-[0.06em]">
                    {s.source === "All" ? "All sources" : s.source}
                  </span>
                  {s.newest && (
                    <span className={`block text-[11px] ${active ? "text-crt" : "text-dim"}`}>newest {timeAgo(s.newest)}</span>
                  )}
                </span>
                <span className="shrink-0 font-display text-lg">{s.count}</span>
              </button>
            );
          })}
        </div>
      </div>
      <div>
        <h2 className="label mb-3">
          {source === "All" ? "All sources" : source}, newest first ({Math.min(data.items.length, shownTotal)} of{" "}
          {shownTotal})
        </h2>
        <ol className="gridlines">
          {data.items.map((item) => (
            <li key={item.id} className="cell grid gap-x-6 gap-y-1 p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,14rem)_6rem]">
              <a
                href={item.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="min-w-0 break-words text-[13px] leading-snug text-phosphor underline decoration-line underline-offset-4 hover:text-hazard hover:decoration-hazard"
              >
                {item.title || hostOf(item.source_url)}
              </a>
              <p className="label truncate">{item.source_label}</p>
              <p className="label md:text-right">
                <time dateTime={item.published_at}>{timeAgo(item.published_at)}</time>
                {item.attempts > 0 && <span className="ml-2 text-hazard">try {item.attempts}</span>}
              </p>
            </li>
          ))}
        </ol>
        {data.items.length < shownTotal && (
          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={() => setLimit((n) => Math.min(500, n + QUEUE_PAGE))}
              disabled={state.loading || limit >= 500}
              className="border border-hazard px-4 py-2 text-[11px] uppercase tracking-[0.1em] text-hazard hover:bg-hazard hover:text-crt disabled:opacity-50"
            >
              {state.loading ? "Loading" : "Show more"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------- page ---------- */

export default function Dashboard() {
  const [tab, setTab] = useState("ideas");
  const [ideaStatus, setIdeaStatus] = useState("All open");
  const [ideaRegion, setIdeaRegion] = useState("All");
  const [region, setRegion] = useState("All");
  const [category, setCategory] = useState("All");
  const [stats, setStats] = useState(null);

  const ideas = useList("/api/ideas", { status: ideaStatus, region: ideaRegion }, tab === "ideas");
  const feed = useList("/api/intel", { region, category }, tab === "feed");
  const insta = useList("/api/intel", { region, category, limit: "120" }, tab === "instagram");
  const instaItems = { ...insta, items: insta.items.filter((i) => (i.source_label || "").startsWith("Instagram")) };

  useEffect(() => {
    const load = () => getJson("/api/stats").then(setStats).catch(() => setStats(null));
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, []);

  const onTabKey = (e) => {
    const i = TABS.findIndex((t) => t.id === tab);
    let next = null;
    if (e.key === "ArrowRight") next = TABS[(i + 1) % TABS.length];
    if (e.key === "ArrowLeft") next = TABS[(i - 1 + TABS.length) % TABS.length];
    if (next) {
      e.preventDefault();
      setTab(next.id);
      document.getElementById(`tab-${next.id}`)?.focus();
    }
  };

  const r7 = stats?.regions_7d || {};
  const telemetry = [
    ["Polling", stats ? (stats.polling_active ? "On" : "Off") : "No link", stats && !stats.polling_active],
    ["Verified 24h", stats?.verified_last_24h ?? "-"],
    ["Open ideas", stats?.ideas_open ?? "-"],
    ["Waiting", stats?.waiting_total ?? "-"],
    ["Sources", stats ? `${stats.sources_enabled} + ${stats.instagram_targets} IG` : "-"],
    ["Apify this month", stats ? `$${Number(stats.apify_month_usd).toFixed(2)} / $5` : "-", stats && stats.apify_month_usd > 4.5],
    ["Last poll", stats ? timeAgo(stats.last_poll_at) : "-"],
  ];

  return (
    <div className="mx-auto min-h-screen max-w-[1600px] px-4 pb-16 pt-6 md:px-8">
      <header className="border-b border-hazard pb-6">
        <p className="label">Zenfest Events · Tamil Nadu · Content desk</p>
        <h1
          className="mt-3 break-words font-display font-semibold uppercase leading-[0.95] tracking-[-0.01em] text-phosphor"
          style={{ fontSize: "clamp(2.2rem, 7vw, 6.5rem)" }}
        >
          Intelligence <span className="text-hazard">Hub</span>
        </h1>
        <p className="mt-4 max-w-[64ch] text-[15px] leading-relaxed text-dim">
          Event news from Tamil Nadu, India and the world (East Asia and the Gulf too), turned into daily reel ideas.
          An item is shown only if its quoted sentence is found, word for word, in the page it came from.
        </p>
      </header>

      <dl className="gridlines mt-6 grid-cols-2 md:grid-cols-4 xl:grid-cols-7" aria-label="System status">
        {telemetry.map(([name, value, warn]) => (
          <div key={name} className="cell p-4">
            <dt className="label">{name}</dt>
            <dd className={`mt-1 font-display text-2xl uppercase ${warn || !stats ? "text-hazard" : "text-phosphor"}`}>{value}</dd>
          </div>
        ))}
      </dl>

      <p className="label mt-3">
        Last 7 days by region:{" "}
        {REGIONS.slice(1)
          .map((r) => `${r} ${r7[r] ?? 0}`)
          .join(" · ")}
      </p>

      <div role="tablist" aria-label="Sections" onKeyDown={onTabKey} className="mt-10 flex flex-wrap border-b border-line">
        {TABS.map((t, i) => {
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              id={`tab-${t.id}`}
              role="tab"
              type="button"
              aria-selected={active}
              aria-controls={`panel-${t.id}`}
              tabIndex={active ? 0 : -1}
              onClick={() => setTab(t.id)}
              className={`-mb-px border-b-2 px-4 py-3 text-xs uppercase tracking-[0.1em] transition-colors ${
                active ? "border-hazard text-phosphor" : "border-transparent text-dim hover:text-phosphor"
              }`}
            >
              <span className="mr-2 text-dim">0{i + 1}</span>
              {t.label}
            </button>
          );
        })}
      </div>

      <main className="mt-8">
        {tab === "ideas" && (
          <section id="panel-ideas" role="tabpanel" aria-labelledby="tab-ideas" className="space-y-6">
            <p className="max-w-[70ch] text-[14px] leading-relaxed text-dim">
              Every morning Claude picks a mix of ideas (Tamil Nadu, India and the world) from the verified news and
              marks one Today&rsquo;s Pick. Nothing is produced until the owner approves a script.
            </p>
            <FilterBar label="Status" options={IDEA_STATUSES} value={ideaStatus} onChange={setIdeaStatus} />
            <FilterBar label="Region" options={REGIONS} value={ideaRegion} onChange={setIdeaRegion} />
            <Grid
              state={ideas}
              emptyHint="No ideas match. The daily idea run adds 7-8 every morning."
              render={(idea) => <IdeaCard key={idea.id} idea={idea} />}
            />
          </section>
        )}

        {tab === "feed" && (
          <section id="panel-feed" role="tabpanel" aria-labelledby="tab-feed" className="space-y-6">
            <FilterBar label="Region" options={REGIONS} value={region} onChange={setRegion} />
            <FilterBar label="Category" options={CATEGORIES} value={category} onChange={setCategory} />
            <Grid
              state={feed}
              emptyHint="No verified items match yet. New items appear after the daily Claude run."
              render={(item) => <IntelCard key={item.id} item={item} />}
            />
          </section>
        )}

        {tab === "instagram" && (
          <section id="panel-instagram" role="tabpanel" aria-labelledby="tab-instagram" className="space-y-6">
            <p className="max-w-[70ch] text-[14px] leading-relaxed text-dim">
              Verified posts from the Instagram pages and hashtags we follow (read through Apify inside the free $5 a
              month). Ideas only: never repost anyone&rsquo;s photos or videos.
            </p>
            <FilterBar label="Region" options={REGIONS} value={region} onChange={setRegion} />
            <Grid
              state={instaItems}
              emptyHint="No Instagram posts verified yet. Accounts run every 2 days, hashtags on Mondays."
              render={(item) => <IntelCard key={item.id} item={item} />}
            />
          </section>
        )}

        {tab === "queue" && (
          <section id="panel-queue" role="tabpanel" aria-labelledby="tab-queue">
            <QueueTab />
          </section>
        )}
      </main>

      <footer className="mt-16 border-t border-line pt-4">
        <p className="label">
          The quote check confirms the quote exists in the source. Titles, summaries and hooks are written by Claude:
          open the source before using a fact in a reel.
        </p>
      </footer>
    </div>
  );
}
