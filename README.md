# Kittr COD RTO Prevention System

> An AI-powered system that classifies every COD order into 4 risk buckets before shipping, saving ₹ on RTOs while protecting genuine customer relationships.

---

## ⚡ Quick Start (< 10 minutes)

### Prerequisites
- Python 3.10+
- pip

### 1. Clone & Install

```bash
git clone <repo-url>
cd cod-rto-system
pip install -r requirements.txt
```

### 2. Configure (Optional)

Copy `.env.example` to `.env` and add your Gemini API key for LLM address validation:
```bash
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your_key_here
```

The system works without an API key — LLM validation gracefully falls back to rule-based checks.

### 3. Run the Backtest (See How It Performs on Historical Data)

```bash
python analysis/backtest_run.py
```

### 4. Run the Dashboard

```bash
# Using python -m (works on all systems regardless of PATH):
python -m streamlit run dashboard/app.py

# Or directly if your Python Scripts folder is in PATH:
streamlit run dashboard/app.py
```
Opens at `http://localhost:8501`

### 5. Run the WhatsApp Mock API

```bash
# Using python -m:
python -m uvicorn whatsapp.api_mock:app --reload --port 8001

# Or directly:
uvicorn whatsapp.api_mock:app --reload --port 8001
```
API docs at `http://localhost:8001/docs`

### 6. Run the WhatsApp Flow Simulator (Interactive Demo)

```bash
python whatsapp/flow_simulator.py
```

### 7. Run Tests

```bash
python -m pytest tests/ -v
```

### 8. Run EDA

```bash
python analysis/eda.py
```

---

## 🏗️ Project Structure

```
cod-rto-system/
├── data/
│   └── orders_sample.csv          # 2,018 historical COD orders
├── config/
│   └── thresholds.yaml            # ← Non-technical team edits this
├── engine/
│   ├── feature_engineering.py     # Risk features from raw order data
│   ├── risk_scorer.py             # Weighted rule-based scorer (0-100)
│   ├── llm_validator.py           # Gemini: address + name quality
│   └── decision_engine.py         # Main 4-bucket decision logic
├── whatsapp/
│   ├── message_templates.py       # Hinglish message templates + state machine
│   ├── flow_simulator.py          # CLI demo of the WhatsApp flow
│   └── api_mock.py                # FastAPI mock WhatsApp API
├── dashboard/
│   ├── app.py                     # Streamlit founder dashboard
│   └── metrics.py                 # ₹ impact calculator
├── analysis/
│   ├── eda.py                     # Exploratory data analysis
│   └── backtest_run.py            # Backtest on historical data
├── docs/
│   ├── business_memo.md           # Founder-facing memo
│   ├── decision_log.md            # Key design decisions
│   └── ai_usage_log.md            # AI tools usage log
├── tests/
│   ├── test_engine.py             # Decision engine & scoring tests
│   └── test_whatsapp.py           # WhatsApp state machine & mock API tests
├── requirements.txt               # Python package dependencies
└── README.md                      # Setup & architecture guide
```

---

## 🎯 How It Works

### The 4 Decision Buckets

| Bucket | Score | Action |
|---|---|---|
| ✅ Ship as-is | 0–24 | Dispatch normally without delay |
| 🟡 Confirm WhatsApp | 25–34 | Hinglish message; ship only on 1-click confirmation |
| 🔵 Nudge Prepaid | 35–49 | Offer 5% discount to switch to online UPI/Card payment |
| 🔴 Hold / Cancel | ≥ 50 or Hard Flag | Flag for ops review / cancel test orders & chronic RTOs |

### Risk Score Factors (Weighted)

| Feature | Weight | Source |
|---|---|---|
| Prior RTO history | 25% | Historical customer phone & past order data |
| Address quality | 20% | **Gemini LLM** (Hinglish landmarks, placeholder detection) |
| Pincode & City RTO rate | 15% | Historical courier delivery rate |
| Order value risk | 10% | Rules (elevated AOV on first order = higher risk) |
| Name quality | 10% | **Gemini LLM** (test name / fake identity detection) |
| Phone validity | 10% | Regex & placeholder checks |
| UTM source risk | 5% | Campaign-level historical return rates |
| Time of day | 5% | Midnight/late-night order placement risk |

### Why LLM for Address/Name Only?

LLMs are used **only** where simple code can't do the job:
- Judging whether "ph krke aana, Masjid ke paas" is a usable address (Hinglish)
- Detecting "Test Order" or "asdf" as fake names
- Distinguishing genuine landmarks from placeholder text

Everything else (RTO rates, scoring math, threshold logic) uses simple Python — faster, cheaper, and more predictable.

### Threshold Configuration

Non-technical ops can edit `config/thresholds.yaml` without touching code:
```yaml
decision_thresholds:
  ship_as_is_below: 25
  confirm_whatsapp_below: 35
  nudge_prepaid_below: 50
  hold_cancel_above: 50

whatsapp:
  prepaid_discount_pct: 5    # % discount offered
  confirmation_timeout_hours: 24
```

---

## 📱 WhatsApp Flow

### Confirmation Flow (for "Ship after confirmation")
```
System → Customer: "Namaste Priya ji! Aapka order #KT200001 ready hai. Confirm karo: YES / NO"
Customer → YES: Order ships ✅
Customer → NO:  Order cancelled ❌
Customer → unclear: System re-asks once, then holds ⏸️
No reply in 24h: Order held ⏸️
```

### Prepaid Nudge Flow
```
System → Customer: "Flat 5% OFF if you pay online now! [payment link]"
Customer pays online: Ships as prepaid ✅
Customer ignores/declines: Ships as COD (not blocked) 📦
```

---

## 💰 The Business Case

- Cost per RTO: **₹169** (₹65 forward + ₹65 return + ₹25 handling + ₹14.4 damage)
- Dataset baseline RTO rate: **28.4%**
- Orders with placeholder addresses: 63.5% RTO rate
- Customers with 2+ prior RTOs: **76.5% RTO rate**
- Prepaid discount cost: **₹32** (5% of ₹649 avg) vs ₹93 expected loss → **₹61 net positive per conversion**

---

## 📋 Key Data Findings

1. **Placeholder addresses (7.7% of orders) have 63.5% RTO rate** — 2.5× baseline
2. **2+ prior RTOs → 76.5% RTO rate** — strongest single predictor
3. **Tier 2/3 cities** (Gorakhpur 63%, Darbhanga 58%) massively outperform metros in RTO
4. **Meta ads have highest RTO** (31.3%) vs direct (22.7%) — marketing context matters
5. **₹2,000+ first orders have 40.4% RTO rate** — high-value, no-trust COD is risky

---

## 📄 Submission Checklist

- [x] GitHub repo with README
- [x] Working decision engine (`engine/decision_engine.py`)
- [x] LLM integration for address/name (`engine/llm_validator.py`)
- [x] WhatsApp mock flow (`whatsapp/api_mock.py`, `whatsapp/flow_simulator.py`)
- [x] Streamlit dashboard (`dashboard/app.py`)
- [x] Business memo (`docs/business_memo.md`)
- [x] Decision log (`docs/decision_log.md`)
- [x] AI usage log (`docs/ai_usage_log.md`)
- [x] Non-technical threshold config (`config/thresholds.yaml`)
- [x] Test suite (`tests/test_engine.py`)
