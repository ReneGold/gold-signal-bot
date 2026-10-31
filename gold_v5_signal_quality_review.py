#!/usr/bin/env python3
"""Descriptive segmentation of observed Gold V5 paper trades.
Uses ledger only; cannot reconstruct EMA/ATR or assert entry quality.
Does not modify signals, trade records, parameters, orders or Telegram.
"""
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with (ROOT / "gold_v5_forward_ledger.csv").open(newline="", encoding="utf-8") as f:
    trades = list(csv.DictReader(f))
forward = [x for x in trades if x.get("cohort") == "FORWARD"]
closed = [x for x in forward if x.get("status") == "CLOSED_PAPER"]
def time_bucket(t):
    hour = datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(timezone.utc).hour
    if hour < 6: return "00-06 UTC"
    if hour < 12: return "06-12 UTC"
    if hour < 18: return "12-18 UTC"
    return "18-24 UTC"

def summarize(rows):
    vals = [float(x["net_R"]) for x in rows]
    return {"trades": len(vals), "wins": sum(v > 0 for v in vals),
            "losses_or_flat": sum(v <= 0 for v in vals),
            "net_R": round(sum(vals), 5),
            "average_R": round(sum(vals)/len(vals), 5) if vals else None}

def segments(key):
    groups = defaultdict(list)
    for x in closed:
        groups[key(x)].append(x)
    return {k: summarize(v) for k, v in sorted(groups.items())}

report = {
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "Only closed FORWARD paper trades; INITIAL_BACKFILL excluded",
    "all_closed_forward": summarize(closed),
    "segments": {
        "direction": segments(lambda x: x.get("side") or "UNKNOWN"),
        "recorded_phase": segments(lambda x: x.get("phase") or "UNKNOWN"),
        "exit_reason": segments(lambda x: x.get("exit_reason") or "UNKNOWN"),
        "signal_time_utc": segments(lambda x: time_bucket(x["signal_utc"])),
    },
    "coverage": {
        "forward_signals": len(forward),
        "closed": len(closed),
        "open_or_pending": sum(x.get("status") in ("OPEN_PAPER", "PENDING_ENTRY") for x in forward),
        "unresolved": sum(x.get("status") == "UNRESOLVED_DATA_GAP" for x in forward),
    },
    "research_limits": [
        "Segmentation is descriptive, not a predictive model or trade recommendation.",
        "One winning trade or a small subgroup cannot establish a favorable market condition.",
        "Historical indicator values, signal-score, spread, fill latency and actual broker execution are not available in the ledger.",
        "UTC time buckets are not verified broker sessions and may mix market regimes.",
        "Broker-verified fills, out-of-sample performance and independent observation are required before considering live trading."
    ],
    "signal_evidence_available": {
        "signal_timestamp": True, "direction": True, "recorded_phase": True,
        "stop_and_target": True, "exit_reason": True,
        "ema_at_signal": False, "atr_at_signal": False, "broker_bid_ask": False,
        "slippage": False, "signal_score": False
    }
}
(ROOT / "gold_v5_signal_quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
