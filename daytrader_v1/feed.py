"""Read-only OHLC adapter. Never substitutes a midpoint for executable bid/ask.
Twelve Data timestamps are treated as UTC bar opens; verify provider contract before use.
"""
import os
from datetime import datetime, timezone
from math import isfinite
import requests
from .engine import PERIODS

INTERVALS = dict(h4="4h", h1="1h", m15="15min", m5="5min")

def fetch_frames(now, api_key=None, http=None, count=320):
    if type(now) is not int or now<=0 or type(count) is not int or not 201<=count<=4998:
        raise ValueError("invalid snapshot parameters")
    key=api_key or os.environ.get("TWELVE_DATA_API_KEY")
    if not key:
        raise RuntimeError("missing Twelve Data API key")
    http=http or requests
    frames={}
    volumes={}
    for tf, interval in INTERVALS.items():
        try:
            response=http.get("https://api.twelvedata.com/time_series",
                params=dict(symbol="XAU/USD",interval=interval,apikey=key,
                            outputsize=count+2,timezone="UTC",format="JSON"),timeout=20)
            response.raise_for_status()
            payload=response.json()
        except (requests.RequestException, ValueError):
            # Do not expose request URLs containing the API key.
            raise RuntimeError("feed request failed: "+tf) from None
        meta=payload.get("meta",{})
        if payload.get("status")=="error" or payload.get("code"):
            raise RuntimeError("provider rejected request: "+tf)
        if meta.get("symbol")!="XAU/USD" or meta.get("interval")!=interval:
            raise ValueError("unexpected provider metadata: "+tf)
        rows=[]
        seen=set()
        for raw in payload["values"]:
            dt=datetime.fromisoformat(raw["datetime"].replace("Z","+00:00"))
            dt=dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
            t=int(dt.timestamp())+PERIODS[tf]
            if t>now:
                continue
            if t in seen:
                raise ValueError("duplicate candle: "+tf)
            seen.add(t)
            o,h,l,c=(float(raw[k]) for k in ("open","high","low","close"))
            if not all(isfinite(x) and x>0 for x in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:
                raise ValueError("invalid candle: "+tf)
            row=dict(timestamp=t,open=o,high=h,low=l,close=c,closed=True)
            if raw.get("volume") is not None:
                v=float(raw["volume"])
                if isfinite(v) and v>=0:
                    row["volume"]=v
            rows.append(row)
        rows=sorted(rows,key=lambda r:r["timestamp"])[-count:]
        if len(rows)<201:
            raise ValueError("insufficient candles: "+tf)
        if now-rows[-1]["timestamp"]>=PERIODS[tf]+60:
            raise ValueError("stale candles: "+tf)
        frames[tf]=rows
        volumes[tf]=all("volume" in r for r in rows)
    return dict(frames=frames,source="Twelve Data XAU/USD",as_of=now,
                volume_present=volumes,volume_kind=None,data_verified=False,
                bid=None,ask=None,quote_time=None,
                blockers=["provider entitlement and timestamp contract not independently verified",
                          "session history and broker price alignment not verified",
                          "executable bid/ask and volume type not supplied"])
