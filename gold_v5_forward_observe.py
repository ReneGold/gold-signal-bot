#!/usr/bin/env python3
"""Gold V5 immutable-rule paper observer with two-stage signal/entry bookkeeping.
No orders or Telegram. Historical original backfill is preserved separately.
New signal must be observed within 15 minutes of signal candle close.
Entry is not known at signal time: mark PENDING_ENTRY; fix entry on next run.
Paper fills are still indicative, not broker-executable quotes.
"""
import csv,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import gold_signal_bot as bot

P=Path(__file__).resolve().parent
LEDGER=P/"gold_v5_forward_ledger.csv"
FREEZE=datetime(2026,10,29,14,38,28,tzinfo=timezone.utc)
CT=ZoneInfo("America/Chicago")
FIELDS=["signal_utc","entry_utc","side","phase","entry","stop","target","risk",
        "status","exit_utc","exit_price","exit_reason","net_R","cohort"]
now=datetime.now(timezone.utc)
raw15=bot.candles("15min",320)
c=sorted((x for x in raw15 if x.t+timedelta(minutes=15)<=now),key=lambda z:z.t)
h=sorted((x for x in bot.candles("1h",220) if x.t+timedelta(hours=1)<=now),key=lambda z:z.t)
if len(c)<85 or len(h)<55:raise RuntimeError("Insufficient completed candles")
def ema(a,n):
 k=2/(n+1);out=[a[0]]
 for v in a[1:]:out.append(z:=v*k+out[-1]*(1-k))
 return out
def atr14(bars):
 tr=[bars[0].h-bars[0].l]
 for i in range(1,len(bars)):
  x=bars[i];pr=bars[i-1].c
  tr.append(max(x.h-x.l,abs(x.h-pr),abs(x.l-pr)))
 out=[None]*len(bars);out[13]=sum(tr[:14])/14
 for i in range(14,len(bars)):out[i]=(out[i-1]*13+tr[i])/14
 return out
ef=ema([x.c for x in c],20);es=ema([x.c for x in c],50);atr=atr14(c)
hf=ema([x.c for x in h],20);hs=ema([x.c for x in h],50);ha=atr14(h)
def session(t):
 loc=t.astimezone(CT);day=loc.weekday();minute=loc.hour*60+loc.minute
 return not (day==5 or (day==4 and minute>=960) or (day==6 and minute<1020)
             or (day<4 and 960<=minute<1020))
def sideways(t):
 candidates=[i for i,z in enumerate(h) if z.t+timedelta(hours=1)<=t]
 if not candidates:return False
 i=candidates[-1]
 return i>=55 and ha[i] and ha[i]>0 and abs(hf[i]-hs[i])/ha[i]<0.5
def pullback(i):
 d=-1 if ef[i]<es[i] and ef[i]<ef[i-1] else 1 if ef[i]>es[i] and ef[i]>ef[i-1] else 0
 if not d or not atr[i]:return 0
 prev=c[i-1];bar=c[i]
 touched=prev.h>=ef[i-1] if d==-1 else prev.l<=ef[i-1]
 confirmed=(bar.c<ef[i] and bar.c<prev.l and bar.c<bar.o) if d==-1 else (bar.c>ef[i] and bar.c>prev.h and bar.c>bar.o)
 return d if touched and confirmed else 0
if LEDGER.exists():
 with LEDGER.open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
else:rows=[]
# Initial five backfilled records had blank cohort; they must never enter forward statistics.
for r in rows:
 if not r.get("cohort"):r["cohort"]="INITIAL_BACKFILL"
signal_seen={r["signal_utc"] for r in rows}
bar_at={x.t:x for x in c}
added=entered=closed=missed=0
# First update previously recorded pending entries. Do not enter if data provider has
# lost the next candle; never invent an entry price.
for r in rows:
 if r["status"]!="PENDING_ENTRY":continue
 t=datetime.fromisoformat(r["entry_utc"]);entrybar=bar_at.get(t)
 if not entrybar:
  if now-t>timedelta(hours=6):
   r["status"]="UNRESOLVED_DATA_GAP";missed+=1
  continue
 d=1 if r["side"]=="LONG" else -1
 risk=float(r["risk"]);entry=entrybar.o
 r.update(entry=f"{entry:.5f}",stop=f"{entry-d*risk:.5f}",target=f"{entry+d*2*risk:.5f}",
          status="OPEN_PAPER")
 entered+=1
