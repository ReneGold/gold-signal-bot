#!/usr/bin/env python3
"""Read-only feed quality gate for V5: fail closed on malformed, missing or stale active-session OHLC.
Runs before forward observer. Weekend and reference maintenance periods avoid false stale alarms.
Does NOT certify prices match the execution broker.
"""
import json,sys,math
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import gold_signal_bot as bot

now=datetime.now(timezone.utc)
CT=ZoneInfo("America/Chicago")
out=Path(__file__).resolve().parent/"gold_v5_feed_quality.json"
errors=[];warnings=[];metrics={}
def active(t):
 x=t.astimezone(CT);d=x.weekday();m=x.hour*60+x.minute
 return not (d==5 or (d==4 and m>=960) or (d==6 and m<1020) or (d<4 and 960<=m<1020))
def check(interval,minutes,amount):
 bars=sorted(bot.candles(interval,amount),key=lambda c:c.t)
 if len(bars)<amount//2:errors.append(f"{interval}: too few candles: {len(bars)}")
 if not bars:return
 stamps=[x.t for x in bars]
 if len(set(stamps))!=len(stamps):errors.append(f"{interval}: duplicate timestamps")
 for i,b in enumerate(bars):
  if b.t.tzinfo is None:errors.append(f"{interval}: naive timestamp");continue
  if b.t>now+timedelta(minutes=1):errors.append(f"{interval}: future candle")
  if b.t.minute%minutes!=0 if minutes<60 else b.t.minute!=0:errors.append(f"{interval}: unaligned timestamp")
  values=(b.o,b.h,b.l,b.c)
  if not all(math.isfinite(float(v)) and float(v)>0 for v in values):
   errors.append(f"{interval}: invalid price values");continue
  if b.h<max(b.o,b.c,b.l) or b.l>min(b.o,b.c,b.h):
   errors.append(f"{interval}: invalid OHLC geometry")
 gaps=[]
 for a,b in zip(stamps,stamps[1:]):
  gap=(b-a).total_seconds()/60
  if gap>minutes*1.5 and active(a+timedelta(minutes=minutes)) and active(b):
   gaps.append({"after":a.isoformat(),"before":b.isoformat(),"minutes":gap})
 if gaps:warnings.append(f"{interval}: {len(gaps)} session gaps detected; possible data interruptions")
 last=max((x.t for x in bars if x.t+timedelta(minutes=minutes)<=now),default=None)
 age=(now-(last+timedelta(minutes=minutes))).total_seconds()/60 if last else None
 metrics[interval]={"bars":len(bars),"latest_completed_open_utc":last.isoformat() if last else None,
  "minutes_since_last_close":round(age,2) if age is not None else None,"session_gaps":gaps[-10:]}
 # Only stale-gate in normal sessions, allow 2 bars latency for provider/scheduler.
 if active(now) and age is not None and age>minutes*2+10:
  errors.append(f"{interval}: latest completed candle stale ({age:.1f} min)")
check("15min",15,320)
check("1h",60,220)
report={"as_of_utc":now.isoformat(),"status":"FAIL" if errors else ("WARN" if warnings else "PASS"),
 "errors":errors,"warnings":warnings,"metrics":metrics,
 "policy":"Only hard failures block paper entries; gaps are warnings pending session-calendar validation.",
 "limitations":"CME GC reference calendar is approximate for XAUUSD spot; not an executable quote or broker reconciliation."}
out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(1 if errors else 0)
