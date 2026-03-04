import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score


def load_data(filepath):
    return pd.read_csv(filepath)


def select_features(df):
    feature_cols = ["price", "area_sqft", "bedrooms", "bathrooms", "price_per_sqft"]
    if "total_agent_listings" in df.columns:
        feature_cols.append("total_agent_listings")
    available = [c for c in feature_cols if c in df.columns]
    return df[available].dropna()


def train_kmeans(X, n_clusters):
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(X)
    return model, labels


def smart_label_clusters(df):
    summary = df.groupby("cluster").agg({
        "price_per_sqft": "mean",
        "price": "mean",
        "area_sqft": "mean"
    }).sort_values("price_per_sqft")

    base_names = ["Budget Area", "Mid-Value Area", "Premium Area", "Luxury Area"]
    num_clusters = len(summary)
    labels_map = {}

    for i, cluster_id in enumerate(summary.index):
        labels_map[cluster_id] = base_names[i] if num_clusters <= 4 else f"Segment {i+1}"

    df["market_segment"] = df["cluster"].map(labels_map)
    return df


def main():
    print("Loading today's cleaned data...")
    # read from root-level today CSV (already preprocessed)
    df = load_data("zameen_karachi_flats_today.csv")

    print(f"Total rows: {len(df)}")

    print("Selecting features...")
    df_model = select_features(df)

    if len(df_model) < 4:
        print("Not enough data to cluster. Saving as-is.")
        df["market_segment"] = "Uncategorized"
        df["lead_score"] = 50
        df.to_csv("zameen_market_segments.csv", index=False)
        return

    print("Scaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_model)

    chosen_k = 4
    print(f"Training KMeans with K={chosen_k}...")
    model, labels = train_kmeans(X_scaled, chosen_k)

    silhouette = silhouette_score(X_scaled, labels)
    print(f"Silhouette Score: {round(silhouette, 4)}")

    df_model = df_model.copy()
    df_model["cluster"] = labels
    df_model = smart_label_clusters(df_model)

    # Merge segment back to original df
    df = df.loc[df_model.index].copy()
    df["market_segment"] = df_model["market_segment"]

    print("\nCluster Summary:")
    print(df.groupby("market_segment")["price"].mean())

    df.to_csv("zameen_market_segments.csv", index=False)
    print("Saved as zameen_market_segments.csv")


if __name__ == "__main__":
    main()