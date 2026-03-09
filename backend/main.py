# main.py

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import os
from typing import Optional

app = FastAPI(title="Zameen Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://b2b-lead-intelligence-platform.vercel.app",
        "https://b2-b-lead-intelligence-platform.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CSVs live at the project root; backend/main.py is one level down
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# ── Data loaders ──────────────────────────────────────────────

def _read(filename: str) -> pd.DataFrame:
    path = os.path.join(ROOT_DIR, filename)
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    # Coerce all numeric-ish columns so downstream math never crashes
    for col in ["price", "area_sqft", "price_per_sqft",
                "bedrooms", "bathrooms", "bed_bath_ratio",
                "total_agent_listings", "lead_score", "cluster"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_today()  -> pd.DataFrame: return _read("zameen_karachi_flats_today.csv")
def load_weekly() -> pd.DataFrame: return _read("zameen_karachi_flats_last_7_days.csv")
def load_scored() -> pd.DataFrame: return _read("zameen_market_segments.csv")


def _safe_records(df: pd.DataFrame) -> list:
    """Convert df to records, replacing NaN/Inf with None for JSON safety."""
    df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
    return df.to_dict(orient="records")


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "root_dir": ROOT_DIR,
        "scored_exists": os.path.exists(os.path.join(ROOT_DIR, "zameen_market_segments.csv")),
        "today_exists":  os.path.exists(os.path.join(ROOT_DIR, "zameen_karachi_flats_today.csv")),
        "weekly_exists": os.path.exists(os.path.join(ROOT_DIR, "zameen_karachi_flats_last_7_days.csv")),
        "files": os.listdir(ROOT_DIR),
    }


@app.get("/api/summary")
def summary():
    df    = load_scored()
    today = load_today()
    if df.empty:
        return {
            "total_leads": 0, "today_leads": 0,
            "avg_lead_score": 0, "avg_price": 0,
            "avg_price_per_sqft": 0, "verified_agencies": 0, "segments": {}
        }

    avg_psf = (
        round(float(df["price_per_sqft"].mean()), 0)
        if "price_per_sqft" in df.columns and not df["price_per_sqft"].isna().all()
        else 0
    )

    return {
        "total_leads":        len(df),
        "today_leads":        len(today),
        "avg_lead_score":     round(float(df["lead_score"].mean()), 1) if "lead_score" in df.columns else 0,
        "avg_price":          int(df["price"].mean())                  if "price"      in df.columns else 0,
        "avg_price_per_sqft": avg_psf,
        "verified_agencies":  int(df["verified_agency"].str.lower().eq("verified").sum())
                              if "verified_agency" in df.columns else 0,
        "segments":           df["market_segment"].value_counts().to_dict()
                              if "market_segment" in df.columns else {},
    }


@app.get("/api/leads")
def leads(
    page:      int            = Query(1,  ge=1),
    limit:     int            = Query(20, ge=1, le=100),
    segment:   Optional[str]  = None,
    min_score: Optional[float]= None,
    location:  Optional[str]  = None,
    sort_by:   str            = Query(
        "lead_score",
        enum=["lead_score", "price", "area_sqft", "price_per_sqft"]
    ),
):
    df = load_scored()
    if df.empty:
        return {"leads": [], "total": 0, "page": page, "pages": 0}

    if segment:
        df = df[df["market_segment"] == segment]
    if min_score is not None and "lead_score" in df.columns:
        df = df[df["lead_score"] >= min_score]
    if location and "location" in df.columns:
        df = df[df["location"].str.contains(location, case=False, na=False)]

    # Sort safely — column must exist and have numeric values
    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=False, na_position="last")

    total = len(df)
    start = (page - 1) * limit
    page_df = df.iloc[start: start + limit]

    return {
        "leads": _safe_records(page_df),
        "total": total,
        "page":  page,
        "pages": max((total + limit - 1) // limit, 1),
    }


@app.get("/api/leads/top")
def top_leads(limit: int = Query(10, ge=1, le=100)):
    df = load_scored()
    if df.empty or "lead_score" not in df.columns:
        return []
    top = df.nlargest(limit, "lead_score")
    return _safe_records(top)


@app.get("/api/trends/weekly")
def weekly_trends():
    df = load_weekly()
    if df.empty:
        return {"days": [], "counts": []}
    df["parsed_date"] = pd.to_datetime(df["posted_date"], errors="coerce")
    df = df.dropna(subset=["parsed_date"])
    if df.empty:
        return {"days": [], "counts": []}
    df["day"] = df["parsed_date"].dt.date.astype(str)
    grouped = df.groupby("day").size().reset_index(name="count").sort_values("day")
    return {"days": grouped["day"].tolist(), "counts": grouped["count"].tolist()}


@app.get("/api/trends/segments")
def segment_stats():
    df = load_scored()
    if df.empty or "market_segment" not in df.columns:
        return []

    agg = (
        df.groupby("market_segment")
        .agg(
            count          =("lead_score",      "count"),
            avg_score      =("lead_score",      "mean"),
            avg_price      =("price",           "mean"),
            avg_price_per_sqft=("price_per_sqft", "mean"),
            avg_area_sqft  =("area_sqft",       "mean"),
            avg_bedrooms   =("bedrooms",        "mean"),
            avg_bathrooms  =("bathrooms",       "mean"),
        )
        .reset_index()
    )

    # Round floats for clean JSON
    for col in ["avg_score", "avg_price", "avg_price_per_sqft",
                "avg_area_sqft", "avg_bedrooms", "avg_bathrooms"]:
        if col in agg.columns:
            agg[col] = agg[col].round(2)

    return _safe_records(agg)


@app.get("/api/trends/locations")
def location_stats():
    df = load_scored()
    if df.empty or "location" not in df.columns:
        return []

    grouped = (
        df.groupby("location")
        .agg(count=("lead_score", "count"), avg_score=("lead_score", "mean"))
        .reset_index()
        .sort_values("count", ascending=False)
        .head(20)
    )
    grouped["avg_score"] = grouped["avg_score"].round(1)
    return _safe_records(grouped)