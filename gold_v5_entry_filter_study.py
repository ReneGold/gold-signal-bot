#!/usr/bin/env python3
"""Research-only: pre-registered Gold V5 entry filters, chronological holdout.
No Telegram, no real trades, no live strategy change. Note: months used in prior
research are NOT genuinely pristine out-of-sample; this is only a chronological check.
"""
import csv,json,statistics
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import gold_v5_session_ab as b
P=Path(__file__).resolve().parent/"gold_data_audit"
bars=b.bars
CUTOFF=datetime(2026,10,1,tzinfo=timezone.utc)
# Exactly three predefined conditions including a no-filter control.
POLICIES=("BASE","EMA_SPREAD_ATR_0_5","EMA_SPREAD_ATR_0_5_AND_MOMENTUM")
def accepts(i,d,p):
    strength=abs(b.ef[i]-b.es[i])/b.atr[i]
    if p=="BASE":return True
    if strength<0.5:return False
    if p=="EMA_SPREAD_ATR_0_5":return True
    if d==1:return bars[i][4]>bars[i-1][4] and b.ef[i]>b.ef[i-1]
    return bars[i][4]<bars[i-1][4] and b.ef[i]<b.ef[i-1]
def replay(rule,policy):
    records=[];next_i=60
    for i in range(60,len(bars)-17):
        if i<next_i:continue
        d=b.candidate(i,rule)
        if not d:continue
        if not b.ref_open(bars[i][0]+timedelta(minutes=15)) or not b.ref_open(bars[i+1][0]):continue
        if not accepts(i,d,policy):continue
        entry=bars[i+1][1];risk=1.5*b.atr[i]
        stop=entry-d*risk;target=entry+d*2*risk;end=i+16
        exitprice=bars[end][4];reason="TIME"
        for j in range(i+1,end+1):
            bar=bars[j]
            stop_hit=(bar[3]<=stop if d==1 else bar[2]>=stop)
            tp_hit=(bar[2]>=target if d==1 else bar[3]<=target)
            if stop_hit:
                exitprice=(min(stop,bar[1]) if d==1 else max(stop,bar[1]));end=j;reason="STOP";break
            if tp_hit:exitprice=target;end=j;reason="TP";break
        r=(d*(exitprice-entry)-0.8)/risk
        records.append(dict(rule=rule,policy=policy,signal_utc=bars[i][0].isoformat(),
          entry_utc=bars[i+1][0].isoformat(),exit_utc=bars[end][0].isoformat(),side="LONG" if d==1 else "SHORT",
          net_R=round(r,5),exit_reason=reason,partition="AUG_SEP_RESEARCH" if bars[i][0]<CUTOFF else "OCT_CHRONOLOGICAL_CHECK"))
        next_i=end+1
    return records
def stats(rows):
    gain=sum(max(0,r["net_R"]) for r in rows);loss=-sum(min(0,r["net_R"]) for r in rows)
    eq=peak=dd=0
    for r in rows:eq+=r["net_R"];peak=max(peak,eq);dd=max(dd,peak-eq)
    return dict(trades=len(rows),net_R=round(eq,3),win_pct=round(100*sum(r["net_R"]>0 for r in rows)/len(rows),2) if rows else None,
       profit_factor=round(gain/loss,3) if loss else None,max_closed_drawdown_R=round(dd,3))
alltrades=[];report=[]
for rule in ("PULLBACK","BREAKOUT"):
 for policy in POLICIES:
    rows=replay(rule,policy);alltrades+=rows
    parts={v:stats([x for x in rows if x["partition"]==v]) for v in ("AUG_SEP_RESEARCH","OCT_CHRONOLOGICAL_CHECK")}
    report.append(dict(rule=rule,policy=policy,overall=stats(rows),periods=parts))
    print(rule,policy,"Aug-Sep",parts["AUG_SEP_RESEARCH"],"Oct",parts["OCT_CHRONOLOGICAL_CHECK"])
with (P/"gold_v5_entry_filter_trades.csv").open("w",newline="",encoding="utf-8") as f:
 w=csv.DictWriter(f,fieldnames=["rule","policy","signal_utc","entry_utc","exit_utc","side","net_R","exit_reason","partition"]);w.writeheader();w.writerows(alltrades)
meta=dict(title="Gold V5 fixed entry filters chronological comparison",data="Twelve Data 15m XAU/USD August-October 2026",
   caveats=["October has been studied in earlier development: not truly unseen or independent.",
   "No 1h trend filter; no broker quotes/executions; CME hours are merely reference.",
   "Indicators use continuous original candles including weekends and closed times.",
   "Only three prespecified variants; no parameter optimization; all backtests exploratory.",
   "0.8 USD/oz assumed roundtrip, 1.5 ATR stop, TP2R, 16bar time stop, conservative same-bar stop priority."],results=report)
(P/"gold_v5_entry_filter_summary.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
