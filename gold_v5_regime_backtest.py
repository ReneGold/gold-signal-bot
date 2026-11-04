#!/usr/bin/env python3
"""Reproducible research backtest for frozen/strong-H1 regime candidates.
Input: two OHLC CSVs (15m and 1h), UTC timestamp/open/high/low/close.
Read-only; NO GitHub forward ledger changes, orders, Telegram or network requests.
"""
import argparse, csv, json
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")

@dataclass(frozen=True)
class Bar:
    t: datetime
    o: float
    h: float
    l: float
    c: float

def load(path, step):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        required={"timestamp","open","high","low","close"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"{path}: expected {sorted(required)}")
        out=[]
        for row in reader:
            t=datetime.fromisoformat(row["timestamp"].replace("Z","+00:00"))
            if t.tzinfo is None: raise ValueError("timestamps must contain timezone")
            t=t.astimezone(timezone.utc)
            o,h,l,c=(float(row[x]) for x in ("open","high","low","close"))
            if min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c):
                raise ValueError(f"invalid OHLC at {t}")
            out.append(Bar(t,o,h,l,c))
    out.sort(key=lambda b:b.t)
    if len(set(x.t for x in out))!=len(out): raise ValueError("duplicate timestamps")
    # Real gold history has weekend and daily trading-session gaps. Keep the gaps
    # rather than filling them with fabricated prices; signal/exit logic handles them.
    if any((b.t-a.t).total_seconds()<step*60 or (b.t-a.t).total_seconds()%(step*60)!=0 for a,b in zip(out,out[1:])):
        raise ValueError("timestamps must progress in whole timeframe steps")
    return out

def ema(vals,n):
    a=2/(n+1); out=[vals[0]]
    for v in vals[1:]:out.append(a*v+(1-a)*out[-1])
    return out

def atr(bars):
    tr=[bars[0].h-bars[0].l]
    for i in range(1,len(bars)):
        b,p=bars[i],bars[i-1]
        tr.append(max(b.h-b.l,abs(b.h-p.c),abs(b.l-p.c)))
    out=[None]*len(bars)
    if len(bars)<14:return out
    out[13]=sum(tr[:14])/14
    for i in range(14,len(bars)):out[i]=(out[i-1]*13+tr[i])/14
    return out

def gold_session(when):
    loc=when.astimezone(CT); d=loc.weekday(); m=loc.hour*60+loc.minute
    return not (d==5 or (d==4 and m>=960) or (d==6 and m<1020)
                or (d<4 and 960<=m<1020))

