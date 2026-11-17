"""The source catalog for the Zenfest Intelligence Hub. Every endpoint here is free and needs no key.

Copied from the AI Intelligent Hub and refilled with event sources (owner, 2026-11-17).
The list mixes five regions so the daily reel can mix them too:
  Tamil Nadu  - our audience: city news, Tamil-language news, local event listings
  India       - wedding platforms and the events trade
  Global      - event trade titles, décor and design, festivals
  East Asia   - China, Korea, Japan: event tech (drone shows, media art, LED) shows up here first
  Middle East - Dubai, Riyadh: giant festivals and installations, also ahead of India

text_from:
  "page"  -> download the linked article and extract its text (falls back to the entry body)
  "entry" -> use the text inside the feed entry itself

kind:
  "rss" -> RSS or Atom feed (the only kind used so far)

events_only: True for general news feeds (city papers, Tamil news, Gulf and Asian dailies).
             Only items whose title or summary contains an event word (EVENT_WORDS) are kept,
             so the queue is not flooded with politics and cricket scores.
max_entries: how many of the newest entries to look at per run (default: config.ENTRIES_PER_FEED).

Instagram accounts and hashtags are NOT feeds: they are read through Apify by instagram_ingest.py
(see INSTAGRAM_ACCOUNTS / INSTAGRAM_HASHTAGS below), inside the free $5 monthly credit.

Not used, on purpose:
  - LinkedIn: its User Agreement bans bots and scrapers. Follow pages and turn on notifications.
  - Reddit: needs API approval (Responsible Builder Policy), same as the AI Hub.
  - Douyin, Xiaohongshu, Weibo, Bilibili: block automated reading; China is covered through
    Chinese-language news via the self-hosted RSSHub instead (owner's choice, 2026-11-17).

Set enabled=False to switch a source off. Run `python check_feeds.py` to see which are alive.
"""
import os
from dataclasses import dataclass
from typing import List
from urllib.parse import quote

import config  # noqa: F401  (loads backend/.env so RSSHUB_URL is set however this file is imported)


@dataclass(frozen=True)
class Feed:
    label: str
    url: str
    group: str  # the region: Tamil Nadu, India, Global, East Asia, Middle East
    interval_min: int
    text_from: str = "page"
    enabled: bool = True
    note: str = ""
    kind: str = "rss"
    keep_all: bool = False  # True = publish every item, even when it is not about events
    max_entries: int = 0  # 0 = use config.ENTRIES_PER_FEED
    events_only: bool = False  # True = keep only items that mention an event word
    scan_only: bool = False  # True = listed by daily_scan.py but never queued for Claude


REGIONS = ("Tamil Nadu", "India", "Global", "East Asia", "Middle East")

# Words that mark an item as event news, for general news feeds (events_only=True).
# English, Tamil and Chinese. Matched case-insensitively against title + summary.
EVENT_WORDS = (
    # English
    "wedding", "marriage hall", "mandapam", "reception", "engagement", "baby shower", "valaikappu",
    "birthday", "housewarming", "griha pravesam", "puberty", "naming ceremony", "festival", "fest ",
    "celebration", "concert", "exhibition", "expo", "trade show", "conference", "carnival",
    "event", "décor", "decor", "decoration", "light show", "drone show", "drone light", "fireworks",
    "projection mapping", "art installation", "immersive", "pop-up", "launch event", "parade", "pongal",
    "deepavali", "diwali", "margazhi", "chithirai", "karthigai", "navaratri", "golu", "christmas",
    "new year", "eid", "mice", "venue", "banquet", "lantern", "theme park", "riyadh season",
    # Tamil
    "திருமண", "கல்யாண", "மண்டப", "விழா", "கொண்டாட்ட", "அலங்கார", "நிகழ்ச்சி", "திருவிழா", "வளைகாப்பு",
    "பிறந்தநாள்", "கச்சேரி", "கண்காட்சி", "பொங்கல்", "தீபாவளி", "மார்கழி", "வரவேற்பு", "நிச்சயதார்த்த",
    # Chinese
    "无人机", "灯光秀", "光影", "沉浸式", "婚礼", "舞台", "演唱会", "展览", "裸眼3D", "全息", "灯会",
    "烟花", "庆典", "春晚", "音乐节", "嘉年华", "文旅", "夜游",
)

