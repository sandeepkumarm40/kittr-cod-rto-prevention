"""
Metrics calculator for the dashboard.
Computes ₹ saved, ₹ lost, and net impact from backtest results.
"""
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "thresholds.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def compute_rto_cost(cfg: dict) -> float:
    """Total cost per RTO event."""
    costs = cfg["costs"]
    return (
        costs["forward_shipping"] +
        costs["return_shipping"] +
        costs["packaging_handling"] +
        costs["damaged_product_rate"] * costs["damaged_product_cost"]
    )


def compute_dashboard_metrics(backtest_results: list[dict], cfg: dict = None) -> dict:
    """
    Given backtest results (list of dicts with action, is_rto, actual),
    compute all dashboard metrics.

    Logic:
    - HOLD_CANCEL on a true RTO → ₹ saved (avoided RTO cost)
    - HOLD_CANCEL on a true DELIVERED → ₹ lost (lost gross margin on valid order)
    - CONFIRM_WHATSAPP reduces RTO risk by ~50% (assumed conversion rate)
    - NUDGE_PREPAID reduces RTO risk by ~60% for those who switch (assumed 20% switch rate)
    """
    if cfg is None:
        cfg = load_config()

    costs = cfg["costs"]
    rto_cost = compute_rto_cost(cfg)
    avg_aov = costs["avg_order_value"]
    gross_margin = costs["gross_margin"]

    buckets = {"SHIP": [], "CONFIRM_WHATSAPP": [], "NUDGE_PREPAID": [], "HOLD_CANCEL": []}
    for r in backtest_results:
        action = r.get("action", "SHIP")
        if action in buckets:
            buckets[action].append(r)

    # --- HOLD/CANCEL analysis ---
    hold_orders = buckets["HOLD_CANCEL"]
    true_holds = [o for o in hold_orders if o["is_rto"] == 1]    # correctly held RTOs
    false_holds = [o for o in hold_orders if o["is_rto"] == 0]   # wrongly held good orders

    rto_saved = len(true_holds) * rto_cost
    revenue_lost = len(false_holds) * avg_aov * gross_margin

    # --- CONFIRM_WHATSAPP analysis ---
    confirm_orders = buckets["CONFIRM_WHATSAPP"]
    confirm_rto_count = sum(o["is_rto"] for o in confirm_orders)
    # Assume 70% reply, of those 15% cancel → 10.5% prevented; rest ship
    confirmation_prevention_rate = 0.105
    confirm_saved = confirm_rto_count * confirmation_prevention_rate * rto_cost
    # Some false confirms (legit customers) get cancelled: assume 5%
    confirm_false_cancel = len(confirm_orders) * (1 - confirm_rto_count / max(len(confirm_orders), 1)) * 0.05
    confirm_lost = confirm_false_cancel * avg_aov * gross_margin

    # --- NUDGE_PREPAID analysis ---
    nudge_orders = buckets["NUDGE_PREPAID"]
    nudge_rto_count = sum(o["is_rto"] for o in nudge_orders)
    # 20% switch to prepaid; prepaid RTO rate drops from ~28% to 4%
    discount_pct = cfg["whatsapp"]["prepaid_discount_pct"] / 100
    switch_rate = 0.20
    prepaid_rto_rate = 0.04
    nudge_saved = len(nudge_orders) * switch_rate * (0.28 - prepaid_rto_rate) * rto_cost
    discount_cost = len(nudge_orders) * switch_rate * avg_aov * discount_pct
    nudge_net = nudge_saved - discount_cost

    net_impact = rto_saved - revenue_lost + confirm_saved - confirm_lost + nudge_net

    return {
        "buckets": {
            "ship": len(buckets["SHIP"]),
            "confirm_whatsapp": len(buckets["CONFIRM_WHATSAPP"]),
            "nudge_prepaid": len(buckets["NUDGE_PREPAID"]),
            "hold_cancel": len(buckets["HOLD_CANCEL"]),
        },
        "hold_cancel": {
            "true_positives": len(true_holds),    # real RTOs caught
            "false_positives": len(false_holds),  # valid orders incorrectly held
            "rto_saved_inr": round(rto_saved),
            "revenue_lost_inr": round(revenue_lost),
        },
        "confirm_whatsapp": {
            "orders": len(confirm_orders),
            "rto_in_bucket": confirm_rto_count,
            "estimated_saved_inr": round(confirm_saved),
            "estimated_lost_inr": round(confirm_lost),
        },
        "nudge_prepaid": {
            "orders": len(nudge_orders),
            "rto_in_bucket": nudge_rto_count,
            "estimated_saved_inr": round(nudge_saved),
            "discount_cost_inr": round(discount_cost),
            "net_inr": round(nudge_net),
        },
        "summary": {
            "total_orders": len(backtest_results),
            "total_rto_in_data": sum(r["is_rto"] for r in backtest_results),
            "estimated_total_saved_inr": round(rto_saved + confirm_saved + nudge_saved),
            "estimated_total_lost_inr": round(revenue_lost + confirm_lost + discount_cost),
            "net_impact_inr": round(net_impact),
            "rto_cost_per_event_inr": round(rto_cost),
        }
    }
