#!/usr/bin/env python3
"""Diagnostic reconstruction only of POSSIBLY MISSED V5 signal candles.
Not actual forward signals, cannot enter trades, no Telegram.
Uses completed closed candles and exact frozen V5 logic from observer.
"""
import csv,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
import gold_signal_bot as bot
from gold_v5_coverage_monitor import reference_open
P=Path(__file__).resolve().parent
report=json.loads((P/"gold_v5_coverage_report.json").read_text())
missing={datetime.fromisoformat(x) for x in report.get("possibly_unobserved_candle_closes_utc",[])}
c=sorted((x for x in bot.candles("15min",320) if x.t+timedelta(minutes=15)<=datetime.now(timezone.utc)),key=lambda x:x.t)
h=sorted((x for x in bot.candles("1h",220) if x.t+timedelta(hours=1)<=datetime.now(timezone.utc)),key=lambda x:x.t)
def ema(values,n):
 a=2/(n+1);o=[values[0]]
 for v in values[1:]:o.append(a*v+(1-a)*o[-1])
 return o
def atr(b):
 tr=[b[0].h-b[0].l]
 for i in range(1,len(b)):
  x=b[i];v=b[i-1].c
  tr.append(max(x.h-x.l,abs(x.h-v),abs(x.l-v)))
 o=[None]*len(b);o[13]=sum(tr[:14])/14
 for i in range(14,len(b)):o[i]=(o[i-1]*13+tr[i])/14
 return o
ef=ema([x.c for x in c],20);es=ema([x.c for x in c],50);a=atr(c)
hf=ema([x.c for x in h],20);hs=ema([x.c for x in h],50);ha=atr(h)
signal_candidates=[]
for i in range(60,len(c)):
 t=c[i].t+timedelta(minutes=15)
 if t not in missing or not reference_open(t):continue
 eligible=[j for j,z in enumerate(h) if z.t+timedelta(hours=1)<=t]
 if not eligible:continue
 j=eligible[-1]
 if j<55 or not ha[j] or abs(hf[j]-hs[j])/ha[j]>=0.5:continue
 d=-1 if ef[i]<es[i] and ef[i]<ef[i-1] else 1 if ef[i]>es[i] and ef[i]>ef[i-1] else 0
 if not d or not a[i]:continue
 prev=c[i-1];bar=c[i]
 touched=prev.h>=ef[i-1] if d==-1 else prev.l<=ef[i-1]
 confirmed=(bar.c<ef[i] and bar.c<prev.l and bar.c<bar.o) if d==-1 else (bar.c>ef[i] and bar.c>prev.h and bar.c>bar.o)
 if touched and confirmed:signal_candidates.append({"signal_candle_open_utc":bar.t.isoformat(),"closed_utc":t.isoformat(),"side":"SHORT" if d==-1 else "LONG"})
out={"status":"DIAGNOSTIC_ONLY","missing_slots":len(missing),
     "historically_detectable_candidates":signal_candidates,
     "limitations":["These signals were NOT observed or tradable live.","Only available provider lookback scanned; cannot prove absence of omitted signals.","Trading session uses approximate CME GC reference, not PU Prime verified hours.","No trades are reconstructed and no positions are entered."]}
(P/"gold_v5_missed_signal_diagnostic.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))
