"""
Decision Engine — the main entry point.
Takes a new COD order and outputs one of 4 actions with a plain-English reason.
"""
import yaml
import functools
from pathlib import Path
from engine.feature_engineering import (
    engineer_features, compute_pincode_rto_rates, compute_city_rto_rates,
    compute_utm_rto_rates, compute_phone_rto_history, load_and_clean
)
from engine.risk_scorer import score_order
from engine.llm_validator import validate_order_with_llm

CONFIG_PATH = Path(__file__).parent.parent / "config" / "thresholds.yaml"
DATA_PATH = Path(__file__).parent.parent / "data" / "orders_sample.csv"

# Cached lookups (loaded once at startup)
_cache = {}


def _load_lookups():
    if not _cache:
        df = load_and_clean(str(DATA_PATH))
        _cache["pincode_rto"] = compute_pincode_rto_rates(df)
        _cache["city_rto"] = compute_city_rto_rates(df)
        _cache["utm_rto"] = compute_utm_rto_rates(df)
        _cache["phone_rto"] = compute_phone_rto_history(df)
    return _cache


@functools.lru_cache(maxsize=1)
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


ACTIONS = {
    "ship": {
        "code": "SHIP",
        "label": "✅ Ship as-is",
        "description": "Order looks genuine. Ship normally.",
        "color": "green",
    },
    "confirm": {
        "code": "CONFIRM_WHATSAPP",
        "label": "🟡 Ship after WhatsApp confirmation",
        "description": "Moderate risk. Ask customer to confirm before shipping.",
        "color": "yellow",
    },
    "nudge": {
        "code": "NUDGE_PREPAID",
        "label": "🔵 Nudge to prepaid",
        "description": "Higher risk. Offer discount to switch to prepaid.",
        "color": "blue",
    },
    "hold": {
        "code": "HOLD_CANCEL",
        "label": "🔴 Hold / Cancel",
        "description": "Very high risk. Do not ship until reviewed.",
        "color": "red",
    },
}


def decide(order: dict, use_llm: bool = True) -> dict:
    """
    Main decision function.

    Args:
        order: dict with order fields (matches CSV columns)
        use_llm: whether to call Gemini for address/name validation

    Returns:
        {
            action: str (SHIP / CONFIRM_WHATSAPP / NUDGE_PREPAID / HOLD_CANCEL),
            label: str (human-friendly),
            score: float (0-100),
            reasons: list[str],
            component_scores: dict,
            llm_scores: dict | None,
        }
    """
    cfg = load_config()
    thresholds = cfg["decision_thresholds"]
    lookups = _load_lookups()

    # Step 1: Rule-based feature engineering
    features = engineer_features(
        order,
        lookups["pincode_rto"],
        lookups["city_rto"],
        lookups["utm_rto"],
        lookups["phone_rto"],
    )

    # Step 2: LLM validation (only for address + name quality)
    llm_scores = None
    if use_llm:
        llm_scores = validate_order_with_llm(order)

    # Step 3: Risk scoring (weighted rule-based)
    scored = score_order(features, llm_scores)
    score = scored["score"]
    reasons = scored["reasons"]

    # Step 4: Instant overrides (regardless of score)
    if features.get("name_is_blocklisted") or features.get("is_zero_value"):
        action_key = "hold"
        reasons.insert(0, "🚫 Automatic hold: test name or ₹0 order value")
    # Step 5: Threshold-based bucketing
    elif score < thresholds["ship_as_is_below"]:
        action_key = "ship"
    elif score < thresholds["confirm_whatsapp_below"]:
        action_key = "confirm"
    elif score < thresholds["nudge_prepaid_below"]:
        action_key = "nudge"
    else:
        action_key = "hold"

    action = ACTIONS[action_key]

    # Build plain-English summary for ops team
    reason_text = " | ".join(reasons) if reasons else "No risk signals detected."

    return {
        "order_id": order.get("order_id", "N/A"),
        "action": action["code"],
        "label": action["label"],
        "score": score,
        "reason": reason_text,
        "reasons": reasons,
        "component_scores": scored["component_scores"],
        "llm_scores": llm_scores,
    }


def backtest(df=None) -> list[dict]:
    """
    Run the decision engine on all historical orders (without LLM for speed).
    Returns list of decisions for analysis.
    """
    if df is None:
        df = load_and_clean(str(DATA_PATH))

    results = []
    lookups = _load_lookups()
    thresholds = load_config()["decision_thresholds"]
    for _, row in df.iterrows():
        order = row.to_dict()
        features = engineer_features(
            order,
            lookups["pincode_rto"],
            lookups["city_rto"],
            lookups["utm_rto"],
            lookups["phone_rto"],
        )
        scored = score_order(features, llm_scores=None)
        score = scored["score"]

        if features.get("name_is_blocklisted") or features.get("is_zero_value"):
            action = "HOLD_CANCEL"
        elif score < thresholds["ship_as_is_below"]:
            action = "SHIP"
        elif score < thresholds["confirm_whatsapp_below"]:
            action = "CONFIRM_WHATSAPP"
        elif score < thresholds["nudge_prepaid_below"]:
            action = "NUDGE_PREPAID"
        else:
            action = "HOLD_CANCEL"

        results.append({
            "order_id": row["order_id"],
            "actual": row["final_status"],
            "is_rto": row["is_rto"],
            "action": action,
            "score": score,
        })
    return results
