"""
WhatsApp Flow Simulator — interactive demo
Run: python whatsapp/flow_simulator.py

Demonstrates the full flow for both CONFIRM and PREPAID scenarios.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from whatsapp.message_templates import (
    WhatsAppFlowState, confirmation_message, prepaid_nudge_message
)
from engine.decision_engine import decide

DEMO_ORDERS = [
    {
        "order_id": "KT200001",
        "order_datetime": "2026-10-30 14:30",
        "customer_name": "Priya Sharma",
        "phone": "9876543210",
        "address": "Flat 12, Sunrise Apartments, MG Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001",
        "order_value": 898,
        "items": "Satin Bonnet|Microfiber Hair Towel",
        "num_items": 2,
        "customer_prior_orders": 1,
        "customer_prior_rto": 1,
        "utm_source": "meta_ads",
        "courier": "Delhivery",
        "payment_method": "COD",
        "final_status": "",
    },
    {
        "order_id": "KT200002",
        "order_datetime": "2026-10-30 02:15",
        "customer_name": "Riya Das",
        "phone": "8765432109",
        "address": "xyz",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400001",
        "order_value": 1547,
        "items": "Heatless Curling Set|Satin Pillowcase|Hair Oil 100ml",
        "num_items": 3,
        "customer_prior_orders": 0,
        "customer_prior_rto": 0,
        "utm_source": "direct",
        "courier": "Shadowfax",
        "payment_method": "COD",
        "final_status": "",
    },
    {
        "order_id": "KT200003",
        "order_datetime": "2026-10-30 11:00",
        "customer_name": "Test Order",
        "phone": "9999999999",
        "address": "near station",
        "city": "Delhi",
        "state": "Delhi",
        "pincode": "110001",
        "order_value": 798,
        "items": "Scrunchies 6pk|Claw Clip Set",
        "num_items": 2,
        "customer_prior_orders": 5,
        "customer_prior_rto": 0,
        "utm_source": "meta_ads",
        "courier": "BlueDart",
        "payment_method": "COD",
        "final_status": "",
    },
]


def run_simulator():
    print("=" * 65)
    print("  KITTR — WhatsApp Flow Simulator")
    print("=" * 65)

    for order in DEMO_ORDERS:
        print(f"\n{'─'*65}")
        print(f"📦 ORDER: {order['order_id']} | {order['customer_name']} | ₹{order['order_value']}")
        print(f"   Address: {order['address']}")
        print(f"   Prior RTOs: {order['customer_prior_rto']}")
        print()

        # Run decision engine (no LLM for demo speed)
        decision = decide(order, use_llm=False)
        print(f"🤖 DECISION: {decision['label']}")
        print(f"   Score: {decision['score']}/100")
        print(f"   Reason: {decision['reason']}")
        print()

        if decision["action"] == "CONFIRM_WHATSAPP":
            print("📱 WHATSAPP OUTBOUND:")
            msg = confirmation_message(order)
            print(msg)
            print()

            flow = WhatsAppFlowState(
                order_id=order["order_id"],
                order=order,
                flow_type="confirm",
            )

            # Simulate YES reply
            print("💬 Customer replies: 'YES'")
            result = flow.process_reply("YES")
            print(f"✅ Action: {result['action']}")
            print(f"📱 Response sent:\n{result['message']}")

        elif decision["action"] == "NUDGE_PREPAID":
            print("📱 WHATSAPP OUTBOUND:")
            msg = prepaid_nudge_message(order)
            print(msg)

        elif decision["action"] == "HOLD_CANCEL":
            print("🔴 Order flagged for HOLD/CANCEL. No WhatsApp message sent (ops team review).")

        elif decision["action"] == "SHIP":
            print("✅ Shipping as-is. No intervention needed.")

    print(f"\n{'─'*65}")
    print("Simulator complete. Run the mock API for full interactive testing:")
    print("  uvicorn whatsapp.api_mock:app --reload --port 8001")
    print(f"{'─'*65}\n")


if __name__ == "__main__":
    run_simulator()
