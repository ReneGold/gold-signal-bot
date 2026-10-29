#!/usr/bin/env python3
"""Frozen Gold V5 sideways pullback forward observation. No Telegram or orders.
Append-only signal ledger in test branch; later candles close pending paper outcomes.
Git workflow is scheduled; runs may be delayed, API history limited.
"""
import csv,json,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import gold_signal_bot as bot
P=Path(__file__).resolve().parent
LEDGER=P/"gold_v5_forward_ledger.csv"
START=datetime(2026,10,29,14,38,28,tzinfo=timezone.utc)
# The first manually run observation backfilled earlier candles. Preserve, but never count as forward.
LIVE_MAX_DELAY=timedelta(minutes=45)
CT=ZoneInfo("America/Chicago")
FIELDS=["signal_utc","entry_utc","side","phase","entry","stop","target","risk","status","exit_utc","exit_price","exit_reason","net_R","cohort"]
now=datetime.now(timezone.utc)
c=[x for x in bot.candles("15min",320) if x.t+timedelta(minutes=15)<=now]
h=[x for x in bot.candles("1h",220) if x.t+timedelta(hours=1)<=now]
if len(c)<85 or len(h)<55:raise RuntimeError("Insufficient completed candles")
def ema(a,n):
 k=2/(n+1);v=[a[0]]
 for z in a[1:]:v.append(z*k+v[-1]*(1-k))
 return v
cl=[x.c for x in c];ef=ema(cl,20);es=ema(cl,50)
true=[c[0].h-c[0].l]
for i in range(1,len(c)):true.append(max(c[i].h-c[i].l,abs(c[i].h-c[i-1].c),abs(c[i].l-c[i-1].c)))
atr=[None]*len(c);atr[13]=sum(true[:14])/14
for i in range(14,len(c)):atr[i]=(atr[i-1]*13+true[i])/14
hc=[x.c for x in h];hf=ema(hc,20);hs=ema(hc,50)
ht=[h[0].h-h[0].l]
for i in range(1,len(h)):ht.append(max(h[i].h-h[i].l,abs(h[i].h-hc[i-1]),abs(h[i].l-hc[i-1])))
ha=[None]*len(h);ha[13]=sum(ht[:14])/14
for i in range(14,len(h)):ha[i]=(ha[i-1]*13+ht[i])/14
def session(t):
 l=t.astimezone(CT);d=l.weekday();m=l.hour*60+l.minute
 return not (d==5 or (d==4 and m>=960) or (d==6 and m<1020) or (d<4 and 960<=m<1020))
def sideways(close_time):
 candidates=[j for j,z in enumerate(h) if z.t+timedelta(hours=1)<=close_time]
 if not candidates:return False
 j=candidates[-1]
 return j>=55 and ha[j] and ha[j]>0 and abs(hf[j]-hs[j])/ha[j]<0.5
def pullback(i):
 d=(-1 if ef[i]<es[i] and ef[i]<ef[i-1] else 1 if ef[i]>es[i] and ef[i]>ef[i-1] else 0)
 if not d or not atr[i]:return 0
 prior=c[i-1];bar=c[i]
 touched=prior.h>=ef[i-1] if d==-1 else prior.l<=ef[i-1]
 confirmed=(bar.c<ef[i] and bar.c<prior.l and bar.c<bar.o) if d==-1 else (bar.c>ef[i] and bar.c>prior.h and bar.c>bar.o)
 return d if touched and confirmed else 0
if LEDGER.exists():
 with LEDGER.open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
