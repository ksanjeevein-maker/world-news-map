"""
World News Map — Backend API Server
=====================================
Serves two consumers:
  1. Your trading bots (GET /api/...)
  2. The frontend dashboard (same endpoints)

Runs independently — dashboard can be offline and bots still get data.
Start with: python main.py
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from feeds import FeedAggregator
from markets import MarketAggregator
from signals import SignalEngine
from acled import ACLEDClient

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("server")

# ─── Core Services ───────────────────────────────────────────────────────────
feeds = FeedAggregator()
markets = MarketAggregator()
signals = SignalEngine()
acled = ACLEDClient()
scheduler = AsyncIOScheduler()


async def refresh_feeds():
    """Scheduled task: fetch RSS feeds and generate signals."""
    await feeds.fetch_all()
    news_items = feeds.get_items(limit=5000)
    signals.process_news(news_items)


async def refresh_markets():
    """Scheduled task: fetch market data."""
    await markets.fetch_all()


async def refresh_acled():
    """Scheduled task: fetch ACLED conflict events."""
    await acled.fetch_events(days_back=7, limit=500)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initial fetch + schedule periodic updates."""
    logger.info("=" * 60)
    logger.info("  WORLD NEWS MAP — API Server Starting")
    logger.info("=" * 60)

    # Initial data load
    await asyncio.gather(refresh_feeds(), refresh_markets(), refresh_acled())

    # Schedule periodic refreshes
    scheduler.add_job(refresh_feeds, "interval", minutes=3, id="feeds",
                      max_instances=1, misfire_grace_time=60)
    scheduler.add_job(refresh_markets, "interval", minutes=5, id="markets",
                      max_instances=1, misfire_grace_time=60)
    scheduler.add_job(refresh_acled, "interval", minutes=10, id="acled",
                      max_instances=1, misfire_grace_time=120)
    scheduler.start()
    logger.info("Scheduler started: feeds/3min, markets/5min, ACLED/10min")
    logger.info(f"ACLED conflict tracking: {'ENABLED' if acled.enabled else 'DISABLED (set ACLED_API_KEY and ACLED_EMAIL)'}")
    logger.info("API ready at http://localhost:8888")
    logger.info("Dashboard at http://localhost:8888/dashboard")
    logger.info("=" * 60)

    yield

    scheduler.shutdown()
    logger.info("Server shutdown complete.")


# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="World News Map API",
    description="Trading intelligence API — news aggregation, market data, and trading signals",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── API Endpoints (for your bots) ──────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Health check — bots can ping this to verify the API is up."""
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - app.state.start_time, 1) if hasattr(app.state, "start_time") else 0,
        "feeds_last_fetch": feeds.last_fetch,
        "markets_last_fetch": markets.last_fetch,
        "total_news": len(feeds.items),
        "total_signals": len(signals.signals),
        "total_tickers": len(markets.tickers),
        "total_conflicts": len(acled.events),
        "acled_enabled": acled.enabled,
    }


@app.get("/api/news/latest")
async def get_news(
    category: str = Query(None, description="Filter: breaking, geopolitical, markets, crypto, military, cyber, disaster, energy"),
    region: str = Query(None, description="Filter: global, us, middle-east, asia, russia, china"),
    severity: str = Query(None, description="Filter: normal, elevated, breaking"),
    search: str = Query(None, description="Search in title and summary"),
    limit: int = Query(100, ge=1, le=500),
):
    """Get latest news items. Your bots' primary news endpoint."""
    return feeds.get_items(
        category=category, region=region, severity=severity,
        search=search, limit=limit,
    )


@app.get("/api/news/breaking")
async def get_breaking():
    """Get only breaking/elevated severity news — high-priority alerts for bots."""
    breaking = feeds.get_items(severity="breaking", limit=50)
    elevated = feeds.get_items(severity="elevated", limit=50)
    return {
        "breaking": breaking,
        "elevated": elevated,
        "count": len(breaking) + len(elevated),
    }


@app.get("/api/signals")
async def get_signals(
    impact: str = Query(None, description="Filter: critical, high, medium"),
    type: str = Query(None, description="Filter by signal type, e.g. rate_decision, sanctions, conflict_escalation"),
    affects: str = Query(None, description="Filter by affected asset class: forex, crypto, equities, commodities"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    🔥 PRIMARY BOT ENDPOINT
    Returns trading signals derived from news analysis.
    Each signal has: type, impact level, affected asset classes, source headline.
    """
    return signals.get_signals(
        impact=impact, signal_type=type, affects=affects, limit=limit,
    )


@app.get("/api/market/tickers")
async def get_tickers(
    category: str = Query(None, description="Filter: crypto, forex, commodity, index"),
):
    """Get market tickers (crypto prices, forex rates, etc.)."""
    return markets.get_tickers(category=category)


@app.get("/api/market/crypto")
async def get_crypto():
    """Get top 30 crypto tickers with prices and 24h changes."""
    tickers = markets.get_tickers(category="crypto")
    fear_greed = markets.fear_greed
    return {
        "tickers": tickers,
        "fear_greed": fear_greed.to_dict() if fear_greed else None,
    }


@app.get("/api/market/forex")
async def get_forex():
    """Get forex rates (USD base)."""
    return markets.get_tickers(category="forex")


@app.get("/api/conflicts")
async def get_conflicts(
    event_type: str = Query(None, description="Filter: Battles, Explosions/Remote violence, Violence against civilians, Riots"),
    country: str = Query(None, description="Filter by country name"),
    severity: str = Query(None, description="Filter: critical, high, medium"),
    limit: int = Query(200, ge=1, le=1000),
):
    """
    ACLED conflict events with exact coordinates.
    Each event has: lat/lng, event type, actors, fatalities, description.
    Requires ACLED_API_KEY and ACLED_EMAIL env vars.
    """
    return {
        "enabled": acled.enabled,
        "events": acled.get_events(
            event_type=event_type, country=country,
            severity=severity, limit=limit,
        ),
        "stats": acled.get_stats(),
    }


@app.get("/api/stats")
async def get_stats():
    """System statistics — useful for monitoring."""
    return {
        "feeds": feeds.get_stats(),
        "markets": markets.get_stats(),
        "signals": signals.get_stats(),
        "acled": acled.get_stats(),
        "server_time": time.time(),
    }


# ─── Serve Frontend Dashboard ───────────────────────────────────────────────
import os
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.isdir(FRONTEND_DIR):
    @app.get("/dashboard")
    @app.get("/dashboard/")
    async def serve_dashboard():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ─── Root ────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "World News Map API",
        "version": "1.0.0",
        "endpoints": {
            "news": "/api/news/latest",
            "breaking": "/api/news/breaking",
            "signals": "/api/signals",
            "conflicts": "/api/conflicts",
            "tickers": "/api/market/tickers",
            "crypto": "/api/market/crypto",
            "forex": "/api/market/forex",
            "stats": "/api/stats",
            "health": "/api/health",
            "dashboard": "/dashboard",
        },
        "docs": "/docs",
    }


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8888))
    app.state.start_time = time.time()
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
