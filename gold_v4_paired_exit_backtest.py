#!/usr/bin/env python3
"""Paired B/C research backtest: original exits vs staged V4 Exit Planner.
Same historical entry signals, 15m XAUUSD OHLC, simulated 0.50 USD/oz cost.
NOT full V4: 5m Entry Timer, verified historical news calendar, FX/contract
risk and Time Machine validation are NOT applied. No trading/orders.
Entry cohorts come from baseline B/C strategy and thus are not a newly
generated non-overlapping V4 trade portfolio.
"""
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from gold_exit_planner import Plan,new_position,on_bar

P=Path(__file__).resolve().parent
DATA=P/"gold_historical_data"/"xauusd_15min_20260801_20261024.csv"
TRADES=P/"gold_market_phase_score65_trades.csv"
OUTPUT=P/"gold_v4_paired_exit_trades.csv"
SUMMARY=P/"gold_v4_paired_exit_summary.csv"
COST_USD_OZ=0.50

def rows(path):
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def make_bars(candles):
    return {r["datetime_utc"]:r for r in candles}

def simulate(trade,candles,index):
    side=1 if trade["side"]=="LONG" else -1
    entry=float(trade["entry"]);sl=float(trade["sl"])
    plan=Plan(entry,sl,side)
    state=new_position(plan)
    start=trade["opened"];end=trade["closed"]
    # The baseline trades were constructed on next 15m open. Iterate through
    # baseline position's own lifetime, and beyond until V4 exit if necessary.
    if start not in index:raise ValueError("Missing historical entry bar: "+start)
    start_i=index[start]
    for bar in candles[start_i:]:
        on_bar(plan,state,open_price=float(bar["open"]),high=float(bar["high"]),
               low=float(bar["low"]),close=float(bar["close"]))
        if state["closed"]:
            return state["gross_R"]-COST_USD_OZ/plan.risk,bar["datetime_utc"],",".join(state["events"])
    return None,None,"OPEN_AT_END"

def metrics(values):
    profit=sum(x for x in values if x>0)
    loss=-sum(x for x in values if x<0)
    equity=peak=dd=0.
    for x in values:
        equity+=x;peak=max(peak,equity);dd=max(dd,peak-equity)
    return {"trades":len(values),"sum_R":round(sum(values),4),
       "win_pct":round(100*sum(x>0 for x in values)/len(values),2) if values else 0,
       "profit_factor":round(profit/loss,4) if loss else None,
       "max_closed_drawdown_R":round(dd,4)}

def run():
    candles=[r for r in rows(DATA) if datetime.fromisoformat(r["datetime_utc"]).weekday()<5]
    index={r["datetime_utc"]:i for i,r in enumerate(candles)}
    history=rows(TRADES)
    if len(candles)<4000:raise RuntimeError("Historical 15min data incomplete")
    selected=[t for t in history if t["variant"] in ("B_HTF_MOMENTUM","C_TREND_STRENGTH")]
    if not selected:raise RuntimeError("No completed historical B/C entries")
    output=[];grouped=defaultdict(list)
    for t in selected:
        result,exit_t,events=simulate(t,candles,index)
        if result is None:continue
        base=float(t["net_R"])
        row={"variant":t["variant"],"opened":t["opened"],"baseline_closed":t["closed"],
             "v4_closed":exit_t,"baseline_net_R":round(base,5),"staged_exit_net_R":round(result,5),
             "difference_R":round(result-base,5),"v4_events":events}
        output.append(row);grouped[t["variant"]].append(row)
    if not output:raise RuntimeError("No fully replayed exit trades")
    with OUTPUT.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(output[0]));w.writeheader();w.writerows(output)
    summary=[]
    for variant,group in grouped.items():
        for tag,key in (("ORIGINAL_EXIT","baseline_net_R"),("STAGED_V4_EXIT_ONLY","staged_exit_net_R")):
            ordered=sorted(group,key=lambda r:r["baseline_closed"] if tag=="ORIGINAL_EXIT" else r["v4_closed"])
            summary.append(dict(variant=variant,method=tag,**metrics([r[key] for r in ordered])))
    with SUMMARY.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    print("PAIRED EXIT COMPARISON (same entries, not full V4):")
    for item in summary:print(item)
    print("LIMITATIONS: B/C entries based on Aug-Oct 2026 exploratory in-sample rules; V4 has different exits,")
    print("therefore overlapping trades are possible; no 5-minute entry confirmations, historical calendar,")
    print("broker spread, FX/currency, slippage or lot sizing. Synthetic 0.50 USD/oz cost only.")
if __name__=="__main__":run()
