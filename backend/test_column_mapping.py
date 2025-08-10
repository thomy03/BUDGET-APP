#!/usr/bin/env python3
"""
Test the column mapping logic to understand the date issue
"""

import pandas as pd
import re
import numpy as np

def norm(s):
    s = str(s).strip().lower()
    s = (s.replace("é","e").replace("è","e").replace("ê","e")
           .replace("à","a").replace("ô","o").replace("ï","i").replace("î","i"))
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s

def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    mapping_src = {
        "dateop":"dateOp","dateval":"dateVal","label":"label","category":"category",
        "categoryparent":"categoryParent","supplierfound":"supplierFound","amount":"amount",
        "comment":"comment","accountnum":"accountNum","accountlabel":"accountLabel","accountbalance":"accountbalance",
        # French column mappings for common CSV formats
        "date":"dateOp","description":"label","montant":"amount","compte":"accountLabel",
        "categorie":"category","libelle":"label","solde":"accountbalance"
    }
    
    cur = {norm(c): c for c in df.columns}
    print(f"Original columns: {df.columns.tolist()}")
    print(f"Normalized mapping: {cur}")
    
    rename = {}
    for k_norm, target in mapping_src.items():
        if k_norm in cur:
            rename[cur[k_norm]] = target
            print(f"  Will rename '{cur[k_norm]}' -> '{target}'")
        else:
            print(f"  Missing mapping for '{k_norm}'")
    
    print(f"Rename mapping: {rename}")
    
    out = df.rename(columns=rename)
    print(f"After rename: {out.columns.tolist()}")
    
    # Check what happens to dateOp
    if 'dateOp' in out.columns:
        print(f"dateOp column found with {out['dateOp'].notna().sum()} non-null values")
        print(f"First 3 dateOp values: {out['dateOp'].head(3).tolist()}")
    else:
        print("❌ dateOp column NOT found after normalization")
        
    return out

# Test with the actual CSV content
print("Testing column normalization with actual CSV:")
print("=" * 50)

# Read the CSV file
df = pd.read_csv('01_happy_path_janvier_2024.csv', dtype=str)
print(f"Read CSV with {len(df)} rows")

# Test normalization
df_normalized = normalize_cols(df)

print("\n" + "=" * 50)
print("EXPECTED COLS CHECK:")
EXPECTED_COLS = ["dateOp","dateVal","label","category","categoryParent",
                 "supplierFound","amount","comment","accountNum","accountLabel","accountbalance"]

for col in EXPECTED_COLS:
    if col in df_normalized.columns:
        non_null = df_normalized[col].notna().sum() if col != 'dateOp' else pd.to_datetime(df_normalized[col], errors='coerce').notna().sum()
        print(f"✅ {col}: {non_null} non-null values")
    else:
        print(f"❌ {col}: missing")

# Test date parsing
print("\n" + "=" * 50)
print("DATE PARSING TEST:")
if 'dateOp' in df_normalized.columns:
    df_normalized["dateOp"] = pd.to_datetime(df_normalized["dateOp"], errors="coerce")
    valid_dates = df_normalized["dateOp"].notna().sum()
    print(f"Valid dates after parsing: {valid_dates}")
    if valid_dates > 0:
        print(f"Date range: {df_normalized['dateOp'].min()} to {df_normalized['dateOp'].max()}")
else:
    print("❌ Cannot test date parsing - dateOp column missing")