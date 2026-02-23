"""
Market Data Aggregator
Fetches crypto, forex, commodities, and stock index data from free APIs.
Designed for trading bot consumption — clean JSON, no fluff.
"""
import asyncio
import time
import logging
from dataclasses import dataclass, asdict
from typing import Optional

import httpx

logger = logging.getLogger("markets")


@dataclass
class MarketTicker:
    symbol: str
    name: str
    price: float
    change_24h: Optional[float]
    change_pct_24h: Optional[float]
    market_cap: Optional[float]
    volume_24h: Optional[float]
    category: str  # "crypto", "forex", "commodity", "index"
    updated_at: float

    def to_dict(self):
        return asdict(self)


@dataclass
class FearGreedData:
    value: int
    label: str  # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    timestamp: float

    def to_dict(self):
        return asdict(self)


class MarketAggregator:
    """Fetches market data from free public APIs."""

    def __init__(self):
        self.tickers: dict[str, MarketTicker] = {}
        self.fear_greed: Optional[FearGreedData] = None
        self.last_fetch: float = 0
        self.errors: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def fetch_all(self):
        """Fetch all market data concurrently."""
        logger.info("Fetching market data...")
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "WorldNewsMap/1.0"},
            timeout=20.0,
        ) as client:
            results = await asyncio.gather(
                self._fetch_crypto(client),
                self._fetch_fear_greed(client),
                self._fetch_forex_commodities(client),
                return_exceptions=True,
            )

        async with self._lock:
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Market fetch error: {result}")
            self.last_fetch = time.time()
            logger.info(f"Market update complete: {len(self.tickers)} tickers")

    async def _fetch_crypto(self, client: httpx.AsyncClient):
        """Fetch top crypto from CoinGecko (free, no key needed)."""
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 30,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h",
            }
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            for coin in data:
                symbol = coin["symbol"].upper()
                ticker = MarketTicker(
                    symbol=symbol,
                    name=coin["name"],
                    price=coin.get("current_price", 0),
                    change_24h=coin.get("price_change_24h"),
                    change_pct_24h=coin.get("price_change_percentage_24h"),
                    market_cap=coin.get("market_cap"),
                    volume_24h=coin.get("total_volume"),
                    category="crypto",
                    updated_at=time.time(),
                )
                self.tickers[f"crypto:{symbol}"] = ticker
            self.errors.pop("crypto", None)
        except Exception as e:
            self.errors["crypto"] = str(e)
            logger.warning(f"Crypto fetch error: {e}")

    async def _fetch_fear_greed(self, client: httpx.AsyncClient):
        """Fetch crypto fear & greed index."""
        try:
            url = "https://api.alternative.me/fng/?limit=1"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("data"):
                entry = data["data"][0]
                self.fear_greed = FearGreedData(
                    value=int(entry["value"]),
                    label=entry["value_classification"],
                    timestamp=float(entry["timestamp"]),
                )
            self.errors.pop("fear_greed", None)
        except Exception as e:
            self.errors["fear_greed"] = str(e)
            logger.warning(f"Fear & Greed fetch error: {e}")

    async def _fetch_forex_commodities(self, client: httpx.AsyncClient):
        """
        Fetch forex rates from exchangerate-api (free tier).
        Also derive some commodity/index proxies.
        """
        try:
            # Free forex rates (USD base)
            url = "https://open.er-api.com/v6/latest/USD"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            rates = data.get("rates", {})

            forex_pairs = {
                "EUR": "Euro",
                "GBP": "British Pound",
                "JPY": "Japanese Yen",
                "CNY": "Chinese Yuan",
                "INR": "Indian Rupee",
                "CHF": "Swiss Franc",
                "AUD": "Australian Dollar",
                "CAD": "Canadian Dollar",
                "RUB": "Russian Ruble",
                "BRL": "Brazilian Real",
                "KRW": "South Korean Won",
                "TRY": "Turkish Lira",
                "AED": "UAE Dirham",
                "SAR": "Saudi Riyal",
                "SGD": "Singapore Dollar",
            }
            for code, name in forex_pairs.items():
                if code in rates:
                    self.tickers[f"forex:USD{code}"] = MarketTicker(
                        symbol=f"USD/{code}",
                        name=name,
                        price=round(rates[code], 4),
                        change_24h=None,
                        change_pct_24h=None,
                        market_cap=None,
                        volume_24h=None,
                        category="forex",
                        updated_at=time.time(),
                    )
            self.errors.pop("forex", None)
        except Exception as e:
            self.errors["forex"] = str(e)
            logger.warning(f"Forex fetch error: {e}")

    def get_tickers(self, category: Optional[str] = None) -> list[dict]:
        """Return tickers, optionally filtered by category."""
        items = list(self.tickers.values())
        if category:
            items = [t for t in items if t.category == category]
        items.sort(key=lambda x: (x.category, -(x.market_cap or 0)))
        return [t.to_dict() for t in items]

    def get_stats(self) -> dict:
        categories = {}
        for t in self.tickers.values():
            categories[t.category] = categories.get(t.category, 0) + 1
        return {
            "total_tickers": len(self.tickers),
            "last_fetch": self.last_fetch,
            "categories": categories,
            "fear_greed": self.fear_greed.to_dict() if self.fear_greed else None,
            "errors": self.errors,
        }
