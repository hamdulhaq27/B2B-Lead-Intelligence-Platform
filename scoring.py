# scoring.py

import pandas as pd
import numpy as np
from datetime import datetime
import re

class LeadScorer:
    def __init__(self, weights=None):
        self.weights = weights or {
            "price": -0.2,
            "area_sqft": 0.15,
            "price_per_sqft": -0.15,
            "bedrooms": 0.1,
            "bathrooms": 0.1,
            "bed_bath_ratio": 0.05,
            "verified_agency": 0.1,
            "total_agent_listings": 0.05,
            "recent_posted": 0.1,
        }

    def normalize(self, series):
        return (series - series.min()) / (series.max() - series.min() + 1e-9)

    def compute_recency_score(self, posted_date_series):
        recency_score = pd.Series(0, index=posted_date_series.index)
        today = datetime.now()
        for i, val in posted_date_series.items():
            try:
                val_str = str(val).lower()
                if "minute" in val_str or "hour" in val_str:
                    days_diff = 0
                elif "day" in val_str:
                    days_diff = int(re.search(r'\d+', val_str).group())
                elif "yesterday" in val_str:
                    days_diff = 1
                else:
                    dt = pd.to_datetime(val, errors='coerce')
                    days_diff = 365 if pd.isna(dt) else (today - dt).days
            except:
                days_diff = 365
            recency_score[i] = 1 - min(days_diff / 365, 1)
        return recency_score

    def compute_bed_bath_ratio_score(self, df):
        ratio = df["bed_bath_ratio"].replace(0, np.nan)
        ideal_ratio = 1.5
        score = 1 - np.abs(ratio - ideal_ratio) / ideal_ratio
        return score.fillna(0.5)

    def compute_verified_agency_score(self, verified_series):
        return verified_series.str.lower().eq("verified").astype(float)

    def score_leads(self, df):
        if "bed_bath_ratio" not in df.columns:
            df["bed_bath_ratio"] = df["bedrooms"] / df["bathrooms"].replace(0, 1)

        score = pd.Series(0, index=df.index, dtype=float)

        for feat in ["price", "area_sqft", "price_per_sqft", "bedrooms", "bathrooms", "total_agent_listings"]:
            if feat in df.columns:
                score += self.weights.get(feat, 0) * self.normalize(df[feat])

        if "posted_date" in df.columns:
            score += self.weights.get("recent_posted", 0) * self.compute_recency_score(df["posted_date"])
        if "verified_agency" in df.columns:
            score += self.weights.get("verified_agency", 0) * self.compute_verified_agency_score(df["verified_agency"])
        if "bed_bath_ratio" in df.columns:
            score += self.weights.get("bed_bath_ratio", 0) * self.compute_bed_bath_ratio_score(df)

        score = 100 * self.normalize(score)
        df["lead_score"] = score
        return df


if __name__ == "__main__":
    df = pd.read_csv("zameen_market_segments.csv")
    scorer = LeadScorer()
    scored_df = scorer.score_leads(df)
    scored_df.to_csv("zameen_market_segments.csv", index=False)
    print(f"Scoring done. {len(scored_df)} leads scored.")
    # Show whatever columns are available
    display_cols = [c for c in ["title", "location", "price", "lead_score"] if c in scored_df.columns]
    print(scored_df[display_cols].sort_values("lead_score", ascending=False).head(5))