"""
Unit tests for WhatsApp confirmation flow and FastAPI mock endpoints.
"""
import sys, os
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from whatsapp.message_templates import (
    WhatsAppFlowState,
    confirmation_message,
    prepaid_nudge_message,
    confirmation_reminder,
    order_confirmed_message,
    order_cancelled_message,
    order_held_timeout_message,
    clarification_message,
)
from whatsapp.api_mock import app, active_flows

client = TestClient(app)

SAMPLE_ORDER = {
    "order_id": "KT109999",
    "customer_name": "Rohan Mehra",
    "phone": "9811122233",
    "address": "402, Lotus Court, Indiranagar, Bengaluru",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560038",
    "order_value": 750,
    "items": "Rosemary Hair Oil | Silk Scrunchie",
}


def test_template_generation():
    msg = confirmation_message(SAMPLE_ORDER)
    assert "Rohan" in msg
    assert "KT109999" in msg
    assert "750" in msg
    assert "YES" in msg and "NO" in msg

    nudge_msg = prepaid_nudge_message(SAMPLE_ORDER)
    assert "Rohan" in nudge_msg
    assert "5% OFF" in nudge_msg or "FLAT 5%" in nudge_msg
    assert "https://pay.kittr.in/KT109999" in nudge_msg


def test_flow_state_yes():
    flow = WhatsAppFlowState(order_id="KT109999", order=SAMPLE_ORDER, flow_type="confirm")
    res = flow.process_reply("haan")
    assert flow.state == "CONFIRMED"
    assert res["action"] == "SHIP"
    assert "Dhanyavaad" in res["message"]


def test_flow_state_no():
    flow = WhatsAppFlowState(order_id="KT109999", order=SAMPLE_ORDER, flow_type="confirm")
    res = flow.process_reply("cancel")
    assert flow.state == "CANCELLED"
    assert res["action"] == "CANCEL"
    assert "cancel kar diya gaya" in res["message"]


def test_flow_state_clarification_and_timeout():
    flow = WhatsAppFlowState(order_id="KT109999", order=SAMPLE_ORDER, flow_type="confirm")
    
    # 1st unclear reply
    res1 = flow.process_reply("bhai kab aayega?")
    assert res1["action"] == "CLARIFY"
    assert flow.clarification_attempts == 1

    # 2nd unclear reply (exceeds max_clarification_attempts = 1)
    res2 = flow.process_reply("kya price hai?")
    assert res2["action"] == "HOLD"
    assert flow.state == "HELD"


def test_flow_timeout():
    flow = WhatsAppFlowState(order_id="KT109999", order=SAMPLE_ORDER, flow_type="confirm")
    flow.sent_at = datetime.now(timezone.utc) - timedelta(hours=25)
    res = flow.check_timeout()
    assert res is not None
    assert res["action"] == "HOLD"
    assert flow.state == "HELD"


def test_fastapi_endpoints():
    # 1. Health check
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # 2. Send WhatsApp message
    payload = {
        "order_id": "KT-TEST-API",
        "order": SAMPLE_ORDER,
        "flow_type": "confirm",
    }
    resp = client.post("/whatsapp/send", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["flow_state"] == "SENT"

    # 3. Check status
    resp = client.get("/whatsapp/status/KT-TEST-API")
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["state"] == "SENT"

    # 4. Receive reply YES
    resp = client.post("/whatsapp/receive", json={"order_id": "KT-TEST-API", "reply": "YES"})
    assert resp.status_code == 200
    assert resp.json()["action"] == "SHIP"
    assert resp.json()["flow_state"] == "CONFIRMED"

    # 5. Check logs
    resp = client.get("/whatsapp/logs")
    assert resp.status_code == 200
    assert resp.json()["total_messages"] >= 2
