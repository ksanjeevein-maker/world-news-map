"""
ACLED Conflict Data Integration
================================
Fetches real-time armed conflict events from ACLED (Armed Conflict Location & Event Data).
https://acleddata.com/

ACLED tracks: Battles, Explosions/Remote violence, Violence against civilians,
Protests, Riots, Strategic developments — with EXACT lat/lng coordinates.

Requires: ACLED_API_KEY and ACLED_EMAIL env vars.
If not configured, this module gracefully returns empty data.
"""
import asyncio
import os
import time
import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from typing import Optional

import httpx

logger = logging.getLogger("acled")

ACLED_API_URL = "https://api.acleddata.com/acled/read"


@dataclass
class ConflictEvent:
    event_id: str
    event_date: str
    event_type: str         # Battles, Explosions/Remote violence, Violence against civilians, etc.
    sub_event_type: str     # Armed clash, Air/drone strike, Shelling/artillery, etc.
    actor1: str             # Primary actor (e.g. "Military Forces of Russia")
    actor2: str             # Secondary actor
    country: str
    admin1: str             # Region/state
    location: str           # City/town name
    latitude: float
    longitude: float
    fatalities: int
    notes: str              # Description of the event
    source: str             # Source of the report
    severity: str           # "critical", "high", "medium" — computed from type + fatalities

    def to_dict(self):
        return asdict(self)


def _compute_severity(event_type: str, fatalities: int) -> str:
    """Compute severity based on event type and fatality count."""
    if fatalities >= 10:
        return "critical"
    if event_type in ("Battles", "Explosions/Remote violence"):
        return "critical" if fatalities > 0 else "high"
    if event_type == "Violence against civilians":
        return "critical" if fatalities > 0 else "high"
    if event_type in ("Riots", "Protests"):
        return "medium" if fatalities == 0 else "high"
    return "medium"


class ACLEDClient:
    """Fetches conflict event data from ACLED API."""

    def __init__(self):
        self.events: dict[str, ConflictEvent] = {}
        self.last_fetch: float = 0
        self.error: Optional[str] = None
        self.enabled: bool = False
        self._lock = asyncio.Lock()

        # Check for API credentials
        self.api_key = os.environ.get("ACLED_API_KEY", "").strip()
        self.email = os.environ.get("ACLED_EMAIL", "").strip()

        if self.api_key and self.email:
            self.enabled = True
            logger.info("ACLED integration enabled (API key found)")
        else:
            logger.info("ACLED integration disabled — set ACLED_API_KEY and ACLED_EMAIL env vars to enable")

    async def fetch_events(self, days_back: int = 7, limit: int = 500):
        """Fetch recent conflict events from ACLED."""
        if not self.enabled:
            return

        logger.info(f"Fetching ACLED conflict events (last {days_back} days)...")

        # Date range: last N days
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

        params = {
            "key": self.api_key,
            "email": self.email,
            "event_date": f"{start_date}|{end_date}",
            "event_date_where": "BETWEEN",
            "limit": limit,
            # Return most recent events first
            "order": "desc",
            # Only get violent events (skip peaceful protests by default)
            "event_type": "Battles|Explosions/Remote violence|Violence against civilians|Riots",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(ACLED_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            if not data.get("success", True) or "data" not in data:
                self.error = data.get("error", "Unknown API error")
                logger.warning(f"ACLED API error: {self.error}")
                return

            events_raw = data["data"]

            async with self._lock:
                new_count = 0
                for e in events_raw:
                    event_id = str(e.get("event_id_cnty", e.get("data_id", "")))
                    if not event_id:
                        continue

                    try:
                        lat = float(e.get("latitude", 0))
                        lng = float(e.get("longitude", 0))
                    except (ValueError, TypeError):
                        continue

                    if lat == 0 and lng == 0:
                        continue

                    event_type = e.get("event_type", "Unknown")
                    fatalities = int(e.get("fatalities", 0))

                    event = ConflictEvent(
                        event_id=event_id,
                        event_date=e.get("event_date", ""),
                        event_type=event_type,
                        sub_event_type=e.get("sub_event_type", ""),
                        actor1=e.get("actor1", "Unknown"),
                        actor2=e.get("actor2", ""),
                        country=e.get("country", "Unknown"),
                        admin1=e.get("admin1", ""),
                        location=e.get("location", ""),
                        latitude=lat,
                        longitude=lng,
                        fatalities=fatalities,
                        notes=e.get("notes", "")[:500],
                        source=e.get("source", "ACLED"),
                        severity=_compute_severity(event_type, fatalities),
                    )

                    if event_id not in self.events:
                        new_count += 1
                    self.events[event_id] = event

                self.last_fetch = time.time()
                self.error = None

                # Prune events older than 14 days
                cutoff_date = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
                expired = [k for k, v in self.events.items() if v.event_date < cutoff_date]
                for k in expired:
                    del self.events[k]

                logger.info(f"ACLED update: {new_count} new events, {len(self.events)} total, {len(expired)} pruned")

        except Exception as e:
            self.error = str(e)
            logger.warning(f"ACLED fetch error: {e}")

    def get_events(self, event_type: Optional[str] = None,
                   country: Optional[str] = None,
                   severity: Optional[str] = None,
                   limit: int = 200) -> list[dict]:
        """Return conflict events, optionally filtered."""
        items = list(self.events.values())

        if event_type:
            items = [e for e in items if event_type.lower() in e.event_type.lower()]
        if country:
            items = [e for e in items if country.lower() in e.country.lower()]
        if severity:
            items = [e for e in items if e.severity == severity]

        # Sort by date desc, then by fatalities desc
        items.sort(key=lambda x: (x.event_date, x.fatalities), reverse=True)
        return [e.to_dict() for e in items[:limit]]

    def get_stats(self) -> dict:
        items = list(self.events.values())
        by_type = {}
        by_country = {}
        total_fatalities = 0
        for e in items:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
            by_country[e.country] = by_country.get(e.country, 0) + 1
            total_fatalities += e.fatalities

        top_countries = sorted(by_country.items(), key=lambda x: x[1], reverse=True)[:15]

        return {
            "enabled": self.enabled,
            "total_events": len(items),
            "total_fatalities": total_fatalities,
            "last_fetch": self.last_fetch,
            "by_type": by_type,
            "top_countries": dict(top_countries),
            "error": self.error,
        }
