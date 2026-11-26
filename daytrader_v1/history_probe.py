"""Read-only historical capability probe, four requests maximum, no trading.
Reports observed coverage only; does not certify a full year of data.
"""
import os,json
from datetime import datetime,timezone
from math import isfinite
import requests

def probe():
    key=os.getenv("TWELVE_DATA_API_KEY")
    if not key:
        return {"status":"MISSING_KEY"}
    result={}
    # Probe an early historical week, not the latest rolling candles.
    for interval,seconds in (("4h",14400),("1h",3600),("15min",900),("5min",300)):
        try:
            r=requests.get("https://api.twelvedata.com/time_series",params={
                "symbol":"XAU/USD","interval":interval,"apikey":key,"timezone":"UTC",
                "start_date":"2025-11-26 00:00:00","end_date":"2025-12-03 00:00:00",
                "outputsize":2500,"format":"JSON"},timeout=30)
            p=r.json()
            if r.status_code!=200 or p.get("status")=="error" or p.get("code"):
                result[interval]={"status":"PROVIDER_REJECTED","http":r.status_code}
                continue
            meta=p.get("meta",{})
            if meta.get("symbol")!="XAU/USD" or meta.get("interval")!=interval:
                raise ValueError("metadata")
            rows=p["values"]
            stamps=[]
            for x in rows:
                t=datetime.fromisoformat(x["datetime"].replace("Z","+00:00"))
                t=t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)
                o,h,l,c=(float(x[k]) for k in ("open","high","low","close"))
                if not all(isfinite(v) and v>0 for v in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:
                    raise ValueError("OHLC")
                if not datetime(2025,11,26,tzinfo=timezone.utc)<=t<=datetime(2025,12,3,tzinfo=timezone.utc):
                    raise ValueError("range")
                stamps.append(t)
            if not stamps or len(set(stamps))!=len(stamps):
                raise ValueError("empty or duplicate")
            stamps.sort()
            result[interval]=dict(status="SAMPLE_RECEIVED",rows=len(rows),first=stamps[0].isoformat(),
                last=stamps[-1].isoformat(),volume_rows=sum(x.get("volume") is not None for x in rows),
                bid_ask_rows=sum(x.get("bid") is not None and x.get("ask") is not None for x in rows),
                gap_count=sum((b-a).total_seconds()!=seconds for a,b in zip(stamps,stamps[1:])))
        except Exception as exc:
            result[interval]={"status":"FAILED","error_type":type(exc).__name__}
    return dict(status="PROBE_ONLY",intervals=result,limitations=["No full-year coverage check",
        "No verified historical bid/ask, volume type, news or session calendar",
        "No strategy performance calculated"])
if __name__=="__main__":
    print(json.dumps(probe(),indent=2))
