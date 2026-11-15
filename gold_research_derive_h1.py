#!/usr/bin/env python3
"""Build H1 XAUUSD bars only from complete groups of four 15m bars.

Do not fill missing bars, do not copy flat weekend H1 candles from another feed,
and do not use a partial hour or any future bar. Research-data preparation only.
"""
import argparse,csv,json
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path

def aggregate(rows):
    by_hour=defaultdict(dict)
    seen=set()
    for row in rows:
        t=datetime.fromisoformat(row["timestamp"].replace("Z","+00:00"))
        if t.tzinfo is None or t.utcoffset()!=timedelta(0):
            raise ValueError("timestamps must be UTC")
        if t in seen:raise ValueError("duplicate 15m candle")
        seen.add(t)
        if t.minute not in (0,15,30,45) or t.second or t.microsecond:
            raise ValueError("unexpected 15m candle alignment")
        hour=t.replace(minute=0,second=0,microsecond=0)
        o,h,l,c=(float(row[k]) for k in ("open","high","low","close"))
        if min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c):
            raise ValueError("invalid 15m OHLC")
        by_hour[hour][t.minute]=(o,h,l,c)
    out=[]
    skipped=0
    for hour,quarters in sorted(by_hour.items()):
        if set(quarters)!={0,15,30,45}:
            skipped+=1
            continue
        first=quarters[0]
        last=quarters[45]
        out.append(dict(timestamp=hour.isoformat(),open=first[0],
                        high=max(q[1] for q in quarters.values()),
                        low=min(q[2] for q in quarters.values()),close=last[3]))
    return out,skipped

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bars15",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    with a.bars15.open(newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    h,skipped=aggregate(rows)
    if len(h)<90:raise ValueError("insufficient complete H1 data")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["timestamp","open","high","low","close"])
        w.writeheader();w.writerows(h)
    print(json.dumps({"complete_1h_bars":len(h),"skipped_partial_hours":skipped,
                      "source":"15m bars only; no forward fill"}))

if __name__=="__main__":main()
