<div align="center">
  <img src="https://img.shields.io/badge/Status-Active-success.svg" alt="Project Status"/>
  <img src="https://img.shields.io/badge/Python-3.13+-blue.svg" alt="Python Version"/>
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"/>
</div>

# 🌍 World News Map — Trading Intelligence Hub

A powerful algorithmic trading intelligence platform and interactive geopolitical dashboard. The World News Map serves dual purposes:
1. **API Backend**: Real-time aggregation of news feeds, market changes, geopolitical events, and conflict data (via ACLED) synthesized into structured **Trading Signals**.
2. **Interactive Front-End Dashboard**: A dynamic, fully responsive "war room" style web interface featuring live tickers, categorized news streams, financial status cards, and a fullscreen-capable interactive Leaflet event map.

---

## 🚀 Key Features

* **Real-time News Aggregation**: Pulls continuously from 40+ global RSS sources spanning wire services *(AP, Reuters)*, major western media *(BBC, NYT)*, financial platforms *(Bloomberg, FT, MarketWatch)*, and regional networks across Asia, Africa, and Latin America.
* **Geopolitical Signal Intelligence**: Natural Language syntax processing identifies structural trading signals (impact, severity, and market-sector targets) instantly.
* **Interactive Live World Map**: Dynamic Leaflet map converting keywords and conflict locations into precise marker clusters. Features map-toggles, Severity filtering (Medium/High/Critical), source combination, and a dedicated **Fullscreen Mode**.
* **Crypto & Forex Status**: Live price and 24h change integrations covering Top 30 Crypto assets, Fear & Greed indices, and 15 global Forex fiat pairs.
* **ACLED Conflict Data Integration**: Opt-in integration for strict verified military conflict and civilian disruption mapping with exact fatalities metrics.

---

## 🛠 Tech Stack & Architecture

- **Backend Platform:** Python 3.13, FastAPI, Uvicorn (ASGI async runner).
- **Asynchronous Data Handling:** `httpx` and `feedparser`.
- **Background Cron Engine:** `apscheduler`.
- **Frontend Environment:** Vanilla ES6 Javascript, HTML5, Modular CSS.
- **Mapping & Visualization:** Leaflet.js with CARTO dark-mode thematic subdomains.

---

## 💻 Quick Start (Local Setup)

The project includes a streamlined local boot configuration. 

### Prerequisites
- Python 3.13+
- Git

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/ksanjeevein-maker/world-news-map.git
   cd world-news-map
   ```
2. Run the startup script (Windows) or install manually:
   ```bash
   # Windows Automatic Setup
   start.bat

   # Manual Setup
   cd backend
   pip install -r requirements.txt
   python main.py
   ```

### Access Points
- **Interactive Dashboard:** [http://localhost:8888/dashboard](http://localhost:8888/dashboard)
- **Interactive Swagger API Docs:** [http://localhost:8888/docs](http://localhost:8888/docs)
- **JSON Signals Output:** [http://localhost:8888/api/signals](http://localhost:8888/api/signals)

*(Note for ACLED Support: To enable live military conflict data, set the `ACLED_API_KEY` and `ACLED_EMAIL` environment variables).*

---

## 📡 API Reference for Trading Bots

Connect algorithm execution bots instantly via standard GET calls:

| Endpoint | Description |
|---|---|
| `GET /api/signals` | Core trading signals (conflict, sanctions, rate decisions, etc.) |
| `GET /api/signals?affects=crypto` | Return signals currently flagged to affect Crypto markers |
| `GET /api/signals?impact=critical` | Critical-impact signals only |
| `GET /api/news/latest` | Clean, chronological JSON feed of latest headlines covering all 40+ sources |
| `GET /api/news/latest?category=markets` | Categorical news filters |
| `GET /api/news/breaking` | Urgent severity filters |
| `GET /api/market/crypto` | Full 30-coin dump and current overarching 'Fear & Greed Index' |
| `GET /api/market/forex` | Current rates across 15+ fiat exchanges |
| `GET /api/conflicts` | Advanced ACLED conflict data queries *(requires environmental setup)* |

---

## ☁️ Deployment

The project is structured to deploy smoothly to **Railway**, **Render**, or any generic **Docker** hosting architecture supporting standard `Uvicorn` deployments. Configurations such as `railway.json`, `render.yaml`, and a standard `Dockerfile` are strictly maintained in the repository root for instantaneous deployment synchronization.

---

## 📜 License

Created under the [MIT License](LICENSE). 
You are free to leverage this intelligence engine, modify its UI, or integrate it commercially without restrictions. 

*Designed and engineered for quantitative advantage.*
