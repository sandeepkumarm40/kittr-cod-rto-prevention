"""
Exploratory Data Analysis Script
Run: python analysis/eda.py
Produces findings used in the business memo.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

CSV_PATH = "data/orders_sample.csv"

def run_eda():
    df = pd.read_csv(CSV_PATH, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    for col in ["order_value", "num_items", "customer_prior_orders", "customer_prior_rto"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["final_status"] = df["final_status"].str.strip().str.upper()
    df["is_rto"] = (df["final_status"] == "RTO").astype(int)
    df["order_datetime"] = pd.to_datetime(df["order_datetime"], errors="coerce")
    df["hour"] = df["order_datetime"].dt.hour
    df["pincode"] = df["pincode"].fillna("").str.strip()
    df["phone"] = df["phone"].fillna("").str.strip()
    df["address"] = df["address"].fillna("").str.strip()
    df["customer_name"] = df["customer_name"].fillna("").str.strip()

    print("=" * 60)
    print("KITTR D2C — EDA FINDINGS")
    print("=" * 60)

    # Basic stats
    total = len(df)
    rto_count = df["is_rto"].sum()
    rto_rate = rto_count / total
    print(f"\n📊 BASIC STATS")
    print(f"   Total orders: {total}")
    print(f"   RTOs: {rto_count} ({rto_rate:.1%})")
    print(f"   Delivered: {total - rto_count} ({1-rto_rate:.1%})")
    print(f"   Avg order value: ₹{df['order_value'].mean():.0f}")
    print(f"   Median order value: ₹{df['order_value'].median():.0f}")

    # Finding 1: Data Quality Issues
    print(f"\n🚨 FINDING 1 — DATA QUALITY ISSUES")
    placeholder_addrs = ["xyz", ".", "call me", "near station", "home"]
    bad_addr = df[df["address"].str.lower().isin(placeholder_addrs)]
    print(f"   Placeholder addresses: {len(bad_addr)} orders ({len(bad_addr)/total:.1%})")
    print(f"   RTO rate in bad-address orders: {bad_addr['is_rto'].mean():.1%}")
    print(f"   RTO rate in normal orders: {df[~df['address'].str.lower().isin(placeholder_addrs)]['is_rto'].mean():.1%}")

    # Test orders
    test_orders = df[df["customer_name"].str.lower().str.contains("test", na=False)]
    print(f"   Test orders: {len(test_orders)}")
    print(f"   Test order RTO rate: {test_orders['is_rto'].mean():.1%}" if len(test_orders) > 0 else "   No test orders")

    # Missing pincodes
    missing_pin = df[df["pincode"] == ""]
    print(f"   Missing pincodes: {len(missing_pin)}")

    # Zero-value orders
    zero_val = df[df["order_value"] == 0]
    print(f"   Zero-value orders: {len(zero_val)} (RTO: {zero_val['is_rto'].mean():.1%})" if len(zero_val) > 0 else "   No zero-value orders")

    # Duplicate phones
    phone_counts = df["phone"].value_counts()
    dup_phones = phone_counts[phone_counts > 1]
    print(f"   Duplicate phone numbers: {len(dup_phones)}")

    # Finding 2: Prior RTO history
    print(f"\n🚨 FINDING 2 — PRIOR RTO HISTORY IS THE STRONGEST PREDICTOR")
    no_prior_rto = df[df["customer_prior_rto"] == 0]["is_rto"].mean()
    one_prior_rto = df[df["customer_prior_rto"] == 1]["is_rto"].mean()
    two_plus_rto = df[df["customer_prior_rto"] >= 2]["is_rto"].mean()
    print(f"   0 prior RTOs → {no_prior_rto:.1%} RTO rate ({len(df[df['customer_prior_rto']==0])} orders)")
    print(f"   1 prior RTO → {one_prior_rto:.1%} RTO rate ({len(df[df['customer_prior_rto']==1])} orders)")
    print(f"   2+ prior RTOs → {two_plus_rto:.1%} RTO rate ({len(df[df['customer_prior_rto']>=2])} orders)")

    # Finding 3: UTM Source RTO rates
    print(f"\n🚨 FINDING 3 — UTM SOURCE DRIVES RTO RATES")
    utm_stats = df.groupby("utm_source").agg(
        count=("is_rto", "count"),
        rto_rate=("is_rto", "mean")
    ).sort_values("rto_rate", ascending=False)
    print(utm_stats.to_string())

    # Finding 4: Time of day
    print(f"\n🚨 FINDING 4 — LATE NIGHT ORDERS HAVE HIGHER RTO")
    df["hour_bucket"] = pd.cut(df["hour"], bins=[0,5,8,12,18,22,24], 
                                labels=["00-05","05-08","08-12","12-18","18-22","22-24"],
                                right=False)
    hour_stats = df.groupby("hour_bucket", observed=True).agg(
        count=("is_rto","count"), rto_rate=("is_rto","mean")
    )
    print(hour_stats.to_string())

    # Finding 5: Pincode-level risk
    print(f"\n🚨 FINDING 5 — PINCODE CONCENTRATION OF RTOs")
    pin_stats = df.groupby("pincode").agg(
        count=("is_rto","count"), rto_rate=("is_rto","mean")
    )
    pin_stats = pin_stats[pin_stats["count"] >= 5].sort_values("rto_rate", ascending=False)
    high_risk_pins = pin_stats[pin_stats["rto_rate"] >= 0.45]
    print(f"   High-risk pincodes (≥45% RTO, min 5 orders): {len(high_risk_pins)}")
    print(f"   Top 5:")
    print(high_risk_pins.head(5).to_string())

    # Finding 6: Order value
    print(f"\n🚨 FINDING 6 — ORDER VALUE vs RTO")
    df["value_bucket"] = pd.cut(df["order_value"], bins=[0,300,500,800,1200,2000,5000],
                                 labels=["<300","300-500","500-800","800-1200","1200-2000","2000+"])
    val_stats = df.groupby("value_bucket", observed=True).agg(
        count=("is_rto","count"), rto_rate=("is_rto","mean")
    )
    print(val_stats.to_string())

    # Finding 7: Courier RTO rates
    print(f"\n🚨 FINDING 7 — COURIER PERFORMANCE")
    courier_stats = df.groupby("courier").agg(
        count=("is_rto","count"), rto_rate=("is_rto","mean")
    ).sort_values("rto_rate", ascending=False)
    print(courier_stats.to_string())

    # Finding 8: City-level
    print(f"\n🚨 FINDING 8 — CITY RTO RATES (top 15 cities by volume)")
    city_stats = df.groupby("city").agg(
        count=("is_rto","count"), rto_rate=("is_rto","mean")
    ).sort_values("count", ascending=False).head(15)
    print(city_stats.to_string())

    # Cost model
    print(f"\n💰 COST MODEL")
    rto_cost = 65 + 65 + 25 + 0.08 * 180
    print(f"   Cost per RTO: ₹{rto_cost:.0f}")
    total_rto_loss = rto_count * rto_cost
    print(f"   Estimated total RTO loss in this dataset: ₹{total_rto_loss:,.0f}")
    print(f"   If we catch 50% of RTOs via hold: ₹{total_rto_loss * 0.5:,.0f} saved")

    print("\n" + "=" * 60)
    print("EDA COMPLETE")
    print("=" * 60)

    return df

if __name__ == "__main__":
    run_eda()
