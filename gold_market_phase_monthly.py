#!/usr/bin/env python3
"""Monthly B/C market regime comparison. Historical exploration only, never orders."""
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

p=Path(__file__).resolve().parent
with (p/"gold_market_phase_score65_trades.csv").open(newline="",encoding="utf-8") as f:
    trades=list(csv.DictReader(f))
if not trades:raise RuntimeError("No market phase A/B/C trades found")
out=[]
for variant in ("B_HTF_MOMENTUM","C_TREND_STRENGTH"):
    subset=[r for r in trades if r["variant"]==variant]
    for period in ["2026-08","2026-09","2026-10","ALL","EXCLUDE_AUG"]:
        selected=[r for r in subset if period=="ALL" or
                  (period=="EXCLUDE_AUG" and not r["opened"].startswith("2026-08")) or
                  r["opened"].startswith(period)]
        values=[float(r["net_R"]) for r in selected]
        gains=sum(max(v,0) for v in values)
        losses=-sum(min(v,0) for v in values)
        ordered=sorted(selected,key=lambda r:r["closed"])
        equity=peak=dd=0.0
        for r in ordered:
            equity+=float(r["net_R"]);peak=max(peak,equity);dd=max(dd,peak-equity)
        record=dict(variant=variant,period=period,trades=len(values),
            wins=sum(v>0 for v in values),net_R=round(sum(values),4),
            profit_factor=round(gains/losses,4) if losses else ("inf" if gains else ""),
            max_closed_dd_R=round(dd,4))
        out.append(record)
        print(f"{variant} {period}: trades={record['trades']} wins={record['wins']} net_R={record['net_R']} PF={record['profit_factor']} max_closed_dd_R={record['max_closed_dd_R']}")
with (p/"gold_market_phase_monthly_report.csv").open("w",newline="",encoding="utf-8") as f:
    writer=csv.DictWriter(f,fieldnames=out[0].keys());writer.writeheader();writer.writerows(out)
print("LIMITATIONS: exploratory; all months previously inspected; closed-trade only drawdown; fills, spread, execution and independent data unverified.")