else:rows=[]
known={r["signal_utc"] for r in rows}
added=closed=0
# Inspect only last 80 completed bars, no backfill before freeze, never produce hypothetical historic live alerts
for i in range(max(60,len(c)-80),len(c)-1):
 close_time=c[i].t+timedelta(minutes=15)
 if close_time<START or close_time>now:continue
 if now-close_time>LIVE_MAX_DELAY:continue
 if not session(close_time) or not session(c[i+1].t):continue
 if not sideways(close_time):continue
 d=pullback(i)
 if not d:continue
 key=c[i].t.isoformat()
 if key in known:continue
 # One new V5 paper position at a time: prevent overlapping positions.
 if any(x.get("cohort")=="FORWARD" and datetime.fromisoformat(x["entry_utc"])<=close_time < datetime.fromisoformat(x["entry_utc"])+timedelta(hours=4) for x in rows):continue
 entry=c[i+1].o;risk=1.5*atr[i]
 stop=entry-d*risk;target=entry+d*2*risk
 rows.append(dict(signal_utc=key,entry_utc=c[i+1].t.isoformat(),side="LONG" if d==1 else "SHORT",
  phase="RANGE_OR_WEAK",entry=f"{entry:.5f}",stop=f"{stop:.5f}",target=f"{target:.5f}",risk=f"{risk:.5f}",
  status="OPEN_PAPER",exit_utc="",exit_price="",exit_reason="",net_R="",cohort="FORWARD"))
 known.add(key);added+=1
bytime={z.t:i for i,z in enumerate(c)}
for r in rows:
 if r["status"]!="OPEN_PAPER":continue
 try:entrydt=datetime.fromisoformat(r["entry_utc"])
 except ValueError:continue
 k=bytime.get(entrydt)
 if k is None:continue
 direction=1 if r["side"]=="LONG" else -1
 stop=float(r["stop"]);target=float(r["target"]);entry=float(r["entry"]);risk=float(r["risk"])
 last=min(k+15,len(c)-1);px=None;reason=None;end=None
 for j in range(k,last+1):
  b=c[j]
  hitstop=b.l<=stop if direction==1 else b.h>=stop
  hittp=b.h>=target if direction==1 else b.l<=target
  if hitstop:
   px=min(b.o,stop) if direction==1 else max(b.o,stop);reason="STOP";end=j;break
  if hittp:px=target;reason="TP";end=j;break
 if reason is None and k+15<len(c):
  end=k+15;px=c[end].c;reason="TIME"
 if reason is not None:
  r.update(status="CLOSED_PAPER",exit_utc=c[end].t.isoformat(),exit_price=f"{px:.5f}",exit_reason=reason,
   net_R=f"{(direction*(px-entry)-0.8)/risk:.5f}")
  closed+=1
# idempotent, sort time. Missing scheduled run can't be fully reconstructed beyond API lookback.
rows.sort(key=lambda r:r["signal_utc"])
with LEDGER.open("w",newline="",encoding="utf-8") as f:
 w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
forward=[x for x in rows if x.get("cohort")=="FORWARD"]
backfill=[x for x in rows if x.get("cohort")!="FORWARD"]
summary={"forward_signals":len(forward),"backfilled_or_recovered":len(backfill),
 "forward_closed":sum(x["status"]=="CLOSED_PAPER" for x in forward),
 "forward_net_R_closed":round(sum(float(x["net_R"]) for x in forward if x["status"]=="CLOSED_PAPER"),4),
 "note":"Original initial manually backfilled signals excluded from forward performance.",
 "as_of_utc":now.isoformat(),"candidate":"RANGE_PULLBACK_ONLY frozen 2026-10-29","total":len(rows),
 "open":sum(r["status"]=="OPEN_PAPER" for r in rows),"closed":sum(r["status"]=="CLOSED_PAPER" for r in rows),
 "added_this_run":added,"closed_this_run":closed,
 "sum_net_R_closed":round(sum(float(r["net_R"]) for r in rows if r["status"]=="CLOSED_PAPER"),4),
 "cautions":"Forward paper simulations only. Limited provider window, possible scheduled-run delays; actual broker spreads and market hours unverified. Missing bars do not imply no market signals."}
(P/"gold_v5_forward_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,indent=2))