# Instagram, read through Apify by instagram_ingest.py. Handles without "@".
# Kept small on purpose: about 30 accounts every 2 days + 5 hashtags a week stays inside the free
# $5 monthly Apify credit (owner, 2026-11-17). instagram_ingest.py also stops itself near the cap.
INSTAGRAM_ACCOUNTS = {
    "Tamil Nadu": ["weddingchakra", "vermiliondecors", "zigzagdecors", "pandian_decor", "studioa_weddings",
                   "knotstories", "dreamlightmedia"],
    "India": ["wedmegoodsouth", "wedmegood", "weddingsutra", "shaadisquad", "theweddingdesigncompany",
              "devikanarainandcompany", "abhinavbhagatevents", "ranipinklove", "botlab.dynamics"],
    "Global": ["bizbash", "jeffleatham", "stylemepretty", "junebugweddings", "weddingchicks", "skyelementsdrones",
               "teamlab", "momentfactory", "refikanadol"],
    "East Asia": ["dstrictholdings"],
    "Middle East": ["arabiaweddings", "alibakhtiardesigns", "brideclubme"],
}
INSTAGRAM_HASHTAGS = {
    "Tamil Nadu": ["chennaiweddingdecor", "tamilwedding"],
    "India": ["mandapdecor", "southindianwedding"],
    "Global": ["eventdecor"],
}

# Base address of your self-hosted RSSHub (see rsshub/README.md). Empty = RSSHub sources stay off.
# The same Render server the AI Hub uses (it is named zenfest-rsshub).
RSSHUB_URL = os.getenv("RSSHUB_URL", "").strip().rstrip("/")


def bing(query: str, market: str = "en-IN") -> str:
    """Bing News search as RSS. Links redirect to the real article, so the page text can be read."""
    return f"https://www.bing.com/news/search?q={quote(query)}&format=rss&setmkt={market}"


def rsshub(path: str) -> str:
    return RSSHUB_URL + path


