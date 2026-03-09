# market_segmentation.py

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score


def load_data(filepath):
    return pd.read_csv(filepath)


def ensure_numeric(df, cols):
    """Coerce columns to numeric in place, returning the df."""
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def select_features(df):
    """Return a clean numeric-only DataFrame for clustering."""
    feature_cols = ["price", "area_sqft", "bedrooms", "bathrooms", "price_per_sqft"]
    if "total_agent_listings" in df.columns:
        feature_cols.append("total_agent_listings")

    available = [c for c in feature_cols if c in df.columns]
    df_feat = df[available].copy()

    # Coerce every feature column to numeric (guards against leftover strings)
    for col in available:
        df_feat[col] = pd.to_numeric(df_feat[col], errors="coerce")

    return df_feat.dropna()


def train_kmeans(X, n_clusters):
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(X)
    return model, labels


def smart_label_clusters(df_with_cluster):
    """Assign human-readable segment names ordered by avg price_per_sqft."""
    summary = df_with_cluster.groupby("cluster").agg(
        price_per_sqft=("price_per_sqft", "mean"),
        price=("price", "mean"),
        area_sqft=("area_sqft", "mean"),
    ).sort_values("price_per_sqft")

    base_names = ["Budget Area", "Mid-Value Area", "Premium Area", "Luxury Area"]
    num_clusters = len(summary)
    labels_map = {
        cluster_id: (base_names[i] if num_clusters <= 4 else f"Segment {i+1}")
        for i, cluster_id in enumerate(summary.index)
    }

    df_with_cluster = df_with_cluster.copy()
    df_with_cluster["market_segment"] = df_with_cluster["cluster"].map(labels_map)
    return df_with_cluster


def main():
    print("Loading today's cleaned data...")
    df = load_data("zameen_karachi_flats_today.csv")
    print(f"Total rows: {len(df)}")

    # Ensure all feature columns are numeric before clustering
    numeric_cols = ["price", "area_sqft", "bedrooms", "bathrooms",
                    "price_per_sqft", "total_agent_listings"]
    df = ensure_numeric(df, numeric_cols)

    # Recompute price_per_sqft if missing or all-NaN (e.g. fresh preprocessed CSV)
    if "price_per_sqft" not in df.columns or df["price_per_sqft"].isna().all():
        area_safe = df["area_sqft"].replace(0, np.nan)
        df["price_per_sqft"] = df["price"] / area_safe

    print("Selecting features...")
    df_model = select_features(df)

    if len(df_model) < 4:
        print("Not enough data to cluster. Saving as-is.")
        df["market_segment"] = "Uncategorized"
        df["cluster"] = 0
        df.to_csv("zameen_market_segments.csv", index=False)
        return

    print("Scaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_model)

    chosen_k = min(4, len(df_model))
    print(f"Training KMeans with K={chosen_k}...")
    model, labels = train_kmeans(X_scaled, chosen_k)

    if chosen_k > 1:
        silhouette = silhouette_score(X_scaled, labels)
        print(f"Silhouette Score: {round(silhouette, 4)}")

    df_model = df_model.copy()
    df_model["cluster"] = labels
    df_model = smart_label_clusters(df_model)

    # Safe merge: align on index, only rows that survived dropna in select_features
    df = df.loc[df_model.index].copy()
    df["cluster"]        = df_model["cluster"].values
    df["market_segment"] = df_model["market_segment"].values

    print("\nCluster Summary:")
    print(df.groupby("market_segment")["price"].agg(["count", "mean"]))

    df.to_csv("zameen_market_segments.csv", index=False)
    print(f"\nSaved {len(df)} rows to zameen_market_segments.csv")


if __name__ == "__main__":
    main()