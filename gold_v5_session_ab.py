#!/usr/bin/env python3
"""Gold V5 research: compare identical candidate entries with/without reference session gate.
Historical candles remain intact for EMA/ATR and trade exits. NO orders or Telegram.
CME GC reference hours are NOT verified XAU/USD spot trading hours.
"""
import csv,json
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
P=Path(__file__).resolve().parent/"gold_data_audit"
CT=ZoneInfo("America/Chicago")
raw=list(csv.DictReader((P/"gold_15min_2026_aug_oct.csv").open(encoding="utf-8")))
bars=[(datetime.fromisoformat(r["utc"]),*[float(r[k]) for k in ("open","high","low","close")]) for r in raw]
def ema(a,n):
    k=2/(n+1);out=[a[0]]
    for v in a[1:]:out.append(v*k+out[-1]*(1-k))
    return out
close=[b[4] for b in bars];ef=ema(close,20);es=ema(close,50)
tr=[bars[0][2]-bars[0][3]]
for i in range(1,len(bars)):
    b=bars[i];tr.append(max(b[2]-b[3],abs(b[2]-bars[i-1][4]),abs(b[3]-bars[i-1][4])))
atr=[None]*len(bars)
atr[13]=sum(tr[:14])/14
for i in range(14,len(bars)):atr[i]=(atr[i-1]*13+tr[i])/14
def ref_open(t):
    l=t.astimezone(CT);d=l.weekday();m=l.hour*60+l.minute
    return not (d==5 or (d==4 and m>=960) or (d==6 and m<1020) or (d<4 and 960<=m<1020))
def side(i):
    if ef[i]<es[i] and ef[i]<ef[i-1]:return -1
    if ef[i]>es[i] and ef[i]>ef[i-1]:return 1
    return 0
def candidate(i,kind):
    d=side(i); b=bars[i];prev=bars[i-1];a=atr[i]
    if not d or not a or a<=0:return 0
    if kind=="PULLBACK":
        touch=prev[2]>=ef[i-1] if d==-1 else prev[3]<=ef[i-1]
        confirm=(b[4]<ef[i] and b[4]<prev[3] and b[4]<b[1]) if d==-1 else (b[4]>ef[i] and b[4]>prev[2] and b[4]>b[1])
        return d if touch and confirm else 0
    prior=bars[i-8:i];old=bars[i-9:i-1]
    crossed=(b[4]<min(x[3] for x in prior)-.1*a and prev[4]>=min(x[3] for x in old)) if d==-1 else (b[4]>max(x[2] for x in prior)+.1*a and prev[4]<=max(x[2] for x in old))
    return d if crossed and abs(b[4]-b[1])>=.35*a else 0
def simulate(kind,gated):
    events=[];available=60;blocked=0
    for i in range(60,len(bars)-17):
        if i<available:continue
        d=candidate(i,kind)
        if not d:continue
        # Check both signal bar close and next bar open, never assume close-time tradability.
        if gated and (not ref_open(bars[i][0]+timedelta(minutes=15)) or not ref_open(bars[i+1][0])):
            blocked+=1;continue
        entry=bars[i+1][1];risk=1.5*atr[i];sl=entry-d*risk;tp=entry+d*2*risk
        last=i+16;exitp=bars[last][4];reason="TIME"
        for j in range(i+1,last+1):
            b=bars[j];stop=b[3]<=sl if d==1 else b[2]>=sl
            target=b[2]>=tp if d==1 else b[3]<=tp
            if stop:
                exitp=min(sl,b[1]) if d==1 else max(sl,b[1]);last=j;reason="STOP";break
            if target:exitp=tp;last=j;reason="TP";break
        r=(d*(exitp-entry)-0.8)/risk
        events.append(dict(rule=kind,session_filter="CME_REFERENCE_ONLY" if gated else "ALL_BARS",
            signal_utc=bars[i][0].isoformat(),entry_utc=bars[i+1][0].isoformat(),
            exit_utc=bars[last][0].isoformat(),side="SHORT" if d==-1 else "LONG",
            entry=round(entry,4),exit=round(exitp,4),net_R=round(r,5),exit_reason=reason))
        available=last+1
    return events,blocked
results=[];summary=[]
for kind in ("PULLBACK","BREAKOUT"):
    for gated in (False,True):
        events,blocked=simulate(kind,gated);results+=events
        eq=0;peak=0;dd=0;gain=0;loss=0
        for e in events:
            r=e["net_R"];eq+=r;peak=max(peak,eq);dd=max(dd,peak-eq);gain+=max(0,r);loss+=-min(0,r)
        summary.append(dict(rule=kind,variant="CME_REFERENCE_ONLY" if gated else "ALL_BARS",trades=len(events),
            blocked_setup_events=blocked,net_R=round(eq,3),
            win_pct=round(100*sum(e["net_R"]>0 for e in events)/len(events),2) if events else None,
            profit_factor=round(gain/loss,3) if loss else None,max_closed_drawdown_R=round(dd,3)))
with (P/"gold_v5_session_ab_trades.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=["rule","session_filter","signal_utc","entry_utc","exit_utc","side","entry","exit","net_R","exit_reason"])
    w.writeheader();w.writerows(results)
report=dict(source="Twelve Data XAU/USD 15-minute August-October 2026",bars=len(bars),
    assumptions="CME GC hours are a proxy, not verified spot session. Futures holidays and edge-overlap bars not modeled; simple indicative OHLC without broker fills, assumed 0.8 USD/oz roundtrip fee; stop-first same-bar ambiguity; entry next bar open, ATR(14), TP 2R and stop 1.5 ATR, max 16 bars; no optimized 1H trend filters.",
    warning="Exploratory in-sample comparisons only. No proof of profitability, statistical significance or execution.",
    strategy="Two independent research candidates, NOT active V4 C score-65 strategy.",summary=summary)
(P/"gold_v5_session_ab_summary.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))
