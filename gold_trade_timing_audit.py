#!/usr/bin/env python3
"""Audit simulated entry/exit timing; diagnostics only, never places orders."""
import csv
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

root=Path(__file__).resolve().parent
with (root/"gold_long_backtest_trades.csv").open(newline="") as f:
    trades=list(csv.DictReader(f))
out=[]
for r in trades:
    entry=datetime.fromisoformat(r["opened"])
    close=datetime.fromisoformat(r["closed"])
    delta=(close-entry).total_seconds()/60
    flags=[]
    if delta<0: flags.append("INVALID_EXIT_BEFORE_ENTRY")
    if delta==0: flags.append("SAME_ENTRY_CANDLE")
    if delta%15!=0: flags.append("MISALIGNED_15MIN_BARS")
    if delta>1440: flags.append("LONG_HOLD_CHECK_WEEKEND_AND_GAPS")
    if r["outcome"]=="STOP":
        stop=float(r["sl"]);ex=float(r["exit"]);ep=float(r["entry"])
        if abs(stop-ex)<1e-8:flags.append("ORIGINAL_STOP")
        elif abs(ex-ep)<1e-8:flags.append("BREAKEVEN_STOP")
        else:flags.append("PROTECTED_STOP")
    out.append({"score_min":r["score_min"],"opened":r["opened"],"closed":r["closed"],
        "side":r["side"],"outcome":r["outcome"],"duration_minutes":delta,
        "flags":";".join(flags),"net_R":r["net_R"]})
fields=list(out[0]) if out else []
with (root/"gold_trade_timing_audit.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
for threshold in ("60","65","70"):
    t=[x for x in out if x["score_min"]==threshold]
    zero=[x for x in t if x["duration_minutes"]==0]
    neg=[x for x in t if x["duration_minutes"]<0]
    print(f"Score {threshold}: trades={len(t)}, same-entry-candle={len(zero)}, negative-duration={len(neg)}")
    for x in zero[:12]:print("  SAME_CANDLE",x["opened"],x["side"],x["outcome"],x["net_R"])
print("Limitation: candle timestamps are bar OPEN times, not tick execution times.")
print("Further validation needed: intrabar TP/SL order, market gaps, spread, partial TP execution.")
