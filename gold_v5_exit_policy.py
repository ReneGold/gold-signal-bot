#!/usr/bin/env python3
"""Gold V5: fixed-entry exit-policy study, NO trades/Telegram.
Important distinction: a fixed-entry cohort evaluates EXIT policy conditional on
the exact same signal candles; it is NOT a simultaneous capital portfolio backtest.
"""
import csv,json,statistics
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
import gold_v5_session_ab as base
P=Path(__file__).resolve().parent/"gold_data_audit"
bars=base.bars
# signal candidates independent of exit outcomes, common to ALL policy experiments
def signals(rule):
    out=[]
    for i in range(60,len(bars)-25):
        d=base.candidate(i,rule)
        if d and base.ref_open(bars[i][0]+timedelta(minutes=15)) and base.ref_open(bars[i+1][0]):
            out.append((i,d))
    return out
def outcome(i,d,stop_mult,tp_mult,hold=16):
    entry=bars[i+1][1]
    risk=stop_mult*base.atr[i]
    sl=entry-d*risk;tp=entry+d*risk*tp_mult
    exit_idx=i+hold;px=bars[exit_idx][4];kind="TIME"
    for j in range(i+1,i+hold+1):
        b=bars[j];stop=(b[3]<=sl if d==1 else b[2]>=sl)
        take=(b[2]>=tp if d==1 else b[3]<=tp)
        if stop:
            px=min(sl,b[1]) if d==1 else max(sl,b[1]);kind="STOP";exit_idx=j;break
        if take:
            px=tp;kind="TP";exit_idx=j;break
    return dict(net_R=(d*(px-entry)-0.8)/risk,exit=kind,bars_held=exit_idx-i,
        entry=entry,exit_price=px,entry_index=i+1,exit_index=exit_idx)
policies=[("BASE_1p5ATR_TP2R",1.5,2.0),("ATR_1p5_TP1p5",1.5,1.5),("ATR_1p5_TP3",1.5,3.0),
          ("ATR_1p0_TP2",1.0,2.0),("ATR_2p0_TP2",2.0,2.0)]
records=[];summaries=[]
for rule in ("PULLBACK","BREAKOUT"):
    cohort=signals(rule)
    for name,sm,tm in policies:
        vals=[]
        for i,d in cohort:
            x=outcome(i,d,sm,tm)
            records.append(dict(rule=rule,policy=name,signal_utc=bars[i][0].isoformat(),
                side="LONG" if d==1 else "SHORT",net_R=round(x["net_R"],5),
                exit_type=x["exit"],bars_held=x["bars_held"]))
            vals.append(x["net_R"])
        pos=sum(max(0,x) for x in vals);neg=-sum(min(0,x) for x in vals)
        summaries.append(dict(rule=rule,policy=name,candidate_signals=len(vals),
            mean_net_R=round(statistics.mean(vals),4) if vals else None,
            median_net_R=round(statistics.median(vals),4) if vals else None,
            sum_net_R=round(sum(vals),3),
            win_pct=round(100*sum(x>0 for x in vals)/len(vals),2) if vals else None,
            profit_factor=round(pos/neg,3) if neg else None))
for x in summaries:print(x)
report=dict(source="Twelve Data historical 15m XAU/USD Aug-Oct 2026",
    method="Same fixed entry signals for every exit policy; overlapping hypothetical positions possible; each candidate inspected for at most 16 bars; stop wins within-bar ambiguity; price gap beyond stop included.",
    risk="This is in-sample research, not a portfolio simulation. Volatile or synthetic weekend feed, indicator broker mismatch, costs and orders not verified.",
    assumptions="CME reference schedule used only as a proxy to allow new entries; 0.8 USD per oz round-trip assumed; no 1h trend filter or calendar exclusions.",
    summary=summaries)
(P/"gold_v5_exit_policy_summary.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
with (P/"gold_v5_exit_policy_trades.csv").open("w",newline="",encoding="utf-8") as f:
    fields=["rule","policy","signal_utc","side","net_R","exit_type","bars_held"]
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
