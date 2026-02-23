"""
RSS Feed Aggregator
Fetches and normalizes news from 40+ global RSS sources.
Each feed is tagged with category, region, and bias level.
"""
import asyncio
import hashlib
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field, asdict

import httpx
import feedparser
from dateutil import parser as dateparser

logger = logging.getLogger("feeds")

# ─── Feed Registry ──────────────────────────────────────────────────────────
# Each feed: (url, name, category, region, bias_tag)
# bias_tag: "neutral", "western", "state-affiliated", "financial"

FEED_SOURCES = [
    # ── Breaking / Wire Services ──
    ("https://news.google.com/rss/search?q=source:Reuters+when:24h&hl=en-US&gl=US&ceid=US:en", "Reuters Top", "breaking", "global", "neutral"),
    ("https://news.google.com/rss/search?q=source:Reuters+World+when:24h&hl=en-US&gl=US&ceid=US:en", "Reuters World", "geopolitical", "global", "neutral"),
    ("https://news.google.com/rss/search?q=source:Reuters+Business+when:24h&hl=en-US&gl=US&ceid=US:en", "Reuters Business", "markets", "global", "neutral"),
    ("https://rss.ap.org/rss/apf-topnews", "AP News", "breaking", "global", "neutral"),
    ("https://rss.ap.org/rss/apf-intlnews", "AP International", "geopolitical", "global", "neutral"),

    # ── Major Western ──
    ("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC World", "geopolitical", "global", "western"),
    ("https://feeds.bbci.co.uk/news/business/rss.xml", "BBC Business", "markets", "global", "western"),
    ("https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "NYT World", "geopolitical", "global", "western"),
    ("https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "NYT Business", "markets", "us", "western"),
    ("https://www.theguardian.com/world/rss", "Guardian World", "geopolitical", "global", "western"),
    ("https://feeds.washingtonpost.com/rss/world", "WaPo World", "geopolitical", "us", "western"),

    # ── Financial / Markets ──
    ("https://feeds.bloomberg.com/markets/news.rss", "Bloomberg Markets", "markets", "global", "financial"),
    ("https://www.cnbc.com/id/100003114/device/rss/rss.html", "CNBC World", "markets", "global", "financial"),
    ("https://www.cnbc.com/id/10000664/device/rss/rss.html", "CNBC Finance", "markets", "us", "financial"),
    ("https://feeds.marketwatch.com/marketwatch/topstories/", "MarketWatch", "markets", "us", "financial"),
    ("https://www.ft.com/rss/home", "Financial Times", "markets", "global", "financial"),
    ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US", "Yahoo Finance", "markets", "us", "financial"),
    ("https://www.economist.com/finance-and-economics/rss.xml", "The Economist", "markets", "global", "financial"),

    # ── Crypto ──
    ("https://cointelegraph.com/rss", "CoinTelegraph", "crypto", "global", "financial"),
    ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk", "crypto", "global", "financial"),
    ("https://decrypt.co/feed", "Decrypt", "crypto", "global", "financial"),
    ("https://bitcoinmagazine.com/.rss/full/", "Bitcoin Magazine", "crypto", "global", "financial"),

    # ── Middle East ──
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera", "geopolitical", "middle-east", "neutral"),
    ("https://www.middleeasteye.net/rss", "Middle East Eye", "geopolitical", "middle-east", "neutral"),

    # ── Asia ──
    ("https://www.scmp.com/rss/91/feed", "SCMP", "geopolitical", "asia", "neutral"),
    ("https://english.kyodonews.net/rss/all.xml", "Kyodo News", "geopolitical", "asia", "neutral"),
    ("https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "Times of India", "breaking", "asia", "neutral"),

    # ── State-Affiliated (included for completeness, tagged) ──
    ("https://tass.com/rss/v2.xml", "TASS", "geopolitical", "russia", "state-affiliated"),
    ("http://www.xinhuanet.com/english/rss/worldrss.xml", "Xinhua", "geopolitical", "china", "state-affiliated"),

    # ── Defense / Military ──
    ("https://breakingdefense.com/feed/", "Breaking Defense", "military", "global", "western"),
    ("https://www.military.com/rss-feeds/content?keyword=news", "Military.com", "military", "global", "western"),
    ("https://news.usni.org/feed", "USNI News", "military", "global", "western"),
    ("https://www.stripes.com/rss", "Stars and Stripes", "military", "global", "western"),
    ("https://www.armyrecognition.com/rss", "Army Recognition", "military", "global", "neutral"),
    ("https://www.navalnews.com/feed/", "Naval News", "military", "global", "neutral"),

    # ── Cyber Security ──
    ("https://thehackernews.com/feeds/posts/default", "Hacker News (Security)", "cyber", "global", "neutral"),
    ("https://feeds.feedburner.com/TheHackersNews", "THN", "cyber", "global", "neutral"),
    ("https://www.bleepingcomputer.com/feed/", "BleepingComputer", "cyber", "global", "neutral"),
    ("https://krebsonsecurity.com/feed/", "Krebs on Security", "cyber", "global", "neutral"),
    ("https://www.darkreading.com/rss.xml", "Dark Reading", "cyber", "global", "neutral"),

    # ── Science / Disaster ──
    ("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.atom", "USGS Earthquakes", "disaster", "global", "neutral"),
    ("https://reliefweb.int/updates/rss.xml", "ReliefWeb", "disaster", "global", "neutral"),

    # ── Energy ──
    ("https://oilprice.com/rss/main", "OilPrice", "energy", "global", "financial"),
    ("https://www.rigzone.com/news/rss/rigzone_latest.aspx", "Rigzone", "energy", "global", "financial"),
    ("https://www.energyvoice.com/feed/", "Energy Voice", "energy", "global", "financial"),
    ("https://www.upstreamonline.com/rss", "Upstream Online", "energy", "global", "financial"),

    # ── India ──
    ("https://www.thehindu.com/news/international/feeder/default.rss", "The Hindu World", "geopolitical", "asia", "neutral"),
    ("https://indianexpress.com/section/world/feed/", "Indian Express", "geopolitical", "asia", "neutral"),
    ("https://www.livemint.com/rss/world", "LiveMint World", "geopolitical", "asia", "financial"),

    # ── Africa ──
    ("https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf", "AllAfrica", "geopolitical", "africa", "neutral"),
    ("https://www.africanews.com/feed/", "AfricaNews", "geopolitical", "africa", "neutral"),
    ("https://feeds.news24.com/articles/news24/World/rss", "News24 World", "geopolitical", "africa", "neutral"),

    # ── Central & South America ──
    ("https://en.mercopress.com/rss", "MercoPress", "geopolitical", "south-america", "neutral"),
    ("https://www.batimes.com.ar/feed", "Buenos Aires Times", "geopolitical", "south-america", "neutral"),
    ("https://ticotimes.net/feed", "Tico Times", "geopolitical", "central-america", "neutral"),
    ("https://www.riotimesonline.com/feed/", "Rio Times", "geopolitical", "south-america", "western"),
]


@dataclass
class NewsItem:
    id: str
    title: str
    summary: str
    link: str
    source: str
    category: str
    region: str
    bias_tag: str
    published: str
    fetched_at: float
    severity: str = "normal"  # "normal", "elevated", "breaking"

    def to_dict(self):
        return asdict(self)


class FeedAggregator:
    """Fetches, deduplicates, and stores news items from all RSS sources."""

    def __init__(self):
        self.items: dict[str, NewsItem] = {}  # id -> NewsItem
        self.last_fetch: float = 0
        self.fetch_errors: dict[str, str] = {}
        self._lock = asyncio.Lock()

    def _make_id(self, title: str, link: str) -> str:
        raw = f"{title.strip().lower()}|{link.strip().lower()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _detect_severity(self, title: str) -> str:
        title_lower = title.lower()
        breaking_keywords = [
            "breaking", "urgent", "just in", "developing",
            "flash", "alert", "emergency"
        ]
        elevated_keywords = [
            "war", "attack", "invasion", "missile", "bomb", "explosion",
            "sanctions", "crash", "collapse", "crisis", "default",
            "nuclear", "killed", "assassination", "coup", "martial law",
            "rate hike", "rate cut", "fed ", "ecb ", "boj ",
            "hack", "breach", "ransomware",
        ]
        for kw in breaking_keywords:
            if kw in title_lower:
                return "breaking"
        for kw in elevated_keywords:
            if kw in title_lower:
                return "elevated"
        return "normal"

    def _parse_date(self, entry) -> str:
        for field_name in ("published", "updated", "created"):
            raw = getattr(entry, field_name, None) or entry.get(field_name)
            if raw:
                try:
                    dt = dateparser.parse(str(raw))
                    if dt:
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt.isoformat()
                except Exception:
                    pass
        return datetime.now(timezone.utc).isoformat()

    async def _fetch_single_feed(self, client: httpx.AsyncClient, url: str,
                                  name: str, category: str, region: str,
                                  bias_tag: str) -> list[NewsItem]:
        items = []
        try:
            resp = await client.get(url, timeout=15.0)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:20]:  # cap per feed
                title = entry.get("title", "").strip()
                if not title:
                    continue
                link = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))
                # Strip HTML tags from summary
                if summary:
                    import re
                    summary = re.sub(r'<[^>]+>', '', summary).strip()
                    summary = summary[:500]  # cap length

                item_id = self._make_id(title, link)
                item = NewsItem(
                    id=item_id,
                    title=title,
                    summary=summary,
                    link=link,
                    source=name,
                    category=category,
                    region=region,
                    bias_tag=bias_tag,
                    published=self._parse_date(entry),
                    fetched_at=time.time(),
                    severity=self._detect_severity(title),
                )
                items.append(item)
            self.fetch_errors.pop(name, None)
        except Exception as e:
            self.fetch_errors[name] = str(e)
            logger.warning(f"Feed error [{name}]: {e}")
        return items

    async def fetch_all(self):
        """Fetch all feeds concurrently with connection pooling."""
        logger.info(f"Fetching {len(FEED_SOURCES)} feeds...")
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "WorldNewsMap/1.0 (News Aggregator)"},
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        ) as client:
            tasks = [
                self._fetch_single_feed(client, url, name, cat, region, bias)
                for url, name, cat, region, bias in FEED_SOURCES
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        async with self._lock:
            new_count = 0
            for result in results:
                if isinstance(result, list):
                    for item in result:
                        if item.id not in self.items:
                            new_count += 1
                        self.items[item.id] = item
            self.last_fetch = time.time()

            # Prune old items (keep last 24 hours only)
            cutoff = time.time() - 86400
            expired = [k for k, v in self.items.items() if v.fetched_at < cutoff]
            for k in expired:
                del self.items[k]

            logger.info(f"Feed update complete: {new_count} new, {len(self.items)} total, {len(expired)} pruned")

    def get_items(self, category: Optional[str] = None,
                  region: Optional[str] = None,
                  severity: Optional[str] = None,
                  limit: int = 100,
                  search: Optional[str] = None) -> list[dict]:
        """Return filtered, sorted news items."""
        items = list(self.items.values())

        if category:
            items = [i for i in items if i.category == category]
        if region:
            items = [i for i in items if i.region == region]
        if severity:
            items = [i for i in items if i.severity == severity]
        if search:
            q = search.lower()
            items = [i for i in items if q in i.title.lower() or q in i.summary.lower()]

        # Sort by published date descending
        items.sort(key=lambda x: x.published, reverse=True)
        return [i.to_dict() for i in items[:limit]]

    def get_stats(self) -> dict:
        """Return aggregator statistics."""
        items = list(self.items.values())
        categories = {}
        regions = {}
        severities = {"normal": 0, "elevated": 0, "breaking": 0}
        for item in items:
            categories[item.category] = categories.get(item.category, 0) + 1
            regions[item.region] = regions.get(item.region, 0) + 1
            severities[item.severity] = severities.get(item.severity, 0) + 1

        return {
            "total_items": len(items),
            "total_sources": len(FEED_SOURCES),
            "sources_with_errors": len(self.fetch_errors),
            "last_fetch": self.last_fetch,
            "categories": categories,
            "regions": regions,
            "severities": severities,
            "errors": self.fetch_errors,
        }
