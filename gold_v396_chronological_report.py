#!/usr/bin/env python3
"""Chronological audit of V3.9.6: retrospective split, NOT independent out-of-sample."""
import csv
from datetime import datetime, timezone
from pathlib import Path
P=Path(__file__).resolve().parent
SOURCE=P/"gold_long_backtest_v396_trades.csv"
BOUNDARY=datetime(2026,10,1,tzinfo=timezone.utc)
with SOURCE.open(newline="",encoding="utf-8") as stream:
    rows=list(csv.DictReader(stream))
if not rows:raise RuntimeError("No completed trades in V3.9.6 report")
result=[]
for threshold in ("60","65","70"):
    trades=[r for r in rows if r["score_min"]==threshold]
    for label,subset in (
        ("DEVELOPMENT_AUG_SEP",[r for r in trades if datetime.fromisoformat(r["opened"])<BOUNDARY]),
        ("RETROSPECTIVE_OCT",[r for r in trades if datetime.fromisoformat(r["opened"])>=BOUNDARY]),
        ("ALL",[r for r in trades]),
    ):
        vals=[float(r["net_R"]) for r in subset]
        gain=sum(x for x in vals if x>0)
        loss=-sum(x for x in vals if x<0)
        ordered=sorted(subset,key=lambda r:r["closed"])
        equity=peak=drawdown=0.
        for r in ordered:
            equity+=float(r["net_R"])
            peak=max(peak,equity)
            drawdown=max(drawdown,peak-equity)
        result.append(dict(score=threshold,period=label,trades=len(vals),wins=sum(x>0 for x in vals),
            win_rate=round(sum(x>0 for x in vals)/len(vals),4) if vals else "",
            net_R=round(sum(vals),4),mean_R=round(sum(vals)/len(vals),4) if vals else "",
            profit_factor=round(gain/loss,4) if loss else ("inf" if gain else ""),
            max_closed_drawdown_R=round(drawdown,4)))
with (P/"gold_v396_chronological_report.csv").open("w",newline="",encoding="utf-8") as stream:
    writer=csv.DictWriter(stream,fieldnames=result[0].keys());writer.writeheader();writer.writerows(result)
for r in result:
    print(f"Score {r['score']} {r['period']}: trades={r['trades']}, wins={r['wins']}, net_R={r['net_R']}, PF={r['profit_factor']}, closed_drawdown_R={r['max_closed_drawdown_R']}")
print("IMPORTANT: All dates Aug-Oct were previously inspected, so October is NOT a blind out-of-sample test.")
print("Trades are allocated by ENTRY timestamp; any trades spanning the boundary remain in their entry group.")
print("A real prospective holdout needs NEWER market data never used during design.")
