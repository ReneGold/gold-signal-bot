#!/usr/bin/env python3
"""Compare exit allocations on the SAME completed B/C entry cohorts.
Research only. Independently simulated exits can overlap with later baseline entries;
not a portfolio backtest, and no 5m/news/broker fill model. No orders.
"""
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from gold_exit_planner import Plan,new_position,on_bar
from gold_v4_paired_exit_backtest import rows,metrics,COST_USD_OZ,DATA,TRADES

P=Path(__file__).resolve().parent
OUTPUT=P/"gold_v4_exit_allocation_trades.csv"
SUMMARY=P/"gold_v4_exit_allocation_summary.csv"
ALLOCATIONS={
    "30_30_40":((0.75,1.5,2.25),(.30,.30,.40)),
    "20_30_50":((0.75,1.5,2.25),(.20,.30,.50)),
    "20_0_80":((0.75,2.25,2.25),(.20,0,.80)),
}
def simulate_alloc(trade,candles,index,allocation):
    direction=1 if trade["side"]=="LONG" else -1
    entry=float(trade["entry"]);sl=float(trade["sl"])
    if allocation=="20_0_80":
        # Two targets: TP1 20%, TP3 80%; stop -> breakeven after TP1.
        risk=(entry-sl)*direction
        if risk<=0:raise ValueError("Invalid trade risk")
        targets=[entry+direction*0.75*risk,entry+direction*2.25*risk]
        left=1.0;gain=0.0;stage=0;events=[]
        for b in candles[index[trade["opened"]]:]:
            o,h,l=(float(b[x]) for x in ("open","high","low"))
            protect=sl if stage==0 else entry
            stopped=l<=protect if direction==1 else h>=protect
            if stopped:
                gap=o<=protect if direction==1 else o>=protect
                px=o if gap else protect
                gain+=left*(px-entry)*direction/risk
                return gain-COST_USD_OZ/risk,b["datetime_utc"],",".join(events+["STOP"])
            if stage==0 and (h>=targets[0] if direction==1 else l<=targets[0]):
                gain+=.2*.75;left=.8;stage=1;events.append("TP1")
            if h>=targets[1] if direction==1 else l<=targets[1]:
                gain+=left*2.25
                return gain-COST_USD_OZ/risk,b["datetime_utc"],",".join(events+["TP3"])
        return None,None,"OPEN_AT_END"
    targets,parts=ALLOCATIONS[allocation]
    plan=Plan(entry,sl,direction,target_r=targets,portions=parts)
    state=new_position(plan)
    for b in candles[index[trade["opened"]:]:
        on_bar(plan,state,open_price=float(b["open"]),high=float(b["high"]),
               low=float(b["low"]),close=float(b["close"]))
        if state["closed"]:
            return state["gross_R"]-COST_USD_OZ/plan.risk,b["datetime_utc"],",".join(state["events"])
    return None,None,"OPEN_AT_END"

def run():
    candles=[r for r in rows(DATA) if datetime.fromisoformat(r["datetime_utc"]).weekday()<5]
    index={r["datetime_utc"]:i for i,r in enumerate(candles)}
    entries=[r for r in rows(TRADES) if r["variant"] in ("B_HTF_MOMENTUM","C_TREND_STRENGTH")]
    if len(candles)<4000 or not entries:raise RuntimeError("Historical inputs missing")
    output=[];groups=defaultdict(list)
    for trade in entries:
        key=trade["variant"]
        base={"variant":key,"allocation":"ORIGINAL","opened":trade["opened"],
              "closed":trade["closed"],"net_R":float(trade["net_R"]),"events":"BASELINE"}
        output.append(base);groups[(key,"ORIGINAL")].append(base)
        for alloc in ALLOCATIONS:
            result,closed,events=simulate_alloc(trade,candles,index,alloc)
            if result is None:continue
            r={"variant":key,"allocation":alloc,"opened":trade["opened"],
               "closed":closed,"net_R":round(result,6),"events":events}
            output.append(r);groups[(key,alloc)].append(r)
    with OUTPUT.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["variant","allocation","opened","closed","net_R","events"]);w.writeheader();w.writerows(output)
    summaries=[]
    for (variant,alloc),ts in sorted(groups.items()):
        ordered=sorted(ts,key=lambda r:r["closed"])
        summaries.append({"variant":variant,"allocation":alloc,**metrics([r["net_R"] for r in ordered])})
    with SUMMARY.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
    for r in summaries:print(r,flush=True)
    print("Exploratory in-sample, same baseline entry cohorts, exits can overlap later entries. No selection from these results without future out-of-sample validation.")
if __name__=="__main__":run()
