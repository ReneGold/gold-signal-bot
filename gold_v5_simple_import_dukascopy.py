#!/usr/bin/env python3
"""Convert Dukascopy-node CSV (Unix ms, UTC) into audited OHLC CSV for Gold research.
No network access, no orders, and no changes to the running Gold V5 observer.
"""
import argparse,csv,json
from datetime import datetime,timezone
from pathlib import Path

def convert(src,dst,minutes):
    rows=[]
    with open(src,newline="",encoding="utf-8-sig") as f:
        rd=csv.DictReader(f)
        if not {"timestamp","open","high","low","close"}.issubset(rd.fieldnames or []):
            raise ValueError("Expected Dukascopy CSV timestamp,open,high,low,close")
        last=None
        for row in rd:
            raw=int(row["timestamp"])
            if raw < 100000000000: raise ValueError("Expected Unix milliseconds, not seconds")
            when=datetime.fromtimestamp(raw/1000,timezone.utc)
            if when.minute%minutes or when.second or when.microsecond:
                raise ValueError(f"Timestamp not aligned to {minutes}m: {when}")
            if last is not None and when<=last:
                raise ValueError("Nonascending/duplicate timestamp")
            values=[float(row[k]) for k in ("open","high","low","close")]
            o,h,l,c=values
            if min(values)<=0 or l>min(o,c) or h<max(o,c):
                raise ValueError(f"Invalid OHLC at {when}")
            rows.append((when.isoformat(),*values))
            last=when
    if len(rows)<100:raise ValueError("Insufficient bars: fewer than 100")
    dst.parent.mkdir(parents=True,exist_ok=True)
    with open(dst,"w",encoding="utf-8",newline="") as f:
        wr=csv.writer(f);wr.writerow(["timestamp","open","high","low","close"]);wr.writerows(rows)
    return {"candles":len(rows),"first":rows[0][0],"last":rows[-1][0],"timeframe_minutes":minutes}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",type=Path,required=True);p.add_argument("--out",type=Path,required=True);p.add_argument("--minutes",type=int,choices=(15,60),required=True)
    a=p.parse_args()
    print(json.dumps(convert(a.source,a.out,a.minutes),indent=2))
