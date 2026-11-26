"""Research-only historical collector. No trading, no Telegram.
Explicit request budget per invocation; no automatic retries or paid upgrades.
Keep output directory persistent across invocations.
"""
import argparse,csv,json,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
from math import isfinite
import requests

START=datetime(2025,9,1,tzinfo=timezone.utc) # warmup before requested test
END=datetime(2026,11,26,tzinfo=timezone.utc)
INTERVALS={"4h":14400,"1h":3600,"15min":900,"5min":300}

def collect(root,budget):
    key=os.getenv("TWELVE_DATA_API_KEY")
    if not key:
        raise RuntimeError("missing API key")
    root.mkdir(parents=True,exist_ok=True)
    remaining=budget
    report=[]
    for interval,seconds in INTERVALS.items():
        # Worst case below 4500 bars per request, including weekends.
        days=min(90,4000*seconds//86400)
        lo=START
        while lo<END:
            hi=min(lo+timedelta(days=days),END)
            path=root/f"{interval}_{lo:%Y%m%d}_{hi:%Y%m%d}.csv"
            if not path.exists() and remaining>0:
                remaining-=1
                try:
                    response=requests.get("https://api.twelvedata.com/time_series",params={
                        "symbol":"XAU/USD","interval":interval,"apikey":key,"timezone":"UTC",
                        "start_date":lo.strftime("%Y-%m-%d %H:%M:%S"),
                        "end_date":hi.strftime("%Y-%m-%d %H:%M:%S"),
                        "outputsize":5000,"format":"JSON"},timeout=40)
                    payload=response.json()
                    if response.status_code!=200 or payload.get("status")=="error" or payload.get("code"):
                        return dict(status="PROVIDER_REJECTED",interval=interval,http=response.status_code,requests_used=budget-remaining)
                    meta=payload.get("meta",{})
                    if meta.get("symbol")!="XAU/USD" or meta.get("interval")!=interval:
                        raise ValueError("metadata")
                    values=payload["values"]
                    if len(values)>=5000:
                        raise ValueError("provider cap")
                    rows={}
                    for raw in values:
                        t=datetime.fromisoformat(raw["datetime"].replace("Z","+00:00"))
                        t=t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)
                        if t==hi: continue
                        if not lo<=t<hi: raise ValueError("out of window")
                        o,h,l,c=(float(raw[k]) for k in ("open","high","low","close"))
                        if not all(isfinite(x) and x>0 for x in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:
                            raise ValueError("invalid OHLC")
                        if t in rows: raise ValueError("duplicate")
                        v=raw.get("volume")
                        if v is not None and (not isfinite(float(v)) or float(v)<0):
                            raise ValueError("invalid volume")
                        rows[t]=[int(t.timestamp())+seconds,o,h,l,c,v]
                    if not rows: raise ValueError("empty window")
                    tmp=path.with_suffix(".tmp")
                    with tmp.open("w",newline="") as f:
                        w=csv.writer(f)
                        w.writerow(["timestamp","open","high","low","close","volume"])
                        w.writerows(rows[t] for t in sorted(rows))
                    tmp.replace(path)
                except Exception as exc:
                    return dict(status="FAILED",interval=interval,error_type=type(exc).__name__,requests_used=budget-remaining)
            report.append(dict(interval=interval,start=lo.isoformat(),end=hi.isoformat(),present=path.exists()))
            lo=hi
    return dict(status="COLLECTED_UNVERIFIED" if all(x["present"] for x in report) else "PARTIAL",
                requests_used=budget-remaining,windows=report,
                limitations=["OHLC only; historical quote, news, volume provenance and session coverage require separate verification"])

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--budget",type=int,default=4)
    a=p.parse_args()
    if not 1<=a.budget<=8: p.error("budget must be 1..8")
    print(json.dumps(collect(a.out,a.budget),indent=2))
