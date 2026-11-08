#!/usr/bin/env python3
"""Historical, non-executable Gold V5 SIMPLE research replay.

One trade at a time, next completed candle's open as indicative entry, stop-first.
No network, Telegram, broker, GitHub ledger or operational trading changes.
"""
import argparse
import csv
import json
from bisect import bisect_right
from datetime import datetime, timedelta
from pathlib import Path
from gold_v5_simple_signal import Bar, decide

def load(path):
    bars=[]
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            t=datetime.fromisoformat(row["timestamp"].replace("Z","+00:00"))
            bars.append(Bar(t, *(float(row[k]) for k in ("open","high","low","close"))))
    return bars

def backtest(b15,b60, roundtrip_cost=0.8, adverse_each_side=0.0):
    if roundtrip_cost<0 or adverse_each_side<0:raise ValueError("Costs cannot be negative")
    if len(b15)<200 or len(b60)<65:raise ValueError("Need more history and 1h warmup")
    hourly_closed=[b.start+timedelta(hours=1) for b in b60]
    results=[]
    reason_counts={}
    unresolved=0
    next_free=80
    for i in range(80,len(b15)-1):
        if i<next_free:continue
        decision=b15[i].start+timedelta(minutes=15)
        j=bisect_right(hourly_closed,decision)-1
        if j<59:continue
        if b15[i+1].start!=decision:continue
        try:
            candidate=decide(b15[max(0,i-79):i+1],b60[max(0,j-79):j+1],decision)
        except ValueError:
            reason_counts["GAP_OR_INVALID_OHLC"]=reason_counts.get("GAP_OR_INVALID_OHLC",0)+1
            continue
        if candidate["status"]!="CANDIDATE_PAPER_ONLY":
            why=candidate["reason"]
            reason_counts[why]=reason_counts.get(why,0)+1
            continue
        direction=1 if candidate["side"]=="LONG" else -1
        risk=candidate["stop_distance"]
        entry=b15[i+1].open+direction*adverse_each_side
        sl=entry-direction*risk
        tp=entry+direction*2*risk
        exit_px=None;reason="TIME";exit_i=None
        interrupted=False
        for k in range(i+1,min(i+17,len(b15))):
            if k>i+1 and b15[k].start-b15[k-1].start!=timedelta(minutes=15):
                interrupted=True;break
            bar=b15[k]
            hit_sl=(bar.low<=sl if direction==1 else bar.high>=sl)
            hit_tp=(bar.high>=tp if direction==1 else bar.low<=tp)
            if hit_sl:
                exit_px=min(sl,bar.open) if direction==1 else max(sl,bar.open)
                exit_i=k;reason="STOP";break
            if hit_tp:
                exit_px=tp;exit_i=k;reason="TP";break
            exit_px=bar.close;exit_i=k
        if interrupted:
            unresolved+=1
            next_free=k+1
            continue
        if exit_i is None:continue
        if exit_i==len(b15)-1 and reason=="TIME":break  # incomplete 16-bar hold
        profit_r=(direction*(exit_px-entry)-adverse_each_side-roundtrip_cost)/risk
        results.append({"signal_utc":decision.isoformat(),"side":candidate["side"],
                        "entry_utc":b15[i+1].start.isoformat(),"entry":round(entry,5),
                        "stop":round(sl,5),"target":round(tp,5),
                        "exit_utc":b15[exit_i].start.isoformat(),"exit_reason":reason,
                        "net_R":round(profit_r,6)})
        next_free=exit_i+1
    gains=sum(max(0,r["net_R"]) for r in results)
    losses=-sum(min(0,r["net_R"]) for r in results)
    equity=peak=dd=0.0
    for t in results:
        equity+=t["net_R"];peak=max(peak,equity);dd=max(dd,peak-equity)
    return {"source":"External Dukascopy bid OHLC (not PU Prime executable quotes)",
            "assumptions":{"roundtrip_extra_price_cost":roundtrip_cost,"adverse_entry_and_exit_each":adverse_each_side,
                           "stop":"1.5 ATR 15m","target":"2R","max_hold_bars":16,
                           "same_bar_stop_and_target":"STOP_FIRST","one_open_trade":True},
            "summary":{"closed":len(results),"wins":sum(t["net_R"]>0 for t in results),
                       "net_R":round(equity,4),
                       "mean_R":round(equity/len(results),4) if results else None,
                       "max_drawdown_R":round(dd,4),"profit_factor":round(gains/losses,3) if losses else None,
                       "unresolved_gap_trades":unresolved},
            "rejections":reason_counts,
            "limitations":["In-sample exploratory replay, not out-of-sample validation.",
                           "Missing candles, daily gaps and broker calendar are unresolved execution risks.",
                           "Illustrative fills and costs; no bid/ask spread, slippage distribution or broker execution.",
                           "No dynamic lot size, live daily risk stop, news blackout or broker margin checks.",
                           "A positive backtest does not establish trading profitability."],
            "trades":results}

def main():
    p=argparse.ArgumentParser();p.add_argument("--bars15",required=True,type=Path)
    p.add_argument("--bars1h",required=True,type=Path);p.add_argument("--out",required=True,type=Path)
    p.add_argument("--roundtrip-cost",type=float,default=0.8)
    p.add_argument("--adverse-each-side",type=float,default=0.0)
    a=p.parse_args()
    result=backtest(load(a.bars15),load(a.bars1h),a.roundtrip_cost,a.adverse_each_side)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"summary":result["summary"],"rejections":result["rejections"]},indent=2))

if __name__=="__main__":main()
