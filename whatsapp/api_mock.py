"""
Mock WhatsApp API — FastAPI server simulating WhatsApp send/receive.
No real WhatsApp account needed. Simulates the full confirmation flow.

Run with: uvicorn whatsapp.api_mock:app --reload --port 8001
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional
import uuid

from whatsapp.message_templates import (
    WhatsAppFlowState, confirmation_message, prepaid_nudge_message
)

app = FastAPI(title="Kittr WhatsApp Mock API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active flows
active_flows: dict[str, WhatsAppFlowState] = {}
message_log: list[dict] = []


class SendMessageRequest(BaseModel):
    order_id: str
    order: dict
    flow_type: str  # "confirm" or "prepaid"


class IncomingReply(BaseModel):
    order_id: str
    reply: str
    phone: Optional[str] = None


class SimulateReply(BaseModel):
    order_id: str
    reply: str


@app.post("/whatsapp/send")
def send_message(req: SendMessageRequest):
    """Initiate a WhatsApp flow for an order."""
    order_id = req.order_id

    if req.flow_type == "confirm":
        msg = confirmation_message(req.order)
    elif req.flow_type == "prepaid":
        msg = prepaid_nudge_message(req.order)
    else:
        raise HTTPException(400, f"Unknown flow_type: {req.flow_type}")

    flow = WhatsAppFlowState(
        order_id=order_id,
        order=req.order,
        flow_type=req.flow_type,
        state="SENT",
    )
    flow.messages_log.append({
        "direction": "out",
        "text": msg,
        "ts": str(datetime.now(timezone.utc)),
    })
    active_flows[order_id] = flow

    log_entry = {
        "id": str(uuid.uuid4()),
        "order_id": order_id,
        "direction": "outbound",
        "flow_type": req.flow_type,
        "message": msg,
        "timestamp": str(datetime.now(timezone.utc)),
        "state": flow.state,
    }
    message_log.append(log_entry)

    return {
        "success": True,
        "order_id": order_id,
        "message_sent": msg,
        "flow_state": flow.state,
    }


@app.post("/whatsapp/receive")
def receive_reply(req: IncomingReply):
    """Process an incoming customer reply."""
    flow = active_flows.get(req.order_id)
    if not flow:
        raise HTTPException(404, f"No active flow for order {req.order_id}")

    flow.messages_log.append({
        "direction": "in",
        "text": req.reply,
        "ts": str(datetime.now(timezone.utc)),
    })

    result = flow.process_reply(req.reply)

    log_entry = {
        "id": str(uuid.uuid4()),
        "order_id": req.order_id,
        "direction": "inbound",
        "reply": req.reply,
        "action_taken": result["action"],
        "timestamp": str(datetime.now(timezone.utc)),
        "state": flow.state,
    }
    message_log.append(log_entry)

    return {
        "order_id": req.order_id,
        "action": result["action"],
        "outbound_message": result.get("message", ""),
        "flow_state": flow.state,
    }


@app.get("/whatsapp/status/{order_id}")
def get_flow_status(order_id: str):
    """Get current state of a WhatsApp flow."""
    flow = active_flows.get(order_id)
    if not flow:
        raise HTTPException(404, f"No active flow for order {order_id}")

    # Check timeout
    timeout_result = flow.check_timeout()

    return {
        "order_id": order_id,
        "flow_type": flow.flow_type,
        "state": flow.state,
        "sent_at": str(flow.sent_at),
        "clarification_attempts": flow.clarification_attempts,
        "messages": flow.messages_log,
        "timeout_triggered": timeout_result is not None,
    }


@app.get("/whatsapp/logs")
def get_all_logs():
    """Get all WhatsApp message logs."""
    return {
        "total_messages": len(message_log),
        "active_flows": len(active_flows),
        "logs": message_log[-50:],  # last 50 entries
    }


@app.post("/whatsapp/simulate")
def simulate_conversation(req: SimulateReply):
    """
    Simulate a customer reply (for demo/testing).
    Same as /receive but with a friendlier name.
    """
    return receive_reply(IncomingReply(order_id=req.order_id, reply=req.reply))


@app.get("/health")
def health():
    return {"status": "ok", "service": "Kittr WhatsApp Mock API"}