def simulate(b15,b60,market,regime,half_spread=0.0,slippage=0.0,cost=0.8):
    """Stop-first when SL and TP both touch same candle; single position at a time.
    Risk distance: 1.5 ATR; target: 2R; max hold: 16 complete entry candles.
    cost is additional USD-price-units round trip; zero by default for BTC.
    Signal bar close -> next bar open; no intrabar lookahead.
    """
    if len(b15)<100 or len(b60)<65:return []
    e20=ema([x.c for x in b15],20);e50=ema([x.c for x in b15],50);a15=atr(b15)
    h20=ema([x.c for x in b60],20);h50=ema([x.c for x in b60],50);a60=atr(b60)
    hcloses=[x.t+timedelta(hours=1) for x in b60]
    trades=[]
    next_free=0
    for i in range(80,len(b15)-1):
        if i<next_free or a15[i] is None:continue
        candle,previous=b15[i],b15[i-1]
        decision=candle.t+timedelta(minutes=15)
        if candle.t-previous.t!=timedelta(minutes=15):continue
        if b15[i+1].t!=decision:continue  # no invented entry after a session/data gap
        if market=="gold" and not gold_session(decision):continue
        j=bisect_right(hcloses,decision)-1
        if j<55 or not a60[j] or a60[j]<=0:continue
        if decision-hcloses[j]>timedelta(hours=1):continue # reject stale H1 context
        strength=abs(h20[j]-h50[j])/a60[j]
        if regime=="frozen":
            if strength>=0.5:continue
        else:
            if strength<0.5:continue
        direction=-1 if e20[i]<e50[i] and e20[i]<e20[i-1] else (1 if e20[i]>e50[i] and e20[i]>e20[i-1] else 0)
        if not direction:continue
        if regime=="strong" and direction*(h20[j]-h50[j])<=0:continue
        touch=previous.h>=e20[i-1] if direction==-1 else previous.l<=e20[i-1]
        confirm=(candle.c<e20[i] and candle.c<previous.l and candle.c<candle.o) if direction==-1 else (candle.c>e20[i] and candle.c>previous.h and candle.c>candle.o)
        if not (touch and confirm):continue
        k=i+1
        risk=1.5*a15[i]
        # spread/slippage penalizes entry in direction of trade.
        entry=b15[k].o+direction*(half_spread+slippage)
        stop=entry-direction*risk
        target=entry+direction*2*risk
        exit_price=None;reason=None;last=None
        gap_found=False
        for z in range(k,min(k+16,len(b15))):
            if z>k and b15[z].t-b15[z-1].t!=timedelta(minutes=15):
                gap_found=True;break
            b=b15[z]
            hit_stop=(b.l<=stop if direction==1 else b.h>=stop)
            hit_tp=(b.h>=target if direction==1 else b.l<=target)
            if hit_stop:
                exit_price=min(b.o,stop) if direction==1 else max(b.o,stop)
                reason="STOP";last=z;break
            if hit_tp:
                exit_price=target;reason="TP";last=z;break
        if gap_found:
            # Outcome cannot safely be modelled across missing/session candles.
            # Stop this market comparison instead of silently cherry-picking trades.
            raise ValueError("Price data gap during open simulated position; no defensible fill model")
        if reason is None:
            if k+15>=len(b15):break
            last=k+15
            exit_price=b15[last].c;reason="TIME"
        # half-spread/slippage AGAIN at exit; cost is an additional fixed price-unit allowance.
        net_r=(direction*(exit_price-entry)-(half_spread+slippage)-cost)/risk
        trades.append({"signal_utc":candle.t.isoformat(),"entry_utc":b15[k].t.isoformat(),
                       "exit_utc":b15[last].t.isoformat(),"side":"LONG" if direction==1 else "SHORT",
                       "regime":regime,"entry":round(entry,6),"stop":round(stop,6),
                       "target":round(target,6),"exit":round(exit_price,6),
                       "reason":reason,"R":round(net_r,6),"h1_strength":round(strength,4)})
        next_free=last+1
    return trades

def summarize(trades):
    if not trades:return {"n":0,"net_R":0,"win_rate":None,"mean_R":None,"max_drawdown_R":None}
    values=[t["R"] for t in trades];balance=peak=drawdown=0
    for v in values:
        balance+=v;peak=max(peak,balance);drawdown=max(drawdown,peak-balance)
    return {"n":len(trades),"net_R":round(sum(values),4),
            "win_rate":round(sum(v>0 for v in values)/len(values),4),
            "mean_R":round(sum(values)/len(values),4),
            "max_drawdown_R":round(drawdown,4)}

def run(b15,b60,market,half_spread,slippage,cost):
    result={"market":market,"assumptions":{"spread_half_each_side":half_spread,
        "slippage_each_side":slippage,"extra_round_trip_price_cost":cost,
        "R":"1.5x15m ATR","TP":"2R","max_hold_bars":16,
        "intrabar_same_bar_hit":"STOP_FIRST","position_limit":1},
        "limitations":["Historical research only; no live signal, broker execution or validated edge.",
            "No leverage, commissions charged as percentage, funding, borrow costs or broker tick-size model.",
            "No risk-gate daily stops/news-window veto; chart regime comparison only.",
            "No data-feed reconciliation with TradingView; no out-of-sample validation."]}
    for regime in ("frozen","strong"):
        trades=simulate(b15,b60,market,regime,half_spread,slippage,cost)
        result[regime]={"summary":summarize(trades),"trades":trades}
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--market",required=True,choices=("gold","bitcoin"))
    p.add_argument("--bars15",type=Path,required=True)
    p.add_argument("--bars1h",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--half-spread",type=float,default=0.0)
    p.add_argument("--slippage",type=float,default=0.0)
    p.add_argument("--cost",type=float,default=0.0)
    a=p.parse_args()
    if min(a.half_spread,a.slippage,a.cost)<0: p.error("costs must be nonnegative")
    bars15,bars60=load(a.bars15,15),load(a.bars1h,60)
    if not bars15 or not bars60:p.error("Missing data")
    result=run(bars15,bars60,a.market,a.half_spread,a.slippage,a.cost)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k]["summary"] for k in ("frozen","strong")},indent=2))
if __name__=="__main__":main()
