#!/usr/bin/env python3
"""Analyze Score 65 A/B by calendar month and leave-one-month-out; exploratory, not forward validated."""
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
p=Path(__file__).resolve().parent
with (p/"gold_ab_score65_trades.csv").open(newline="",encoding="utf-8") as f:
    trades=list(csv.DictReader(f))
if not trades:raise RuntimeError("Missing A/B trade rows")
report=[]
def summarize(subset,variant,segment):
    r=sorted(subset,key=lambda x:x["closed"])
    values=[float(x["net_R"]) for x in r]
    gain=sum(x for x in values if x>0);loss=-sum(x for x in values if x<0)
    balance=peak=dd=0.
    for value in values:
        balance+=value;peak=max(peak,balance);dd=max(dd,peak-balance)
    result=dict(variant=variant,period=segment,trades=len(values),
                wins=sum(x>0 for x in values),net_R=round(sum(values),4),
                profit_factor=round(gain/loss,4) if loss else ("inf" if gain else ""),
                max_closed_dd_R=round(dd,4))
    report.append(result)
    print(f"{variant} {segment}: trades={result['trades']} wins={result['wins']} net_R={result['net_R']} PF={result['profit_factor']} max_closed_dd_R={result['max_closed_dd_R']}")
for variant in ("A_BASELINE","B_HTF_MOMENTUM"):
    group=[r for r in trades if r["variant"]==variant]
    summarize(group,variant,"ALL")
    months=sorted({datetime.fromisoformat(r["opened"]).strftime("%Y-%m") for r in group})
    for month in months:
        summarize([r for r in group if datetime.fromisoformat(r["opened"]).strftime("%Y-%m")==month],variant,month)
        summarize([r for r in group if datetime.fromisoformat(r["opened"]).strftime("%Y-%m")!=month],variant,"EXCLUDE_"+month)
with (p/"gold_ab_score65_stability.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=report[0].keys());w.writeheader();w.writerows(report)
print("CAUTION: months already used in development, NOT blind validation; brokerage spread/slippage and actual fills unverified.")
