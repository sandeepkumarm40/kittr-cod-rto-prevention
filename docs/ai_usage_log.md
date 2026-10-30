# AI Usage Log

## Tools Used and How

---

### 1. Antigravity (Claude Sonnet / Gemini) — Primary Development

**Used for:**
- Writing all Python modules (feature engineering, risk scorer, decision engine, WhatsApp flow, dashboard)
- Writing the business memo draft
- Designing the WhatsApp message templates in Hinglish
- Structuring the project architecture
- Writing test cases

**Where AI was wrong or weak:**

**Example 1 — LLM SDK import (caught and fixed):**  
The AI initially imported `google.generativeai` (deprecated package). Caught via the FutureWarning at runtime: *"All support for the `google.generativeai` package has ended."* Fixed by adding fallback to `google.genai` new SDK.

**Example 2 — EDA emoji encoding issue (caught and fixed):**  
The AI used emoji characters in print statements (e.g., 📊) which caused a `UnicodeEncodeError` on Windows with cp1252 encoding. Fixed by setting `$env:PYTHONIOENCODING="utf-8"` and using explicit `sys.stdout.reconfigure(encoding='utf-8')` where needed.

**Example 3 — Pincode risk: insufficient sample size:**  
Initial EDA showed "5 high-risk pincodes" with ≥45% RTO rate, but some had only 5 orders (small sample). The AI's first version didn't filter by minimum order count, which would have flagged pincodes unreliably. Fixed by adding `stats[stats["total"] >= 5]` filter with a note that production should require ≥10 orders.

**Example 4 — Redundant YAML disk I/O in inner loops (caught and fixed):**  
The AI placed `load_config()` calls inside inner feature checking functions (`is_valid_phone()`, `is_placeholder_address()`, `score_order()`). On a 2,018-order backtest, this triggered over 10,000 redundant disk file reads, causing the backtest to run for >30 seconds. Fixed by decorating `load_config` with `@functools.lru_cache(maxsize=1)` and loading lookups once, cutting runtime from >30s to 2.9s.

**Example 5 — Uncalibrated score distribution (caught and fixed):**  
The AI initially assumed risk scores would naturally span uniformly from 0 to 100, and set arbitrary thresholds in `thresholds.yaml` (`ship < 30`, `confirm < 55`, `nudge < 72`, `hold ≥ 72`). Because clean orders score 0 across most penalty components, actual scores clustered between 8 and 60, leaving `NUDGE_PREPAID` empty. We ran empirical quantile analysis, recalibrated component scaling, and tuned cutoffs to (25, 35, 50), achieving a realistic multi-bucket distribution with 78.9% hold precision.

---

### 2. Gemini 1.5 Flash — LLM Address/Name Validator

**Used for:**
- Judging address completeness (is "xyz" a real address?)
- Detecting fake customer names ("Test Order", "asdf")
- Parsing ambiguous Hinglish addresses

**Where Gemini was weak:**

**Example 1 — Hallucinated address scores:**  
In testing, Gemini occasionally gave an address like "ph krke aana, Masjid ke paas" (Hinglish for "call before coming, near mosque") a score of 7/10, interpreting it as a recognizable landmark address. A human ops person would know this is insufficient for delivery. Fixed by adding explicit guidance in the prompt: *"Hinglish direction-only addresses score 4-6, not 7+"*

**Example 2 — JSON format inconsistency:**  
Gemini sometimes returned JSON wrapped in markdown code fences (```json ... ```) instead of raw JSON, causing `json.loads()` to fail. Fixed by adding regex stripping of code fences before parsing.

**Example 3 — Over-generous name scoring:**  
Gemini gave "Riya Das" a 9/10 and "Test Order" a 2/10, but gave "Amit" (single-word name) a 6/10 — which is technically correct but we expected it to be flagged more strongly. Adjusted prompt guidance to clarify single-name ambiguity.

---

### Summary

| Tool | Task | Issues Found |
|---|---|---|
| Antigravity Agent | Code generation, architecture | SDK deprecation, encoding errors, sample size filtering |
| Gemini 1.5 Flash | Address/name validation | Hallucinated scores, JSON format, over-generous for single names |
| pdfplumber | PDF extraction | None (worked first try) |
| Streamlit | Dashboard | None |
