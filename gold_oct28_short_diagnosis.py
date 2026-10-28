#!/usr/bin/env python3
"""Read-only Gold Short diagnosis. No Telegram, orders, or changes to signal thresholds."""
import contextlib,csv,io,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
import gold_signal_bot as bot

P=Path(__file__).resolve().parent
bot.send=lambda *args,**kwargs:None
bot.MIN_SCORE=0
bot.OBSERVE_SCORE=101
c=bot.candles("15min",320)
h=bot.candles("1h",220)
ef,es,atr=bot.indicators(c)
start=datetime(2026,10,27,23,0,tzinfo=timezone.utc)
end=datetime(2026,10,28,7,0,tzinfo=timezone.utc)
rows=[]
for i in range(85,len(c)):
    bar=c[i];closed=bar.t+timedelta(minutes=15)
    if not start<=closed<=end:continue
    hh=[z for z in h if z.t+timedelta(hours=1)<=closed]
    if len(hh)<40 or atr[i] is None:continue
    with contextlib.redirect_stdout(io.StringIO()):
        sig=bot.signal(c[:i+1],ef[:i+1],es[:i+1],atr[:i+1],hh,i)
    try:
        bull,bear,_,_=bot.htf_context_at(hh,bar.t)
    except Exception:
        bull,bear=False,False
    momentum=ef[i]<ef[i-1] and bar.c<c[i-1].c
    strength=abs(ef[i]-es[i])/atr[i] if atr[i] else 0
    cand_side=("LONG" if sig[0]==1 else "SHORT") if sig else "NONE"
    score=sig[8] if sig else ""
    b=bool(sig and sig[0]==-1 and score>=65 and bear and momentum)
    cc=b and strength>=0.50
    reasons=[]
    if not sig:reasons.append("NO_BASE_PATTERN_OR_OTHER_BASE_GATE")
    elif sig[0]!=-1:reasons.append("BASE_CANDIDATE_IS_LONG")
    else:
        if score<65:reasons.append("SCORE_BELOW_65")
        if not bear:reasons.append("NO_CONFIRMED_1H_SHORT_TREND")
        if not momentum:reasons.append("15M_SHORT_MOMENTUM_MISSING")
        if strength<0.50:reasons.append("EMA_STRENGTH_BELOW_0_50")
    if not reasons:reasons=["C_ELIGIBLE_RESEARCH_ONLY"]
    rows.append(dict(closed_utc=closed.isoformat(),close=round(bar.c,4),
        ema_fast=round(ef[i],4),ema_slow=round(es[i],4),
        base_candidate=cand_side,base_score=score,htf_short=int(bear),
        momentum_short=int(momentum),ema_strength=round(strength,3),
        B_eligible=int(b),C_eligible=int(cc),reason=";".join(reasons)))
fields=["closed_utc","close","ema_fast","ema_slow","base_candidate","base_score","htf_short","momentum_short","ema_strength","B_eligible","C_eligible","reason"]
with (P/"gold_oct28_short_diagnosis.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
if not rows:raise RuntimeError("No closed bars in requested Oct 28 interval; data provider window unavailable")
print("GOLD SHORT DIAGNOSIS 2026-10-28; indicator-independent Python baseline research only")
for r in rows:print(r)
print("Total",len(rows),"B",sum(r["B_eligible"] for r in rows),"C",sum(r["C_eligible"] for r in rows))
print("No candidate cannot distinguish every internal base-condition; no TP/SL broker fills.")
