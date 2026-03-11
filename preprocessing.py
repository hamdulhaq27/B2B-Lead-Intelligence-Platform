# preprocessing.py

import pandas as pd
import numpy as np
import re
import sys


# ── Unit conversions ──────────────────────────────────────────
UNIT_TO_SQFT = {
    "sq. yd.": 9,
    "sq. ft.": 1,
    "sq. m.":  10.7639,
    "marla":   272.25,
    "kanal":   5445,
}

def convert_area_to_sqft(area_str):
    """Convert any area string (Sq. Yd., Sq. Ft., Marla, etc.) to sq. ft."""
    if pd.isna(area_str) or str(area_str).strip() == "":
        return np.nan
    s = str(area_str).strip().lower()
    # If already a plain float/int (already converted), return as-is
    try:
        return float(s)
    except ValueError:
        pass
    try:
        num = float(re.findall(r"[\d.]+", s)[0])
    except (IndexError, ValueError):
        return np.nan
    for unit, factor in UNIT_TO_SQFT.items():
        if unit in s:
            return num * factor
    # Bare number with non-numeric chars stripped — assume sq. ft.
    return num


def convert_to_numeric(value):
    """Strip non-numeric characters and return float, or NaN."""
    if pd.isna(value):
        return np.nan
    try:
        cleaned = re.sub(r"[^\d.]", "", str(value))
        return float(cleaned) if cleaned else np.nan
    except (ValueError, TypeError):
        return np.nan


def standardize_location(location):
    if pd.isna(location):
        return np.nan
    location = str(location).strip()
    location = re.sub(r"\s+", " ", location)
    return location


def format_phone_number(phone):
    if pd.isna(phone):
        return np.nan
    phone = str(phone).replace(" ", "").replace("-", "")
    return phone


def remove_duplicates(df, subset_cols=None):
    if subset_cols is None:
        subset_cols = ["property_id"]
    cols = [c for c in subset_cols if c in df.columns]
    if not cols:
        return df
    return df.drop_duplicates(subset=cols, keep="first")


def safe_mode(series):
    """Return the most common non-null value, or 0 as fallback."""
    try:
        counts = series.dropna().value_counts()
        if len(counts) == 0:
            return 0
        return counts.index[0]
    except Exception:
        return 0


def fill_missing_values(df):
    # Numeric columns — fill with median
    for col in ["price", "area_sqft", "price_per_sqft"]:
        if col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce")
            median_val = series.median()
            if pd.isna(median_val):
                median_val = 0
            df[col] = series.fillna(median_val)

    # Discrete numeric columns — fill with mode
    for col in ["bedrooms", "bathrooms", "total_agent_listings"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            mode_val = safe_mode(df[col])
            df[col] = df[col].fillna(mode_val)

    return df


def create_features(df):
    """Compute derived columns: price_per_sqft and bed_bath_ratio."""
    if "price" in df.columns and "area_sqft" in df.columns:
        area_safe = pd.to_numeric(df["area_sqft"], errors="coerce").replace(0, np.nan)
        price_num = pd.to_numeric(df["price"], errors="coerce")
        df["price_per_sqft"] = (price_num / area_safe).replace([np.inf, -np.inf], np.nan)

    if "bedrooms" in df.columns and "bathrooms" in df.columns:
        baths_safe = pd.to_numeric(df["bathrooms"], errors="coerce").replace(0, np.nan)
        beds_num   = pd.to_numeric(df["bedrooms"],  errors="coerce")
        df["bed_bath_ratio"] = (beds_num / baths_safe).replace([np.inf, -np.inf], np.nan)

    return df


def preprocess_listings(df):
    df = df.copy()

    # ── 1. Convert area to sq. ft. ────────────────────────────
    # Handles both raw strings ("106 Sq. Yd.") and already-numeric values
    if "area_sqft" in df.columns:
        df["area_sqft"] = df["area_sqft"].apply(convert_area_to_sqft)
    elif "area" in df.columns:
        df["area_sqft"] = df["area"].apply(convert_area_to_sqft)
    else:
        df["area_sqft"] = np.nan

    # ── 2. Coerce numeric columns ─────────────────────────────
    for col in ["price", "bedrooms", "bathrooms"]:
        if col in df.columns:
            df[col] = df[col].apply(convert_to_numeric)
    if "total_agent_listings" in df.columns:
        df["total_agent_listings"] = df["total_agent_listings"].apply(convert_to_numeric)

    # ── 3. Standardize text columns ───────────────────────────
    if "location" in df.columns:
        df["location"] = df["location"].apply(standardize_location)
    if "phone_number" in df.columns:
        df["phone_number"] = df["phone_number"].apply(format_phone_number)

    # ── 4. Deduplicate ────────────────────────────────────────
    df = remove_duplicates(df)

    # ── 5. Fill missing values ────────────────────────────────
    df = fill_missing_values(df)

    # ── 6. Create / refresh derived features ──────────────────
    df = create_features(df)

    return df


if __name__ == "__main__":
    input_path  = "zameen_karachi_flats_today.csv"
    output_path = "zameen_karachi_flats_today.csv"

    try:
        df_raw = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"ERROR: {input_path} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR reading {input_path}: {e}")
        sys.exit(1)

    print(f"Loaded {len(df_raw)} raw rows.")

    if df_raw.empty:
        print("WARNING: Input CSV is empty. Saving empty file and exiting.")
        df_raw.to_csv(output_path, index=False)
        sys.exit(0)

    df_clean = preprocess_listings(df_raw)
    df_clean.to_csv(output_path, index=False)
    print(f"Preprocessing done. {len(df_clean)} listings saved to {output_path}.")

    # Safe describe — only show columns that actually exist
    cols_to_show = [c for c in ["price", "area_sqft", "bedrooms", "bathrooms"] if c in df_clean.columns]
    if cols_to_show:
        print(df_clean[cols_to_show].describe())
