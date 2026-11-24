#!/usr/bin/env python3
"""PBD-INSPIRED HYPOTHESIS V1 — not Tom Vorwald's complete original method.

Single research question: after an upward impulse and a short body-based balance,
does a candle closing BELOW that balance produce a profitable short?
Strictly past-only candles; research only, no order execution or alerts.
All numerical thresholds and 2R exit are our OWN assumptions, not PbD originals.
"""
import argparse, csv, json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

PERIOD=timedelta(minutes=15)
TRAIN_END=datetime(2026,11,1,tzinfo=timezone.utc)
SEEN_END=datetime(2026,11,15,tzinfo=timezone.utc)
VALIDATE_END=datetime(2026,11,24,tzinfo=timezone.utc)

def read(path):
    rows=[]
    with path.open(newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            dt=datetime.fromisoformat(r["timestamp"].replace("Z","+00:00"))
            if dt.tzinfo is None or dt.utcoffset()!=timedelta(0):raise ValueError("timestamps must be UTC")
            o,h,l,c=(float(r[k]) for k in ("open","high","low","close"))
            if min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c):raise ValueError("invalid OHLC")
            if rows and dt<=rows[-1][0]:raise ValueError("nonascending input")
            rows.append((dt,o,h,l,c))
    return rows

def adjacent(rows):
    return all(y[0]-x[0]==PERIOD for x,y in zip(rows,rows[1:]))

def setup(past):
    """Called on exactly 29 fully completed 15m candles: 20 ATR reference, 4 impulse,
    4 balance, 1 downward break. Return signal zone or None, no future data.
    """
    if len(past)!=29 or not adjacent(past):return None
    ref=past[:20]
    impulse=past[20:24]
    balance=past[24:28]
    trigger=past[28]
    tr=[x[2]-x[3] for x in ref]
    atr=sum(tr)/20
    if atr<=0:return None
    if impulse[-1][4]-impulse[0][1]<2.0*atr:return None
    if not all(x[4]>x[1] for x in impulse[:2]):return None
    upper=max(max(x[1],x[4]) for x in balance)
    lower=min(min(x[1],x[4]) for x in balance)
    if upper-lower>1.2*atr or upper<=lower:return None
    if trigger[4]>=lower or trigger[4]>=trigger[1]:return None
    if trigger[4]<lower-1.5*atr:return None  # no huge late chase
    return {"upper":upper,"lower":lower,"atr":atr}

def backtest(rows,cost=0.8):
    if cost<0:raise ValueError("cost must be nonnegative")
    trades=[];rejected=Counter();pending=0;unresolved=[]
    for i in range(28,len(rows)-17):
        if i<pending:continue
        window=rows[i-28:i+1]
        if not adjacent(window):
            rejected["SETUP_DATA_GAP"]+=1;continue
        z=setup(window)
        if z is None:continue
        if rows[i+1][0]-rows[i][0]!=PERIOD:
            rejected["MISSING_ENTRY_BAR"]+=1;continue
        entry=rows[i+1][1]
        stop=z["upper"]+0.2*z["atr"]
        risk=stop-entry
        if risk<=0.0 or risk>4.0*z["atr"]:
            rejected["INVALID_RISK"]+=1;continue
        target=entry-2*risk
        exit_px=None;last=None;reason="TIME_16_BARS"
        gap=False
        for j in range(i+1,i+17):
            if j>i+1 and rows[j][0]-rows[j-1][0]!=PERIOD:
                gap=True;break
            bar=rows[j]
            last=j
            if bar[2]>=stop:  # worst-case stop before target if both touched
                exit_px=max(stop,bar[1]);reason="STOP";break
            if bar[3]<=target:
                exit_px=target;reason="TARGET";break
            exit_px=bar[4]
        if gap:
            unresolved.append({"signal":rows[i][0].isoformat(),"reason":"EXIT_GAP"})
            pending=j+1
            continue
        if last is None:raise RuntimeError("no exit")
        if reason=="TIME_16_BARS" and last==i+16:reason="TIME_16_BARS"
        net_r=(entry-exit_px-cost)/risk
        trades.append({"signal_utc":(rows[i][0]+PERIOD).isoformat(),
                       "entry_utc":rows[i+1][0].isoformat(),
                       "exit_utc":rows[last][0].isoformat(),
                       "entry":round(entry,5),"stop":round(stop,5),"target":round(target,5),
                       "exit_reason":reason,"net_R":round(net_r,6),
                       "zone_upper":round(z["upper"],5),"zone_lower":round(z["lower"],5)})
        pending=last+1
    return trades,dict(rejected),unresolved

def stats(trades):
    r=[x["net_R"] for x in trades]
    gains=sum(max(0,x) for x in r);losses=-sum(min(0,x) for x in r)
    equity=peak=drawdown=0.0
    for x in r:
        equity+=x;peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
    return {"trades":len(r),"wins":sum(x>0 for x in r),
            "net_R":round(equity,4),"average_R":round(equity/len(r),4) if r else None,
            "profit_factor":round(gains/losses,3) if losses else None,
            "max_closed_drawdown_R":round(drawdown,4)}

def split(trades):
    bins={"aug_oct_seen":[],"nov1_14_seen":[],"nov15_23_later":[]}
    for t in trades:
        dt=datetime.fromisoformat(t["signal_utc"])
        if dt<TRAIN_END:bins["aug_oct_seen"].append(t)
        elif dt<SEEN_END:bins["nov1_14_seen"].append(t)
        elif dt<VALIDATE_END:bins["nov15_23_later"].append(t)
    return {name:stats(items) for name,items in bins.items()}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bars15",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--cost",type=float,default=0.8)
    a=p.parse_args()
    rows=read(a.bars15)
    trades,rejections,unresolved=backtest(rows,a.cost)
    results=split(trades)
    later=results["nov15_23_later"]
    if later["trades"]<30:
        decision="INSUFFICIENT_LATER_TRADES"
    elif later["average_R"] is None or later["average_R"]<=0 or later["profit_factor"] is None or later["profit_factor"]<=1.1:
        decision="NO_POSITIVE_LATER_EDGE"
    else:
        decision="PRELIMINARY_ONLY_NEEDS_NEW_FORWARD_OBSERVATION"
    report={"name":"PBD-inspired hypothetical P-failure short, NOT original PbD",
            "decision":decision,"source":"Dukascopy indicative bid 15m XAUUSD",
            "frozen_own_assumptions":{"atr_reference":20,"impulse_bars":4,"min_impulse_ATR":2.0,
                "balance_bars":4,"max_body_range_ATR":1.2,"max_break_extension_ATR":1.5,
                "stop_buffer_ATR":0.2,"target_R":2.0,"max_hold_bars":16,
                "cost_usd_per_oz_roundtrip":a.cost},
            "results":results,"rejections":rejections,"unresolved":unresolved,"trades":trades,
            "caveats":["ONE separately defined research hypothesis, not a reproduction of Tom Vorwald's paid or complete method.",
                       "No futures footprint/DOM, only indicative spot bid OHLC.",
                       "No executable spread, verified broker conditions, intrabar tick path or slippage.",
                       "Both August–October and Nov1–14 were previously inspected for other strategies: not independent.",
                       "Nov15–23 later period has a short horizon and could be inconclusive.",
                       "No automated order placement, Telegram signals or live-money release."]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"decision":decision,"results":results,"rejections":rejections,
                     "unresolved":len(unresolved)},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
