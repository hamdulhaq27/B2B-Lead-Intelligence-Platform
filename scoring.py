# scoring.py

import pandas as pd
import numpy as np
from datetime import datetime
import re


class LeadScorer:
    def __init__(self, weights=None):
        self.weights = weights or {
            "price":               -0.20,
            "area_sqft":            0.15,
            "price_per_sqft":      -0.15,
            "bedrooms":             0.10,
            "bathrooms":            0.10,
            "bed_bath_ratio":       0.05,
            "verified_agency":      0.10,
            "total_agent_listings": 0.05,
            "recent_posted":        0.10,
        }

    def normalize(self, series):
        """Min-max normalize; returns 0.5 for constant or all-NaN series."""
        s = pd.to_numeric(series, errors="coerce")
        mn, mx = s.min(), s.max()
        if pd.isna(mn) or pd.isna(mx) or mx == mn:
            return pd.Series(0.5, index=series.index)
        return (s - mn) / (mx - mn)

    def compute_recency_score(self, posted_date_series):
        """Convert relative date strings to a 0–1 recency score."""
        recency = pd.Series(0.0, index=posted_date_series.index)
        today = datetime.now()
        for i, val in posted_date_series.items():
            try:
                val_str = str(val).lower().strip()
                if any(k in val_str for k in ("minute", "hour", "just now")):
                    days_diff = 0
                elif "yesterday" in val_str:
                    days_diff = 1
                elif "day" in val_str:
                    match = re.search(r"\d+", val_str)
                    days_diff = int(match.group()) if match else 7
                else:
                    dt = pd.to_datetime(val, errors="coerce")
                    days_diff = 365 if pd.isna(dt) else max((today - dt.replace(tzinfo=None)).days, 0)
            except Exception:
                days_diff = 365
            recency[i] = 1 - min(days_diff / 365, 1)
        return recency

    def compute_bed_bath_ratio_score(self, df):
        """Closeness-to-ideal-ratio score (ideal = 1.5)."""
        ratio = pd.to_numeric(df["bed_bath_ratio"], errors="coerce").replace(0, np.nan)
        ideal = 1.5
        score = 1 - (ratio - ideal).abs() / ideal
        return score.clip(0, 1).fillna(0.5)

    def compute_verified_agency_score(self, verified_series):
        return verified_series.astype(str).str.strip().str.lower().eq("verified").astype(float)

    def score_leads(self, df):
        df = df.copy()

        # Ensure numeric types for all feature columns
        numeric_cols = ["price", "area_sqft", "price_per_sqft",
                        "bedrooms", "bathrooms", "total_agent_listings"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Compute bed_bath_ratio if absent
        if "bed_bath_ratio" not in df.columns:
            if "bedrooms" in df.columns and "bathrooms" in df.columns:
                baths_safe = df["bathrooms"].replace(0, np.nan)
                df["bed_bath_ratio"] = df["bedrooms"] / baths_safe
            else:
                df["bed_bath_ratio"] = 0.5

        score = pd.Series(0.0, index=df.index)

        # Numeric features
        for feat in ["price", "area_sqft", "price_per_sqft",
                     "bedrooms", "bathrooms", "total_agent_listings"]:
            if feat in df.columns:
                w = self.weights.get(feat, 0)
                score += w * self.normalize(df[feat])

        # Recency
        if "posted_date" in df.columns:
            score += self.weights.get("recent_posted", 0) * self.compute_recency_score(df["posted_date"])

        # Verified agency
        if "verified_agency" in df.columns:
            score += self.weights.get("verified_agency", 0) * self.compute_verified_agency_score(df["verified_agency"])

        # Bed/bath ratio
        if "bed_bath_ratio" in df.columns:
            score += self.weights.get("bed_bath_ratio", 0) * self.compute_bed_bath_ratio_score(df)

        # Rescale to 0–100
        df["lead_score"] = (100 * self.normalize(score)).round(1)

        return df


if __name__ == "__main__":
    import sys

    path = "zameen_market_segments.csv"
    if not pd.io.common.file_exists(path):
        print(f"ERROR: {path} not found. Run market_segmentation.py first.")
        sys.exit(1)

    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows.")

    scorer = LeadScorer()
    scored_df = scorer.score_leads(df)
    scored_df.to_csv(path, index=False)

    print(f"Scoring done. {len(scored_df)} leads scored.")
    display_cols = [c for c in ["title", "location", "price", "market_segment", "lead_score"]
                    if c in scored_df.columns]
    print(scored_df[display_cols].sort_values("lead_score", ascending=False).head(10).to_string(index=False))