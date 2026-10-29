#!/usr/bin/env python3
"""Gold V5 research: independent portfolio replay for predeclared market-phase gates.
No orders/Telegram. Filters use only fully closed 1h candles at SIGNAL CLOSE.
Each variant reruns non-overlapping trades from scratch; outputs month detail.
CME GC reference hours are a proxy, not verified XAU/USD spot trading hours.
"""
import bisect,csv,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from collections import defaultdict
import gold_v5_session_ab as b
P=Path(__file__).resolve().parent/"gold_data_audit"
with (P/"gold_1h_2026_aug_oct.csv").open(encoding="utf-8",newline="") as f:h=list(csv.DictReader(f))
ht=[datetime.fromisoformat(x["utc"]) for x in h]
close=[float(x["close"]) for x in h]
high=[float(x["high"]) for x in h];low=[float(x["low"]) for x in h]
def ema(vals,n):
 a=2/(n+1);out=[vals[0]]
 for v in vals[1:]:out.append(out[-1]*(1-a)+v*a)
 return out
fast=ema(close,20);slow=ema(close,50)
tr=[high[0]-low[0]]
for i in range(1,len(h)):tr.append(max(high[i]-low[i],abs(high[i]-close[i-1]),abs(low[i]-close[i-1])))
atr=[None]*len(h);atr[13]=sum(tr[:14])/14
for i in range(14,len(h)):atr[i]=(atr[i-1]*13+tr[i])/14
def phase_at(signal_closed):
 # Hourly timestamps represent open. Only candle close <= signal close qualifies.
 k=bisect.bisect_right(ht,signal_closed-timedelta(hours=1))-1
 if k<55 or not atr[k] or atr[k]<=0:return "WARMUP"
 strength=abs(fast[k]-slow[k])/atr[k]
 if strength<0.5:return "RANGE_OR_WEAK"
 if fast[k]>slow[k] and fast[k]>fast[k-1]:return "UP_TREND"
 if fast[k]<slow[k] and fast[k]<fast[k-1]:return "DOWN_TREND"
 return "TRANSITION"
POLICIES=("BASE","EXCLUDE_TRANSITION","RANGE_PULLBACK_ONLY")
def allowed(policy,kind,ph):
 if ph=="WARMUP":return False
 if policy=="BASE":return True
 if policy=="EXCLUDE_TRANSITION":return ph!="TRANSITION"
 return kind=="PULLBACK" and ph=="RANGE_OR_WEAK"
def run(kind,policy):
 trades=[];next_available=60;declined=defaultdict(int)
 for i in range(60,len(b.bars)-17):
  if i<next_available:continue
  d=b.candidate(i,kind)
  if not d:continue
  close_time=b.bars[i][0]+timedelta(minutes=15)
  if not (b.ref_open(close_time) and b.ref_open(b.bars[i+1][0])):continue
  ph=phase_at(close_time)
  if not allowed(policy,kind,ph):
   declined[ph]+=1;continue
  entry=b.bars[i+1][1];risk=1.5*b.atr[i]
  stop=entry-d*risk;tp=entry+d*2*risk
  last=i+16;px=b.bars[last][4];exit_type="TIME"
  for j in range(i+1,last+1):
   bar=b.bars[j]
   sh=(bar[3]<=stop if d==1 else bar[2]>=stop)
   th=(bar[2]>=tp if d==1 else bar[3]<=tp)
   if sh:
    px=min(stop,bar[1]) if d==1 else max(stop,bar[1]);last=j;exit_type="STOP";break
   if th:px=tp;last=j;exit_type="TP";break
  trades.append(dict(strategy=kind,policy=policy,signal_utc=b.bars[i][0].isoformat(),
   entry_utc=b.bars[i+1][0].isoformat(),exit_utc=b.bars[last][0].isoformat(),
   side="LONG" if d==1 else "SHORT",phase=ph,net_R=round((d*(px-entry)-0.8)/risk,5),
   exit_type=exit_type,month=b.bars[i][0].strftime("%Y-%m")))
  next_available=last+1
 return trades,dict(declined)
def stats(ts):
 gain=sum(max(0,t["net_R"]) for t in ts);loss=-sum(min(0,t["net_R"]) for t in ts)
 eq=peak=dd=0
 for t in ts:eq+=t["net_R"];peak=max(peak,eq);dd=max(dd,peak-eq)
 return dict(n=len(ts),net_R=round(eq,3),mean_R=round(eq/len(ts),4) if ts else None,
  win_pct=round(100*sum(t["net_R"]>0 for t in ts)/len(ts),2) if ts else None,
  profit_factor=round(gain/loss,3) if loss else None,closed_drawdown_R=round(dd,3))
results=[];events=[]
for kind in ("PULLBACK","BREAKOUT"):
 for policy in POLICIES:
  tr,declined=run(kind,policy);events+=tr
  months={m:stats([x for x in tr if x["month"]==m]) for m in ("2026-08","2026-09","2026-10")}
  result=dict(strategy=kind,policy=policy,overall=stats(tr),months=months,declined=declined)
  results.append(result);print(json.dumps(result,ensure_ascii=False))
meta=dict(source="Twelve Data XAU/USD Aug-Oct 2026",analysis="Full separate nonoverlapping trading replays for predefined phase filters.",
 caveats=["All months previously studied; NOT independent out-of-sample.","Spot gold sessions not verified; CME GC as reference only.","Candle OHLC are indicative, 0.8 USD/oz assumed round-trip cost, stop-first if same bar, next bar open, 1.5 ATR stop, 2R target, 16-bar expiry.","No true broker spread/slippage or holiday calendar; no promises of profitability.","V5 experimental research rules are NOT the running V4 score-65 C bot."],results=results)
(P/"gold_v5_phase_policy_summary.json").write_text(json.dumps(meta,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
with (P/"gold_v5_phase_policy_trades.csv").open("w",newline="",encoding="utf-8") as f:
 fields=["strategy","policy","signal_utc","entry_utc","exit_utc","side","phase","net_R","exit_type","month"]
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(events)
