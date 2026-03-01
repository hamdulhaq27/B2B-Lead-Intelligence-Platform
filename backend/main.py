from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
import os
from typing import Optional

app = FastAPI(title="Zameen Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def load_today():
    path = os.path.join(DATA_DIR, "zameen_karachi_flats_today.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

def load_weekly():
    path = os.path.join(DATA_DIR, "zameen_karachi_flats_last_7_days.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

def load_scored():
    path = os.path.join(DATA_DIR, "zameen_market_segments.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()


@app.get("/api/summary")
def summary():
    df = load_scored()
    today = load_today()
    if df.empty:
        return {}
    return {
        "total_leads": len(df),
        "today_leads": len(today),
        "avg_lead_score": round(df["lead_score"].mean(), 1) if "lead_score" in df else 0,
        "avg_price": int(df["price"].mean()) if "price" in df else 0,
        "verified_agencies": int(df["verified_agency"].str.lower().eq("verified").sum()) if "verified_agency" in df else 0,
        "segments": df["market_segment"].value_counts().to_dict() if "market_segment" in df else {},
    }


@app.get("/api/leads")
def leads(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    segment: Optional[str] = None,
    min_score: Optional[float] = None,
    location: Optional[str] = None,
    sort_by: str = Query("lead_score", enum=["lead_score", "price", "area_sqft"]),
):
    df = load_scored()
    if df.empty:
        return {"leads": [], "total": 0, "page": page, "pages": 0}

    if segment:
        df = df[df["market_segment"] == segment]
    if min_score is not None:
        df = df[df["lead_score"] >= min_score]
    if location:
        df = df[df["location"].str.contains(location, case=False, na=False)]

    df = df.sort_values(sort_by, ascending=False)
    total = len(df)
    start = (page - 1) * limit
    page_df = df.iloc[start: start + limit]

    return {
        "leads": page_df.where(pd.notna(page_df), None).to_dict(orient="records"),
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@app.get("/api/leads/top")
def top_leads(limit: int = 10):
    df = load_scored()
    if df.empty:
        return []
    top = df.nlargest(limit, "lead_score")
    return top.where(pd.notna(top), None).to_dict(orient="records")


@app.get("/api/trends/weekly")
def weekly_trends():
    df = load_weekly()
    if df.empty:
        return {"days": [], "counts": [], "avg_scores": []}
    df["parsed_date"] = pd.to_datetime(df["posted_date"], errors="coerce")
    df = df.dropna(subset=["parsed_date"])
    df["day"] = df["parsed_date"].dt.date.astype(str)
    grouped = df.groupby("day").agg(count=("price", "count")).reset_index()
    return {
        "days": grouped["day"].tolist(),
        "counts": grouped["count"].tolist(),
    }


@app.get("/api/trends/segments")
def segment_stats():
    df = load_scored()
    if df.empty:
        return []
    grouped = df.groupby("market_segment").agg(
        count=("lead_score", "count"),
        avg_score=("lead_score", "mean"),
        avg_price=("price", "mean"),
    ).reset_index()
    return grouped.where(pd.notna(grouped), None).to_dict(orient="records")


@app.get("/api/trends/locations")
def location_stats():
    df = load_scored()
    if df.empty:
        return []
    grouped = df.groupby("location").agg(
        count=("lead_score", "count"),
        avg_score=("lead_score", "mean"),
    ).reset_index().sort_values("count", ascending=False).head(20)
    return grouped.where(pd.notna(grouped), None).to_dict(orient="records")


@app.get("/health")
def health():
    return {"status": "ok"}