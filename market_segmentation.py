# market_segmentation.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score


# -----------------------------
# Load Data
# -----------------------------
def load_data(filepath):
    return pd.read_csv(filepath)


# -----------------------------
# Select Features
# -----------------------------
def select_features(df):
    feature_cols = [
        "price",
        "area_sqft",
        "bedrooms",
        "bathrooms",
        "price_per_sqft"
    ]

    if "total_agent_listings" in df.columns:
        feature_cols.append("total_agent_listings")

    return df[feature_cols].dropna()


# -----------------------------
# Elbow Method
# -----------------------------
def find_optimal_k(X, max_k=10):
    inertias = []

    for k in range(2, max_k + 1):
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        model.fit(X)
        inertias.append(model.inertia_)

    plt.figure()
    plt.plot(range(2, max_k + 1), inertias, marker="o")
    plt.title("Elbow Method")
    plt.xlabel("Number of Clusters (K)")
    plt.ylabel("Inertia")
    plt.show()


# -----------------------------
# Train KMeans
# -----------------------------
def train_kmeans(X, n_clusters):
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(X)
    return model, labels


# -----------------------------
# Automatic Smart Naming
# -----------------------------
def smart_label_clusters(df):

    # Compute cluster statistics
    summary = df.groupby("cluster").agg({
        "price_per_sqft": "mean",
        "price": "mean",
        "area_sqft": "mean"
    })

    # Sort clusters by price_per_sqft (ascending)
    summary = summary.sort_values("price_per_sqft")

    # Dynamically create segment labels based on number of clusters
    num_clusters = len(summary)

    base_names = [
        "Budget Area",
        "Mid-Value Area",
        "Premium Area",
        "Luxury Area"
    ]

    labels_map = {}

    sorted_clusters = list(summary.index)

    for i, cluster_id in enumerate(sorted_clusters):
        if num_clusters <= 4:
            labels_map[cluster_id] = base_names[i]
        else:
            labels_map[cluster_id] = f"Segment {i+1}"

    # Map labels back to dataframe
    df["market_segment"] = df["cluster"].map(labels_map)

    return df


# -----------------------------
# Main
# -----------------------------
def main():
    print("Loading cleaned dataset...")
    df = load_data("data/processed/zameen_listings_clean.csv")

    print("Selecting features...")
    df_model = select_features(df)

    print("Scaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_model)

    print("Finding optimal K...")
    find_optimal_k(X_scaled)

    # Choose K manually after elbow
    chosen_k = 4

    print(f"Training KMeans with K={chosen_k}...")
    model, labels = train_kmeans(X_scaled, chosen_k)

    silhouette = silhouette_score(X_scaled, labels)
    print("Silhouette Score:", round(silhouette, 4))

    # Add cluster labels
    df_model["cluster"] = labels

    # Add smart market segment names
    df_model = smart_label_clusters(df_model)

    print("\nCluster Summary:")
    print(df_model.groupby("market_segment").mean())

    df_model.to_csv("zameen_market_segments.csv", index=False)
    print("\nClustered dataset saved as 'zameen_market_segments.csv'")


if __name__ == "__main__":
    main()