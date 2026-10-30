import sys; sys.path.insert(0,'.')
from engine.decision_engine import backtest
from dashboard.metrics import compute_dashboard_metrics

results = backtest()
print("Backtest done:", len(results), "orders")

metrics = compute_dashboard_metrics(results)
s = metrics['summary']
b = metrics['buckets']
h = metrics['hold_cancel']

print("SHIP:", b['ship'], "| CONFIRM:", b['confirm_whatsapp'], "| NUDGE:", b['nudge_prepaid'], "| HOLD:", b['hold_cancel'])
print("True holds (caught RTOs):", h['true_positives'])
print("False holds (wrongly stopped):", h['false_positives'])

total_hold = h['true_positives'] + h['false_positives']
precision = h['true_positives'] / total_hold if total_hold > 0 else 0
recall = h['true_positives'] / s['total_rto_in_data']
print("Hold Precision:", round(precision*100,1), "%")
print("Hold Recall:", round(recall*100,1), "%")

print("Estimated saved: Rs.", s['estimated_total_saved_inr'])
print("Estimated lost: Rs.", s['estimated_total_lost_inr'])
print("Net impact: Rs.", s['net_impact_inr'])
