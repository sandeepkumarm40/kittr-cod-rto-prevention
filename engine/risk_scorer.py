"""
Risk Scorer — converts engineered features into a 0–100 risk score.
Fully rule-based and transparent. Weights are loaded from config/thresholds.yaml.
No ML model needed at this scale; rules are auditable and adjustable by ops team.
"""
import yaml
import functools
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "thresholds.yaml"


@functools.lru_cache(maxsize=1)
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def score_order(features: dict, llm_scores: dict = None) -> dict:
    """
    Given engineered features (and optional LLM scores), compute a 0-100 risk score.

    Args:
        features: dict from feature_engineering.engineer_features()
        llm_scores: dict with keys 'address_score' (0-10), 'name_score' (0-10), 'reason' (str)
                    If None, rule-based fallbacks are used.

    Returns:
        dict with: score (0-100), component_scores, explanation
    """
    cfg = load_config()
    weights = cfg["feature_weights"]
    components = {}
    reasons = []

    # ------------------------------------------------------------------ #
    # 1. Prior RTO History (weight: 25)
    # ------------------------------------------------------------------ #
    prior_rto_rate = features.get("prior_rto_rate", 0)
    prior_rto_count = features.get("prior_rto_count", 0)

    if prior_rto_count >= 2:
        prior_score = 100
        reasons.append(f"⚠️ {int(prior_rto_count)} prior RTOs on record")
    elif prior_rto_count == 1:
        prior_score = 60
        reasons.append("1 prior RTO on record")
    elif prior_rto_rate > 0.5:
        prior_score = 75
        reasons.append(f"Phone history shows {prior_rto_rate:.0%} RTO rate")
    else:
        prior_score = 0

    components["prior_rto_history"] = prior_score

    # ------------------------------------------------------------------ #
    # 2. Address Quality (weight: 20)
    # ------------------------------------------------------------------ #
    if features.get("address_is_placeholder"):
        addr_score = 100
        reasons.append("🚩 Address is a placeholder (e.g. 'xyz', 'call me')")
    elif llm_scores and llm_scores.get("address_score") is not None:
        llm_addr = llm_scores["address_score"]  # 0-10, lower = worse
        addr_score = int((10 - llm_addr) * 10)  # convert to 0-100 risk
        if llm_addr < 4:
            reasons.append(f"Address quality poor (score {llm_addr}/10): {llm_scores.get('address_reason','')}")
        elif llm_addr < 7:
            reasons.append(f"Address quality moderate (score {llm_addr}/10)")
    else:
        # Fallback: short address = more suspicious
        addr_len = features.get("address_length", 0)
        if addr_len < 10:
            addr_score = 80
            reasons.append("Address is very short or incomplete")
        elif addr_len < 20:
            addr_score = 40
        else:
            addr_score = 10

    components["address_quality"] = addr_score

    # ------------------------------------------------------------------ #
    # 3. Pincode / City RTO Rate (weight: 15)
    # ------------------------------------------------------------------ #
    pincode_rto = features.get("pincode_rto_rate", 0.28)
    pin_score = min(100, int((pincode_rto / 0.55) * 100))
    if features.get("is_high_rto_pincode") or pincode_rto >= 0.45:
        reasons.append(f"📍 High-RTO pincode/city ({pincode_rto:.0%} historical rate)")

    components["pincode_rto_rate"] = pin_score

    # ------------------------------------------------------------------ #
    # 4. Name Quality (weight: 10)
    # ------------------------------------------------------------------ #
    if features.get("name_is_blocklisted"):
        name_score = 100
        reasons.append("🚩 Name is on the blocklist (test/fake name)")
    elif llm_scores and llm_scores.get("name_score") is not None:
        llm_name = llm_scores["name_score"]  # 0-10, lower = worse
        name_score = int((10 - llm_name) * 10)
        if llm_name < 5:
            reasons.append(f"Name appears suspicious: {llm_scores.get('name_reason','')}")
    else:
        name_score = 0

    components["name_quality"] = name_score

    # ------------------------------------------------------------------ #
    # 5. Order Value Risk (weight: 10)
    # ------------------------------------------------------------------ #
    order_val = features.get("order_value", 0)
    if features.get("is_zero_value"):
        val_score = 100
        reasons.append("🚩 Order value is ₹0")
    elif order_val >= 2500:
        val_score = 80
        reasons.append(f"High-value order (₹{order_val:.0f})")
    elif order_val >= 1500:
        val_score = 50
        reasons.append(f"Above-average order value (₹{order_val:.0f})")
    elif order_val >= 1000:
        val_score = 25
    else:
        val_score = 0

    components["order_value_risk"] = val_score

    # ------------------------------------------------------------------ #
    # 6. Phone Validity (weight: 10)
    # ------------------------------------------------------------------ #
    if not features.get("phone_valid", True):
        phone_score = 100
        reasons.append("🚩 Phone number is invalid or a placeholder")
    else:
        phone_score = 0

    components["phone_validity"] = phone_score

    # ------------------------------------------------------------------ #
    # 7. UTM Source Risk (weight: 5)
    # ------------------------------------------------------------------ #
    utm_rto = features.get("utm_rto_rate", 0.28)
    utm_score = min(100, int((utm_rto / 0.40) * 100))
    if utm_rto >= 0.31:
        reasons.append("Acquired via high-RTO campaign channel")
    components["utm_source_risk"] = utm_score

    # ------------------------------------------------------------------ #
    # 8. Time of Day Risk (weight: 5)
    # ------------------------------------------------------------------ #
    time_risk = features.get("time_risk", 0)
    time_score = int(time_risk * 80)
    if time_risk > 0.5:
        reasons.append("Order placed late at night (00:00–05:00)")
    components["time_of_day_risk"] = time_score

    # ------------------------------------------------------------------ #
    # Weighted Final Score
    # ------------------------------------------------------------------ #
    total_weight = sum(weights.values())
    final_score = sum(
        components[key] * weights[key] / total_weight
        for key in components if key in weights
    )
    final_score = round(min(100, max(0, final_score)), 1)

    return {
        "score": final_score,
        "component_scores": components,
        "reasons": reasons,
    }
