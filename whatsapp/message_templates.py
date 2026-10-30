"""
WhatsApp Message Templates and Flow State Machine
Supports both Hinglish and English messages.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
import yaml
import functools
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "thresholds.yaml"


@functools.lru_cache(maxsize=1)
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ------------------------------------------------------------------ #
# Message Templates
# ------------------------------------------------------------------ #

def confirmation_message(order: dict) -> str:
    """WhatsApp message for CONFIRM_WHATSAPP action."""
    cfg = load_config()
    timeout_hours = cfg["whatsapp"]["confirmation_timeout_hours"]
    name = order.get("customer_name", "").split()[0]  # first name
    order_id = order.get("order_id", "")
    amount = order.get("order_value", "")
    items = order.get("items", "").replace("|", ", ")

    return f"""🛍️ *Kittr Order Update*

Namaste {name} ji! 🙏

Aapka order #{order_id} ready hai:
📦 *{items}*
💰 Amount: *₹{amount}* (Cash on Delivery)

Kya aap delivery confirm karte hain?
Reply karo: *YES* ya *NO*

⏰ {timeout_hours} ghante mein reply na aaye toh order automatically hold ho jayega.

— Kittr Team"""


def prepaid_nudge_message(order: dict) -> str:
    """WhatsApp message for NUDGE_PREPAID action."""
    cfg = load_config()
    discount_pct = cfg["whatsapp"]["prepaid_discount_pct"]
    valid_hours = cfg["whatsapp"]["prepaid_offer_valid_hours"]
    name = order.get("customer_name", "").split()[0]
    order_id = order.get("order_id", "")
    amount = int(order.get("order_value", 0))
    discount_amt = round(amount * discount_pct / 100)
    final_amount = amount - discount_amt

    # Generate a mock payment link
    payment_link = f"https://pay.kittr.in/{order_id}"

    return f"""🎁 *Special Offer — Kittr*

Namaste {name} ji! 🙏

Aapka order #{order_id} (₹{amount}) COD par hai.

💳 *Online pay karo aur pao FLAT {discount_pct}% OFF!*
✅ Aapko sirf *₹{final_amount}* dena hoga (₹{discount_amt} ki bachat!)

👉 Pay now: {payment_link}
⏰ Offer sirf *{valid_hours} ghante* valid hai.

COD rakhna chahte ho? Koi baat nahi, order normally ship hoga.

— Kittr Team"""


def confirmation_reminder(order: dict, hours_left: int) -> str:
    """Follow-up message if no reply."""
    name = order.get("customer_name", "").split()[0]
    order_id = order.get("order_id", "")
    return f"""⏰ *Reminder — Kittr*

Namaste {name} ji!

Aapke order #{order_id} ka confirmation abhi pending hai.
{hours_left} ghante baad order hold ho jayega.

Reply karo: *YES* (confirm) ya *NO* (cancel)"""


def order_confirmed_message(order: dict) -> str:
    name = order.get("customer_name", "").split()[0]
    order_id = order.get("order_id", "")
    return f"""✅ *Order Confirmed — Kittr*

Dhanyavaad {name} ji! 🙏
Aapka order #{order_id} confirm ho gaya.
Hum jald hi ship karenge aur tracking link bhejenge.

— Kittr Team"""


def order_cancelled_message(order: dict) -> str:
    name = order.get("customer_name", "").split()[0]
    order_id = order.get("order_id", "")
    return f"""❌ *Order Cancelled — Kittr*

Samajh gaye {name} ji.
Aapka order #{order_id} cancel kar diya gaya hai.
Koi problem ho toh humse baat karein: support@kittr.in

— Kittr Team"""


def order_held_timeout_message(order: dict) -> str:
    name = order.get("customer_name", "").split()[0]
    order_id = order.get("order_id", "")
    return f"""⏸️ *Order On Hold — Kittr*

{name} ji, aapka order #{order_id} hold par rakh diya gaya hai
kyunki 24 ghante mein koi reply nahi aaya.

Agar aap deliver karna chahte hain, humse contact karein:
📞 support@kittr.in

— Kittr Team"""


def clarification_message(order: dict) -> str:
    name = order.get("customer_name", "").split()[0]
    return f"""🤔 Samajha nahi {name} ji.

Kripya sirf *YES* ya *NO* reply karein:
• *YES* → Order deliver karo
• *NO* → Order cancel karo"""


# ------------------------------------------------------------------ #
# Flow State Machine
# ------------------------------------------------------------------ #

@dataclass
class WhatsAppFlowState:
    order_id: str
    order: dict
    flow_type: str          # "confirm" or "prepaid"
    state: str = "SENT"     # SENT → CONFIRMED / CANCELLED / HELD / PREPAID_PAID / SHIPPED_COD
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    clarification_attempts: int = 0
    messages_log: list = field(default_factory=list)

    def process_reply(self, reply: str) -> dict:
        """Process a customer reply. Returns action to take."""
        cfg = load_config()
        reply_clean = reply.strip().lower()
        max_attempts = cfg["whatsapp"]["max_clarification_attempts"]

        if self.flow_type == "confirm":
            if reply_clean in ("yes", "haan", "ha", "ok", "okay", "1", "y", "confirm"):
                self.state = "CONFIRMED"
                self.last_activity = datetime.now(timezone.utc)
                msg = order_confirmed_message(self.order)
                self.messages_log.append({"direction": "out", "text": msg, "ts": str(datetime.now(timezone.utc))})
                return {"action": "SHIP", "message": msg}

            elif reply_clean in ("no", "nahi", "nai", "cancel", "n", "0"):
                self.state = "CANCELLED"
                self.last_activity = datetime.now(timezone.utc)
                msg = order_cancelled_message(self.order)
                self.messages_log.append({"direction": "out", "text": msg, "ts": str(datetime.now(timezone.utc))})
                return {"action": "CANCEL", "message": msg}

            else:
                # Unclear reply
                if self.clarification_attempts < max_attempts:
                    self.clarification_attempts += 1
                    msg = clarification_message(self.order)
                    self.messages_log.append({"direction": "out", "text": msg, "ts": str(datetime.now(timezone.utc))})
                    return {"action": "CLARIFY", "message": msg}
                else:
                    self.state = "HELD"
                    return {"action": "HOLD", "message": "Max clarification attempts reached."}

        elif self.flow_type == "prepaid":
            # For prepaid nudge, any payment is detected via payment gateway webhook
            # "no" or "chal raha hai" → ship as COD
            if reply_clean in ("no", "nahi", "cod", "cash", "n"):
                self.state = "SHIPPED_COD"
                return {"action": "SHIP_COD", "message": "Shipping as COD as requested."}
            else:
                # Any other reply → keep as COD, don't block
                self.state = "SHIPPED_COD"
                return {"action": "SHIP_COD", "message": "No prepaid switch; shipping as COD."}

        return {"action": "UNKNOWN", "message": "Unknown flow type."}

    def check_timeout(self) -> Optional[dict]:
        """Call periodically. Returns hold action if timed out."""
        cfg = load_config()
        timeout_h = cfg["whatsapp"]["confirmation_timeout_hours"]
        if self.state == "SENT" and self.flow_type == "confirm":
            elapsed = (datetime.now(timezone.utc) - self.sent_at).total_seconds() / 3600
            if elapsed >= timeout_h:
                self.state = "HELD"
                msg = order_held_timeout_message(self.order)
                self.messages_log.append({"direction": "out", "text": msg, "ts": str(datetime.now(timezone.utc))})
                return {"action": "HOLD", "message": msg}
        return None
