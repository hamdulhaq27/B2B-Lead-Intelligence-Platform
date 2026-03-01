# 🏠 Zameen Intelligence Platform

> **Automated B2B Lead Intelligence for Karachi Real Estate**  
> Scrapes, scores, and segments daily property listings from Zameen.com into a live dashboard.

---

## 🚀 Live Demo

| Service | URL |
|---|---|
| 🖥️ Frontend | [b2-b-lead-intelligence-platform.vercel.app](https://b2-b-lead-intelligence-platform.vercel.app/) |
| ⚙️ Backend API | [b2b-lead-intelligence-platform.onrender.com](https://b2b-lead-intelligence-platform.onrender.com) |
| 📖 API Docs | [b2b-lead-intelligence-platform.onrender.com/docs](https://b2b-lead-intelligence-platform.onrender.com/docs) |

---

## 📌 What It Does

Every morning at **7AM PKT**, the platform automatically:

1. 🕷️ **Scrapes** today's flat listings from Zameen.com Karachi
2. 🧹 **Cleans** and normalizes the raw data
3. 🧠 **Segments** listings into market tiers using KMeans clustering
4. 🏆 **Scores** each lead based on price, area, recency, agency quality
5. 💾 **Commits** fresh CSVs back to the repo
6. 🔄 **Redeploys** the backend with updated data

---

## 🏗️ Architecture

```
GitHub Actions (Cron 2AM UTC / 7AM PKT)
        │
        ├── scraper/automated_scraper.py     → scrapes Zameen.com
        ├── preprocessing.py                 → cleans & normalizes
        ├── market_segmentation.py           → KMeans clustering
        ├── scoring.py                       → lead quality scoring
        │
        ├── commits CSVs → triggers Render deploy hook
        │
        ├── Render (Docker)  ←──→  FastAPI backend
        └── Vercel           ←──→  React frontend (index.html)
```

---

## 🗂️ Project Structure

```
zameen-intelligence/
│
├── .github/
│   └── workflows/
│       ├── daily_scraper.yml        ← nightly automation
│       └── deploy.yml               ← Render deploy trigger
│
├── scraper/
│   ├── automated_scraper.py         ← main daily scraper
│   └── zameen_scraper.py            ← original scraper (archived)
│
├── backend/
│   └── main.py                      ← FastAPI REST API
│
├── frontend/
│   └── index.html                   ← single-file dashboard
│
├── data/
│   ├── raw/
│   │   └── zameen_karachi_flats_full.csv
│   └── processed/
│       └── zameen_listings_clean.csv
│
├── market_segmentation.py
├── preprocessing.py
├── scoring.py
│
├── zameen_karachi_flats_today.csv       ← replaced daily
├── zameen_karachi_flats_last_7_days.csv ← rolling 7-day window
├── zameen_market_segments.csv           ← final scored output
│
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Scraping | Python, Selenium, BeautifulSoup |
| Data Processing | Pandas, NumPy, SciPy |
| ML / Segmentation | Scikit-learn (KMeans) |
| Backend | FastAPI, Uvicorn |
| Frontend | Vanilla JS, HTML/CSS |
| Containerization | Docker |
| CI/CD | GitHub Actions |
| Backend Hosting | Render (free tier) |
| Frontend Hosting | Vercel (free tier) |

---

## 📊 Dashboard Pages

### 🏠 Dashboard
- KPI cards — total leads, today's leads, avg score, avg price, verified agencies
- Weekly lead volume bar chart
- Market segment donut chart
- Top scored leads table

### ⬡ Leads
- Full paginated leads list
- Filter by segment, min score, location
- Sort by score, price, area
- Expandable cards with agent name, phone, email, agency listings count

### ◉ Analytics
- Avg price by market segment
- Avg lead score by segment
- Top 20 locations by lead volume

---

## 🤖 How the Scraper Works

The scraper visits every listing on Zameen.com Karachi and **only keeps listings posted today**:

```
Open Zameen.com page 1
        ↓
For each listing → open detail page
        ↓
Posted today? → No  → skip
Posted today? → Yes → extract data
        ↓
Visit agency profile → get phone, email, total listings
        ↓
Next listing → next page
        ↓
Stop when no more today's listings found
        ↓
Save → today CSV (overwrite) + weekly CSV (rolling)
```

**Each listing collects:** title, price, area, bedrooms, bathrooms, location, agent name, agency name, phone number, email, verified status, total agent listings, posted date.

---

## 🧠 Lead Scoring

Each lead is scored 0–100 based on weighted features:

| Feature | Weight | Logic |
|---|---|---|
| Price | -0.20 | Lower price = better value |
| Area (sqft) | +0.15 | Larger area = better |
| Price per sqft | -0.15 | Lower = better value |
| Bedrooms | +0.10 | More = preferred |
| Bathrooms | +0.10 | More = preferred |
| Recency | +0.10 | Posted today = highest score |
| Verified Agency | +0.10 | Verified badge = trusted |
| Bed/Bath Ratio | +0.05 | Ideal ratio ~1.5 |
| Agent Listings | +0.05 | More listings = established agent |

---

## 🏷️ Market Segments

KMeans clustering (K=4) groups listings into:

| Segment | Color | Description |
|---|---|---|
| 🔵 Budget Area | Blue | Lowest price per sqft |
| 🟢 Mid-Value Area | Green | Mid-range pricing |
| 🟡 Premium Area | Yellow | Above average |
| 🟠 Luxury Area | Orange | Highest price per sqft |

---

## ⚙️ API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/summary` | Dashboard KPIs |
| `GET` | `/api/leads` | Paginated + filtered leads |
| `GET` | `/api/leads/top` | Top scored leads |
| `GET` | `/api/trends/weekly` | 7-day trend data |
| `GET` | `/api/trends/segments` | Segment statistics |
| `GET` | `/api/trends/locations` | Top locations by volume |

---

## 🔐 GitHub Secrets Required

| Secret | Description |
|---|---|
| `RENDER_DEPLOY_HOOK` | Render webhook URL to trigger redeploy |

---

## 🚦 CI/CD Pipeline

### `daily_scraper.yml` — Runs every night at 2AM UTC (7AM PKT)
```
Install Chrome → Install dependencies
→ Run scraper → preprocessing → segmentation → scoring
→ git commit fresh CSVs back to main
→ triggers deploy.yml
```

### `deploy.yml` — Triggers on CSV or backend changes
```
curl POST to Render deploy hook
→ Render pulls latest main
→ Rebuilds Docker image with fresh data
→ Live in ~2 minutes
```

---

## 🧪 Testing

**Check backend is live:**
```bash
curl https://YOUR-RENDER-URL.onrender.com/health
```

**Check data is loading:**
```bash
curl https://YOUR-RENDER-URL.onrender.com/api/summary
```

**Manually trigger a scrape:**
```
GitHub → Actions → Daily Scrape & Process → Run workflow
```

---

## 💻 Local Development

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/zameen-intelligence.git
cd zameen-intelligence

# Install dependencies
pip install -r requirements.txt

# Run backend
uvicorn backend.main:app --reload --port 8000

# Open frontend
open frontend/index.html
```

> ⚠️ Make sure `SINGLE_LISTING_MODE = False` in `scraper/automated_scraper.py` before running the full scrape in production.

---

## 📅 Data Flow Summary

```
Every night at 7AM PKT
        ↓
Scraper runs → today's listings collected
        ↓
Preprocessing → cleaned & normalized
        ↓
Segmentation → Budget / Mid-Value / Premium / Luxury
        ↓
Scoring → each lead gets 0-100 score
        ↓
zameen_market_segments.csv committed to repo
        ↓
Render redeploys with fresh data
        ↓
Dashboard updated by morning ✅
```

---

## 📄 License

MIT License — free to use and modify.

---

<div align="center">
  Built for Karachi Real Estate Intelligence 🏙️
</div>
