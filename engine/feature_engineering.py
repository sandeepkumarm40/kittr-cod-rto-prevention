"""
Feature Engineering for COD RTO Risk Engine
Converts raw order data into risk features for scoring.
"""
import pandas as pd
import numpy as np
import re
import yaml
import functools
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "thresholds.yaml"


@functools.lru_cache(maxsize=1)
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_and_clean(csv_path: str) -> pd.DataFrame:
    """Load CSV and apply basic cleaning."""
    df = pd.read_csv(csv_path, dtype=str)

    # Normalise column names
    df.columns = df.columns.str.strip().str.lower()

    # Numeric conversions
    for col in ["order_value", "num_items", "customer_prior_orders", "customer_prior_rto"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Normalise final_status
    df["final_status"] = df["final_status"].str.strip().str.upper()
    df["is_rto"] = (df["final_status"] == "RTO").astype(int)

    # Normalise text fields
    for col in ["customer_name", "address", "city", "state", "utm_source", "courier", "payment_method"]:
        df[col] = df[col].fillna("").str.strip()

    df["pincode"] = df["pincode"].fillna("").str.strip()
    df["phone"] = df["phone"].fillna("").str.strip()

    return df


def compute_pincode_rto_rates(df: pd.DataFrame) -> dict:
    """Compute historical RTO rate per pincode (min 5 orders to be reliable)."""
    stats = df.groupby("pincode").agg(
        total=("is_rto", "count"),
        rto=("is_rto", "sum")
    )
    stats = stats[stats["total"] >= 5]
    stats["rto_rate"] = stats["rto"] / stats["total"]
    return stats["rto_rate"].to_dict()


def compute_city_rto_rates(df: pd.DataFrame) -> dict:
    """Compute historical RTO rate per city."""
    stats = df.groupby("city").agg(
        total=("is_rto", "count"),
        rto=("is_rto", "sum")
    )
    stats = stats[stats["total"] >= 5]
    stats["rto_rate"] = stats["rto"] / stats["total"]
    return stats["rto_rate"].to_dict()


def compute_utm_rto_rates(df: pd.DataFrame) -> dict:
    """Compute historical RTO rate per UTM source."""
    stats = df.groupby("utm_source").agg(
        total=("is_rto", "count"),
        rto=("is_rto", "sum")
    )
    stats["rto_rate"] = stats["rto"] / stats["total"]
    return stats["rto_rate"].to_dict()


def compute_phone_rto_history(df: pd.DataFrame) -> dict:
    """Map phone → historical RTO rate for repeat customers."""
    stats = df.groupby("phone").agg(
        total=("is_rto", "count"),
        rto=("is_rto", "sum")
    )
    stats = stats[stats["total"] >= 2]  # need at least 2 orders
    stats["rto_rate"] = stats["rto"] / stats["total"]
    return stats["rto_rate"].to_dict()


def is_valid_phone(phone: str) -> bool:
    """Return False if phone is invalid/placeholder."""
    cfg = load_config()
    phone_clean = re.sub(r"[\s\+\-\(\)]", "", str(phone))
    # Remove country code prefix
    if phone_clean.startswith("91") and len(phone_clean) == 12:
        phone_clean = phone_clean[2:]
    if len(phone_clean) != cfg["valid_phone_digits"]:
        return False
    if phone_clean in cfg.get("placeholder_phones", []):
        return False
    if not phone_clean.isdigit():
        return False
    return True


def is_placeholder_address(address: str) -> bool:
    """Instant flag for known-bad addresses (no LLM needed)."""
    cfg = load_config()
    addr_lower = address.strip().lower()
    return addr_lower in [p.lower() for p in cfg.get("placeholder_addresses", [])]


def is_blocklisted_name(name: str) -> bool:
    """Check if customer name is in the blocklist."""
    cfg = load_config()
    return name.strip().lower() in [n.lower() for n in cfg.get("name_blocklist", [])]


def get_time_risk(order_datetime: str) -> float:
    """Late night orders (00:00–05:00) get a small risk bump."""
    try:
        dt = pd.to_datetime(order_datetime)
        hour = dt.hour
        if 0 <= hour < 5:
            return 1.0   # higher risk
        elif 5 <= hour < 8:
            return 0.5
        else:
            return 0.0
    except Exception:
        return 0.0


def engineer_features(order: dict, pincode_rto: dict, city_rto: dict,
                      utm_rto: dict, phone_rto: dict) -> dict:
    """
    Compute all rule-based features for a single order dict.
    Returns feature dict ready for risk scoring.
    """
    cfg = load_config()

    pincode = str(order.get("pincode", "")).strip()
    city = str(order.get("city", "")).strip()
    utm = str(order.get("utm_source", "")).strip()
    phone = str(order.get("phone", "")).strip()
    address = str(order.get("address", "")).strip()
    name = str(order.get("customer_name", "")).strip()
    order_value = float(order.get("order_value", 0) or 0)
    prior_rto = float(order.get("customer_prior_rto", 0) or 0)
    prior_orders = float(order.get("customer_prior_orders", 0) or 0)
    order_datetime = str(order.get("order_datetime", ""))

    features = {}

    # 1. Prior RTO history (strongest signal)
    if prior_rto > 0 and prior_orders > 0:
        features["prior_rto_rate"] = prior_rto / prior_orders
    elif phone in phone_rto:
        features["prior_rto_rate"] = phone_rto[phone]
    else:
        features["prior_rto_rate"] = 0.0
    features["prior_rto_count"] = int(prior_rto)

    # 2. Pincode risk
    features["pincode_rto_rate"] = pincode_rto.get(pincode, city_rto.get(city, 0.28))
    # 0.28 = dataset baseline if no pincode/city history

    # 3. UTM source risk
    features["utm_rto_rate"] = utm_rto.get(utm, 0.28)

    # 4. Phone validity
    features["phone_valid"] = is_valid_phone(phone)
    features["phone_has_history"] = phone in phone_rto

    # 5. Address quality (rule-based flag; LLM score added later)
    features["address_is_placeholder"] = is_placeholder_address(address)
    features["address_length"] = len(address)

    # 6. Name quality (rule-based; LLM score added later)
    features["name_is_blocklisted"] = is_blocklisted_name(name)

    # 7. Order value risk
    features["order_value"] = order_value
    features["is_zero_value"] = (order_value == 0)
    features["is_suspicious_high_value"] = (
        order_value > cfg["suspicious_high_value"] and prior_orders == 0
    )

    # 8. Time of day
    features["time_risk"] = get_time_risk(order_datetime)

    # 9. High-risk pincode override
    rto_threshold = cfg["high_rto_pincode_threshold_pct"] / 100
    features["is_high_rto_pincode"] = (
        features["pincode_rto_rate"] >= rto_threshold and pincode in pincode_rto
    )

    return features


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build feature matrix for the entire historical dataset (for EDA/backtesting)."""
    pincode_rto = compute_pincode_rto_rates(df)
    city_rto = compute_city_rto_rates(df)
    utm_rto = compute_utm_rto_rates(df)
    phone_rto = compute_phone_rto_history(df)

    rows = []
    for _, row in df.iterrows():
        feat = engineer_features(row.to_dict(), pincode_rto, city_rto, utm_rto, phone_rto)
        feat["order_id"] = row["order_id"]
        feat["is_rto"] = row["is_rto"]
        feat["final_status"] = row["final_status"]
        rows.append(feat)

    return pd.DataFrame(rows)
