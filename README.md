# World News Map — Trading Intelligence Hub

Real-time news aggregation + market data API for trading bots, with a web dashboard.

## Quick Start (Local)

```bash
# Double-click start.bat, or:
cd backend
pip install -r requirements.txt
python main.py
```

- **Dashboard:** http://localhost:8888/dashboard
- **API docs:** http://localhost:8888/docs
- **Health check:** http://localhost:8888/api/health

## Bot API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/signals` | Trading signals (conflict, sanctions, rate decisions, etc.) |
| `GET /api/signals?affects=crypto` | Signals affecting crypto only |
| `GET /api/signals?impact=critical` | Only critical-impact signals |
| `GET /api/news/latest` | Latest headlines from 36+ sources |
| `GET /api/news/latest?category=markets` | Filter by category |
| `GET /api/news/breaking` | Breaking + elevated severity only |
| `GET /api/market/crypto` | Top 30 crypto + Fear & Greed Index |
| `GET /api/market/forex` | 15 USD forex pairs |
| `GET /api/stats` | System statistics |

## Deploy to Cloud (for 24/7 bot access)

### Option 1: Railway (Recommended)
1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app)
3. New Project → Deploy from GitHub repo
4. Railway auto-detects `railway.json` and deploys
5. Your bot endpoint becomes: `https://your-app.up.railway.app/api/signals`

### Option 2: Render
1. Push to GitHub
2. Go to [render.com](https://render.com)
3. New Web Service → Connect your repo
4. Render auto-detects `render.yaml` and deploys (free tier available)

### Option 3: Docker (any VPS)
```bash
docker build -t world-news-map .
docker run -d -p 8888:8888 --name wnm world-news-map
```

## Data Sources
- **News RSS (36 feeds):** Reuters, AP, BBC, NYT, Guardian, WaPo, Bloomberg, CNBC, FT, Al Jazeera, SCMP, TASS, Xinhua, Defense News, Hacker News, and more
- **Crypto:** CoinGecko (top 30), Fear & Greed Index
- **Forex:** Open Exchange Rates (15 USD pairs)

## Architecture
```
Backend (FastAPI)         Frontend (Dashboard)
┌─────────────────┐      ┌──────────────────┐
│ RSS Aggregator   │      │ News Feed Panel  │
│ Market Fetcher   │──────│ Signal Panel     │
│ Signal Engine    │ API  │ Crypto Panel     │
│ Scheduler (3min) │      │ Forex Panel      │
└─────────────────┘      └──────────────────┘
         │
    Your Trading Bots
    (GET /api/signals)
```
