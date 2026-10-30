"""
Tests for the COD RTO Decision Engine
Run: python -m pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine.feature_engineering import is_valid_phone, is_placeholder_address, is_blocklisted_name
from engine.risk_scorer import score_order
from engine.decision_engine import decide

# ── Fixtures ──────────────────────────────────────────────────────────────

CLEAN_ORDER = {
    "order_id": "TEST001",
    "order_datetime": "2026-10-30 14:00",
    "customer_name": "Priya Sharma",
    "phone": "9876543210",
    "address": "Flat 12, Sunrise Apartments, MG Road, Bengaluru",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560001",
    "order_value": 649,
    "items": "Satin Bonnet",
    "num_items": 1,
    "customer_prior_orders": 3,
    "customer_prior_rto": 0,
    "utm_source": "direct",
    "courier": "Delhivery",
    "payment_method": "COD",
    "final_status": "",
}

RISKY_ORDER = {
    **CLEAN_ORDER,
    "order_id": "TEST002",
    "customer_name": "Test Order",
    "phone": "9999999999",
    "address": "xyz",
    "customer_prior_rto": 3,
    "order_value": 0,
}


# ── Phone Tests ───────────────────────────────────────────────────────────

def test_valid_phone():
    assert is_valid_phone("9876543210") == True

def test_invalid_phone_too_short():
    assert is_valid_phone("98765") == False

def test_invalid_phone_placeholder():
    assert is_valid_phone("9999999999") == False

def test_phone_with_country_code():
    assert is_valid_phone("+91 98765 43210") == True


# ── Address Tests ─────────────────────────────────────────────────────────

def test_placeholder_address_xyz():
    assert is_placeholder_address("xyz") == True

def test_placeholder_address_dot():
    assert is_placeholder_address(".") == True

def test_placeholder_call_me():
    assert is_placeholder_address("call me") == True

def test_valid_address():
    assert is_placeholder_address("Flat 12, Sunrise Apartments, MG Road") == False


# ── Name Tests ────────────────────────────────────────────────────────────

def test_blocklisted_name_test_order():
    assert is_blocklisted_name("Test Order") == True

def test_blocklisted_name_case_insensitive():
    assert is_blocklisted_name("TEST ORDER") == True

def test_valid_name():
    assert is_blocklisted_name("Priya Sharma") == False


# ── Scoring Tests ─────────────────────────────────────────────────────────

def test_clean_order_low_score():
    features = {
        "prior_rto_rate": 0.0,
        "prior_rto_count": 0,
        "pincode_rto_rate": 0.25,
        "utm_rto_rate": 0.23,
        "phone_valid": True,
        "phone_has_history": False,
        "address_is_placeholder": False,
        "address_length": 40,
        "name_is_blocklisted": False,
        "order_value": 649,
        "is_zero_value": False,
        "is_suspicious_high_value": False,
        "time_risk": 0.0,
        "is_high_rto_pincode": False,
    }
    result = score_order(features)
    assert result["score"] < 40, f"Expected low score, got {result['score']}"


def test_risky_order_high_score():
    features = {
        "prior_rto_rate": 1.0,
        "prior_rto_count": 3,
        "pincode_rto_rate": 0.6,
        "utm_rto_rate": 0.4,
        "phone_valid": False,
        "phone_has_history": False,
        "address_is_placeholder": True,
        "address_length": 3,
        "name_is_blocklisted": True,
        "order_value": 0,
        "is_zero_value": True,
        "is_suspicious_high_value": False,
        "time_risk": 1.0,
        "is_high_rto_pincode": True,
    }
    result = score_order(features)
    assert result["score"] > 70, f"Expected high score, got {result['score']}"


# ── Decision Engine Tests ─────────────────────────────────────────────────

def test_test_order_gets_held():
    decision = decide(RISKY_ORDER, use_llm=False)
    assert decision["action"] == "HOLD_CANCEL"

def test_clean_order_gets_shipped():
    decision = decide(CLEAN_ORDER, use_llm=False)
    # Clean order with no RTOs and good history should be ship or confirm
    assert decision["action"] in ("SHIP", "CONFIRM_WHATSAPP")

def test_decision_has_reason():
    decision = decide(CLEAN_ORDER, use_llm=False)
    assert "reason" in decision
    assert len(decision["reason"]) > 0

def test_decision_has_score():
    decision = decide(CLEAN_ORDER, use_llm=False)
    assert 0 <= decision["score"] <= 100
