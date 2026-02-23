"""
Signal Engine
Computes trading-relevant signals from news + market data.
Your bots hit GET /api/signals to get a clean, actionable feed.
"""
import time
import logging
from typing import Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("signals")

# Keywords that indicate market-moving events, grouped by impact type
SIGNAL_RULES = {
    "rate_decision": {
        "keywords": ["rate hike", "rate cut", "interest rate", "fed ", "federal reserve",
                      "ecb ", "european central bank", "boj ", "bank of japan",
                      "rbi ", "reserve bank", "monetary policy", "basis points", "bps"],
        "impact": "high",
        "affects": ["forex", "crypto", "equities"],
    },
    "sanctions": {
        "keywords": ["sanctions", "sanctioned", "embargo", "trade ban", "blacklist",
                      "ofac", "export controls", "trade war", "tariff"],
        "impact": "high",
        "affects": ["forex", "commodities", "crypto"],
    },
    "conflict_escalation": {
        "keywords": ["war ", "invasion", "missile", "airstrike", "military operation",
                      "nuclear", "troops deployed", "nato ", "mobilization",
                      "martial law", "coup"],
        "impact": "critical",
        "affects": ["commodities", "forex", "crypto", "equities"],
    },
    "crypto_regulation": {
        "keywords": ["crypto regulation", "crypto ban", "bitcoin ban", "sec crypto",
                      "stablecoin", "cbdc", "digital currency", "defi regulation",
                      "crypto crackdown", "bitcoin etf", "ethereum etf"],
        "impact": "high",
        "affects": ["crypto"],
    },
    "market_crash": {
        "keywords": ["market crash", "stock crash", "flash crash", "black monday",
                      "circuit breaker", "trading halt", "market plunge",
                      "sell-off", "selloff", "capitulation"],
        "impact": "critical",
        "affects": ["equities", "crypto", "forex"],
    },
    "oil_energy": {
        "keywords": ["oil price", "opec", "oil production", "crude oil", "brent",
                      "natural gas", "energy crisis", "pipeline", "oil supply",
                      "petroleum", "lng"],
        "impact": "medium",
        "affects": ["commodities", "forex"],
    },
    "election_political": {
        "keywords": ["election", "elected", "inaugurated", "prime minister",
                      "president", "referendum", "impeach", "resign",
                      "political crisis", "government collapse"],
        "impact": "medium",
        "affects": ["forex", "equities"],
    },
    "cyber_attack": {
        "keywords": ["cyberattack", "cyber attack", "ransomware", "data breach",
                      "hacked", "hack ", "ddos", "zero-day", "vulnerability",
                      "apt ", "nation-state hack"],
        "impact": "medium",
        "affects": ["equities", "crypto"],
    },
    "natural_disaster": {
        "keywords": ["earthquake", "tsunami", "hurricane", "typhoon", "flood",
                      "wildfire", "volcanic eruption", "tornado"],
        "impact": "medium",
        "affects": ["commodities", "equities"],
    },
    "default_debt": {
        "keywords": ["default", "debt crisis", "sovereign debt", "bankruptcy",
                      "bail out", "bailout", "restructuring", "credit downgrade",
                      "junk status"],
        "impact": "high",
        "affects": ["forex", "equities", "crypto"],
    },
}


@dataclass
class Signal:
    id: str
    type: str  # key from SIGNAL_RULES
    impact: str  # "critical", "high", "medium"
    title: str
    summary: str
    source: str
    link: str
    affects: list[str]
    region: str
    timestamp: float
    news_id: str  # reference to the original news item

    def to_dict(self):
        d = asdict(self)
        return d


class SignalEngine:
    """Scans news items and generates trading signals."""

    def __init__(self):
        self.signals: dict[str, Signal] = {}
        self.processed_news_ids: set[str] = set()

    def process_news(self, news_items: list[dict]):
        """Scan news items and generate signals for any matching rules."""
        new_signals = 0
        for item in news_items:
            news_id = item.get("id", "")
            if news_id in self.processed_news_ids:
                continue
            self.processed_news_ids.add(news_id)

            title_lower = item.get("title", "").lower()
            summary_lower = item.get("summary", "").lower()
            text = f"{title_lower} {summary_lower}"

            for signal_type, rule in SIGNAL_RULES.items():
                for keyword in rule["keywords"]:
                    if keyword in text:
                        sig_id = f"{signal_type}:{news_id}"
                        if sig_id not in self.signals:
                            self.signals[sig_id] = Signal(
                                id=sig_id,
                                type=signal_type,
                                impact=rule["impact"],
                                title=item.get("title", ""),
                                summary=item.get("summary", "")[:300],
                                source=item.get("source", ""),
                                link=item.get("link", ""),
                                affects=rule["affects"],
                                region=item.get("region", "global"),
                                timestamp=item.get("fetched_at", time.time()),
                                news_id=news_id,
                            )
                            new_signals += 1
                        break  # one signal per rule per news item

        # Prune old signals (keep last 12 hours)
        cutoff = time.time() - 43200
        expired = [k for k, v in self.signals.items() if v.timestamp < cutoff]
        for k in expired:
            del self.signals[k]
        # Also prune processed IDs
        if len(self.processed_news_ids) > 50000:
            self.processed_news_ids = set(list(self.processed_news_ids)[-25000:])

        if new_signals:
            logger.info(f"Generated {new_signals} new signals, {len(self.signals)} total active")

    def get_signals(self, impact: Optional[str] = None,
                    signal_type: Optional[str] = None,
                    affects: Optional[str] = None,
                    limit: int = 50) -> list[dict]:
        """Return signals, optionally filtered."""
        items = list(self.signals.values())
        if impact:
            items = [s for s in items if s.impact == impact]
        if signal_type:
            items = [s for s in items if s.type == signal_type]
        if affects:
            items = [s for s in items if affects in s.affects]
        # Sort by timestamp desc, critical first
        impact_order = {"critical": 0, "high": 1, "medium": 2}
        items.sort(key=lambda x: (impact_order.get(x.impact, 3), -x.timestamp))
        return [s.to_dict() for s in items[:limit]]

    def get_stats(self) -> dict:
        items = list(self.signals.values())
        by_type = {}
        by_impact = {"critical": 0, "high": 0, "medium": 0}
        for s in items:
            by_type[s.type] = by_type.get(s.type, 0) + 1
            by_impact[s.impact] = by_impact.get(s.impact, 0) + 1
        return {
            "total_signals": len(items),
            "by_type": by_type,
            "by_impact": by_impact,
            "processed_news": len(self.processed_news_ids),
        }
