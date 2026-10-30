"""
Streamlit Dashboard — Founder Morning View
Run: streamlit run dashboard/app.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yaml

from engine.feature_engineering import load_and_clean
from engine.decision_engine import backtest
from dashboard.metrics import compute_dashboard_metrics, load_config

st.set_page_config(
    page_title="Kittr — COD Risk Dashboard",
    page_icon="📦",
    layout="wide",
)

st.markdown("""
<style>
.metric-card {background: #f8f9fa; border-radius: 12px; padding: 20px; text-align: center;}
.metric-title {font-size: 14px; color: #666; margin-bottom: 4px;}
.metric-value {font-size: 32px; font-weight: bold;}
.green {color: #22c55e;}
.red {color: #ef4444;}
.yellow {color: #f59e0b;}
.blue {color: #3b82f6;}
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.image("https://via.placeholder.com/200x60?text=🧴+Kittr", width=200)
st.sidebar.title("Kittr RTO Dashboard")
st.sidebar.markdown("---")

date_range = st.sidebar.selectbox(
    "Time Period",
    ["Yesterday", "Last 7 Days", "Last 30 Days", "All Data"],
    index=3
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Config Controls**")
cfg = load_config()
ship_threshold = st.sidebar.slider("Ship as-is below score", 5, 40, cfg["decision_thresholds"]["ship_as_is_below"])
confirm_threshold = st.sidebar.slider("Confirm WhatsApp below score", 20, 60, cfg["decision_thresholds"]["confirm_whatsapp_below"])
nudge_threshold = st.sidebar.slider("Nudge prepaid below score", 35, 80, cfg["decision_thresholds"]["nudge_prepaid_below"])

# ─── Load Data ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_backtest_results():
    results = backtest()
    return results

with st.spinner("Loading order data..."):
    results = get_backtest_results()
    metrics = compute_dashboard_metrics(results)

df_results = pd.DataFrame(results)

# ─── Header ─────────────────────────────────────────────────────────────────
st.title("📦 Kittr — COD Risk Intelligence Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %I:%M %p')} | {date_range}")

st.markdown("---")

# ─── Top KPI Row ────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    val = metrics["summary"]["estimated_total_saved_inr"]
    st.metric("✅ Estimated ₹ Saved", f"₹{val:,}", 
              help="Avoided RTO costs from held/cancelled orders + WhatsApp conversions")

with col2:
    val = metrics["summary"]["estimated_total_lost_inr"]
    st.metric("⚠️ Estimated ₹ Lost", f"₹{val:,}",
              help="Lost gross margin from valid orders incorrectly held")

with col3:
    net = metrics["summary"]["net_impact_inr"]
    delta_color = "normal" if net > 0 else "inverse"
    st.metric("💰 Net ₹ Impact", f"₹{net:,}", delta=f"{'Positive' if net > 0 else 'Negative'}",
              delta_color=delta_color)

with col4:
    total_rto = metrics["summary"]["total_rto_in_data"]
    total = metrics["summary"]["total_orders"]
    st.metric("📊 Dataset RTO Rate", f"{total_rto/total:.1%}",
              help=f"{total_rto} RTOs out of {total} COD orders")

st.markdown("---")

# ─── Order Buckets ──────────────────────────────────────────────────────────
st.subheader("📋 Orders by Decision Bucket")

buckets = metrics["buckets"]
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-title'>✅ Ship as-is</div>
        <div class='metric-value green'>{buckets['ship']}</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-title'>🟡 Confirm WhatsApp</div>
        <div class='metric-value yellow'>{buckets['confirm_whatsapp']}</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-title'>🔵 Nudge Prepaid</div>
        <div class='metric-value blue'>{buckets['nudge_prepaid']}</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-title'>🔴 Hold / Cancel</div>
        <div class='metric-value red'>{buckets['hold_cancel']}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ─── Charts Row ─────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("🍩 Decision Distribution")
    fig_pie = px.pie(
        names=["Ship as-is", "Confirm WhatsApp", "Nudge Prepaid", "Hold/Cancel"],
        values=[buckets["ship"], buckets["confirm_whatsapp"],
                buckets["nudge_prepaid"], buckets["hold_cancel"]],
        color_discrete_sequence=["#22c55e", "#f59e0b", "#3b82f6", "#ef4444"],
        hole=0.45,
    )
    fig_pie.update_layout(margin=dict(t=20, b=20))
    st.plotly_chart(fig_pie, use_container_width=True)

with col_r:
    st.subheader("🎯 Hold/Cancel Accuracy")
    hold_tp = metrics["hold_cancel"]["true_positives"]
    hold_fp = metrics["hold_cancel"]["false_positives"]
    fig_bar = go.Figure(go.Bar(
        x=["True Holds (Actual RTOs)", "False Holds (Valid Orders)"],
        y=[hold_tp, hold_fp],
        marker_color=["#22c55e", "#ef4444"],
        text=[hold_tp, hold_fp],
        textposition="auto",
    ))
    fig_bar.update_layout(margin=dict(t=20, b=20), showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# ─── Risk Score Distribution ────────────────────────────────────────────────
st.subheader("📈 Risk Score Distribution")
fig_hist = px.histogram(
    df_results, x="score", color="actual",
    nbins=30,
    color_discrete_map={"DELIVERED": "#22c55e", "RTO": "#ef4444"},
    labels={"score": "Risk Score (0-100)", "actual": "Actual Outcome"},
    opacity=0.75,
)
fig_hist.add_vline(x=ship_threshold, line_dash="dash", line_color="green",
                   annotation_text="Ship", annotation_position="top")
fig_hist.add_vline(x=confirm_threshold, line_dash="dash", line_color="orange",
                   annotation_text="Confirm", annotation_position="top")
fig_hist.add_vline(x=nudge_threshold, line_dash="dash", line_color="blue",
                   annotation_text="Nudge", annotation_position="top")
fig_hist.update_layout(margin=dict(t=20, b=20))
st.plotly_chart(fig_hist, use_container_width=True)

st.markdown("---")

# ─── ₹ Impact Summary ───────────────────────────────────────────────────────
st.subheader("💰 ₹ Impact Breakdown")

impact_data = {
    "Category": [
        "RTO Saved (Hold/Cancel)",
        "Prepaid Nudge Savings",
        "WhatsApp Confirm Savings",
        "Revenue Lost (False Holds)",
        "Discount Cost (Prepaid Nudge)",
    ],
    "Amount (₹)": [
        metrics["hold_cancel"]["rto_saved_inr"],
        metrics["nudge_prepaid"]["estimated_saved_inr"],
        metrics["confirm_whatsapp"]["estimated_saved_inr"],
        -metrics["hold_cancel"]["revenue_lost_inr"],
        -metrics["nudge_prepaid"]["discount_cost_inr"],
    ],
}
df_impact = pd.DataFrame(impact_data)
df_impact["Color"] = df_impact["Amount (₹)"].apply(lambda x: "#22c55e" if x > 0 else "#ef4444")

fig_impact = go.Figure(go.Bar(
    x=df_impact["Category"],
    y=df_impact["Amount (₹)"],
    marker_color=df_impact["Color"],
    text=[f"₹{abs(v):,}" for v in df_impact["Amount (₹)"]],
    textposition="auto",
))
fig_impact.update_layout(margin=dict(t=20, b=20))
st.plotly_chart(fig_impact, use_container_width=True)

st.markdown("---")

# ─── Order Table ────────────────────────────────────────────────────────────
st.subheader("🔍 Order Details")
action_filter = st.multiselect(
    "Filter by action",
    ["SHIP", "CONFIRM_WHATSAPP", "NUDGE_PREPAID", "HOLD_CANCEL"],
    default=["HOLD_CANCEL", "NUDGE_PREPAID"],
)

display_df = df_results[df_results["action"].isin(action_filter)].copy()
display_df["score"] = display_df["score"].round(1)
display_df = display_df.sort_values("score", ascending=False).head(100)

def color_action(val):
    colors = {
        "SHIP": "background-color: #dcfce7",
        "CONFIRM_WHATSAPP": "background-color: #fef9c3",
        "NUDGE_PREPAID": "background-color: #dbeafe",
        "HOLD_CANCEL": "background-color: #fee2e2",
    }
    return colors.get(val, "")

st.dataframe(
    display_df[["order_id", "action", "score", "actual", "is_rto"]].style.map(
        color_action, subset=["action"]
    ),
    use_container_width=True,
    height=400,
)

st.markdown("---")
st.caption("Kittr RTO Intelligence System | Built for Oyetra D2C Assignment")