FEEDS: List[Feed] = [
    # ---------------------------------------------------------------- Tamil Nadu
    Feed("The Hindu - Tamil Nadu", "https://www.thehindu.com/news/national/tamil-nadu/feeder/default.rss",
         "Tamil Nadu", 30, events_only=True, max_entries=40),
    Feed("The Hindu - Chennai", "https://www.thehindu.com/news/cities/chennai/feeder/default.rss",
         "Tamil Nadu", 30, events_only=True, max_entries=40),
    Feed("The Hindu - Coimbatore", "https://www.thehindu.com/news/cities/Coimbatore/feeder/default.rss",
         "Tamil Nadu", 60, events_only=True, max_entries=40),
    Feed("The Hindu - Madurai", "https://www.thehindu.com/news/cities/Madurai/feeder/default.rss",
         "Tamil Nadu", 60, events_only=True, max_entries=40),
    Feed("The Hindu - Tiruchi", "https://www.thehindu.com/news/cities/Tiruchirapalli/feeder/default.rss",
         "Tamil Nadu", 60, events_only=True, max_entries=40),
    Feed("DT Next", "https://www.dtnext.in/stories.rss", "Tamil Nadu", 30, events_only=True, max_entries=40),
    Feed("Hindu Tamil Thisai (Tamil)", "https://www.hindutamil.in/stories.rss", "Tamil Nadu", 30,
         events_only=True, max_entries=40, note="Tamil-language news; Claude translates."),
    Feed("Dinamani (Tamil)", "https://www.dinamani.com/stories.rss", "Tamil Nadu", 30,
         events_only=True, max_entries=40, note="Tamil-language news; Claude translates."),
    Feed("Vikatan (Tamil)", "https://www.vikatan.com/stories.rss", "Tamil Nadu", 30,
         events_only=True, max_entries=40, note="Tamil-language news; Claude translates."),
    Feed("Mylapore Times", "https://www.mylaporetimes.com/feed/", "Tamil Nadu", 60),
    Feed("The Madras Day", "https://themadrasday.in/feed/", "Tamil Nadu", 360,
         note="Posts rarely (newest was 85 days old on 2026-11-17); kept for Madras Week and Margazhi."),
    Feed("AllEvents Chennai", "https://allevents.in/chennai/RSS", "Tamil Nadu", 360, "entry",
         scan_only=True,
         note="Ticket listings (runs, matches, stand-up), not news: shown in daily_scan only, never queued "
              "(owner's first test run, 2026-11-17: 5 of 5 were not usable)."),
    Feed("News: Tamil Nadu weddings", bing("Tamil Nadu wedding"), "Tamil Nadu", 360,
         note="Bing News search; links redirect to the real article.", events_only=True),
    Feed("News: Chennai events", bing("Chennai event OR festival OR exhibition"), "Tamil Nadu", 360, events_only=True),
    Feed("News: Coimbatore events", bing("Coimbatore event OR festival OR wedding"), "Tamil Nadu", 360, events_only=True),
    Feed("News: Madurai events", bing("Madurai festival OR event OR wedding"), "Tamil Nadu", 360, events_only=True),
    Feed("News: Tamil wedding halls (Tamil)", bing("திருமண மண்டபம்"), "Tamil Nadu", 720,
         note="Tamil-language search; few results, often old.", events_only=True),
    # ---------------------------------------------------------------- India
    Feed("EventFAQs", "https://in.eventfaqs.com/feed/", "India", 30),
    Feed("WeddingSutra Blog", "https://weddingsutra.com/blog/feed/", "India", 60),
    Feed("Wedding Affair", "https://weddingaffair.co.in/feed/", "India", 120),
    Feed("MediaNews4U", "https://www.medianews4u.com/feed/", "India", 60, events_only=True),
    Feed("TravTalk India", "https://travtalkindia.com/feed/", "India", 120),
    Feed("Exhibition Showcase", "https://www.exhibitionshowcase.com/feed/", "India", 120),
    Feed("News: WedMeGood", bing("WedMeGood wedding"), "India", 720,
         note="WedMeGood's blog has no feed (404); news coverage of its reports instead.", events_only=True),
    Feed("News: exchange4media events", bing("site:exchange4media.com event"), "India", 720,
         note="exchange4media has no working feed. The query already asks for events, so no word filter."),
    Feed("News: India wedding trends", bing("Indian wedding trends"), "India", 720, events_only=True),
    # ---------------------------------------------------------------- Global
    Feed("BizBash", "https://www.bizbash.com/rss.xml", "Global", 30,
         note="Lists future-dated event pages too (newest showed -16 days); those are skipped by date."),
    Feed("Skift Meetings", "https://meetings.skift.com/feed/", "Global", 60),
    Feed("TTGmice", "https://www.ttgmice.com/feed/", "Global", 60),
    Feed("TSNN", "https://www.tsnn.com/rss.xml", "Global", 60),
    Feed("Exhibition News", "https://exhibitionnews.uk/feed/", "Global", 60),
    Feed("Access All Areas", "https://accessaa.co.uk/feed/", "Global", 120),
    Feed("TPi Magazine", "https://www.tpimagazine.com/feed/", "Global", 120),
    Feed("Festival Insights", "https://www.festivalinsights.com/feed/", "Global", 120),
    Feed("Pollstar", "https://news.pollstar.com/feed/", "Global", 120),
    Feed("Smart Meetings", "https://www.smartmeetings.com/feed", "Global", 120),
    Feed("PCMA Convene", "https://www.pcma.org/feed/", "Global", 120),
    Feed("ICCA News", "https://www.iccaworld.org/feed/", "Global", 360),
    Feed("MIX Meetings", "https://mixmeetings.com/feed/", "Global", 360),
    Feed("mice.net.au", "https://mice.net.au/feed/", "Global", 360),
    Feed("blooloop", "https://blooloop.com/feeds/feed.rss", "Global", 60),
    Feed("DroneXL", "https://dronexl.co/feed.xml", "Global", 60, events_only=True,
         note="Drone news; only light shows and other event items are kept."),
    Feed("Designboom", "https://www.designboom.com/feed/", "Global", 60, events_only=True),
    Feed("My Modern Met", "https://mymodernmet.com/feed", "Global", 120, events_only=True),
    Feed("ILEA", "https://www.ileahub.com/blog-feed.xml", "Global", 720,
         note="Posts rarely (newest was 132 days old on 2026-11-17)."),
    Feed("News: Event Industry News", bing("site:eventindustrynews.com"), "Global", 360,
         note="Event Industry News has no working feed. Every item is event news, so no word filter."),
    Feed("News: Event Marketer", bing("site:eventmarketer.com"), "Global", 360,
         note="Event Marketer's feed returns 403. Every item is event news, so no word filter."),
    Feed("News: wedding décor trends", bing("wedding decor trends"), "Global", 720, events_only=True),
    Feed("News: event technology", bing("event technology OR \"drone light show\" OR \"projection mapping\"", "en-US"),
         "Global", 360, events_only=True),
    # ---------------------------------------------------------------- East Asia
    Feed("Entertainment Technology Asia", "https://www.e-techasia.com/feed/", "East Asia", 60),
    Feed("Korea Herald", "https://www.koreaherald.com/rss/newsAll", "East Asia", 60, events_only=True,
         max_entries=50),
    Feed("Korea Times", "https://feed.koreatimes.co.kr/k/allnews.xml", "East Asia", 60, events_only=True,
         max_entries=50),
    Feed("Japan Times", "https://www.japantimes.co.jp/feed/", "East Asia", 60, events_only=True, max_entries=30),
    Feed("d'strict (Korea media art)", "https://www.dstrict.com/rss", "East Asia", 720),
    Feed("News: China drone shows", bing("China drone show", "en-US"), "East Asia", 360, events_only=True),
    Feed("News: Japan projection mapping", bing("Japan projection mapping OR teamLab", "en-US"), "East Asia", 720, events_only=True),
    Feed("News: Korea media art", bing("Korea media art OR anamorphic", "en-US"), "East Asia", 720, events_only=True),
    Feed("36Kr search: drone shows (Chinese)", rsshub("/36kr/search/articles/" + quote("无人机表演")), "East Asia", 360,
         enabled=bool(RSSHUB_URL), note="Needs the self-hosted RSSHub. Chinese; Claude translates."),
    Feed("36Kr search: light shows (Chinese)", rsshub("/36kr/search/articles/" + quote("灯光秀")), "East Asia", 360,
         enabled=bool(RSSHUB_URL), note="Needs the self-hosted RSSHub. Chinese; Claude translates."),
    Feed("36Kr search: immersive (Chinese)", rsshub("/36kr/search/articles/" + quote("沉浸式")), "East Asia", 360,
         enabled=bool(RSSHUB_URL), note="Needs the self-hosted RSSHub. Chinese; Claude translates."),
    Feed("36Kr search: weddings (Chinese)", rsshub("/36kr/search/articles/" + quote("婚礼")), "East Asia", 720,
         enabled=bool(RSSHUB_URL), note="Needs the self-hosted RSSHub. Chinese; Claude translates."),
    Feed("The Paper (Chinese)", rsshub("/thepaper/featured"), "East Asia", 120, enabled=bool(RSSHUB_URL),
         events_only=True, max_entries=30, note="Needs the self-hosted RSSHub. Chinese news; event items only."),
    Feed("Zaobao China (Chinese)", rsshub("/zaobao/realtime/china"), "East Asia", 120, enabled=bool(RSSHUB_URL),
         events_only=True, max_entries=30, note="Needs the self-hosted RSSHub. Chinese news; event items only."),
    # ---------------------------------------------------------------- Middle East
    Feed("Gulf News", "https://gulfnews.com/stories.rss", "Middle East", 60, events_only=True, max_entries=40),
    Feed("Khaleej Times", "https://www.khaleejtimes.com/api/v1/collections/top-section.rss", "Middle East", 60,
         events_only=True, max_entries=40),
    Feed("Arab News", "https://www.arabnews.com/rss.xml", "Middle East", 60, events_only=True, max_entries=50),
    Feed("Arabian Business", "https://www.arabianbusiness.com/feed", "Middle East", 60, events_only=True,
         max_entries=60),
    Feed("Global Village Dubai", "https://www.globalvillage.ae/en/rss.xml", "Middle East", 720),
    Feed("News: Riyadh Season", bing("Riyadh Season", "en-US"), "Middle East", 360,
         note="Riyadh Season's site has no feed.", events_only=True),
    Feed("News: Dubai events", bing("Dubai event OR festival OR installation", "en-US"), "Middle East", 360, events_only=True),
    Feed("News: Saudi festivals", bing("Saudi festival OR \"Noor Riyadh\" OR \"light show\"", "en-US"),
         "Middle East", 720, events_only=True),
    # ---------------------------------------------------------------- off (no working free feed yet)
    Feed("WedMeGood Blog", "https://www.wedmegood.com/blog/feed/", "India", 60, enabled=False,
         note="404: no RSS. Covered by News: WedMeGood."),
    Feed("Event Industry News", "https://www.eventindustrynews.com/", "Global", 60, enabled=False,
         note="No RSS found. Covered by News: Event Industry News."),
    Feed("Event Marketer", "https://www.eventmarketer.com/feed/", "Global", 60, enabled=False,
         note="403 for automated readers. Covered by News: Event Marketer."),
    Feed("Rock My Wedding", "https://www.rockmywedding.co.uk/", "Global", 360, enabled=False, note="No RSS found."),
    Feed("Boardroom", "https://www.boardroom.global/", "Global", 360, enabled=False, note="No RSS found."),
    Feed("CGTN", "https://www.cgtn.com/", "East Asia", 360, enabled=False, note="No RSS found."),
    Feed("Xinhua Tech (Chinese)", "https://www.news.cn/tech/", "East Asia", 360, enabled=False, note="No RSS found."),
    Feed("SCMP Drones", "https://www.scmp.com/topics/drones", "East Asia", 360, enabled=False, note="No RSS found."),
    Feed("TradeArabia", "https://tradearabia.com/", "Middle East", 360, enabled=False, note="No RSS found."),
    Feed("r/weddingplanning", "https://www.reddit.com/r/weddingplanning/top/.rss?t=day", "Global", 60, "entry",
         enabled=False, note="Reddit requires API approval (Responsible Builder Policy), as in the AI Hub."),
]

