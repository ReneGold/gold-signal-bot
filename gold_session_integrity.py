#!/usr/bin/env python3
"""Research-only quality report on exported XAU/USD OHLC bars.

Diagnoses off-session/weekend price bars; it never deletes bars or changes bot settings.
UTC weekend is only an audit FLAG, not proof that a bar is invalid.
"""
import csv,json,statistics
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent/"gold_data_audit"
def load(name):
    path=ROOT/name
    with path.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    out=[]
    for r in rows:
        t=datetime.fromisoformat(r["utc"]).astimezone(timezone.utc)
        out.append((t,*[float(r[k]) for k in ("open","high","low","close")]))
    return out

def assess(rows,interval):
    days=Counter();hours=Counter();wknd=[];flat=0;unchanged=0;large_same=0
    max_streak=0;streak=0;examples=[]
    for i,(t,o,h,l,c) in enumerate(rows):
        days[t.strftime("%A")]+=1
        hours[f"{t.weekday()}:{t.hour:02d}"]+=1
        if t.weekday()>=5:
            wknd.append(t)
            if len(examples)<12:examples.append({"utc":t.isoformat(),"ohlc":[o,h,l,c]})
        if o==h==l==c:flat+=1
        if i and c==rows[i-1][4]:
            unchanged+=1;streak+=1;max_streak=max(max_streak,streak)
        else:streak=0
    saturdays=sum(t.weekday()==5 for t in wknd)
    sundays=sum(t.weekday()==6 for t in wknd)
    return {"interval":interval,"total":len(rows),"bars_saturday_utc":saturdays,
        "bars_sunday_utc":sundays,"weekend_fraction":round(len(wknd)/len(rows),4) if rows else 0,
        "flat_ohlc_bars":flat,"close_unchanged_from_previous":unchanged,
        "max_consecutive_equal_close_transitions":max_streak,
        "weekday_counts":dict(days),"utc_weekend_examples":examples,
        "interpretation":"Weekend UTC flag is NOT a trading-session calendar. Sunday opening / Friday closing and broker feed conventions require verification."}

x15=load("gold_15min_2026_aug_oct.csv")
x1h=load("gold_1h_2026_aug_oct.csv")
r15=assess(x15,"15min");r1=assess(x1h,"1h")
# Hourly candle consistency: only compare complete sets of four consecutive 15m candles.
by15={t:(o,h,l,c) for t,o,h,l,c in x15}
cross=[];checked=0
from datetime import timedelta
for t,o,h,l,c in x1h:
    sub=[by15.get(t+timedelta(minutes=15*k)) for k in range(4)]
    if any(v is None for v in sub):continue
    checked+=1
    ao=sub[0][0];ah=max(v[1] for v in sub);al=min(v[2] for v in sub);ac=sub[-1][3]
    diffs=[abs(a-b) for a,b in zip((o,h,l,c),(ao,ah,al,ac))]
    if max(diffs)>0.05:
        if len(cross)<30:cross.append({"utc":t.isoformat(),"max_abs_usd":round(max(diffs),5),
            "hourly_ohlc":[o,h,l,c],"from_15m":[ao,ah,al,ac]})
result={"source":"Twelve Data gold_data_quality_audit.py outputs",
    "recommendation":"REVIEW_BEFORE_BACKTEST",
    "fifteen_minute":r15,"one_hour":r1,
    "cross_interval":{"compared_complete_hours":checked,
        "mismatches_over_0_05_usd_examples":cross,
        "example_count_is_capped":True},
    "cautions":["A continuous weekend feed can be synthetic, indicative, or provider-specific.",
        "A UTC weekend flag is not an authoritative gold market calendar.",
        "Do not delete or interpolate candles until source metadata and session schedule are verified.",
        "No trades, Telegram calls, or strategy changes were made."]}
path=ROOT/"gold_session_integrity_report.json"
path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("GOLD SESSION REPORT")
print("15m weekend Saturday",r15["bars_saturday_utc"],"Sunday",r15["bars_sunday_utc"],
      "flat",r15["flat_ohlc_bars"],"equal-close",r15["close_unchanged_from_previous"])
print("1h weekend Saturday",r1["bars_saturday_utc"],"Sunday",r1["bars_sunday_utc"],
      "flat",r1["flat_ohlc_bars"],"equal-close",r1["close_unchanged_from_previous"])
print("Cross-timeframe checked",checked,"mismatch examples",len(cross))
print("REVIEW REQUIRED: provider and gold sessions before backtesting.")
