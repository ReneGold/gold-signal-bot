"""Historical technical diagnostic, NOT a complete strategy backtest.
No invented VWAP, quotes or news. Never emits an executable signal.
Reads history_collect CSVs, uses only completed bars at each M5 close.
"""
import argparse,csv,json
from pathlib import Path
from bisect import bisect_right
from collections import Counter
from math import isfinite
from .structure import multi_timeframe
from .pullback import zone,observe
from .indicators import features
from .smc import analyze_smc
from .scoring import score_setup

INTERVALS=dict(h4="4h",h1="1h",m15="15min",m5="5min")
PERIODS=dict(h4=14400,h1=3600,m15=900,m5=300)

def load(root):
    frames={}
    for tf,interval in INTERVALS.items():
        rows={}
        for path in sorted(root.glob(interval+"_*.csv")):
            with path.open(newline="") as f:
                for raw in csv.DictReader(f):
                    t=int(raw["timestamp"])
                    o,h,l,c=(float(raw[k]) for k in ("open","high","low","close"))
                    if t<=0 or not all(isfinite(x) and x>0 for x in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:
                        raise ValueError("invalid historical bar")
                    if t in rows: raise ValueError("duplicate historical bar")
                    row=dict(timestamp=t,open=o,high=h,low=l,close=c,closed=True)
                    if raw.get("volume") not in ("",None):
                        v=float(raw["volume"])
                        if not isfinite(v) or v<0: raise ValueError("invalid volume")
                        row["volume"]=v
                    rows[t]=row
        frames[tf]=[rows[t] for t in sorted(rows)]
        if len(rows)<201: raise ValueError("insufficient history: "+tf)
    return frames

def replay(frames,start,end):
    stamps={tf:[r["timestamp"] for r in rows] for tf,rows in frames.items()}
    counts=Counter()
    score_hist=Counter()
    candidates=[]
    seen=set()
    for now in stamps["m5"]:
        if not start<=now<end: continue
        counts["m5_closes"]+=1
        window={}
        for tf,period in PERIODS.items():
            j=bisect_right(stamps[tf],now)
            if j<201 or now-stamps[tf][j-1]>=period+60:
                break
            w=frames[tf][max(0,j-320):j]
            if any(b["timestamp"]-a["timestamp"]!=period for a,b in zip(w[-5:-1],w[-4:])):
                break
            window[tf]=w
        if len(window)!=4:
            counts["history_or_gap_block"]+=1
            continue
        trend=multi_timeframe(window)
        side=trend["side"]
        if side=="NO TRADE":
            counts["timeframe_conflict"]+=1
            continue
        counts["aligned"]+=1
        z=zone(window["m15"],side)
        if not z or window["m5"][0]["timestamp"]>z["confirmed_at"]:
            counts["zone_unavailable"]+=1
            continue
        obs=observe(z,window["m5"])
        counts["zone_"+obs["status"]]+=1
        if obs["status"]!="CANDIDATE": continue
        f={tf:features(window[tf]) for tf in ("m5","h1")}
        smc=analyze_smc(window["m5"])
        q=score_setup(side,trend["frames"],f,smc,z,obs)
        score_hist[str(q["score"])]+=1
        m=f["m5"]
        if q["score"]<80 or m["price_action"]!=side or m["momentum"]!=side or not m["atr14"]>0 or not .5<=(m.get("atr_ratio") or 0)<=2.5:
            counts["technical_rejected"]+=1
            continue
        key=(side,z["start_time"],z["end_time"])
        if key in seen:
            counts["duplicate_candidate"]+=1
            continue
        seen.add(key)
        counts["technical_candidate"]+=1
        candidates.append(dict(timestamp=now,side=side,score=q["score"],zone=z,
                               status="UNVERIFIED_RESEARCH_CANDIDATE"))
    return dict(mode="RESEARCH_DIAGNOSTIC",start=start,end_exclusive=end,
                counts=dict(counts),score_histogram=dict(score_hist),candidates=candidates,
                approved_signals=0,performance=None,
                blockers=["Verified historical VWAP, bid/ask, calendar and execution inputs required"],
                limitations=["Not a profit backtest; no modeled fills, no changes to production rules",
                             "No verified historical session coverage; counts may include out-of-session bars"])

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data",type=Path,required=True)
    p.add_argument("--start",type=int,required=True)
    p.add_argument("--end",type=int,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if a.start>=a.end: p.error("invalid range")
    report=replay(load(a.data),a.start,a.end)
    a.out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report["counts"],indent=2))