ENABLED_FEEDS = [f for f in FEEDS if f.enabled]
# Sources whose items are published even when they are not about events.
KEEP_ALL_LABELS = {f.label for f in FEEDS if f.keep_all}
# Region of every source label, used when Claude's answer is saved.
REGION_OF = {f.label: f.group for f in FEEDS}
for _region, _handles in INSTAGRAM_ACCOUNTS.items():
    REGION_OF.update({f"Instagram @{h}": _region for h in _handles})
for _region, _tags in INSTAGRAM_HASHTAGS.items():
    REGION_OF.update({f"Instagram #{t}": _region for t in _tags})


import re  # noqa: E402

# English words must match as whole words ("eid" must not match "said"); Tamil and Chinese have no
# spaces between word parts, so those match anywhere.
_ASCII_WORDS = [w.strip() for w in EVENT_WORDS if w.strip().isascii()]
_EVENT_RE = re.compile(r"\b(?:" + "|".join(re.escape(w) + "s?" for w in _ASCII_WORDS) + r")\b", re.I)
_OTHER_WORDS = [w for w in EVENT_WORDS if not w.strip().isascii()]


def is_event_item(entry) -> bool:
    """True if the entry's TITLE mentions an event word (for events_only feeds).
    Only the title: general-news summaries mention 'event' or 'celebration' in passing far too often."""
    title = entry.get("title", "") or ""
    return bool(_EVENT_RE.search(title)) or any(w in title for w in _OTHER_WORDS)
