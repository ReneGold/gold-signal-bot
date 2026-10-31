#!/usr/bin/env python3
"""Evidence sufficiency for isolated Gold V5 paper FORWARD cohort.
Descriptive research only: no strategy edits, signals, live orders or notifications.
"""
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with (ROOT / "gold_v5_forward_ledger.csv").open(newline="", encoding="utf-8") as handle:
    records = list(csv.DictReader(handle))
forward = [r for r in records if r.get("cohort") == "FORWARD"]
closed = [r for r in forward if r.get("status") == "CLOSED_PAPER"]
values = [float(r["net_R"]) for r in closed]
if not all(math.isfinite(v) for v in values):
    raise ValueError("Non-finite forward return")
n = len(values)
wins = sum(v > 0 for v in values)
# Wilson 95% score interval for the win proportion, not a profitability interval.
if n:
    z = 1.959963984540054
    p = wins / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    spread = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    ci = [round(max(0.0, center-spread)*100, 2),
          round(min(1.0, center+spread)*100, 2)]
else:
    ci = None
if n < 30:
    stage = "INSUFFICIENT"
    note = "Fewer than 30 closed observed FORWARD trades; no strategy-quality inference."
elif n < 100:
    stage = "EARLY_EXPLORATORY"
    note = "30-99 trades permit exploratory review only; no readiness or profitability certification."
else:
    stage = "LARGER_SAMPLE_STILL_UNVALIDATED"
    note = "At least 100 trades, but independent out-of-sample and executable broker validation still required."
result = {
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "FORWARD CLOSED_PAPER only; INITIAL_BACKFILL excluded",
    "closed_forward_trades": n,
    "forward_open_or_pending": sum(r.get("status") in ("OPEN_PAPER", "PENDING_ENTRY") for r in forward),
    "observed_wins": wins,
    "observed_net_R": round(sum(values), 5),
    "win_rate_wilson_95_pct": ci,
    "evidence_stage": stage,
    "interpretation": note,
    "thresholds_are": "Illustrative research milestones, NOT statistical proof or trading approval.",
    "critical_limits": [
        "Win-rate confidence interval is not a profitability confidence interval and assumes independent comparable trades.",
        "Trading outcomes may be dependent or regime-specific; historical results cannot guarantee future results.",
        "Fills are indicative next-bar OHLC, not executable broker bid/ask or verified spread/slippage.",
        "Market session and missed executions may bias observed sample; no live-money readiness assertion."
    ]
}
(ROOT / "gold_v5_evidence_report.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
