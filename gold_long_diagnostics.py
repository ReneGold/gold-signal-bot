#!/usr/bin/env python3
"""Diagnose only: analyzes simulated trades, no orders."""
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

root=Path(__file__).resolve().parent
with (root/"gold_long_backtest_trades.csv").open(newline="") as f:
    records=list(csv.DictReader(f))
if not records: raise RuntimeError("No trade records for analysis")

def summarize(rows):
    v=[float(r["net_R"]) for r in rows]
    gain=sum(x for x in v if x>0)
    loss=-sum(x for x in v if x<0)
    return len(v),sum(x>0 for x in v),round(sum(v),3),round(gain/loss,3) if loss else None

out=[]
for minimum in (60,65,70):
    group=[r for r in records if int(r["score_min"])==minimum]
    for category,func in (
        ("ALL",lambda r:"all"),
        ("SIDE",lambda r:r["side"]),
        ("EXIT",lambda r:r["outcome"]),
        ("ENTRY_UTC_HOUR",lambda r:datetime.fromisoformat(r["opened"]).strftime("%H")),
        ("ENTRY_WEEKDAY_UTC",lambda r:datetime.fromisoformat(r["opened"]).strftime("%A")),
        ("ENTRY_MONTH_UTC",lambda r:datetime.fromisoformat(r["opened"]).strftime("%Y-%m")),
    ):
        buckets=defaultdict(list)
        for row in group:buckets[func(row)].append(row)
        for key,values in sorted(buckets.items()):
            count,wins,total,pf=summarize(values)
            out.append({"threshold":minimum,"category":category,"group":key,"trades":count,"wins":wins,
                        "winrate_pct":round(100*wins/count,1),"net_R":total,
                        "mean_R":round(total/count,3),"profit_factor":pf if pf is not None else "n/a"})
fields=["threshold","category","group","trades","wins","winrate_pct","net_R","mean_R","profit_factor"]
with (root/"gold_long_backtest_diagnostics.csv").open("w",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(out)
for row in out:
    if row["category"] in ("ALL","SIDE","EXIT","ENTRY_MONTH_UTC"):
        print(f'Score {row["threshold"]} {row["category"]} {row["group"]}: '
              f'trades={row["trades"]}, wins={row["wins"]}, net_R={row["net_R"]}, PF={row["profit_factor"]}')
print("CSV: gold_long_backtest_diagnostics.csv")
print("CAUTION: exploratory grouped results; no multiple-testing correction, session data not broker-validated.")
