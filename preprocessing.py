# preprocessing.py

import pandas as pd
import numpy as np
import re
from scipy.stats import mode

# Converting square yards area to square feet
def convert_area_to_sqft(area_str):
    if pd.isna(area_str):
        return np.nan
    try:
        num = float(re.findall(r"[\d.]+", str(area_str))[0])
        return num * 9 
    except:
        return np.nan

# numeric feature conversion
def convert_to_numeric(value):
    if pd.isna(value):
        return np.nan
    try:
        return float(re.sub(r'[^\d.]', '', str(value)))
    except:
        return np.nan

# normalizing location text
def standardize_location(location):
    if pd.isna(location):
        return np.nan
    location = str(location).strip().lower()
    location = re.sub(r"\s+", " ", location)
    return location

# phone number standardization
def format_phone_number(phone):
    if pd.isna(phone):
        return np.nan
    phone = str(phone).replace(" ", "").replace("-", "")
    return phone

def remove_duplicates(df, subset_cols=["property_id"]):
    return df.drop_duplicates(subset=subset_cols, keep='first')

# feature creation
def create_features(df):
    if "price" in df.columns and "area_sqft" in df.columns:
        df.loc[:, "price_per_sqft"] = df["price"] / df["area_sqft"].replace(0, np.nan)
    if "bedrooms" in df.columns and "bathrooms" in df.columns:
        df.loc[:, "bed_bath_ratio"] = df["bedrooms"] / df["bathrooms"].replace(0, np.nan)
    return df


def fill_missing_values(df):
    
    # Continuous
    for col in ["price", "area_sqft"]:
        if col in df.columns:
            df.loc[:, col] = df[col].fillna(df[col].median())

    # Discrete/categorical
    for col in ["bedrooms", "bathrooms", "total_agent_listings"]:
        if col in df.columns:
            try:
                m = mode(df[col], nan_policy='omit')
                # handle both array and scalar outputs
                if hasattr(m.mode, "__len__"):
                    mode_val = m.mode[0] if len(m.mode) > 0 else 0
                else:
                    mode_val = float(m.mode)
            except:
                mode_val = 0
            df.loc[:, col] = df[col].fillna(mode_val)
    
    return df


def preprocess_listings(df):
    df = df.copy()
    df["area_sqft"] = df["area"].apply(convert_area_to_sqft)
    df["price"] = df["price"].apply(convert_to_numeric)
    df["bedrooms"] = df["bedrooms"].apply(convert_to_numeric)
    df["bathrooms"] = df["bathrooms"].apply(convert_to_numeric)
    df["location"] = df["location"].apply(standardize_location)
    if "phone_number" in df.columns:
        df["phone_number"] = df["phone_number"].apply(format_phone_number)
    
    df = remove_duplicates(df)
    df = fill_missing_values(df)
    df = create_features(df)
    
    return df

if __name__ == "__main__":
    df_raw = pd.read_csv("data/raw/zameen_karachi_flats_full.csv")
    df_clean = preprocess_listings(df_raw)
    df_clean.to_csv("data/processed/zameen_listings_clean.csv", index=False)
    print("Preprocessing completed! Clean dataset saved as 'zameen_listings_clean.csv'")
