#!/usr/bin/env python3
"""Gold research only: fully closed bars, no Telegram, no live orders.

Compares two NEW candidate rules on the same recent Twelve Data feed.
Signals are determined at a candle close and entered only at next candle open.
One non-overlapping position at a time per strategy. Stops win same-bar ambiguity.
Results are research, not broker-executable prices or out-of-sample proof.
"""
import csv,json,os
from datetime import timedelta,datetime,timezone
from pathlib import Path
import gold_signal_bot as bot

P=Path(__file__).resolve().parent
c=bot.candles("15min",320)
if len(c)<100:raise RuntimeError("Insufficient complete 15-min candles")
ef,es,atr=bot.indicators(c)
rows=[]
cost=float(os.getenv("GOLD_RESEARCH_ROUNDTRIP_USD_PER_OZ","0.8"))
if cost<0:raise ValueError("Cost must be nonnegative")
def direction(i):
    return -1 if ef[i]<es[i] and ef[i]<ef[i-1] else 1 if ef[i]>es[i] and ef[i]>ef[i-1] else 0

def setup(i,kind):
    if atr[i] is None or atr[i]<=0:return 0
    d=direction(i)
    if not d:return 0
    # Trend continuation: prior candle touched fast EMA, signal closes back in trend
    if kind=="PULLBACK":
        touched=(c[i-1].h>=ef[i-1] if d==-1 else c[i-1].l<=ef[i-1])
        confirmed=(c[i].c<ef[i] and c[i].c<c[i-1].l and c[i].c<c[i].o) if d==-1 else (c[i].c>ef[i] and c[i].c>c[i-1].h and c[i].c>c[i].o)
        return d if touched and confirmed else 0
    if kind=="BREAKOUT":
        prior_low=min(x.l for x in c[i-8:i])
        prior_high=max(x.h for x in c[i-8:i])
        crossed=(c[i].c<prior_low-0.1*atr[i] and c[i-1].c>=min(x.l for x in c[i-9:i-1])) if d==-1 else (c[i].c>prior_high+0.1*atr[i] and c[i-1].c<=max(x.h for x in c[i-9:i-1]))
        body=abs(c[i].c-c[i].o)>=0.35*atr[i]
        return d if crossed and body else 0
    raise ValueError(kind)

def simulate(kind):
    records=[];next_allowed=85
    for i in range(85,len(c)-2):
        if i<next_allowed:continue
        d=setup(i,kind)
        if not d:continue
        entry=c[i+1].o
        risk=max(1.5*atr[i],0.01)
        stop=entry-d*risk
        target=entry+d*2*risk
        status="TIME";exitprice=None;exitidx=None
        # 16 x 15min maximum hold; never examine bars beyond current closed data
        for j in range(i+1,min(len(c),i+17)):
            bar=c[j]
            hit_stop=(bar.l<=stop if d==1 else bar.h>=stop)
            hit_tp=(bar.h>=target if d==1 else bar.l<=target)
            if hit_stop:
                status="STOP";exitprice=min(bar.o,stop) if d==1 else max(bar.o,stop);exitidx=j;break
            if hit_tp:
                status="TP";exitprice=target;exitidx=j;break
        if exitidx is None:
            if i+16>=len(c):continue # incomplete outcome: exclude, never label closed
            exitidx=i+16;exitprice=c[exitidx].c
        net_r=(d*(exitprice-entry)-cost)/risk
        records.append(dict(strategy=kind,signal_utc=c[i].t.isoformat(),entry_utc=c[i+1].t.isoformat(),
            exit_utc=c[exitidx].t.isoformat(),side="LONG" if d==1 else "SHORT",
            entry=round(entry,5),stop=round(stop,5),target=round(target,5),exit=round(exitprice,5),
            outcome=status,net_R=round(net_r,5),cost_per_oz=cost))
        next_allowed=exitidx+1
    return records

for kind in ("PULLBACK","BREAKOUT"):rows.extend(simulate(kind))
fieldnames=["strategy","signal_utc","entry_utc","exit_utc","side","entry","stop","target","exit","outcome","net_R","cost_per_oz"]
with (P/"gold_research_candidates.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=fieldnames);w.writeheader();w.writerows(rows)
summary=[]
for kind in ("PULLBACK","BREAKOUT"):
    a=[r for r in rows if r["strategy"]==kind]
    gains=sum(max(0,r["net_R"]) for r in a)
    losses=-sum(min(0,r["net_R"]) for r in a)
    equity=peak=dd=0
    for r in a:
        equity+=r["net_R"];peak=max(peak,equity);dd=max(dd,peak-equity)
    summary.append(dict(strategy=kind,trades=len(a),
        net_R=round(equity,3),win_rate=round(100*sum(r["net_R"]>0 for r in a)/len(a),1) if a else None,
        profit_factor=round(gains/losses,3) if losses else None,max_closed_drawdown_R=round(dd,3)))
result=dict(source="Twelve Data XAU/USD 15min",sample_start_utc=c[0].t.isoformat(),sample_end_utc=c[-1].t.isoformat(),
    config=dict(roundtrip_cost_usd_per_oz=cost,atr_stop=1.5,profit_target_R=2,max_hold_bars=16),
    limitations="Exploratory same-sample, limited feed, non-broker prices, no spread variability, no calendar, no hourly filter, no forward validation; not a recommendation to trade.",summary=summary)
(P/"gold_research_summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2))
