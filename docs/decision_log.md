# Decision Log

## Key Design Choices — COD RTO Prevention System

---

### 1. Rule-based vs. ML Model

**Decision:** Pure rule-based scoring (no trained ML model)  
**Alternatives considered:**  
- Logistic Regression / Random Forest on the dataset  
- XGBoost with feature importance  

**Why we chose rules:**  
- Dataset is ~2,000 rows — insufficient for a reliable ML model without overfitting  
- Rules are fully transparent: an ops manager can read them and understand every decision  
- Threshold changes don't require retraining — just edit `thresholds.yaml`  
- ML would have given marginal accuracy gains at the cost of interpretability and maintenance overhead  

---

### 2. LLM for Address/Name Only — Not for Scoring

**Decision:** Use Gemini only for address quality and name validity checks  
**Alternatives considered:**  
- Use LLM to score everything including RTO risk  
- Don't use LLM at all  

**Why we drew this line:**  
- LLMs are good at qualitative judgment (is "xyz" a real address?) but bad at arithmetic and rate comparisons  
- Using LLM for pincode RTO rates would be slower, more expensive, and less accurate than a simple dict lookup  
- Address quality is genuinely hard to assess with rules alone (Hinglish addresses, cultural conventions)  
- Cost: 1 LLM call per order ~₹0.01 (Gemini Flash). On 1,650 COD orders/month = ₹16.50/month. Acceptable  

---

### 3. WhatsApp Mock vs. Real Twilio Integration

**Decision:** FastAPI mock API with in-memory state  
**Alternatives considered:**  
- Real Twilio WhatsApp Business API  
- Simple print-based CLI simulator  

**Why mock:**  
- Assignment explicitly says "You don't need a real WhatsApp account"  
- The mock demonstrates the full state machine (SENT → CONFIRMED / CANCELLED / HELD) with real HTTP endpoints  
- Anyone evaluating can run `uvicorn whatsapp.api_mock:app` and POST to simulate any scenario  
- Production switch would just replace the mock send/receive with Twilio SDK calls  

---

### 4. Streamlit for Dashboard (not React/Next.js)

**Decision:** Streamlit  
**Alternatives considered:**  
- React + FastAPI + Plotly  
- Metabase / Grafana  

**Why Streamlit:**  
- Zero frontend build required; `streamlit run dashboard/app.py` is self-contained  
- "Run in under 10 minutes" requirement is easily met  
- Plotly charts are interactive and founder-friendly  
- React would be overkill for a single dashboard screen  

---

### 5. 5% Prepaid Discount (Not Higher, Not Lower)

**Decision:** 5% discount on AOV  
**Alternatives considered:** 8%, 10%, flat ₹50  

**Why 5%:**  
- Math: Expected RTO cost at 55% risk level = 0.55 × ₹169 = ₹93  
- 5% on ₹649 avg = ₹32 cost of discount  
- Net save = ₹61 → positive ROI even at moderate switch rate  
- 10% would be ₹65 cost → still positive but thinner margin  
- Empirical A/B test should validate the actual conversion rate before scaling  

---

### 6. Threshold Configuration in YAML (Not Database)

**Decision:** `config/thresholds.yaml` file  
**Alternatives considered:** Database table, environment variables, hardcoded constants  

**Why YAML:**  
- Ops team can open it in Notepad and edit numbers  
- Changes are version-controlled in git (you can see what changed and when)  
- No database setup required to run the project  
- Migration path: once the system scales, move to a DB-backed config panel  

---

### 7. No Pincode Blocklist — Use Rate Instead

**Decision:** Weight pincodes by historical RTO rate, not a static blocklist  
**Alternatives considered:** "Block all COD for pincode X" (Operations Head's approach)  

**Why rate-based:**  
- Even "bad" pincodes have some legitimate orders  
- A 60% RTO pincode still has 40% delivered orders — cancelling all of them loses real revenue  
- Rate-based scoring lets the system balance risk vs. opportunity  
- Agrees with Marketing Head's concern about over-cancellation  
- Hard blocklist can be added for extreme cases (>80% RTO) in a future iteration  
