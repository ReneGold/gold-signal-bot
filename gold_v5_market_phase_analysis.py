#!/usr/bin/env python3
"""Gold V5 research: describe performance by PRIOR CLOSED 1-hour market phase.
Uses identical previously simulated entries/exits; does not alter trades or Telegram.
CME hours are a proxy, and this is in-sample descriptive analysis, not optimization.
"""
import bisect,csv,json
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
P=Path(__file__).resolve().parent/"gold_data_audit"
with (P/"gold_1h_2026_aug_oct.csv").open(newline="",encoding="utf-8") as f:
    hourly=list(csv.DictReader(f))
with (P/"gold_v5_session_ab_trades.csv").open(newline="",encoding="utf-8") as f:
    trades=[r for r in csv.DictReader(f) if r["session_filter"]=="CME_REFERENCE_ONLY"]
times=[datetime.fromisoformat(r["utc"]) for r in hourly]
closes=[float(r["close"]) for r in hourly]
highs=[float(r["high"]) for r in hourly];lows=[float(r["low"]) for r in hourly]
def ema(vals,n):
    a=2/(n+1);out=[vals[0]]
    for v in vals[1:]:out.append(out[-1]*(1-a)+v*a)
    return out
fast=ema(closes,20);slow=ema(closes,50)
tr=[highs[0]-lows[0]]
for i in range(1,len(times)):
    tr.append(max(highs[i]-lows[i],abs(highs[i]-closes[i-1]),abs(lows[i]-closes[i-1])))
atr=[None]*len(times)
atr[13]=sum(tr[:14])/14
for i in range(14,len(times)):atr[i]=(atr[i-1]*13+tr[i])/14
def phase(i):
    if i<55 or not atr[i] or atr[i]<=0:return "WARMUP"
    strength=abs(fast[i]-slow[i])/atr[i]
    if strength<0.5:return "RANGE_OR_WEAK"
    if fast[i]>slow[i] and fast[i]>fast[i-1]:return "UP_TREND"
    if fast[i]<slow[i] and fast[i]<fast[i-1]:return "DOWN_TREND"
    return "TRANSITION"
groups=defaultdict(list);rows=[];unmatched=0
for r in trades:
    entry=datetime.fromisoformat(r["entry_utc"])
    # Candle timestamp is opening timestamp, so at entry only 1h candles that
    # closed <= entry are admissible (no future-data lookahead).
    i=bisect.bisect_right(times,entry-timedelta(hours=1))-1
    if i<0:unmatched+=1;continue
    ph=phase(i)
    side=r["side"]
    alignment="ALIGNED" if (ph=="UP_TREND" and side=="LONG") or (ph=="DOWN_TREND" and side=="SHORT") else "OTHER"
    v={**r,"hourly_phase":ph,"trend_alignment":alignment,"net_R":float(r["net_R"])}
    rows.append(v)
    for key in [(r["rule"],"ALL"),(r["rule"],ph),(r["rule"],ph,side),(r["rule"],alignment)]:
        groups[key].append(v)
def stats(a):
    gains=sum(max(0,v["net_R"]) for v in a)
    losses=-sum(min(0,v["net_R"]) for v in a)
    return dict(trades=len(a),sum_R=round(sum(v["net_R"] for v in a),4),
        avg_R=round(sum(v["net_R"] for v in a)/len(a),4) if a else None,
        win_pct=round(100*sum(v["net_R"]>0 for v in a)/len(a),2) if a else None,
        profit_factor=round(gains/losses,3) if losses else None)
report=dict(title="Gold V5 1H phase attribution of pre-existing trades",
   data="XAU/USD 15m and 1h historical Aug-Oct 2026, Twelve Data",
   limitations=["CME reference schedule is not verified spot broker session.",
     "1h bar timestamps assumed to mark candle opening; use only bars closed by entry.",
     "All history previously studied: NOT independent out-of-sample.",
     "Descriptions of subsets are not investable strategies or portfolios: removing trades can change future entries.",
     "1h EMA 20/50 and ATR 14 thresholds are exploratory; no order execution or actual spread verified."],
   included_trades=len(rows),unmatched=unmatched,
   groups=[dict(group="|".join(key),**stats(vals)) for key,vals in sorted(groups.items())])
with (P/"gold_v5_market_phase_summary.json").open("w",encoding="utf-8") as f:json.dump(report,f,indent=2,ensure_ascii=False)
with (P/"gold_v5_market_phase_trades.csv").open("w",newline="",encoding="utf-8") as f:
    fields=["rule","session_filter","signal_utc","entry_utc","exit_utc","side","entry","exit","net_R","exit_reason","hourly_phase","trend_alignment"]
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
for g in report["groups"]:
    if g["group"].count("|")<=1:print(g)
print("No live bot/Telegram changes; research report saved.")