# Close established paper positions using completed 15m candles ONLY.
for r in rows:
 if r["status"]!="OPEN_PAPER":continue
 entry_t=datetime.fromisoformat(r["entry_utc"])
 k=next((i for i,x in enumerate(c) if x.t==entry_t),None)
 if k is None:
  # Old historical rows may age out of the provider lookback; preserve as unresolved.
  if now-entry_t>timedelta(days=4):r["status"]="UNRESOLVED_DATA_GAP"
  continue
 d=1 if r["side"]=="LONG" else -1;entry=float(r["entry"])
 stop=float(r["stop"]);target=float(r["target"]);risk=float(r["risk"])
 end=None;px=None;reason=None
 for j in range(k,min(k+16,len(c))):
  b=c[j]
  hitstop=(b.l<=stop if d==1 else b.h>=stop)
  hittp=(b.h>=target if d==1 else b.l<=target)
  if hitstop:
   end=j;px=(min(b.o,stop) if d==1 else max(b.o,stop));reason="STOP";break
  if hittp:
   end=j;px=target;reason="TP";break
 if reason is None and k+15<len(c):
  end=k+15;px=c[end].c;reason="TIME"
 if reason is not None:
  r.update(status="CLOSED_PAPER",exit_utc=c[end].t.isoformat(),exit_price=f"{px:.5f}",
           exit_reason=reason,net_R=f"{(d*(px-entry)-0.8)/risk:.5f}")
  closed+=1
# Only most recently closed candle may become an authentic newly seen signal.
i=len(c)-1
close_t=c[i].t+timedelta(minutes=15)
fresh=(FREEZE<=close_t<=now and now-close_t<=timedelta(minutes=15))
if fresh and c[i].t.isoformat() not in signal_seen and session(close_t) and sideways(close_t):
 d=pullback(i)
 # One active or pending forward position at a time. Earlier closed backfill trades
 # never block fresh signals.
 active=any(r.get("cohort")=="FORWARD" and r["status"] in ("OPEN_PAPER","PENDING_ENTRY") for r in rows)
 if d and not active:
  risk=1.5*atr[i]
  rows.append(dict(signal_utc=c[i].t.isoformat(),entry_utc=close_t.isoformat(),
    side="LONG" if d==1 else "SHORT",phase="RANGE_OR_WEAK",entry="",stop="",target="",
    risk=f"{risk:.5f}",status="PENDING_ENTRY",exit_utc="",exit_price="",
    exit_reason="",net_R="",cohort="FORWARD"))
  added+=1
rows.sort(key=lambda r:r["signal_utc"])
with LEDGER.open("w",newline="",encoding="utf-8") as f:
 w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
forward=[r for r in rows if r["cohort"]=="FORWARD"]
completed=[r for r in forward if r["status"]=="CLOSED_PAPER"]
result=dict(as_of_utc=now.isoformat(),candidate="Gold V5 frozen sideways pullback",
 forward_signals=len(forward),forward_pending=sum(r["status"]=="PENDING_ENTRY" for r in forward),
 forward_open=sum(r["status"]=="OPEN_PAPER" for r in forward),
 forward_closed=len(completed),forward_net_R_closed=round(sum(float(r["net_R"]) for r in completed),5),
 initial_backfill_count=sum(r["cohort"]!="FORWARD" for r in rows),
 new_signals_this_run=added,entries_recorded_this_run=entered,positions_closed_this_run=closed,
 unresolved_missing_data=missed,
 caveat="Observational paper fill at next bar open; not executable broker data. No lookahead signal candidates; schedule may be delayed or miss signals.")
(P/"gold_v5_forward_summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2))
